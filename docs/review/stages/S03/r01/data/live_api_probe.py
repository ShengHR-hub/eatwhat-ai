"""S03 真实 HTTP 探针：只读写 S03 隔离副本，保护演示库 / S10 库 / 开发源库。

隔离副本由 `backend/eatwhat_dev_pre00_r02.db` 复制而来；服务在 127.0.0.1:8015
启动，DATABASE_URL 指向该副本。脚本自己拉起/停止 uvicorn，并把服务端输出写到
`logs/20_live_server.log`。

覆盖：
1. 冰箱列表的过期 / 临期 / 新鲜标记；
2. 下厨推荐 status 分与临期双倍；
3. 采购清单已有扣减（过期不抵扣、同名重录）；
4. 跨用户读 / 写 / 删 / 推荐 / 清单消费；
5. 外食推荐不因库存改变结果；
6. 全程无 500。
"""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path("D:/EatWhat")
ISO_DB = ROOT / "backend" / "eatwhat_s03_r01_iso.db"
DEV_DB = ROOT / "backend" / "eatwhat_dev_pre00_r02.db"
OUT = ROOT / "docs" / "review" / "stages" / "S03" / "r01"
LOG = OUT / "logs" / "20_live_server.log"
BASE = "http://127.0.0.1:8015/api/v1"

PROTECTED = {
    "demo": ROOT / "backend" / "eatwhat.db",
    "s10_import": ROOT / "backend" / "eatwhat_batch4.db",
    "dev_source": DEV_DB,
}
EXPECTED_PROTECTED = {
    "demo": "775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b",
    "s10_import": "315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28",
    "dev_source": "b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579",
}

MAINS = ["S03活体甲", "S03活体乙", "S03活体丙", "S03活体丁"]
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

steps = []
status_codes = []
dish_id = None


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def db_exec(sql, params=()):
    con = sqlite3.connect(ISO_DB, timeout=10)
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def db_rows(sql, params=()):
    con = sqlite3.connect(f"file:{ISO_DB}?mode=ro", uri=True)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def counts():
    tables = [
        "users",
        "restaurants",
        "dishes_and_recipes",
        "fridge_inventory",
        "eating_logs",
        "group_rooms",
        "room_votes",
    ]
    return {table: db_rows(f"select count(*) from {table}")[0][0] for table in tables}


def record(name, response, extra=None, expect=None):
    item = {
        "name": name,
        "status": response.status_code,
        "body_head": response.text[:400],
    }
    status_codes.append(response.status_code)
    if extra:
        item.update(extra)
    if expect is not None:
        assert response.status_code == expect, (name, response.status_code, response.text)
    steps.append(item)
    return item


def add_stock(name, expire_days, created_at, user_id=1):
    db_exec(
        "insert into fridge_inventory "
        "(user_id, ingredient_name, category, quantity_desc, expire_days, created_at) "
        "values (?,?,?,?,?,?)",
        (
            user_id,
            name,
            "新鲜果蔬",
            "适量",
            expire_days,
            created_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
        ),
    )


def fridge_items(user_id=1):
    response = requests.get(
        f"{BASE}/fridge/{user_id}", headers={"X-User-Id": str(user_id)}, timeout=10
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def recommend(mode_type, user_id=1, body_extra=None):
    body = {"mode_type": mode_type, "limit": 100, **(body_extra or {})}
    response = requests.post(
        f"{BASE}/recommend/single",
        json=body,
        headers={"X-User-Id": str(user_id)},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response


def status_for(payload, target_id):
    for item in payload["recommendations"]:
        if int(item["dish_id"]) == int(target_id):
            return item["radar_5d"]["status"]
    raise AssertionError(f"recommendations 里没有 dish {target_id}")


def shopping(dish_ids, user_id=1, body_extra=None):
    body = {"dish_ids": list(dish_ids), **(body_extra or {})}
    response = requests.post(
        f"{BASE}/fridge/shopping-list",
        json=body,
        headers={"X-User-Id": str(user_id)},
        timeout=20,
    )
    assert response.status_code == 200, response.text
    return response


def shopping_sets(response):
    payload = response.json()
    owned = {item["ingredient"] for item in payload["owned_ingredients"]}
    to_buy = {item["ingredient"] for item in payload["to_buy_ingredients"]}
    return owned, to_buy


def start_server():
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{ISO_DB.as_posix()}"
    handle = open(LOG, "wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8015",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        if process.poll() is not None:
            handle.close()
            raise RuntimeError(f"uvicorn 提前退出，详见 {LOG}")
        try:
            health = requests.get("http://127.0.0.1:8015/health", timeout=1)
            if health.status_code == 200:
                return process, handle, health
        except requests.RequestException:
            pass
        time.sleep(0.5)
    process.terminate()
    handle.close()
    raise RuntimeError("uvicorn 30 秒内未就绪")


def stop_server(process, handle):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    handle.close()


def main():
    assert ISO_DB.parent.exists()
    shutil.copyfile(DEV_DB, ISO_DB)
    iso_before = sha256(ISO_DB)
    counts_before = counts()
    protected_before = {name: sha256(path) for name, path in PROTECTED.items()}
    assert protected_before == EXPECTED_PROTECTED, protected_before

    # 隔离库前置：清掉 user1 自带库存，建一道 4 主料菜
    db_exec("delete from fridge_inventory where user_id=1")
    dish_id = db_exec(
        "insert into dishes_and_recipes "
        "(name, mode_type, restaurant_id, cuisine_type, dish_role, price_or_cost, "
        "cook_minutes, appliance_tag, ingredients_main, ingredients_aux, recipe_steps, "
        "feature_vector, image_url) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "S03活体菜",
            "HOME_COOKING",
            None,
            "家常菜",
            "ONE_MEAL",
            5.0,
            10,
            json.dumps(["炒锅"], ensure_ascii=False),
            json.dumps(MAINS, ensure_ascii=False),
            json.dumps([], ensure_ascii=False),
            "",
            json.dumps(VECTOR),
            None,
        ),
    )

    process, handle, health = start_server()
    try:
        record("health", health, expect=200)

        # 1) 列表：过期 / 新鲜
        now = utcnow()
        add_stock(MAINS[0], 3, now - timedelta(days=5))  # 过期
        add_stock(MAINS[1], 5, now)  # 新鲜
        items = fridge_items(1)
        by_name = {item["ingredient_name"]: item for item in items}
        assert (by_name[MAINS[0]]["expire_days"], by_name[MAINS[0]]["is_expiring_soon"]) == (0, False)
        assert (by_name[MAINS[1]]["expire_days"], by_name[MAINS[1]]["is_expiring_soon"]) == (5, False)
        record(
            "fridge_list_expired_vs_fresh",
            requests.get(f"{BASE}/fridge/1", headers={"X-User-Id": "1"}, timeout=10),
            {"expired_days": 0, "fresh_days": 5},
            expect=200,
        )

        # 2) 推荐：只有 1/4 主料有效 → 25
        rec = recommend("HOME_COOKING")
        assert status_for(rec.json(), dish_id) == 25.0
        record("recommend_fresh_stock_status_25", rec, {"status": 25.0}, expect=200)

        # 3) 采购清单：过期不抵扣
        buy = shopping([dish_id])
        owned, to_buy = shopping_sets(buy)
        assert owned == {MAINS[1]}, owned
        assert {MAINS[0], MAINS[2], MAINS[3]} <= to_buy, to_buy
        record("shopping_expired_not_owned", buy, {"owned": sorted(owned)}, expect=200)

        # 4) 临期双倍：剩余 0.5 天 → 50
        db_exec(
            "update fridge_inventory set expire_days=?, created_at=? "
            "where user_id=1 and ingredient_name=?",
            (3, (now - timedelta(days=2, hours=12)).strftime("%Y-%m-%d %H:%M:%S.%f"), MAINS[1]),
        )
        items = fridge_items(1)
        soon = next(item for item in items if item["ingredient_name"] == MAINS[1])
        assert (soon["expire_days"], soon["is_expiring_soon"]) == (1, True), soon
        rec = recommend("HOME_COOKING")
        assert status_for(rec.json(), dish_id) == 50.0
        record("recommend_expiring_double_50", rec, {"status": 50.0}, expect=200)

        # 5) 恰好过期：不加分、不抵扣
        db_exec(
            "update fridge_inventory set expire_days=?, created_at=? "
            "where user_id=1 and ingredient_name=?",
            (3, (now - timedelta(days=3, seconds=1)).strftime("%Y-%m-%d %H:%M:%S.%f"), MAINS[1]),
        )
        rec = recommend("HOME_COOKING")
        assert status_for(rec.json(), dish_id) == 0.0
        owned, to_buy = shopping_sets(shopping([dish_id]))
        assert MAINS[1] in to_buy and MAINS[1] not in owned
        record("recommend_expired_status_0", rec, {"status": 0.0}, expect=200)

        # 6) 同名重录：created_at 重置，列表回到 3 天
        first = requests.post(
            f"{BASE}/fridge/1",
            json={"ingredient_name": MAINS[1], "expire_days": 1},
            headers={"X-User-Id": "1"},
            timeout=10,
        )
        record("readd_existing_expire_1", first, expect=200)
        db_exec(
            "update fridge_inventory set created_at=? where user_id=1 and ingredient_name=?",
            ((now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S.%f"), MAINS[1]),
        )
        stale = next(i for i in fridge_items(1) if i["ingredient_name"] == MAINS[1])
        assert stale["expire_days"] == 0

        second = requests.post(
            f"{BASE}/fridge/1",
            json={"ingredient_name": MAINS[1], "expire_days": 3},
            headers={"X-User-Id": "1"},
            timeout=10,
        )
        record("readd_existing_resets_created_at", second, expect=200)
        rows = db_rows(
            "select count(*), expire_days, created_at from fridge_inventory "
            "where user_id=1 and ingredient_name=?",
            (MAINS[1],),
        )
        assert rows[0][0] == 1
        assert rows[0][1] == 3
        created = datetime.fromisoformat(rows[0][2])
        assert abs((utcnow() - created).total_seconds()) <= 30
        fresh = next(i for i in fridge_items(1) if i["ingredient_name"] == MAINS[1])
        assert fresh["expire_days"] == 3

        # 7) expire_days=0 立即过期
        zero = requests.post(
            f"{BASE}/fridge/1",
            json={"ingredient_name": "S03零天", "expire_days": 0},
            headers={"X-User-Id": "1"},
            timeout=10,
        )
        record("add_zero_days_expired", zero, expect=200)
        zero_item = next(i for i in zero.json()["items"] if i["ingredient_name"] == "S03零天")
        assert (zero_item["expire_days"], zero_item["is_expiring_soon"]) == (0, False)

        # 8) 跨用户：读 / 写 / 删 / 推荐 / 清单消费
        add_stock("S03他人特供", 5, utcnow(), user_id=2)
        other_mains = ["S03他人特供", "S03他人配一", "S03他人配二", "S03他人配三"]
        other_dish_id = db_exec(
            "insert into dishes_and_recipes "
            "(name, mode_type, restaurant_id, cuisine_type, dish_role, price_or_cost, "
            "cook_minutes, appliance_tag, ingredients_main, ingredients_aux, recipe_steps, "
            "feature_vector, image_url) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "S03他人活体菜",
                "HOME_COOKING",
                None,
                "家常菜",
                "ONE_MEAL",
                5.0,
                10,
                json.dumps(["炒锅"], ensure_ascii=False),
                json.dumps(other_mains, ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                "",
                json.dumps(VECTOR),
                None,
            ),
        )
        user2_before = db_rows(
            "select ingredient_name, expire_days, created_at from fridge_inventory "
            "where user_id=2 order by id"
        )
        for name, method, path, body in [
            ("cross_user_get", "get", "/fridge/2", None),
            (
                "cross_user_add",
                "post",
                "/fridge/2",
                {"ingredient_name": "S03越权新增"},
            ),
            (
                "cross_user_remove",
                "post",
                "/fridge/2",
                {"ingredient_name": "S03他人特供", "action": "REMOVE"},
            ),
        ]:
            response = requests.request(
                method,
                BASE + path,
                json=body,
                headers={"X-User-Id": "1"},
                timeout=10,
            )
            record(name, response, expect=403)
        user2_after = db_rows(
            "select ingredient_name, expire_days, created_at from fridge_inventory "
            "where user_id=2 order by id"
        )
        assert user2_after == user2_before

        spoof = recommend("HOME_COOKING", 1, {"user_id": 2})
        as_user_1 = recommend("HOME_COOKING", 1)
        as_user_2 = recommend("HOME_COOKING", 2)
        assert spoof.json() == as_user_1.json()
        assert status_for(spoof.json(), other_dish_id) == 0.0
        assert status_for(as_user_2.json(), other_dish_id) == 25.0
        record("cross_user_recommend_header_wins", spoof, {"status": 0.0}, expect=200)

        spoof_list = shopping([other_dish_id], 1, {"user_id": 2})
        as_user_1_list = shopping([other_dish_id], 1)
        as_user_2_list = shopping([other_dish_id], 2)
        assert spoof_list.json() == as_user_1_list.json()
        assert "S03他人特供" in shopping_sets(spoof_list)[1]
        assert "S03他人特供" in shopping_sets(as_user_2_list)[0]
        record("cross_user_shopping_header_wins", spoof_list, expect=200)
        assert user2_after == user2_before

        # 9) 外食推荐不受库存影响
        before_out = recommend("OUT_DINING", 1).json()
        add_stock("S03外食无关", 5, utcnow())
        after_out = recommend("OUT_DINING", 1).json()
        before_pairs = [(i["dish_id"], i["radar_5d"]["status"]) for i in before_out["recommendations"]]
        after_pairs = [(i["dish_id"], i["radar_5d"]["status"]) for i in after_out["recommendations"]]
        assert before_pairs == after_pairs
        record(
            "out_dining_unaffected_by_stock",
            recommend("OUT_DINING", 1),
            {"same_ids_and_status": True},
            expect=200,
        )

        # 10) 全程无 500
        assert all(code < 500 for code in status_codes), status_codes
    finally:
        stop_server(process, handle)

    iso_after = sha256(ISO_DB)
    counts_after = counts()
    protected_after = {name: sha256(path) for name, path in PROTECTED.items()}
    assert protected_after == protected_before == EXPECTED_PROTECTED

    result = {
        "base_url": "http://127.0.0.1:8015",
        "iso_db": str(ISO_DB),
        "iso_source": str(DEV_DB),
        "iso_sha256_before": iso_before,
        "iso_sha256_after": iso_after,
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_before == protected_after,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "status_codes": sorted(set(status_codes)),
        "no_500": all(code < 500 for code in status_codes),
        "steps": steps,
        "passed": True,
    }
    (OUT / "data" / "live_api_probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "steps"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
