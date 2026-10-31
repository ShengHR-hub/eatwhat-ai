import pytest

from backend.algorithms.single_recommender import _budget_score, recommend_single
from backend.models import Dish, UserPreference


def _by_name(result, name):
    return next(item for item in result["recommendations"] if item["name"] == name)


def test_hard_filters_and_radar(db):
    result = recommend_single(
        db, 2, "OUT_DINING", weather_temp=15.0, weather_text="晴", limit=100
    )
    names = {item["name"] for item in result["recommendations"]}
    assert "白灼虾" not in names  # 海鲜忌口
    assert "水煮鱼" not in names  # 香菜忌口
    assert "麻辣香锅" not in names  # 用户 2 黑榜
    radar_keys = {"taste", "weather", "budget", "freshness", "status"}
    for item in result["recommendations"]:
        assert set(item["radar_5d"]) == radar_keys
        assert 0.0 <= item["radar_5d"]["status"] <= 100.0
    scores = [item["total_score"] for item in result["recommendations"]]
    assert scores == sorted(scores, reverse=True)


def test_favorite_boost_is_exactly_1_15(db):
    before = _by_name(
        recommend_single(db, 2, "OUT_DINING", limit=100), "老火靓汤"
    )
    prefs = db.query(UserPreference).filter(UserPreference.user_id == 2).first()
    prefs.favorite_dish_ids = [
        i for i in (prefs.favorite_dish_ids or []) if i != before["dish_id"]
    ]
    db.commit()
    after = _by_name(
        recommend_single(db, 2, "OUT_DINING", limit=100), "老火靓汤"
    )
    assert before["raw_score"] == pytest.approx(
        after["raw_score"] * 1.15, rel=1e-3
    )


def test_budget_score_boundaries():
    assert _budget_score(0.0, 25.0) == 100.0
    assert _budget_score(25.0, 25.0) == 85.0
    assert _budget_score(50.0, 25.0) < 85.0
    assert _budget_score(10.0, 25.0) == pytest.approx(94.0)


def test_light_healthy_penalty_is_0_2(db):
    base = _by_name(
        recommend_single(db, 1, "OUT_DINING", limit=100), "麻辣香锅"
    )
    light_result = recommend_single(
        db, 1, "OUT_DINING", bubbles=["light_healthy"], limit=100
    )
    light = _by_name(light_result, "麻辣香锅")
    assert light["raw_score"] == pytest.approx(
        base["raw_score"] * 0.2, rel=1e-4
    )


def test_lazy_one_pot_hard_filter(db):
    result = recommend_single(
        db, 2, "HOME_COOKING", bubbles=["lazy_one_pot"], limit=100
    )
    assert result["recommendations"]
    # v2.3.2 第二章：白名单只含 电饭煲 / 一锅出；免开火凉拌是合法枚举但不入此白名单。
    # 速度门槛已在 v2.3.2 删除（厨具可用性与出餐速度正交），因此不再断言 prep_speed。
    allowed = {"电饭煲", "一锅出"}
    for item in result["recommendations"]:
        dish = db.query(Dish).filter(Dish.id == item["dish_id"]).first()
        tags = dish.appliance_tag if isinstance(dish.appliance_tag, list) else [dish.appliance_tag]
        assert set(tags) & allowed


def test_restaurant_blacklist_removes_whole_store(db):
    """v2.3.1 第三章：外食模式下黑榜门店的所有菜品一并剔除，下厨模式不受影响。"""
    from backend.models import Restaurant

    prefs = db.query(UserPreference).filter(UserPreference.user_id == 3).first()
    restaurant = db.query(Restaurant).filter(Restaurant.name == "阿香麻辣烫").first()
    target_dishes = (
        db.query(Dish)
        .filter(Dish.restaurant_id == restaurant.id)
        .all()
    )
    assert target_dishes
    prefs.blacklist_restaurant_ids = [restaurant.id]
    db.commit()

    out = recommend_single(db, 3, "OUT_DINING", limit=100)
    out_ids = {item["dish_id"] for item in out["recommendations"]}
    assert not (out_ids & {dish.id for dish in target_dishes})

    home = recommend_single(db, 3, "HOME_COOKING", limit=100)
    assert home["recommendations"]  # 门店黑榜不影响下厨


def test_broke_end_month_filters_and_reweights(db):
    result = recommend_single(
        db,
        3,
        "OUT_DINING",
        budget=12.0,
        bubbles=["broke_end_month"],
        limit=100,
    )
    assert result["recommendations"]
    assert all(item["price"] <= 12.0 for item in result["recommendations"])
    assert result["params_used"]["gamma_budget"] == pytest.approx(
        0.55 / 1.35, rel=1e-4
    )


def test_combo_mode_returns_valid_package(db):
    result = recommend_single(
        db, 1, "OUT_DINING", budget=40.0, combo_mode=True, limit=10
    )
    combo = result["combo"]
    assert combo is not None
    assert {dish["dish_role"] for dish in combo["dishes"]} == {
        "MEAT",
        "VEG",
        "SOUP",
    }
    assert combo["total_price"] <= 40.0
    assert combo["avg_oily_level"] <= 0.65


def test_missing_preferences_raises(db):
    with pytest.raises(ValueError):
        recommend_single(db, 999, "OUT_DINING")


def test_raw_score_sorted_before_output_cap(db):
    from backend.models import User, UserPreference

    dish = (
        db.query(Dish)
        .filter(Dish.name == "麻辣香锅", Dish.mode_type == "OUT_DINING")
        .first()
    )
    user = User(
        username="cap_user",
        nickname="封顶测试",
        avatar="",
        persona_title="",
        is_demo_persona=False,
    )
    db.add(user)
    db.flush()
    db.add(
        UserPreference(
            user_id=user.id,
            base_vector=dict(dish.feature_vector),
            default_budget=100.0,
            veto_tags=[],
            preferred_cuisines=[],
            favorite_dish_ids=[dish.id],
            blacklist_dish_ids=[],
        )
    )
    db.commit()

    result = recommend_single(
        db,
        user.id,
        "OUT_DINING",
        override_params={
            "alpha_taste": 1.0,
            "beta_weather": 0.0,
            "gamma_budget": 0.0,
            "delta_status": 0.0,
        },
        limit=100,
    )
    target = next(
        item for item in result["recommendations"] if item["dish_id"] == dish.id
    )
    assert target["raw_score"] > 100
    assert target["total_score"] == 100.0
    assert result["recommendations"][0]["dish_id"] == dish.id
    raw_scores = [item["raw_score"] for item in result["recommendations"]]
    assert raw_scores == sorted(raw_scores, reverse=True)

def test_image_url_is_exposed_and_relative(db):
    """v2.3.2 后补：卡面图位读 image_url；无图必须是 None，不能是空串或外链。"""
    result = recommend_single(db, 1, "OUT_DINING", limit=50)
    assert result["recommendations"]
    for item in result["recommendations"]:
        assert "image_url" in item
        assert item["image_url"] is None or item["image_url"].startswith("/dishes/")
