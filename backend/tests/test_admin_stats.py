from datetime import datetime

import pytest

from backend.models import Dish, EatingLog, GroupRoom, Restaurant, RoomVote, User, UserPreference


CAMPUS = "JIANDA_CAOTANG"
CUISINE = "G4_TEST"
VECTOR = {
    "spicy_level": 0.1,
    "oily_level": 0.2,
    "soup_level": 0.3,
    "temp_fit": 0.4,
    "satiety_level": 0.5,
    "prep_speed": 0.6,
    "social_fit": 0.7,
    "comfort_level": 0.8,
}


@pytest.fixture()
def g4_sample(client, db):
    restaurant = Restaurant(
        name="G4 统计门店",
        source_type="AMAP_POI",
        campus=CAMPUS,
        longitude=109.078487,
        latitude=34.234818,
        avg_price=20,
        rating=4.5,
        is_synthetic=False,
    )
    other_restaurant = Restaurant(
        name="G4 其他门店",
        source_type="CANTEEN",
        campus=CAMPUS,
        longitude=109.1,
        latitude=34.2,
        avg_price=10,
        rating=None,
        is_synthetic=True,
    )
    db.add_all([restaurant, other_restaurant])
    db.flush()
    dishes = [
        Dish(
            name="鸡肉土豆测试菜",
            mode_type="OUT_DINING",
            restaurant_id=restaurant.id,
            cuisine_type=CUISINE,
            dish_role="MEAT",
            price_or_cost=18,
            ingredients_main=["鸡肉"],
            ingredients_aux=["土豆"],
            feature_vector=VECTOR,
            allergen_tags=["香菜"],
            tagging_status="SUCCESS",
        ),
        Dish(
            name="鸡肉土豆香菇饭",
            mode_type="HOME_COOKING",
            cuisine_type=CUISINE,
            dish_role="ONE_MEAL",
            price_or_cost=6,
            ingredients_main=["鸡肉", "土豆"],
            ingredients_aux=["香菇", "盐"],
            feature_vector=None,
            allergen_tags=[],
            tagging_status="PENDING",
        ),
        Dish(
            name="异常向量隔离菜",
            mode_type="HOME_COOKING",
            cuisine_type=CUISINE,
            dish_role="VEG",
            price_or_cost=None,
            ingredients_main=["鸡肉", "土豆", "香菇"],
            ingredients_aux=[],
            feature_vector={**VECTOR, "spicy_level": 2},
            allergen_tags=None,
            tagging_status="SUCCESS",
        ),
        Dish(
            name="其他菜系菜",
            mode_type="OUT_DINING",
            restaurant_id=other_restaurant.id,
            cuisine_type="G4_OTHER",
            dish_role="ONE_MEAL",
            price_or_cost=12,
            ingredients_main=[],
            ingredients_aux=[],
            feature_vector=None,
            tagging_status="PENDING",
        ),
    ]
    db.add_all(dishes)
    db.flush()
    out_dish, home_dish, invalid_dish, other_dish = dishes
    db.add_all(
        [
            # UTC -> Asia/Shanghai：1 月 5 日 00:30，周一夜宵。
            EatingLog(user_id=1, dish_id=out_dish.id, mode_type="OUT_DINING", eaten_at=datetime(2026, 1, 4, 16, 30)),
            # 1 月 5 日 10:00，周一午餐（左闭右开边界）。
            EatingLog(user_id=1, dish_id=out_dish.id, mode_type="OUT_DINING", eaten_at=datetime(2026, 1, 5, 2, 0)),
            EatingLog(user_id=2, dish_id=home_dish.id, mode_type="HOME_COOKING", eaten_at=datetime(2026, 1, 5, 3, 0)),
            # 留出 1 月 6 日空档，日历与趋势必须补零。
            EatingLog(user_id=2, dish_id=home_dish.id, mode_type="HOME_COOKING", eaten_at=datetime(2026, 1, 7, 4, 0)),
        ]
    )
    room = GroupRoom(
        room_code="G4T001",
        host_user_id=1,
        member_user_ids=[1, 2],
        mode_type="OUT_DINING",
        status="FINISHED",
        candidate_dish_ids=[out_dish.id],
        winner_dish_id=out_dish.id,
        campus=CAMPUS,
    )
    db.add(room)
    db.add_all(
        [
            RoomVote(room_code=room.room_code, user_id=1, dish_id=out_dish.id, vote_type="LIKE", voted_at=datetime(2026, 1, 5, 4, 0)),
            RoomVote(room_code=room.room_code, user_id=2, dish_id=out_dish.id, vote_type="VETO", voted_at=datetime(2026, 1, 5, 4, 1)),
        ]
    )
    db.commit()
    return {
        "restaurant": restaurant,
        "other_restaurant": other_restaurant,
        "out_dish": out_dish,
        "home_dish": home_dish,
        "invalid_dish": invalid_dish,
        "other_dish": other_dish,
        "room": room,
    }


def get_stats(admin_client, path, **params):
    response = admin_client.get(f"/api/v1/admin/stats/{path}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_overview_has_campus_shared_and_real_feature_count(admin_client, g4_sample):
    body = get_stats(admin_client, "overview", campus=CAMPUS, cuisine_type=CUISINE)
    assert body["applicable"] is True
    assert body["by_campus"][CAMPUS]["restaurants"] == 2
    assert body["by_campus"][CAMPUS]["dishes"] == 1
    assert body["by_campus"]["SHARED"]["dishes"] == 2
    # 总数 = 当前校区外食 1 + 共享下厨 2；只有 1 条合法成功向量。
    assert body["total"]["dishes"] == 3
    assert body["feature_values_total"] == 8
    assert body["logs_total"] == 4
    assert body["votes_total"] == 2
    assert body["rooms_total"] == 1
    assert body["tagging_coverage"] == pytest.approx(1 / 3)
    assert body["meta"]["scope"] == CAMPUS


def test_geo_preserves_gcj02_and_home_mode_empty_state(admin_client, g4_sample):
    body = get_stats(admin_client, "geo", campus=CAMPUS, cuisine_type=CUISINE)
    assert body["applicable"] is True
    assert len(body["points"]) == 1
    point = body["points"][0]
    assert point["id"] == g4_sample["restaurant"].id
    assert point["lng"] == 109.078487
    assert point["lat"] == 34.234818
    assert point["heat"] == 2
    assert point["meta"] if "meta" in point else True
    assert body["meta"]["coordinate"] == "GCJ-02"

    unavailable = get_stats(admin_client, "geo", mode_type="HOME_COOKING")
    assert unavailable["applicable"] is False
    assert unavailable["items"] == []
    assert unavailable["meta"]["scope"] == "SHARED"


def test_calendar_fills_zero_dates_and_heatmap_boundaries(admin_client, g4_sample):
    body = get_stats(admin_client, "calendar", campus=CAMPUS, cuisine_type=CUISINE)
    assert body["daily"] == [
        {"date": "2026-01-05", "count": 3},
        {"date": "2026-01-06", "count": 0},
        {"date": "2026-01-07", "count": 1},
    ]

    matrix = get_stats(admin_client, "heatmap", campus=CAMPUS, cuisine_type=CUISINE)["matrix"]
    assert len(matrix) == 28
    counts = {(row["weekday"], row["slot"]): row["count"] for row in matrix}
    assert counts[(0, "夜宵")] == 1
    assert counts[(0, "午餐")] == 2
    assert counts[(2, "午餐")] == 1
    assert sum(counts.values()) == 4


def test_cuisine_and_trend_share_can_be_reconciled(admin_client, g4_sample):
    cuisine = get_stats(admin_client, "cuisine", campus=CAMPUS, cuisine_type=CUISINE)
    assert cuisine["items"] == [{"cuisine_type": CUISINE, "count": 3, "share": 1.0}]
    assert cuisine["meta"]["unit"] == "dishes_rows"

    trend = get_stats(admin_client, "cuisine-trend", campus=CAMPUS, cuisine_type=CUISINE)
    assert trend["dates"] == ["2026-01-05", "2026-01-06", "2026-01-07"]
    assert trend["series"] == [{"cuisine_type": CUISINE, "data": [3, 0, 1]}]
    assert sum(trend["series"][0]["data"]) == sum(row["count"] for row in get_stats(admin_client, "calendar", campus=CAMPUS, cuisine_type=CUISINE)["daily"])


def test_personas_global_filter_is_explicit_empty_state(admin_client, g4_sample):
    body = get_stats(admin_client, "personas")
    assert body["applicable"] is True
    assert len(body["personas"]) == 4
    assert all(set(row["base_vector"]) == set(VECTOR) for row in body["personas"])
    unavailable = get_stats(admin_client, "personas", campus="SIYUAN")
    assert unavailable["applicable"] is False
    assert unavailable["meta"]["scope"] == "GLOBAL"


def test_personas_scope_can_include_real_accounts(admin_client, session_factory, g4_sample):
    with session_factory() as session:
        user = User(
            username="real_profile_probe",
            nickname="真实画像甲",
            role="USER",
            is_demo_persona=False,
        )
        session.add(user)
        session.flush()
        session.add(
            UserPreference(
                user_id=user.id,
                base_vector=dict(VECTOR),
                default_budget=25.0,
                veto_tags=[],
                preferred_cuisines=[],
                favorite_dish_ids=[],
                blacklist_dish_ids=[],
                blacklist_restaurant_ids=[],
            )
        )
        session.commit()

    demo = get_stats(admin_client, "personas", scope="demo")
    assert demo["scope"] == "demo"
    assert demo["personas"] and all(row["is_demo"] for row in demo["personas"])

    real = get_stats(admin_client, "personas", scope="real")
    assert real["scope"] == "real"
    assert any(row["nickname"] == "真实画像甲" for row in real["personas"])
    assert all(not row["is_demo"] for row in real["personas"])

    every = get_stats(admin_client, "personas", scope="all")
    assert len(every["personas"]) >= 5


def test_scatter_never_fakes_home_rating(admin_client, g4_sample):
    body = get_stats(admin_client, "scatter", campus=CAMPUS, cuisine_type=CUISINE)
    points = {(row["entity_type"], row["entity_id"]): row for row in body["points"]}
    restaurant = points[("RESTAURANT", g4_sample["restaurant"].id)]
    out_dish = points[("DISH", g4_sample["out_dish"].id)]
    home_dish = points[("DISH", g4_sample["home_dish"].id)]
    assert restaurant["rating"] == 4.5
    assert restaurant["freq"] == 3  # 两条日志 + 一条非 VETO 票
    assert out_dish["freq"] == 3
    assert home_dish["rating"] is None
    assert home_dish["freq"] == 2
    assert body["meta"]["not_plotted_no_rating"] == 2


def test_flow_is_conserved_in_vote_units(admin_client, g4_sample):
    body = get_stats(admin_client, "flow", campus=CAMPUS)
    assert body["meta"]["unit"] == "票"
    assert body["meta"]["total_opportunities"] == 2
    assert body["meta"]["actual_votes"] == 2
    assert body["meta"]["absent_votes"] == 0
    links = {(row["source"], row["target"]): row["value"] for row in body["links"]}
    assert links[("全部候选", "LIKE")] == 1
    assert links[("全部候选", "VETO")] == 1
    assert links[("LIKE", "赢家")] == 1
    assert links[("VETO", "否决")] == 1
    assert sum(row["value"] for row in body["links"] if row["source"] == "全部候选") == 2
    filtered = get_stats(admin_client, "flow", cuisine_type=CUISINE)
    assert filtered["applicable"] is False


def test_keywords_race_and_veto_exclusion(admin_client, g4_sample):
    words = get_stats(admin_client, "keywords", campus=CAMPUS, cuisine_type=CUISINE)
    values = {row["name"]: row["value"] for row in words["words"]}
    assert values["香菜"] == 1
    assert values["鸡肉"] >= 1

    race = get_stats(admin_client, "race", campus=CAMPUS, cuisine_type=CUISINE)
    top = race["latest_top10"]
    assert top[0]["dish_id"] == g4_sample["out_dish"].id
    assert top[0]["value"] == 3  # VETO 不计热门
    assert race["weeks"] == ["2026-01-05"]
    out_series = next(row for row in race["series"] if row["dish_id"] == g4_sample["out_dish"].id)
    assert out_series["data"] == [3]


def test_cooccurrence_threshold_stopwords_and_out_mode_empty(admin_client, db, g4_sample):
    db.add_all([
        Dish(
            name=f"共现隔离菜 {index}",
            mode_type="HOME_COOKING",
            cuisine_type="G4_COOC",
            dish_role="ONE_MEAL",
            ingredients_main=["鸡肉", "土豆"],
            ingredients_aux=["香菇", "盐"],
        )
        for index in range(3)
    ])
    db.commit()
    body = get_stats(admin_client, "cooccurrence", campus=CAMPUS, cuisine_type="G4_COOC")
    links = {(row["source"], row["target"]): row["value"] for row in body["links"]}
    assert links[("土豆", "香菇")] == 3
    assert links[tuple(sorted(("鸡肉", "土豆")))] == 3
    assert all("盐" not in pair for pair in links)
    assert body["meta"]["min_count"] == 3
    assert body["meta"]["top_n"] == 30
    unavailable = get_stats(admin_client, "cooccurrence", mode_type="OUT_DINING")
    assert unavailable["applicable"] is False
    assert unavailable["items"] == []


def test_quality_counts_anomalous_rows_once(admin_client, g4_sample):
    body = get_stats(admin_client, "quality", campus=CAMPUS, cuisine_type=CUISINE)
    assert body["total_dishes"] == 3
    assert body["tagged_dishes"] == 1
    assert body["tagging_coverage"] == pytest.approx(1 / 3)
    assert body["vector_anomalies"]["total"] == 1
    assert body["vector_anomalies"]["invalid_vector"] == 1
    assert body["vector_anomalies"]["success_without_valid_vector"] == 1
    missing = {row["field"]: row["count"] for row in body["missing_fields"]}
    assert missing["feature_vector"] == 1
    assert missing["allergen_tags"] == 2


def test_all_stats_return_legal_empty_results(admin_client, g4_sample):
    params = {"campus": CAMPUS, "cuisine_type": "NO_SUCH_CUISINE"}
    expectations = {
        "overview": lambda body: body["total"]["dishes"] == 0 and body["logs_total"] == 0,
        "geo": lambda body: body["points"] == [],
        "calendar": lambda body: body["daily"] == [],
        "heatmap": lambda body: len(body["matrix"]) == 28 and sum(row["count"] for row in body["matrix"]) == 0,
        "cuisine": lambda body: body["items"] == [],
        "cuisine-trend": lambda body: body["dates"] == [] and body["series"] == [],
        "scatter": lambda body: body["points"] == [] and body["meta"]["not_plotted_no_rating"] == 0,
        "keywords": lambda body: body["words"] == [],
        "race": lambda body: body["weeks"] == [] and body["latest_top10"] == [],
        "cooccurrence": lambda body: body["nodes"] == [] and body["links"] == [],
        "quality": lambda body: body["total_dishes"] == 0 and body["tagging_coverage"] == 0,
    }
    for path, assertion in expectations.items():
        body = get_stats(admin_client, path, **params)
        assert body["applicable"] is True, path
        assert assertion(body), path
