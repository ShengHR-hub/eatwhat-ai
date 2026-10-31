"""S02 真实 HTTP 探针：只读写 S02 隔离库，保护演示库/S10 库/开发源库。

前置：uvicorn 已在 127.0.0.1:8014 启动，DATABASE_URL 指向
backend/eatwhat_s02_r02_iso.db（本脚本会核对演示库哈希前后不变）。
"""

import hashlib
import json
import math
import os
import sqlite3
import sys

import requests

ROOT = "D:/EatWhat"
ISO_DB = os.path.join(ROOT, "backend", "eatwhat_s02_r02_iso.db")
PROTECTED = {
    "demo": os.path.join(ROOT, "backend", "eatwhat.db"),
    "s10_import": os.path.join(ROOT, "backend", "eatwhat_batch4.db"),
    "dev_source": os.path.join(ROOT, "backend", "eatwhat_dev_pre00_r02.db"),
}
BASE = "http://127.0.0.1:8014/api/v1"
H = {"X-User-Id": "1"}
EIGHT_KEYS = {
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
}

steps = []


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def query(sql, params=()):
    con = sqlite3.connect(f"file:{ISO_DB}?mode=ro", uri=True)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def db_write(sql, params=()):
    con = sqlite3.connect(ISO_DB, timeout=5)
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()


def prefs_full(user_id=1):
    raw, budget, veto, cuisines = query(
        "select base_vector, default_budget, veto_tags, preferred_cuisines "
        "from user_preferences where user_id=?",
        (user_id,),
    )[0]
    return {
        "base_vector": json.loads(raw),
        "default_budget": float(budget),
        "veto_tags": json.loads(veto),
        "preferred_cuisines": json.loads(cuisines),
    }


def counts():
    return {
        "user_preferences": query("select count(*) from user_preferences")[0][0],
        "eating_logs": query("select count(*) from eating_logs")[0][0],
        "group_rooms": query("select count(*) from group_rooms")[0][0],
        "room_votes": query("select count(*) from room_votes")[0][0],
        "fridge_inventory": query("select count(*) from fridge_inventory")[0][0],
    }


def prefs(user_id=1):
    raw, budget, veto = query(
        "select base_vector, default_budget, veto_tags from user_preferences where user_id=?",
        (user_id,),
    )[0]
    return {
        "base_vector": json.loads(raw),
        "default_budget": float(budget),
        "veto_tags": json.loads(veto),
    }


def favorites(user_id=1):
    raw = query(
        "select favorite_dish_ids from user_preferences where user_id=?", (user_id,)
    )[0][0]
    return json.loads(raw)


def record(name, response, extra=None):
    item = {
        "name": name,
        "status": response.status_code,
        "body_head": response.text[:300],
    }
    if extra:
        item.update(extra)
    steps.append(item)
    return item


def raw_json(method, path, raw):
    return requests.request(
        method,
        BASE + path,
        data=raw.encode("utf-8"),
        headers={**H, "Content-Type": "application/json"},
        timeout=10,
    )


def check_scores(payload):
    for item in payload["recommendations"]:
        for key, value in item["radar_5d"].items():
            assert math.isfinite(value) and 0.0 <= value <= 100.0, (key, value)
        assert math.isfinite(item["total_score"]) and 0.0 <= item["total_score"] <= 100.0
        assert math.isfinite(item["decay_weight"]) and 0.0 <= item["decay_weight"] <= 1.0
    params = payload["params_used"]
    assert all(math.isfinite(v) for v in params.values())
    total = sum(
        params[k]
        for k in ("alpha_taste", "beta_weather", "gamma_budget", "delta_status")
    )
    assert abs(total - 1.0) <= 1e-3, total


def main():
    assert os.path.exists(ISO_DB), ISO_DB
    healthy = requests.get("http://127.0.0.1:8014/health", timeout=5)
    assert healthy.status_code == 200, healthy.text
    record("health", healthy)

    protected_before = {name: sha256(path) for name, path in PROTECTED.items()}
    iso_before = sha256(ISO_DB)
    counts_before = counts()
    prefs_before = prefs()
    favorites_before = favorites()

    # 1) 合法部分更新：合并后仍八键
    partial = requests.put(
        BASE + "/users/1/preferences",
        json={"base_vector": {"spicy_level": 0.91, "oily_level": 0.61}},
        headers=H,
        timeout=10,
    )
    assert partial.status_code == 200, partial.text
    after_partial = prefs()
    assert set(after_partial["base_vector"]) == EIGHT_KEYS
    assert after_partial["base_vector"]["spicy_level"] == 0.91
    for key in EIGHT_KEYS - {"spicy_level", "oily_level"}:
        assert after_partial["base_vector"][key] == prefs_before["base_vector"][key], key
    record(
        "preferences_partial_merge",
        partial,
        {"stored_keys": sorted(after_partial["base_vector"])},
    )

    # 2) 空对象/布尔/字符串/NaN/Infinity/越界：422 且库内不变
    bad_cases = [
        ("preferences_empty_vector", '{"base_vector":{}}'),
        ("preferences_bool_vector", '{"base_vector":{"spicy_level":true}}'),
        ("preferences_string_vector", '{"base_vector":{"spicy_level":"0.5"}}'),
        ("preferences_nan_vector", '{"base_vector":{"spicy_level":NaN}}'),
        (
            "preferences_infinity_vector",
            '{"base_vector":{"spicy_level":Infinity}}',
        ),
        ("preferences_out_of_range", '{"base_vector":{"spicy_level":1.01}}'),
        ("preferences_unknown_key", '{"base_vector":{"umami_level":0.5}}'),
    ]
    for name, raw in bad_cases:
        response = raw_json("PUT", "/users/1/preferences", raw)
        assert response.status_code == 422, (name, response.status_code, response.text)
        assert prefs() == after_partial, name
        record(name, response, {"db_unchanged": True})

    # 2b) 历史脏向量守卫：预算/忌口/菜系路径同样必须原子失败
    user2_before = prefs_full(2)

    db_write(
        "update user_preferences set base_vector=? where user_id=2",
        (json.dumps({"spicy_level": 95, "oily_level": 0.8}),),
    )
    response = requests.put(
        BASE + "/users/2/preferences",
        json={"default_budget": 31},
        headers={"X-User-Id": "2"},
        timeout=10,
    )
    assert response.status_code == 409, response.text
    assert prefs_full(2) == {
        **user2_before,
        "base_vector": {"spicy_level": 95, "oily_level": 0.8},
    }
    record("history_out_of_range_blocks_budget_only", response, {"db_unchanged": True})

    db_write(
        "update user_preferences set base_vector=? where user_id=2",
        (json.dumps({"spicy_level": 0.5, "umami_level": 0.5}),),
    )
    unknown_before = prefs_full(2)
    response = requests.put(
        BASE + "/users/2/preferences",
        json={"base_vector": {"soup_level": 0.7}},
        headers={"X-User-Id": "2"},
        timeout=10,
    )
    assert response.status_code == 409, response.text
    assert prefs_full(2) == unknown_before
    assert "umami_level" in prefs_full(2)["base_vector"]
    record("history_unknown_key_blocks_vector_update", response, {"db_unchanged": True})

    response = requests.put(
        BASE + "/users/2/preferences",
        json={
            "base_vector": {"spicy_level": 0.4},
            "default_budget": 33,
            "veto_tags": ["香菜"],
            "preferred_cuisines": ["粤菜"],
        },
        headers={"X-User-Id": "2"},
        timeout=10,
    )
    assert response.status_code == 409, response.text
    assert prefs_full(2) == unknown_before
    record("history_unknown_key_blocks_combined_update", response, {"db_unchanged": True})

    db_write(
        "update user_preferences set base_vector=? where user_id=2",
        (json.dumps({"spicy_level": 0.2, "oily_level": 0.8}),),
    )
    response = requests.put(
        BASE + "/users/2/preferences",
        json={"default_budget": 31},
        headers={"X-User-Id": "2"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    filled = prefs_full(2)
    assert set(filled["base_vector"]) == EIGHT_KEYS
    assert filled["base_vector"]["spicy_level"] == 0.2
    assert filled["base_vector"]["oily_level"] == 0.8
    assert all(
        filled["base_vector"][key] == 0.5
        for key in EIGHT_KEYS - {"spicy_level", "oily_level"}
    )
    assert filled["default_budget"] == 31
    record(
        "history_incomplete_valid_filled_on_budget_update",
        response,
        {"base_vector_keys": sorted(filled["base_vector"])},
    )

    vector_before = prefs()["base_vector"]
    response = requests.put(
        BASE + "/users/1/preferences",
        json={"default_budget": 32},
        headers=H,
        timeout=10,
    )
    assert response.status_code == 200, response.text
    assert prefs()["base_vector"] == vector_before
    record("complete_vector_unchanged_on_budget_update", response)

    db_write(
        "update user_preferences set base_vector=?, default_budget=?, "
        "veto_tags=?, preferred_cuisines=? where user_id=2",
        (
            json.dumps(user2_before["base_vector"]),
            user2_before["default_budget"],
            json.dumps(user2_before["veto_tags"]),
            json.dumps(user2_before["preferred_cuisines"]),
        ),
    )
    assert prefs_full(2) == user2_before

    # 3) 推荐：合法边界 + 分数有限/范围正确
    for name, body in [
        ("recommend_budget_0", {"mode_type": "OUT_DINING", "budget": 0, "limit": 5}),
        ("recommend_budget_2000", {"mode_type": "OUT_DINING", "budget": 2000, "limit": 5}),
        ("recommend_weather_min", {"mode_type": "OUT_DINING", "weather_temp": -30, "limit": 5}),
        ("recommend_weather_max", {"mode_type": "OUT_DINING", "weather_temp": 50, "limit": 5}),
        ("recommend_limit_100", {"mode_type": "OUT_DINING", "limit": 100}),
        (
            "recommend_override_bounds",
            {
                "mode_type": "OUT_DINING",
                "override_params": {
                    "lambda_decay": 2.0,
                    "omega_group": 1.0,
                    "alpha_taste": 1.0,
                    "beta_weather": 1.0,
                    "gamma_budget": 1.0,
                    "delta_status": 1.0,
                },
                "limit": 5,
            },
        ),
    ]:
        response = requests.post(BASE + "/recommend/single", json=body, headers=H, timeout=20)
        assert response.status_code == 200, (name, response.text)
        check_scores(response.json())
        record(name, response, {"scores_finite": True})

    # 4) 推荐非法入参：422，不写库
    log_count = counts()["eating_logs"]
    for name, raw in [
        ("recommend_unknown_bubble", '{"mode_type":"OUT_DINING","bubbles":["bogus"]}'),
        ("recommend_bool_budget", '{"mode_type":"OUT_DINING","budget":true}'),
        ("recommend_bool_limit", '{"mode_type":"OUT_DINING","limit":true}'),
        ("recommend_bool_exclude", '{"mode_type":"OUT_DINING","exclude_dish_ids":[true]}'),
        ("recommend_nan_budget", '{"mode_type":"OUT_DINING","budget":NaN}'),
        (
            "recommend_bool_override",
            '{"mode_type":"OUT_DINING","override_params":{"lambda_decay":true}}',
        ),
    ]:
        response = raw_json("POST", "/recommend/single", raw)
        assert response.status_code == 422, (name, response.status_code, response.text)
        assert counts()["eating_logs"] == log_count, name
        record(name, response, {"db_unchanged": True})

    # 5) 天气：NaN/越界 422，合法边界 200
    for name, params in [
        ("weather_nan", {"temp": "nan"}),
        ("weather_inf", {"temp": "Infinity"}),
        ("weather_1000", {"temp": "1000"}),
        ("weather_text_too_long", {"temp": "20", "weather": "x" * 33}),
    ]:
        response = requests.get(BASE + "/context/weather", params=params, timeout=10)
        assert response.status_code == 422, (name, response.status_code, response.text)
        record(name, response)
    for name, params in [
        ("weather_min", {"temp": "-30"}),
        ("weather_max", {"temp": "50"}),
        ("weather_text_32", {"temp": "20", "weather": "晴" * 32}),
    ]:
        response = requests.get(BASE + "/context/weather", params=params, timeout=10)
        assert response.status_code == 200, (name, response.text)
        assert math.isfinite(response.json()["temp"])
        record(name, response)

    # 6) 打卡：非法不写，合法 +1
    dish_id, dish_mode = query(
        "select id, mode_type from dishes_and_recipes order by id limit 1"
    )[0]
    before_logs = counts()["eating_logs"]
    for name, raw in [
        (
            "checkin_bool_dish",
            '{"dish_id":true,"mode_type":"%s"}' % dish_mode,
        ),
        (
            "checkin_bool_cost",
            '{"dish_id":%d,"mode_type":"%s","cost_amount":true}' % (dish_id, dish_mode),
        ),
        (
            "checkin_negative_cost",
            '{"dish_id":%d,"mode_type":"%s","cost_amount":-0.01}'
            % (dish_id, dish_mode),
        ),
        (
            "checkin_unknown_bubble",
            '{"dish_id":%d,"mode_type":"%s","bubbles":["bogus"]}'
            % (dish_id, dish_mode),
        ),
    ]:
        response = raw_json("POST", "/logs/checkin", raw)
        assert response.status_code == 422, (name, response.status_code, response.text)
        assert counts()["eating_logs"] == before_logs, name
        record(name, response, {"db_unchanged": True})

    missing = requests.post(
        BASE + "/logs/checkin",
        json={"dish_id": 99999, "mode_type": "OUT_DINING"},
        headers=H,
        timeout=10,
    )
    assert missing.status_code == 404, missing.text
    assert counts()["eating_logs"] == before_logs
    record("checkin_missing_dish", missing, {"db_unchanged": True})

    valid = requests.post(
        BASE + "/logs/checkin",
        json={"dish_id": dish_id, "mode_type": dish_mode, "cost_amount": 0},
        headers=H,
        timeout=10,
    )
    assert valid.status_code == 200, valid.text
    assert counts()["eating_logs"] == before_logs + 1
    record("checkin_valid_zero_cost", valid, {"logs_delta": 1})

    # 7) 冰箱空白名 422；购物清单部分未知 404
    fridge_before = counts()["fridge_inventory"]
    for name, payload in [
        ("fridge_blank_name", {"ingredient_name": "   "}),
        ("fridge_bool_expire", {"ingredient_name": "鸡蛋", "expire_days": True}),
    ]:
        response = requests.post(BASE + "/fridge/1", json=payload, headers=H, timeout=10)
        assert response.status_code == 422, (name, response.text)
        assert counts()["fridge_inventory"] == fridge_before, name
        record(name, response, {"db_unchanged": True})

    home_dish = query(
        "select id from dishes_and_recipes where mode_type='HOME_COOKING' order by id limit 1"
    )[0][0]
    shopping = requests.post(
        BASE + "/fridge/shopping-list",
        json={"dish_ids": [home_dish, 99999]},
        headers=H,
        timeout=10,
    )
    assert shopping.status_code == 404, shopping.text
    assert "99999" in shopping.text
    record("shopping_list_partial_unknown", shopping)

    # 8) 红黑榜布尔 ID 422，收藏不变
    redblack = raw_json(
        "POST",
        "/users/1/red-black-list",
        '{"target_type":"DISH","target_id":true,"list_type":"FAV","action":"ADD"}',
    )
    assert redblack.status_code == 422, redblack.text
    assert favorites() == favorites_before
    record("redblack_bool_target", redblack, {"db_unchanged": True})

    # 9) 房间布尔数字 422，不建房
    rooms_before = counts()["group_rooms"]
    room_bad = raw_json(
        "POST", "/rooms/create", '{"mode_type":"OUT_DINING","budget":true}'
    )
    assert room_bad.status_code == 422, room_bad.text
    room_override = raw_json(
        "POST",
        "/rooms/create",
        '{"mode_type":"OUT_DINING","override_params":{"omega_group":true}}',
    )
    assert room_override.status_code == 422, room_override.text
    assert counts()["group_rooms"] == rooms_before
    record("room_bool_budget", room_bad, {"db_unchanged": True})
    record("room_bool_override", room_override, {"db_unchanged": True})

    # 10) 收尾：向量完整/有限/范围；受保护库不变
    final_vector = prefs()["base_vector"]
    assert set(final_vector) == EIGHT_KEYS
    assert all(
        math.isfinite(value) and 0.0 <= value <= 1.0
        for value in final_vector.values()
    )
    protected_after = {name: sha256(path) for name, path in PROTECTED.items()}
    result = {
        "base_url": BASE,
        "iso_db": ISO_DB,
        "iso_sha256_before": iso_before,
        "iso_sha256_after": sha256(ISO_DB),
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_before == protected_after,
        "counts_before": counts_before,
        "counts_after": counts(),
        "vector_after": final_vector,
        "vector_eight_keys_finite_in_range": True,
        "steps": steps,
        "passed": protected_before == protected_after,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
