"""G2/BRIDGE-10 回归：单人推荐必须按校区过滤，外食缺 campus 返回 422。"""

from __future__ import annotations

import json

from backend.algorithms.single_recommender import recommend_single
from backend.algorithms.vector_spec import FEATURE_KEYS
from backend.models import Dish, Restaurant

H1 = {"X-User-Id": "1"}
URL = "/api/v1/recommend/single"
VECTOR = {key: 0.5 for key in FEATURE_KEYS}


def _add_store(session, name: str, campus: str | None):
    store = Restaurant(
        name=name,
        source_type="CANTEEN",
        category="test",
        avg_price=12.0,
        rating=None,
        longitude=109.0,
        latitude=34.2,
        distance_meters=100,
        address="test",
        campus=campus,
        is_synthetic=True,
        source_dataset="g2_campus_test",
        source_record_id=name,
    )
    session.add(store)
    session.flush()
    dish = Dish(
        name=f"{name}招牌",
        mode_type="OUT_DINING",
        restaurant_id=store.id,
        cuisine_type="川湘菜",
        dish_role="MEAT",
        price_or_cost=12.0,
        cook_minutes=15,
        appliance_tag=["炒锅"],
        ingredients_main=["测试主料"],
        ingredients_aux=[],
        recipe_steps="test",
        feature_vector=dict(VECTOR),
        allergen_tags=[],
        tagging_status="SUCCESS",
        is_synthetic=True,
        source_dataset="g2_campus_test",
        source_record_id=f"{name}-dish",
    )
    session.add(dish)
    session.commit()
    return store, dish


def test_out_dining_requires_campus(client):
    response = client.post(URL, json={"mode_type": "OUT_DINING", "limit": 5}, headers=H1)
    assert response.status_code == 422, response.text
    assert "校区" in json.dumps(response.json(), ensure_ascii=False)


def test_out_dining_rejects_unknown_campus(client):
    response = client.post(
        URL, json={"mode_type": "OUT_DINING", "campus": "JIANDA_CAOTANG", "limit": 5}, headers=H1
    )
    assert response.status_code == 422, response.text


def test_home_cooking_ignores_campus_and_stays_shared(client):
    without = client.post(URL, json={"mode_type": "HOME_COOKING", "limit": 5}, headers=H1)
    with_campus = client.post(
        URL, json={"mode_type": "HOME_COOKING", "campus": "SIYUAN", "limit": 5}, headers=H1
    )
    assert without.status_code == 200, without.text
    assert with_campus.status_code == 200, with_campus.text
    assert [row["dish_id"] for row in without.json()["recommendations"]] == [
        row["dish_id"] for row in with_campus.json()["recommendations"]
    ]


def test_campus_filter_and_null_exclusion(client, db):
    jianda_store, jianda_dish = _add_store(db, "建大测试档口", "JIANDA_YANTA")
    null_store, null_dish = _add_store(db, "无校区测试档口", None)

    siyuan = client.post(
        URL, json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 100}, headers=H1
    )
    assert siyuan.status_code == 200, siyuan.text
    siyuan_rows = siyuan.json()["recommendations"]
    assert siyuan_rows
    assert all(row["restaurant_id"] not in {jianda_store.id, null_store.id} for row in siyuan_rows)

    jianda = client.post(
        URL, json={"mode_type": "OUT_DINING", "campus": "JIANDA_YANTA", "limit": 100}, headers=H1
    )
    assert jianda.status_code == 200, jianda.text
    jianda_ids = {row["dish_id"] for row in jianda.json()["recommendations"]}
    assert jianda_dish.id in jianda_ids
    assert null_dish.id not in jianda_ids
    assert all(
        row["restaurant_id"] != null_store.id for row in jianda.json()["recommendations"]
    )


def test_algorithm_legacy_call_without_campus_still_works(db):
    result = recommend_single(db, user_id=1, mode_type="OUT_DINING", limit=5)
    assert result["recommendations"]
