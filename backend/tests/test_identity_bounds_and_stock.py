"""审查报告第二轮：F07 路径身份、F08 偏好边界、F09 过期库存。

这三条是「改了一半」的典型：F07 只堵了 body、F09 只改了展示。所以这里的用例
刻意从**写入口**和**消费端**两头断言，而不是只测展示字段。
"""

from datetime import datetime, timedelta

from backend.algorithms.single_recommender import _fridge_status_score
from backend.models import Dish, FridgeInventory


# ---------------------------------------------------------------- F07 路径身份


def test_profile_rejects_header_path_mismatch(client):
    response = client.get("/api/v1/users/2/profile", headers={"X-User-Id": "1"})
    assert response.status_code == 403
    assert "不能操作其他用户的资源" in response.json()["detail"]


def test_preferences_rejects_header_path_mismatch(client):
    response = client.put(
        "/api/v1/users/2/preferences",
        json={"default_budget": 30},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 403


def test_red_black_list_rejects_header_path_mismatch(client):
    response = client.post(
        "/api/v1/users/2/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": 24,
            "list_type": "BLACK",
            "action": "ADD",
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 403


def test_preferences_allowed_when_identity_matches(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"default_budget": 33},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    assert response.json()["default_budget"] == 33


def test_preferences_without_header_is_rejected(client):
    """S01：身份头必填，不再按演示约定回退用户 1。"""
    response = client.put("/api/v1/users/1/preferences", json={"default_budget": 34})
    assert response.status_code == 422


def test_mismatch_does_not_write_other_users_prefs(client):
    before = client.get(
        "/api/v1/users/2/profile", headers={"X-User-Id": "2"}
    ).json()["default_budget"]
    client.put(
        "/api/v1/users/2/preferences",
        json={"default_budget": 99},
        headers={"X-User-Id": "1"},
    )
    after = client.get(
        "/api/v1/users/2/profile", headers={"X-User-Id": "2"}
    ).json()["default_budget"]
    assert after == before


# ---------------------------------------------------------------- F08 偏好边界


def test_preferences_reject_out_of_range_vector(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"base_vector": {"spicy_level": 95}},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422
    assert "0~1" in str(response.json())


def test_preferences_reject_negative_vector(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"base_vector": {"spicy_level": -0.2}},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422


def test_preferences_reject_unknown_vector_key(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"base_vector": {"umami_level": 0.5}},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422
    assert "未知口味维度" in str(response.json())


def test_preferences_reject_negative_budget(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"default_budget": -5},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422


def test_preferences_reject_absurd_budget(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"default_budget": 99999},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422


def test_preferences_accept_valid_payload(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={
            "base_vector": {"spicy_level": 0.9, "oily_level": 0.6},
            "default_budget": 40,
            "veto_tags": ["香菜"],
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["base_vector"]["spicy_level"] == 0.9
    assert body["veto_tags"] == ["香菜"]


def test_preferences_reject_blank_veto_tag(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"veto_tags": ["   "]},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- F09 过期库存


def _expired_row(db, user_id=1, name="牛肉", total_days=2):
    row = FridgeInventory(
        user_id=user_id,
        ingredient_name=name,
        category="肉禽蛋奶",
        quantity_desc="适量",
        expire_days=total_days,
        created_at=datetime.utcnow() - timedelta(days=total_days + 1),
    )
    db.add(row)
    db.commit()
    return row


def test_expired_item_is_reported_as_zero_days_and_not_expiring(client, db):
    """S03：过期只返回 0 天，不再冒充「临期」（临期 = 未过期且 ≤48h）。"""
    _expired_row(db, name="过期牛肉")
    items = client.get(
        "/api/v1/fridge/1", headers={"X-User-Id": "1"}
    ).json()["items"]
    row = next(item for item in items if item["ingredient_name"] == "过期牛肉")
    assert row["expire_days"] == 0
    assert row["is_expiring_soon"] is False


def test_shopping_list_ignores_expired_stock(client, db):
    """过期食材不能算「冰箱里有」，必须进「还要买」。"""
    dish = db.query(Dish).filter(Dish.name == "番茄炒蛋").first()
    db.query(FridgeInventory).filter(FridgeInventory.user_id == 1).delete()
    _expired_row(db, name="鸡蛋", total_days=2)

    payload = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": [dish.id]},
        headers={"X-User-Id": "1"},
    ).json()

    owned = {item["ingredient"] for item in payload["owned_ingredients"]}
    to_buy = {item["ingredient"] for item in payload["to_buy_ingredients"]}
    assert "鸡蛋" not in owned
    assert "鸡蛋" in to_buy


def test_fresh_stock_still_counts_as_owned(client, db):
    dish = db.query(Dish).filter(Dish.name == "番茄炒蛋").first()
    db.query(FridgeInventory).filter(FridgeInventory.user_id == 1).delete()
    db.add(
        FridgeInventory(
            user_id=1,
            ingredient_name="鸡蛋",
            category="肉禽蛋奶",
            quantity_desc="4 个",
            expire_days=5,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()

    payload = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": [dish.id]},
        headers={"X-User-Id": "1"},
    ).json()

    owned = {item["ingredient"] for item in payload["owned_ingredients"]}
    assert "鸡蛋" in owned


def test_expired_stock_does_not_boost_status_score(db):
    """推荐端同口径：过期食材不进 status 分。"""
    dish = db.query(Dish).filter(Dish.name == "番茄炒蛋").first()
    db.query(FridgeInventory).filter(FridgeInventory.user_id == 1).delete()
    db.commit()
    baseline = _fridge_status_score(db, 1, dish)

    _expired_row(db, name="鸡蛋", total_days=2)
    assert _fridge_status_score(db, 1, dish) == baseline

    # 同一种食材没过期时应当加分，证明上面的相等不是因为算法坏了
    db.query(FridgeInventory).filter(FridgeInventory.user_id == 1).delete()
    db.add(
        FridgeInventory(
            user_id=1,
            ingredient_name="鸡蛋",
            category="肉禽蛋奶",
            quantity_desc="4 个",
            expire_days=5,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    assert _fridge_status_score(db, 1, dish) > baseline
