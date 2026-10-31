import pytest

from backend.models import AlgoConfig, Dish, Restaurant, User


def test_seed_data_volume(db):
    assert db.query(Restaurant).count() == 20
    assert db.query(Dish).count() == 100
    assert db.query(Dish).filter(Dish.mode_type == "OUT_DINING").count() == 60
    assert db.query(Dish).filter(Dish.mode_type == "HOME_COOKING").count() == 40
    assert db.query(User).filter(User.is_demo_persona.is_(True)).count() == 4
    config = (
        db.query(AlgoConfig)
        .filter(AlgoConfig.config_name == "default_production")
        .first()
    )
    assert config is not None
    benchmark = config.benchmark_json
    # 结构锁定：SSOT 第三章。键名与长度都必须与规格一致，且不许残留手写曲线
    assert set(benchmark) == {
        "generated_at",
        "sample",
        "duplication_rate_curve",
        "group_satisfaction_bars",
    }
    curve = benchmark["duplication_rate_curve"]
    assert len(curve["days"]) == 14
    assert len(curve["ours_lambda_0.5"]) == 14
    assert len(curve["baseline_no_decay"]) == 14
    bars = benchmark["group_satisfaction_bars"]
    assert len(bars["strategies"]) == 3
    assert len(bars["avg_scores"]) == 3
    assert len(bars["least_misery_scores"]) == 3
    assert all(0 <= v <= 100 for v in bars["avg_scores"] + bars["least_misery_scores"])
    assert benchmark["sample"]["personas"] == 200
    assert benchmark["sample"]["meals_per_day"] == 2


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "2.3.2"


def test_demo_list(client):
    response = client.get("/api/v1/users/demo-list")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 4
    titles = {user["persona_title"] for user in users}
    assert "川渝麻辣派" in titles
    assert "广府清淡爱汤派" in titles


def test_login_validates_payload(client):
    """v2.3.6 恢复本地账号登录（§30 管理鉴权需要真实 token）。

    这条用例原本断言 /auth/login 已下架，路由恢复后语义变了：
    现在验的是「缺密码 422、未知账号 401」，而不是 404/405。
    """
    assert client.post("/api/v1/auth/login", json={"username": "chuan_yu"}).status_code == 422
    assert client.post(
        "/api/v1/auth/login", json={"username": "nobody_here", "password": "whatever123"}
    ).status_code == 401


def test_profile(client):
    response = client.get(
        "/api/v1/users/1/profile", headers={"X-User-Id": "1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["persona_title"] == "川渝麻辣派"
    assert "meals_logged" in body["achievements"]
    assert body["achievements"]["meals_logged"] >= 3


def test_weather_override(client):
    response = client.get(
        "/api/v1/context/weather", params={"temp": 12, "weather": "小雨"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "override"
    assert body["temp"] == 12.0
    assert "雨" in body["capsule_tip"]


def test_weather_fallback_never_500(client):
    """无高德 Key 时必须有降级来源，不允许 500。

    降级链已扩展为 高德 → open-meteo → 离线常量，
    所以这里只断言「来源是已知降级之一」，不再写死 offline。
    """
    response = client.get("/api/v1/context/weather")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] in ("offline", "open-meteo")
    assert body["temp"] > 0
    assert body["capsule_tip"]


def test_single_recommend_with_header(client):
    response = client.post(
        "/api/v1/recommend/single",
        json={
            "mode_type": "OUT_DINING", "campus": "SIYUAN",
            "bubbles": ["craving_heavy"],
            "weather_temp": 8,
            "weather_text": "小雨",
            "limit": 5,
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]
    assert body["params_used"]["alpha_taste"] == pytest.approx(
        0.5 / 1.15, rel=1e-4
    )
    assert body["bubble_effects"]["applied"]
    radar = body["recommendations"][0]["radar_5d"]
    assert set(radar) == {"taste", "weather", "budget", "freshness", "status"}


def test_single_recommend_uses_header_user(client):
    response = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["recommendations"]}
    assert "白切鸡饭" not in names  # 用户 1 黑榜
    assert "凉拌折耳根" not in names  # 用户 1 忌口


def test_single_recommend_override_params_and_combo(client):
    response = client.post(
        "/api/v1/recommend/single",
        json={
            "mode_type": "OUT_DINING", "campus": "SIYUAN",
            "budget": 40,
            "combo_mode": True,
            "override_params": {"lambda_decay": 1.5},
            "limit": 10,
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["params_used"]["lambda_decay"] == 1.5
    assert body["combo"] is not None
    assert body["combo"]["total_price"] <= 40


def test_home_lazy_one_pot_api(client, db):
    response = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "HOME_COOKING", "bubbles": ["lazy_one_pot"], "limit": 100},
        headers={"X-User-Id": "2"},
    )
    assert response.status_code == 200
    items = response.json()["recommendations"]
    assert items
    # v2.3.2 第二章：lazy_one_pot 白名单只有「电饭煲」「一锅出」，免开火凉拌不在内；
    # 速度门槛已删除，所以一锅出菜（prep_speed 0.40~0.45）应当被召回
    allowed = {"电饭煲", "一锅出"}
    seen = set()
    for item in items:
        dish = db.query(Dish).filter(Dish.id == item["dish_id"]).first()
        tags = dish.appliance_tag if isinstance(dish.appliance_tag, list) else [dish.appliance_tag]
        assert set(tags) & allowed
        seen |= set(tags) & allowed
    assert "一锅出" in seen


def test_missing_user_returns_404(client):
    # F07：身份以请求头为准，body 的 user_id 不再能压过请求头
    response = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "999"},
    )
    assert response.status_code == 404


def test_invalid_mode_returns_422(client):
    response = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "TAKEAWAY"},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422


def test_red_black_list_roundtrip(client, db):
    dish = (
        db.query(Dish)
        .filter(Dish.name == "麻辣香锅", Dish.mode_type == "OUT_DINING")
        .first()
    )
    added = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": dish.id,
            "list_type": "BLACK",
            "action": "ADD",
        },
        headers={"X-User-Id": "1"},
    )
    assert added.status_code == 200
    assert dish.id in added.json()["blacklist_dish_ids"]

    profile = client.get(
        "/api/v1/users/1/profile", headers={"X-User-Id": "1"}
    ).json()
    assert dish.id in profile["blacklist_dish_ids"]
    assert profile["blacklist_restaurant_ids"] == []

    removed = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": dish.id,
            "list_type": "BLACK",
            "action": "REMOVE",
        },
        headers={"X-User-Id": "1"},
    )
    assert dish.id not in removed.json()["blacklist_dish_ids"]


def test_favorite_only_accepts_dish(client, db):
    restaurant = db.query(Restaurant).first()
    response = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "RESTAURANT",
            "target_id": restaurant.id,
            "list_type": "FAV",
            "action": "ADD",
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 400

    dish = db.query(Dish).filter(Dish.mode_type == "OUT_DINING").first()
    ok = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": dish.id,
            "list_type": "FAV",
            "action": "ADD",
        },
        headers={"X-User-Id": "1"},
    )
    assert ok.status_code == 200
    assert dish.id in ok.json()["favorite_dish_ids"]


def test_restaurant_blacklist_filters_whole_store(client, db):
    # 用户 3 未拉黑任何门店；选一家有外食菜品的门店拉黑
    restaurant = db.query(Restaurant).filter(Restaurant.name == "阿香麻辣烫").first()
    response = client.post(
        "/api/v1/users/3/red-black-list",
        json={
            "target_type": "RESTAURANT",
            "target_id": restaurant.id,
            "list_type": "BLACK",
            "action": "ADD",
        },
        headers={"X-User-Id": "3"},
    )
    assert response.status_code == 200
    assert restaurant.id in response.json()["blacklist_restaurant_ids"]

    body = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 100},
        headers={"X-User-Id": "3"},
    ).json()
    assert body["recommendations"]
    assert all(
        item["restaurant_id"] != restaurant.id for item in body["recommendations"]
    )


def test_red_black_list_unknown_target_returns_404(client):
    dish_resp = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": 99999,
            "list_type": "BLACK",
            "action": "ADD",
        },
        headers={"X-User-Id": "1"},
    )
    assert dish_resp.status_code == 404

    restaurant_resp = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "RESTAURANT",
            "target_id": 99999,
            "list_type": "BLACK",
            "action": "ADD",
        },
        headers={"X-User-Id": "1"},
    )
    assert restaurant_resp.status_code == 404


def test_update_preferences(client):
    response = client.put(
        "/api/v1/users/1/preferences",
        json={"default_budget": 35.0, "veto_tags": ["香菜", "折耳根"]},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["default_budget"] == 35.0
    assert body["veto_tags"] == ["香菜", "折耳根"]


def test_catalog_dishes_resolves_ids(client):
    response = client.get("/api/v1/catalog/dishes", params={"ids": "1,40"})
    assert response.status_code == 200
    rows = response.json()
    assert [row["dish_id"] for row in rows] == [1, 40]
    assert rows[0]["name"] and rows[0]["mode_type"] in ("OUT_DINING", "HOME_COOKING")
    # 红黑榜要拿它把 id 翻成名字，所以这几个键必须在
    for key in ("dish_id", "name", "cuisine_type", "price", "image_url"):
        assert key in rows[0]


def test_catalog_dishes_rejects_all_garbage_ids(client):
    """?ids 全是非法值时必须 422。

    原用例断言「忽略非法 id、返回全量」——调用方会以为筛选生效，
    实际拿到全部菜谱（当前 6560 道），属于静默降级。
    """
    response = client.get("/api/v1/catalog/dishes", params={"ids": "abc,,"})
    assert response.status_code == 422, response.text


def test_catalog_dishes_keeps_valid_ids_among_garbage(client):
    """部分非法时保留合法 id（宽容解析），不整体拒绝。"""
    response = client.get("/api/v1/catalog/dishes", params={"ids": "1,abc"})
    assert response.status_code == 200, response.text
    rows = response.json()
    # 只保留合法 id，且确实做了过滤（不是把全量返回回来）
    assert len(rows) == 1, rows[:5]
    assert rows[0]["dish_id"] == 1


def test_catalog_restaurants_resolves_ids(client):
    response = client.get("/api/v1/catalog/restaurants", params={"ids": "1,2"})
    assert response.status_code == 200
    rows = response.json()
    assert [row["restaurant_id"] for row in rows] == [1, 2]
    assert rows[0]["name"]


def test_exclude_dish_ids_returns_new_candidates(client):
    """审查 F13：换一批不能反复给同一批 Top N。"""
    base = {"mode_type": "OUT_DINING", "campus": "SIYUAN", "bubbles": [], "weather_temp": 22, "weather_text": "晴", "limit": 5}
    first = client.post("/api/v1/recommend/single", json=base, headers={"X-User-Id": "1"})
    assert first.status_code == 200
    first_ids = [item["dish_id"] for item in first.json()["recommendations"]]
    assert len(first_ids) == 5

    second = client.post(
        "/api/v1/recommend/single",
        json={**base, "exclude_dish_ids": first_ids},
        headers={"X-User-Id": "1"},
    )
    assert second.status_code == 200
    second_ids = [item["dish_id"] for item in second.json()["recommendations"]]
    assert second_ids, "排除后不应为空"
    assert not set(first_ids) & set(second_ids), "第二批不能包含第一批的菜"


# ---------------- 审查 F08：入参边界（越界一律 422，不许 500） ----------------
import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 0},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 101},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": -1},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "weather_temp": 120},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "weather_text": "x" * 200},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "max_distance_meters": -5},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "exclude_dish_ids": list(range(600))},
    ],
)
def test_recommend_rejects_out_of_range_input(client, payload):
    response = client.post(
        "/api/v1/recommend/single", json=payload, headers={"X-User-Id": "1"}
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "override",
    [
        {"unknown_param": 0.5},
        {"lambda_decay": 5.0},
        {"omega_group": -0.2},
        {"alpha_taste": "abc"},
        {"beta_weather": "inf"},
    ],
)
def test_recommend_rejects_bad_override_params(client, override):
    response = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "override_params": override},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422, response.text


def test_recommend_accepts_valid_override_params(client):
    response = client.post(
        "/api/v1/recommend/single",
        json={
            "mode_type": "OUT_DINING", "campus": "SIYUAN",
            "limit": 3,
            "override_params": {"lambda_decay": 2.0, "omega_group": 0.5},
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    assert len(response.json()["recommendations"]) == 3


def test_checkin_rejects_negative_cost(client, db):
    dish = db.query(Dish).filter(Dish.mode_type == "OUT_DINING").first()
    response = client.post(
        "/api/v1/logs/checkin",
        json={"dish_id": dish.id, "mode_type": "OUT_DINING", "cost_amount": -3},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422, response.text

