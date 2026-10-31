"""S03 / F09：冰箱时效与采购闭环。

口径由用户 2026-10-26 裁决（1A/2A/3B），已同步 MASTER_SPEC：

* `expire_days` 是入库时的保质期；到期时刻 = `created_at + expire_days × 24h`，
  统一按 UTC 绝对时间计算，DST 不改变结果；`now >= 到期时刻` 即过期。
* 过期返回 0 天；未过期剩余天数向上取整，最小 1 天
  （实际剩余 2.4 天显示 3 天，剩余 0.5 天显示 1 天）。
* 临期 = 未过期且实际剩余 ≤ 48h，因此 `remaining_days <= 2` 与「≤48h」严格等价；
  过期项不再计入临期。
* 同名食材再次 ADD 视为重新入库：覆盖属性并把 `created_at` 重置为当前时间。
* 冰箱列表、下厨推荐、采购清单、组合采购共用同一时钟；外食推荐不读取冰箱。

本文件刻意用固定时钟与手算期望值，不调用被测函数生成自己的期望。
"""

import math
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from backend.algorithms import fridge_clock
from backend.algorithms.combo_optimizer import build_shopping_list
from backend.algorithms.single_recommender import recommend_single
from backend.models import Dish, FridgeInventory

NOW = datetime(2026, 10, 26, 12, 0, 0)
SECONDS_PER_DAY = 86400

VECTOR = {
    "spicy_level": 0.3,
    "oily_level": 0.3,
    "soup_level": 0.3,
    "temp_fit": 0.5,
    "satiety_level": 0.5,
    "prep_speed": 0.5,
    "social_fit": 0.5,
    "comfort_level": 0.5,
}


@pytest.fixture()
def frozen_now(monkeypatch):
    """让所有消费端（展示/推荐/清单）共用同一个固定时钟。"""
    monkeypatch.setattr(fridge_clock, "now_utc", lambda: NOW)
    return NOW


def _row(name, expire_days=3, created_at=None, user_id=1):
    return FridgeInventory(
        user_id=user_id,
        ingredient_name=name,
        category="新鲜果蔬",
        quantity_desc="适量",
        expire_days=expire_days,
        created_at=NOW if created_at is None else created_at,
    )


def _clock_row(expire_days=3, elapsed_seconds=0):
    return _row(
        "时钟测试",
        expire_days,
        NOW - timedelta(seconds=elapsed_seconds),
    )


def _reset_stock(db, user_id=1):
    db.query(FridgeInventory).filter(FridgeInventory.user_id == user_id).delete()
    db.commit()


def _add_dish(db, name, mains, aux=(), price=10.0):
    dish = Dish(
        name=name,
        mode_type="HOME_COOKING",
        restaurant_id=None,
        cuisine_type="家常菜",
        dish_role="ONE_MEAL",
        price_or_cost=price,
        cook_minutes=10,
        appliance_tag=["炒锅"],
        ingredients_main=list(mains),
        ingredients_aux=list(aux),
        recipe_steps="",
        feature_vector=dict(VECTOR),
        image_url=None,
    )
    db.add(dish)
    db.commit()
    return dish


def _status_of(payload, dish_id):
    for item in payload["recommendations"]:
        if int(item["dish_id"]) == int(dish_id):
            return item
    raise AssertionError(f"推荐结果里没有 dish {dish_id}")


def _shopping(client, dish_ids, user_id=1):
    response = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": list(dish_ids)},
        headers={"X-User-Id": str(user_id)},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _sets(payload):
    owned = {item["ingredient"] for item in payload["owned_ingredients"]}
    to_buy = {item["ingredient"] for item in payload["to_buy_ingredients"]}
    return owned, to_buy


# --------------------------------------------------------------------------
# 1. 纯时钟：到期前 / 到期 / 到期后 / 取整 / 时区与 DST
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expire_days,elapsed_seconds,days,expired,soon",
    [
        # 入库即开始；剩余 3 天 > 48h，不临期
        (3, 0, 3, False, False),
        # 剩余 2.4 天 → 向上取整 3 天（用户裁决的示例）
        (3, int(0.6 * SECONDS_PER_DAY), 3, False, False),
        # 恰好剩余 48h：临期下界（含）
        (3, 1 * SECONDS_PER_DAY, 2, False, True),
        (3, int(1.5 * SECONDS_PER_DAY), 2, False, True),
        # 剩余 0.6 天 → 1 天
        (3, int(2.4 * SECONDS_PER_DAY), 1, False, True),
        # F09 原缺陷点：剩余 0.5 天曾被 round 成 0 并提前判过期
        (3, int(2.5 * SECONDS_PER_DAY), 1, False, True),
        # 到期前 1 秒
        (3, 3 * SECONDS_PER_DAY - 1, 1, False, True),
        # 恰好到期即过期
        (3, 3 * SECONDS_PER_DAY, 0, True, False),
        (3, 3 * SECONDS_PER_DAY + 1, 0, True, False),
        (1, 0, 1, False, True),
        # 保质期 0 天：入库即到期
        (0, 0, 0, True, False),
        # 缺省 3 天
        (None, 0, 3, False, False),
        # 脏数据负数按 0 处理
        (-2, 0, 0, True, False),
    ],
)
def test_clock_boundary_matrix(expire_days, elapsed_seconds, days, expired, soon):
    row = _clock_row(expire_days, elapsed_seconds)
    assert fridge_clock.is_expired(row, NOW) is expired
    assert fridge_clock.remaining_days(row, NOW) == days
    assert fridge_clock.is_expiring_soon(row, NOW) is soon


def test_clock_invariants_hold_across_sweep():
    """边界等价关系：0 天 ⇔ 过期；≤2 天 ⇔ 实际剩余 ≤48h。"""
    for elapsed in range(-3600, 4 * SECONDS_PER_DAY + 7200, 1800):
        row = _clock_row(3, elapsed)
        actual = 3 * SECONDS_PER_DAY - elapsed
        expired = fridge_clock.is_expired(row, NOW)
        days = fridge_clock.remaining_days(row, NOW)
        soon = fridge_clock.is_expiring_soon(row, NOW)

        assert expired == (actual <= 0), elapsed
        assert days == (0 if actual <= 0 else math.ceil(actual / SECONDS_PER_DAY))
        assert soon == (0 < actual <= 2 * SECONDS_PER_DAY), elapsed
        assert soon == ((not expired) and days <= 2), elapsed


def test_clock_uses_absolute_utc_instants_across_dst_offsets():
    """同一 UTC 时刻换不同时区/夏令时偏移，结论必须一致。"""
    created = datetime(2026, 10, 30, 5, 30, 0)  # naive UTC
    row = _row("时区边界", 2, created)
    expiry = created + timedelta(days=2)  # 2026-11-01 05:30 UTC

    # 美国 2026-11-01 回拨日：01:30 -04:00 与 01:30 -05:00
    fall_back_edt = datetime(2026, 11, 1, 1, 30, tzinfo=timezone(timedelta(hours=-4)))
    fall_back_est = datetime(2026, 11, 1, 1, 30, tzinfo=timezone(timedelta(hours=-5)))
    assert fall_back_edt.astimezone(timezone.utc).replace(tzinfo=None) == expiry
    assert fridge_clock.is_expired(row, fall_back_edt) is True
    assert fridge_clock.is_expired(row, fall_back_est) is True

    # Asia/Shanghai (+08:00) 同一时刻
    shanghai = datetime(2026, 11, 1, 13, 30, tzinfo=timezone(timedelta(hours=8)))
    assert fridge_clock.is_expired(row, shanghai) is True

    # 到期前 1 秒 / 到期时刻：naive UTC 与 aware 写法一致
    assert fridge_clock.remaining_days(row, expiry - timedelta(seconds=1)) == 1
    assert fridge_clock.is_expired(row, expiry - timedelta(seconds=1)) is False
    assert fridge_clock.remaining_days(row, expiry) == 0

    # 美国 2026-03-08 春进日：两个不同偏移表达同一 UTC 时刻，结果一致
    spring_a = datetime(2026, 3, 8, 1, 30, tzinfo=timezone(timedelta(hours=-5)))  # 06:30Z
    spring_b = datetime(2026, 3, 8, 14, 30, tzinfo=timezone(timedelta(hours=8)))  # 06:30Z
    for when in (spring_a, spring_b):
        assert fridge_clock.remaining_days(row, when) == fridge_clock.remaining_days(
            row, spring_a
        )
        assert fridge_clock.is_expired(row, when) is fridge_clock.is_expired(
            row, spring_a
        )


def test_clock_missing_created_at_counts_from_now():
    row = _row("缺入库时间", 3, created_at=None)
    assert fridge_clock.is_expired(row, NOW) is False
    assert fridge_clock.remaining_days(row, NOW) == 3


# --------------------------------------------------------------------------
# 2. 冰箱列表：过期不计临期、仍可查看/删除
# --------------------------------------------------------------------------


def test_fridge_list_flags_and_order_with_fixed_clock(client, db, frozen_now):
    _reset_stock(db)
    db.add_all(
        [
            _row("新鲜蔬菜", 5, NOW),
            _row("临期鸡蛋", 3, NOW - timedelta(days=1)),
            _row("边界牛肉", 3, NOW - timedelta(days=3) + timedelta(seconds=1)),
            _row("过期豆腐", 3, NOW - timedelta(days=3)),
            _row("过期一月", 3, NOW - timedelta(days=30)),
        ]
    )
    db.commit()

    response = client.get("/api/v1/fridge/1", headers={"X-User-Id": "1"})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    by_name = {item["ingredient_name"]: item for item in items}

    assert len(items) == 5
    assert (by_name["新鲜蔬菜"]["expire_days"], by_name["新鲜蔬菜"]["is_expiring_soon"]) == (5, False)
    assert (by_name["临期鸡蛋"]["expire_days"], by_name["临期鸡蛋"]["is_expiring_soon"]) == (2, True)
    assert (by_name["边界牛肉"]["expire_days"], by_name["边界牛肉"]["is_expiring_soon"]) == (1, True)
    assert (by_name["过期豆腐"]["expire_days"], by_name["过期豆腐"]["is_expiring_soon"]) == (0, False)
    assert (by_name["过期一月"]["expire_days"], by_name["过期一月"]["is_expiring_soon"]) == (0, False)

    # 临期置顶；过期项仍在列表里，但不带临期标记
    assert [item["expire_days"] for item in items] == [1, 2, 0, 0, 5]
    assert [item["ingredient_name"] for item in items[:2]] == ["边界牛肉", "临期鸡蛋"]


def test_expired_item_is_visible_and_removable(client, db, frozen_now):
    _reset_stock(db)
    db.add(_row("过期可删", 1, NOW - timedelta(days=5)))
    db.commit()

    items = client.get("/api/v1/fridge/1", headers={"X-User-Id": "1"}).json()["items"]
    assert [item["ingredient_name"] for item in items] == ["过期可删"]
    assert items[0]["expire_days"] == 0
    assert items[0]["is_expiring_soon"] is False

    response = client.post(
        "/api/v1/fridge/1",
        json={"ingredient_name": "过期可删", "action": "REMOVE"},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


# --------------------------------------------------------------------------
# 3. 四处同口径：列表 / 下厨推荐 / 采购清单 / 组合采购
# --------------------------------------------------------------------------


def test_expired_stock_consistent_across_all_consumers(client, db, frozen_now):
    _reset_stock(db)
    dish = _add_dish(
        db, "S03一致菜", ["S03主料甲", "S03主料乙", "S03主料丙", "S03主料丁"]
    )
    db.add_all(
        [
            _row("S03主料甲", 2, NOW - timedelta(days=3)),  # 过期
            _row("S03主料乙", 5, NOW),  # 有效
        ]
    )
    db.commit()

    # 冰箱列表
    items = client.get("/api/v1/fridge/1", headers={"X-User-Id": "1"}).json()["items"]
    by_name = {item["ingredient_name"]: item for item in items}
    assert (by_name["S03主料甲"]["expire_days"], by_name["S03主料甲"]["is_expiring_soon"]) == (0, False)
    assert (by_name["S03主料乙"]["expire_days"], by_name["S03主料乙"]["is_expiring_soon"]) == (5, False)

    # 下厨推荐：只有 4 个主料中的 1 个有效命中 → 100 × 1/4
    rec = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert rec.status_code == 200, rec.text
    assert _status_of(rec.json(), dish.id)["radar_5d"]["status"] == 25.0

    # 采购清单（API）
    api_payload = _shopping(client, [dish.id])
    owned, to_buy = _sets(api_payload)
    assert "S03主料乙" in owned
    assert "S03主料甲" in to_buy
    assert owned.isdisjoint(to_buy)

    # 组合采购（算法侧同一实现）
    combo_payload = build_shopping_list(db, 1, [dish.id], now=NOW)
    assert set(combo_payload["owned_ingredients"]) == owned
    assert set(combo_payload["to_buy_ingredients"]) == to_buy


def test_status_score_uses_exact_clock_and_double_weight(client, db, frozen_now):
    _reset_stock(db)
    dish = _add_dish(db, "S03权重菜", ["S03甲", "S03乙", "S03丙", "S03丁"])

    def status_with(rows):
        _reset_stock(db)
        db.add_all(rows)
        db.commit()
        payload = client.post(
            "/api/v1/recommend/single",
            json={"mode_type": "HOME_COOKING", "limit": 100},
            headers={"X-User-Id": "1"},
        )
        assert payload.status_code == 200, payload.text
        return _status_of(payload.json(), dish.id)["radar_5d"]["status"]

    assert status_with([_row("S03甲", 5, NOW)]) == 25.0
    # 剩余 0.5 天仍算有效，且临期双倍：100 × 2/4
    assert status_with([_row("S03甲", 3, NOW - timedelta(days=2, hours=12))]) == 50.0
    # 恰好到期：不加分
    assert status_with([_row("S03甲", 3, NOW - timedelta(days=3))]) == 0.0
    # 剩余 48h 整：临期双倍
    assert status_with([_row("S03甲", 3, NOW - timedelta(days=1))]) == 50.0
    # 剩余 48h + 1 秒：不双倍
    assert (
        status_with([_row("S03甲", 3, NOW - timedelta(days=1, seconds=-1))])
        == 25.0
    )


def test_expiring_stock_ranks_above_fresh_stock(client, db, frozen_now):
    _reset_stock(db)
    expiring = _add_dish(db, "S03临期菜", ["S03临甲", "S03临乙", "S03临丙", "S03临丁"])
    fresh = _add_dish(db, "S03新鲜菜", ["S03鲜甲", "S03鲜乙", "S03鲜丙", "S03鲜丁"])
    db.add_all(
        [
            _row("S03临甲", 3, NOW - timedelta(days=2)),  # 剩余 1 天，双倍
            _row("S03鲜甲", 5, NOW),  # 剩余 5 天，正常
        ]
    )
    db.commit()

    payload = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert payload.status_code == 200, payload.text
    result = payload.json()
    expiring_item = _status_of(result, expiring.id)
    fresh_item = _status_of(result, fresh.id)
    assert expiring_item["radar_5d"]["status"] == 50.0
    assert fresh_item["radar_5d"]["status"] == 25.0
    assert expiring_item["total_score"] > fresh_item["total_score"]
    order = [int(item["dish_id"]) for item in result["recommendations"]]
    assert order.index(expiring.id) < order.index(fresh.id)


def test_home_cooking_without_mains_or_stock_scores_zero(client, db, frozen_now):
    _reset_stock(db)
    no_mains = _add_dish(db, "S03无主料", [], aux=["S03辅料"])
    missing = _add_dish(db, "S03全缺料", ["S03缺甲", "S03缺乙", "S03缺丙", "S03缺丁"])
    db.commit()

    payload = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert payload.status_code == 200, payload.text
    result = payload.json()
    assert _status_of(result, no_mains.id)["radar_5d"]["status"] == 0.0
    assert _status_of(result, missing.id)["radar_5d"]["status"] == 0.0

    owned, to_buy = _sets(_shopping(client, [no_mains.id, missing.id]))
    assert owned == set()
    assert {"S03辅料", "S03缺甲", "S03缺乙", "S03缺丙", "S03缺丁"} <= to_buy


# --------------------------------------------------------------------------
# 4. 采购清单：合并、去重、已有扣减、多余库存
# --------------------------------------------------------------------------


def test_shopping_list_merges_dedupes_and_subtracts_valid_stock(client, db, frozen_now):
    _reset_stock(db)
    first = _add_dish(db, "S03清单一", ["S03番茄", "S03鸡蛋"], aux=["S03葱"])
    second = _add_dish(db, "S03清单二", ["S03鸡蛋", "S03豆腐"], aux=["S03葱"])
    db.add_all(
        [
            _row("S03鸡蛋", 5, NOW),  # 有效 → 已有
            _row("S03番茄", 2, NOW - timedelta(days=3)),  # 过期 → 仍要买
            _row("S03多余", 5, NOW),  # 不在任何菜谱里 → 不出现
        ]
    )
    db.commit()

    payload = _shopping(client, [first.id, first.id, second.id])
    owned, to_buy = _sets(payload)
    assert owned == {"S03鸡蛋"}
    assert to_buy == {"S03番茄", "S03豆腐", "S03葱"}
    assert "S03多余" not in owned | to_buy
    assert owned.isdisjoint(to_buy)

    used_by = {
        item["ingredient"]: item["used_by"]
        for item in payload["owned_ingredients"] + payload["to_buy_ingredients"]
    }
    assert used_by["S03鸡蛋"] == ["S03清单一", "S03清单二"]
    assert used_by["S03葱"] == ["S03清单一", "S03清单二"]
    # 重复 dish_id 不能让 used_by 重复
    assert used_by["S03鸡蛋"].count("S03清单一") == 1
    # 需求最多的排前面
    assert payload["to_buy_ingredients"][0]["ingredient"] == "S03葱"

    combo = build_shopping_list(db, 1, [first.id, second.id], now=NOW)
    assert set(combo["owned_ingredients"]) == owned
    assert set(combo["to_buy_ingredients"]) == to_buy


def test_shopping_list_quantity_desc_is_descriptive_not_deducted(client, db, frozen_now):
    """SSOT 的库存只有自由文本 quantity_desc；本步不发明数量/单位扣减规则。"""
    _reset_stock(db)
    dish = _add_dish(db, "S03单位菜", ["S03单位料", "S03单位配一"])
    response = client.post(
        "/api/v1/fridge/1",
        json={
            "ingredient_name": "S03单位料",
            "quantity_desc": "半个",
            "expire_days": 5,
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["items"] if i["ingredient_name"] == "S03单位料")
    assert item["quantity_desc"] == "半个"

    owned, to_buy = _sets(_shopping(client, [dish.id]))
    # 有有效库存即视为已有，不按「半个 / 2 个」做算术语义推断
    assert "S03单位料" in owned
    assert "S03单位料" not in to_buy
    assert "S03单位配一" in to_buy

    row = db.query(FridgeInventory).filter_by(user_id=1, ingredient_name="S03单位料").one()
    assert row.quantity_desc == "半个"


def test_shopping_list_duplicate_same_name_rows_one_valid_is_owned(client, db, frozen_now):
    _reset_stock(db)
    dish = _add_dish(db, "S03同名菜", ["S03双鸡蛋", "S03配菜", "S03配菜二", "S03配菜三"])
    db.add_all(
        [
            _row("S03双鸡蛋", 1, NOW - timedelta(days=5)),  # 旧行已过期
            _row("S03双鸡蛋", 5, NOW - timedelta(days=1)),  # 新行有效且非临期
        ]
    )
    db.commit()

    # 历史重复行保留：列表里两条都在
    items = client.get("/api/v1/fridge/1", headers={"X-User-Id": "1"}).json()["items"]
    same_name = [item for item in items if item["ingredient_name"] == "S03双鸡蛋"]
    assert len(same_name) == 2
    assert sorted(item["expire_days"] for item in same_name) == [0, 4]

    owned, to_buy = _sets(_shopping(client, [dish.id]))
    assert "S03双鸡蛋" in owned
    assert "S03双鸡蛋" not in to_buy

    # 推荐只按有效那条命中一次（普通权重 1/4），不会因重复行叠加
    payload = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert _status_of(payload.json(), dish.id)["radar_5d"]["status"] == 25.0


# --------------------------------------------------------------------------
# 5. 增删改查闭环 + 同名重录
# --------------------------------------------------------------------------


def test_fridge_crud_loop_and_readd_resets_created_at(client, db, frozen_now):
    _reset_stock(db)
    dish = _add_dish(db, "S03闭环菜", ["S03闭环料", "S03配一", "S03配二", "S03配三"])

    added = client.post(
        "/api/v1/fridge/1",
        json={"ingredient_name": "S03闭环料", "expire_days": 5},
        headers={"X-User-Id": "1"},
    )
    assert added.status_code == 200, added.text
    assert _sets(_shopping(client, [dish.id]))[0] == {"S03闭环料"}

    row = db.query(FridgeInventory).filter_by(user_id=1, ingredient_name="S03闭环料").one()
    row.created_at = NOW - timedelta(days=10)  # 人为放旧，模拟过期
    db.commit()
    items = client.get("/api/v1/fridge/1", headers={"X-User-Id": "1"}).json()["items"]
    assert next(i for i in items if i["ingredient_name"] == "S03闭环料")["expire_days"] == 0
    assert _sets(_shopping(client, [dish.id]))[0] == set()

    # 同名再次 ADD：重新入库，created_at 重置，属性覆盖
    readded = client.post(
        "/api/v1/fridge/1",
        json={"ingredient_name": "S03闭环料", "expire_days": 3, "quantity_desc": "1 份"},
        headers={"X-User-Id": "1"},
    )
    assert readded.status_code == 200, readded.text
    rows = db.query(FridgeInventory).filter_by(user_id=1, ingredient_name="S03闭环料").all()
    assert len(rows) == 1
    assert rows[0].created_at == NOW
    assert rows[0].expire_days == 3
    assert rows[0].quantity_desc == "1 份"

    items = client.get("/api/v1/fridge/1", headers={"X-User-Id": "1"}).json()["items"]
    assert next(i for i in items if i["ingredient_name"] == "S03闭环料")["expire_days"] == 3

    # 删除后：列表消失、推荐回落、清单改为待买
    removed = client.post(
        "/api/v1/fridge/1",
        json={"ingredient_name": "S03闭环料", "action": "REMOVE"},
        headers={"X-User-Id": "1"},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["items"] == []
    assert _sets(_shopping(client, [dish.id]))[0] == set()
    assert "S03闭环料" in _sets(_shopping(client, [dish.id]))[1]

    rec = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert _status_of(rec.json(), dish.id)["radar_5d"]["status"] == 0.0


def test_zero_expire_days_is_expired_everywhere(client, db, frozen_now):
    _reset_stock(db)
    dish = _add_dish(db, "S03零天菜", ["S03零天料", "S03零配一", "S03零配二", "S03零配三"])

    response = client.post(
        "/api/v1/fridge/1",
        json={"ingredient_name": "S03零天料", "expire_days": 0},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["items"] if i["ingredient_name"] == "S03零天料")
    assert (item["expire_days"], item["is_expiring_soon"]) == (0, False)

    owned, to_buy = _sets(_shopping(client, [dish.id]))
    assert "S03零天料" not in owned
    assert "S03零天料" in to_buy

    rec = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert _status_of(rec.json(), dish.id)["radar_5d"]["status"] == 0.0


# --------------------------------------------------------------------------
# 6. 跨用户隔离：读、写、删、推荐、清单消费
# --------------------------------------------------------------------------


def test_cross_user_cannot_read_update_delete_or_consume_fridge(client, db, frozen_now):
    _reset_stock(db, user_id=2)
    db.add(_row("S03他人特供", 5, NOW, user_id=2))
    db.commit()

    dish = _add_dish(db, "S03他人菜", ["S03他人特供", "S03他人配一", "S03他人配二", "S03他人配三"])

    def snapshot():
        return [
            (row.ingredient_name, row.expire_days, row.created_at)
            for row in db.query(FridgeInventory)
            .filter(FridgeInventory.user_id == 2)
            .order_by(FridgeInventory.id)
            .all()
        ]

    before = snapshot()

    assert client.get("/api/v1/fridge/2", headers={"X-User-Id": "1"}).status_code == 403
    assert (
        client.post(
            "/api/v1/fridge/2",
            json={"ingredient_name": "S03越权新增"},
            headers={"X-User-Id": "1"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/fridge/2",
            json={"ingredient_name": "S03他人特供", "action": "REMOVE"},
            headers={"X-User-Id": "1"},
        ).status_code
        == 403
    )
    assert snapshot() == before

    # 推荐：body 里塞 user_id=2 也必须按请求头算 user 1（拿不到别人的库存加分）
    spoofed = client.post(
        "/api/v1/recommend/single",
        json={"user_id": 2, "mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    as_user_1 = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    as_user_2 = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "limit": 100},
        headers={"X-User-Id": "2"},
    )
    assert spoofed.status_code == as_user_1.status_code == as_user_2.status_code == 200
    assert spoofed.json() == as_user_1.json()
    assert _status_of(spoofed.json(), dish.id)["radar_5d"]["status"] == 0.0
    assert _status_of(as_user_2.json(), dish.id)["radar_5d"]["status"] == 25.0

    # 采购清单：body user_id=2 + 请求头 1 → 只用 user 1 的冰箱
    spoofed_list = client.post(
        "/api/v1/fridge/shopping-list",
        json={"user_id": 2, "dish_ids": [dish.id]},
        headers={"X-User-Id": "1"},
    )
    as_user_1_list = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": [dish.id]},
        headers={"X-User-Id": "1"},
    )
    as_user_2_list = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": [dish.id]},
        headers={"X-User-Id": "2"},
    )
    assert spoofed_list.status_code == as_user_1_list.status_code == 200
    assert spoofed_list.json() == as_user_1_list.json()
    assert "S03他人特供" in _sets(spoofed_list.json())[1]
    assert "S03他人特供" in _sets(as_user_2_list.json())[0]
    assert snapshot() == before


# --------------------------------------------------------------------------
# 7. 外食推荐不读取冰箱
# --------------------------------------------------------------------------


def test_out_dining_does_not_read_fridge(client, db, session_factory, frozen_now):
    _reset_stock(db)
    as_user_1 = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 20},
        headers={"X-User-Id": "1"},
    )
    assert as_user_1.status_code == 200, as_user_1.text

    db.add(_row("S03外食无关", 5, NOW))
    db.commit()

    with_stock = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 20},
        headers={"X-User-Id": "1"},
    )
    assert with_stock.status_code == 200, with_stock.text
    assert with_stock.json() == as_user_1.json()

    statements = []
    engine = session_factory.kw["bind"]

    def _before(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    session = session_factory()
    try:
        recommend_single(session, 1, "OUT_DINING", limit=20)
    finally:
        session.close()
        event.remove(engine, "before_cursor_execute", _before)

    assert not [s for s in statements if "fridge_inventory" in s.lower()]
