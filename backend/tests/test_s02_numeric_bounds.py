"""S02：数值、向量与持久化边界。

期望值独立于生产常量：八维键名按 MASTER_SPEC 第二章逐字抄写，
范围 0~1、展示 0~100、四权重和为 1 均来自 SSOT，而不是 import 被测模块。
"""

import json
import math

import pytest

from backend.models import Dish, EatingLog, FridgeInventory, GroupRoom, UserPreference

EIGHT_KEYS = (
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
)
H1 = {"X-User-Id": "1"}
PREFS_URL = "/api/v1/users/1/preferences"
RECOMMEND_URL = "/api/v1/recommend/single"
CHECKIN_URL = "/api/v1/logs/checkin"
FRIDGE_URL = "/api/v1/fridge/1"
SHOPPING_URL = "/api/v1/fridge/shopping-list"


def _json(value):
    return json.loads(json.dumps(value))


def _prefs(session_factory, user_id=1):
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .one()
        )
        return _json(row.base_vector), float(row.default_budget), _json(row.veto_tags)


def _pref_snapshot(session_factory, user_id=1):
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .one()
        )
        return {
            "base_vector": _json(row.base_vector),
            "default_budget": float(row.default_budget),
            "veto_tags": _json(row.veto_tags),
            "preferred_cuisines": _json(row.preferred_cuisines),
            "favorite_dish_ids": _json(row.favorite_dish_ids),
            "blacklist_dish_ids": _json(row.blacklist_dish_ids),
            "blacklist_restaurant_ids": _json(row.blacklist_restaurant_ids),
        }


def _snapshot_json(snapshot):
    # NaN != NaN，普通 dict 比较会把“未变化”误判成变化。
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, allow_nan=True)


def _set_vector(session_factory, vector, user_id=1):
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .one()
        )
        row.base_vector = vector
        session.commit()


def _count(session_factory, model, **filters):
    with session_factory() as session:
        query = session.query(model)
        for key, value in filters.items():
            query = query.filter(getattr(model, key) == value)
        return query.count()


def _put_json(client, url, payload, headers=None):
    return client.put(url, json=payload, headers=headers or H1)


def _put_raw(client, url, raw):
    return client.put(
        url,
        content=raw,
        headers={**H1, "Content-Type": "application/json"},
    )


# ---------------------------------------------------------------- 向量：部分更新


def test_schema_keys_match_algorithm_spec():
    from backend.algorithms import vector_spec
    from backend.schemas import BUBBLE_IDS, GENE_KEYS

    assert tuple(GENE_KEYS) == tuple(vector_spec.FEATURE_KEYS)
    assert set(EIGHT_KEYS) == set(vector_spec.FEATURE_KEYS)
    assert set(BUBBLE_IDS) == set(vector_spec.STATUS_BUBBLE_RULES)


def test_partial_vector_merges_and_keeps_eight_keys(client, session_factory):
    before, _, _ = _prefs(session_factory)
    response = _put_json(
        client,
        PREFS_URL,
        {"base_vector": {"spicy_level": 0.9, "oily_level": 0.6}},
    )
    assert response.status_code == 200, response.text

    stored, _, _ = _prefs(session_factory)
    assert set(stored) == set(EIGHT_KEYS)
    assert len(stored) == 8
    assert stored["spicy_level"] == pytest.approx(0.9)
    assert stored["oily_level"] == pytest.approx(0.6)
    for key in set(EIGHT_KEYS) - {"spicy_level", "oily_level"}:
        assert stored[key] == pytest.approx(before[key]), key
    assert response.json()["base_vector"] == stored


def test_empty_vector_is_rejected_and_db_unchanged(client, session_factory):
    before = _prefs(session_factory)
    response = _put_json(client, PREFS_URL, {"base_vector": {}})
    assert response.status_code == 422, response.text
    assert _prefs(session_factory) == before


def test_extra_vector_key_is_rejected_and_db_unchanged(client, session_factory):
    before = _prefs(session_factory)
    response = _put_json(
        client,
        PREFS_URL,
        {"base_vector": {"spicy_level": 0.5, "umami_level": 0.5}},
    )
    assert response.status_code == 422, response.text
    assert "未知口味维度" in response.text
    assert _prefs(session_factory) == before


def test_boolean_is_not_a_vector_number(client, session_factory):
    before = _prefs(session_factory)
    for value in (True, False):
        response = _put_json(
            client, PREFS_URL, {"base_vector": {"spicy_level": value}}
        )
        assert response.status_code == 422, response.text
    assert _prefs(session_factory) == before


def test_string_is_not_a_vector_number(client, session_factory):
    before = _prefs(session_factory)
    response = _put_json(
        client, PREFS_URL, {"base_vector": {"spicy_level": "0.5"}}
    )
    assert response.status_code == 422, response.text
    assert _prefs(session_factory) == before


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_vector_is_rejected(client, session_factory, literal):
    before = _prefs(session_factory)
    response = _put_raw(
        client,
        PREFS_URL,
        '{"base_vector":{"spicy_level":%s}}' % literal,
    )
    assert response.status_code == 422, response.text
    assert _prefs(session_factory) == before


def test_vector_accepts_both_bounds(client, session_factory):
    zeros = {key: 0 for key in EIGHT_KEYS}
    assert _put_json(client, PREFS_URL, {"base_vector": zeros}).status_code == 200

    ones = {key: 1 for key in EIGHT_KEYS}
    assert _put_json(client, PREFS_URL, {"base_vector": ones}).status_code == 200

    stored, _, _ = _prefs(session_factory)
    assert set(stored) == set(EIGHT_KEYS)
    assert all(value == 1.0 for value in stored.values())
    assert all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in stored.values())


def test_vector_out_of_range_is_rejected(client, session_factory):
    before = _prefs(session_factory)
    for bad in (-0.01, 1.01, -1, 95):
        response = _put_json(
            client, PREFS_URL, {"base_vector": {"spicy_level": bad}}
        )
        assert response.status_code == 422, (bad, response.text)
    assert _prefs(session_factory) == before


def test_legacy_incomplete_vector_is_completed_on_write(client, session_factory):
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == 1)
            .one()
        )
        row.base_vector = {"spicy_level": 0.2, "oily_level": 0.8}
        session.commit()

    response = _put_json(
        client, PREFS_URL, {"base_vector": {"soup_level": 0.7}}
    )
    assert response.status_code == 200, response.text

    stored, _, _ = _prefs(session_factory)
    assert set(stored) == set(EIGHT_KEYS)
    assert stored["spicy_level"] == pytest.approx(0.2)
    assert stored["oily_level"] == pytest.approx(0.8)
    assert stored["soup_level"] == pytest.approx(0.7)
    assert stored["comfort_level"] == pytest.approx(0.5)


INVALID_HISTORY_STATES = [
    ("unknown_key", {"spicy_level": 0.5, "umami_level": 0.5}),
    ("out_of_range", {"spicy_level": 95, "oily_level": 0.8}),
    ("nan", {"spicy_level": float("nan")}),
    ("infinity", {"spicy_level": float("inf")}),
    ("boolean", {"spicy_level": True}),
    ("string", {"spicy_level": "0.5"}),
    ("null_value", {"spicy_level": None}),
    ("huge_int", {"spicy_level": 10**400}),
    ("not_object", []),
]

UPDATE_PATHS = [
    ("budget_only", {"default_budget": 31}),
    ("veto_only", {"veto_tags": ["香菜"]}),
    ("cuisine_only", {"preferred_cuisines": ["粤菜"]}),
    ("vector_only", {"base_vector": {"soup_level": 0.7}}),
]


@pytest.mark.parametrize(
    "state_id,legacy", INVALID_HISTORY_STATES, ids=[s[0] for s in INVALID_HISTORY_STATES]
)
@pytest.mark.parametrize(
    "path_id,payload", UPDATE_PATHS, ids=[p[0] for p in UPDATE_PATHS]
)
def test_invalid_history_blocks_every_update_path(
    client, session_factory, state_id, legacy, path_id, payload
):
    _set_vector(session_factory, legacy)
    before = _pref_snapshot(session_factory)
    response = _put_json(client, PREFS_URL, payload)
    assert response.status_code == 409, (state_id, path_id, response.text)
    assert _snapshot_json(_pref_snapshot(session_factory)) == _snapshot_json(before)


@pytest.mark.parametrize(
    "state_id,legacy", INVALID_HISTORY_STATES, ids=[s[0] for s in INVALID_HISTORY_STATES]
)
def test_full_vector_cannot_bypass_invalid_history(
    client, session_factory, state_id, legacy
):
    _set_vector(session_factory, legacy)
    before = _pref_snapshot(session_factory)
    full = {key: 0.5 for key in EIGHT_KEYS}
    response = _put_json(client, PREFS_URL, {"base_vector": full})
    assert response.status_code == 409, (state_id, response.text)
    assert _snapshot_json(_pref_snapshot(session_factory)) == _snapshot_json(before)


def test_invalid_history_blocks_combined_update(client, session_factory):
    _set_vector(session_factory, {"spicy_level": 95, "umami_level": 0.5})
    before = _pref_snapshot(session_factory)
    payload = {
        "base_vector": {"spicy_level": 0.4},
        "default_budget": 33,
        "veto_tags": ["香菜"],
        "preferred_cuisines": ["粤菜"],
    }
    response = _put_json(client, PREFS_URL, payload)
    assert response.status_code == 409, response.text
    assert _snapshot_json(_pref_snapshot(session_factory)) == _snapshot_json(before)


@pytest.mark.parametrize(
    "path_id,payload", UPDATE_PATHS, ids=[p[0] for p in UPDATE_PATHS]
)
def test_valid_but_incomplete_history_is_completed_on_every_update_path(
    client, session_factory, path_id, payload
):
    _set_vector(session_factory, {"spicy_level": 0.2, "oily_level": 0.8})
    response = _put_json(client, PREFS_URL, payload)
    assert response.status_code == 200, (path_id, response.text)

    stored, budget, veto = _prefs(session_factory)
    assert set(stored) == set(EIGHT_KEYS)
    assert stored["spicy_level"] == pytest.approx(0.2)
    assert stored["oily_level"] == pytest.approx(0.8)
    for key in set(EIGHT_KEYS) - {"spicy_level", "oily_level", "soup_level"}:
        assert stored[key] == pytest.approx(0.5), key
    if path_id == "budget_only":
        assert budget == pytest.approx(31)
        assert stored["soup_level"] == pytest.approx(0.5)
    elif path_id == "veto_only":
        assert veto == ["香菜"]
        assert stored["soup_level"] == pytest.approx(0.5)
    elif path_id == "cuisine_only":
        assert stored["soup_level"] == pytest.approx(0.5)
        with session_factory() as session:
            row = (
                session.query(UserPreference)
                .filter(UserPreference.user_id == 1)
                .one()
            )
            assert _json(row.preferred_cuisines) == ["粤菜"]
    else:
        assert stored["soup_level"] == pytest.approx(0.7)


def test_valid_complete_history_keeps_vector_on_non_vector_updates(
    client, session_factory
):
    before, _, _ = _prefs(session_factory)
    assert set(before) == set(EIGHT_KEYS)
    for payload in (
        {"default_budget": 31},
        {"veto_tags": ["香菜"]},
        {"preferred_cuisines": ["粤菜"]},
    ):
        response = _put_json(client, PREFS_URL, payload)
        assert response.status_code == 200, response.text
        stored, _, _ = _prefs(session_factory)
        assert stored == before


def test_preferences_nan_budget_returns_422_not_500(client, session_factory):
    before = _prefs(session_factory)
    response = _put_raw(client, PREFS_URL, '{"default_budget":NaN}')
    assert response.status_code == 422, response.text
    assert _prefs(session_factory) == before


@pytest.mark.parametrize(
    "url,payload",
    [
        (RECOMMEND_URL, {"mode_type": "DINE_IN"}),
        ("/api/v1/rooms/create", {"mode_type": "PICNIC"}),
        (FRIDGE_URL, {"ingredient_name": "鸡蛋", "category": "零食"}),
        (
            "/api/v1/users/1/red-black-list",
            {
                "target_type": "SHOP",
                "target_id": 1,
                "list_type": "BLACK",
                "action": "ADD",
            },
        ),
    ],
)
def test_invalid_enums_are_422(client, url, payload):
    response = client.post(url, json=payload, headers=H1)
    assert response.status_code == 422, response.text


def test_preferences_budget_and_veto_bounds(client, session_factory):
    assert _put_json(client, PREFS_URL, {"default_budget": 8}).status_code == 200
    assert _put_json(client, PREFS_URL, {"default_budget": 500}).status_code == 200
    for bad in (7.99, 500.01, -1):
        assert (
            _put_json(client, PREFS_URL, {"default_budget": bad}).status_code == 422
        ), bad

    assert _put_json(client, PREFS_URL, {"veto_tags": ["字" * 16]}).status_code == 200
    before_tag = _prefs(session_factory)
    assert (
        _put_json(client, PREFS_URL, {"veto_tags": ["字" * 17]}).status_code == 422
    )
    assert _prefs(session_factory) == before_tag
    assert (
        _put_json(
            client, PREFS_URL, {"veto_tags": [f"标签{i}" for i in range(21)]}
        ).status_code
        == 422
    )
    assert _prefs(session_factory) == before_tag


# ---------------------------------------------------------------- 推荐：参数与气泡


@pytest.mark.parametrize(
    "payload",
    [
        {"budget": True},
        {"weather_temp": True},
        {"max_distance_meters": True},
        {"limit": True},
        {"exclude_dish_ids": [True]},
    ],
)
def test_recommend_rejects_boolean_numbers(client, session_factory, payload):
    logs_before = _count(session_factory, EatingLog)
    response = client.post(
        RECOMMEND_URL, json={"mode_type": "OUT_DINING", "campus": "SIYUAN", **payload}, headers=H1
    )
    assert response.status_code == 422, response.text
    assert _count(session_factory, EatingLog) == logs_before


@pytest.mark.parametrize(
    "raw",
    [
        '{"mode_type":"OUT_DINING","budget":NaN}',
        '{"mode_type":"OUT_DINING","budget":Infinity}',
        '{"mode_type":"OUT_DINING","override_params":{"lambda_decay":-Infinity}}',
        '{"mode_type":"OUT_DINING","weather_temp":NaN}',
    ],
)
def test_non_finite_body_returns_422_not_500(client, raw):
    response = client.post(
        RECOMMEND_URL,
        content=raw,
        headers={**H1, "Content-Type": "application/json"},
    )
    assert response.status_code == 422, response.text


def test_recommend_rejects_unknown_bubble(client, session_factory):
    prefs_before = _prefs(session_factory)
    response = client.post(
        RECOMMEND_URL,
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "bubbles": ["bogus_bubble"], "limit": 5},
        headers=H1,
    )
    assert response.status_code == 422, response.text
    assert _prefs(session_factory) == prefs_before


def test_recommend_ignores_valid_bubble_outside_mode(client):
    response = client.post(
        RECOMMEND_URL,
        json={
            "mode_type": "HOME_COOKING",
            "bubbles": ["broke_end_month"],
            "limit": 5,
        },
        headers=H1,
    )
    assert response.status_code == 200, response.text
    assert "broke_end_month" in response.json()["bubble_effects"]["ignored"]


def test_recommend_override_bounds(client):
    legal = [
        {"lambda_decay": 0.1},
        {"lambda_decay": 2.0},
        {"omega_group": 0.0},
        {"omega_group": 1.0},
        {
            "alpha_taste": 0.0,
            "beta_weather": 0.0,
            "gamma_budget": 0.0,
            "delta_status": 0.0,
        },
        {"alpha_taste": 1.0, "beta_weather": 1.0, "gamma_budget": 1.0, "delta_status": 1.0},
    ]
    for override in legal:
        response = client.post(
            RECOMMEND_URL,
            json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "override_params": override, "limit": 3},
            headers=H1,
        )
        assert response.status_code == 200, (override, response.text)
        _assert_scores_finite(response.json())

    for override in (
        {"lambda_decay": 0.09},
        {"lambda_decay": 2.01},
        {"omega_group": -0.01},
        {"omega_group": 1.01},
        {"alpha_taste": True},
    ):
        response = client.post(
            RECOMMEND_URL,
            json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "override_params": override},
            headers=H1,
        )
        assert response.status_code == 422, (override, response.text)


def _assert_scores_finite(payload):
    for item in payload["recommendations"]:
        for key in ("taste", "weather", "budget", "freshness", "status"):
            value = item["radar_5d"][key]
            assert math.isfinite(value) and 0.0 <= value <= 100.0, (key, value)
        assert math.isfinite(item["total_score"])
        assert 0.0 <= item["total_score"] <= 100.0
        assert math.isfinite(item["decay_weight"])
        assert 0.0 <= item["decay_weight"] <= 1.0
    params = payload["params_used"]
    assert all(math.isfinite(value) for value in params.values())
    weight_sum = sum(
        params[key]
        for key in ("alpha_taste", "beta_weather", "gamma_budget", "delta_status")
    )
    assert weight_sum == pytest.approx(1.0, abs=1e-3)


def test_recommend_accepts_legal_boundaries_with_finite_scores(client):
    cases = [
        {"budget": 0},
        {"budget": 2000},
        {"weather_temp": -30},
        {"weather_temp": 50},
        {"limit": 1},
        {"limit": 100},
        {"max_distance_meters": 0},
        {"max_distance_meters": 100000},
    ]
    for extra in cases:
        response = client.post(
            RECOMMEND_URL,
            json={"mode_type": "OUT_DINING", "campus": "SIYUAN", **extra},
            headers=H1,
        )
        assert response.status_code == 200, (extra, response.text)
        _assert_scores_finite(response.json())


# ---------------------------------------------------------------- 天气


def test_weather_rejects_non_finite_and_out_of_range(client):
    assert client.get("/api/v1/context/weather", params={"temp": "nan"}).status_code == 422
    assert client.get("/api/v1/context/weather", params={"temp": "inf"}).status_code == 422
    assert client.get("/api/v1/context/weather", params={"temp": "1000"}).status_code == 422
    assert client.get("/api/v1/context/weather", params={"temp": "-40"}).status_code == 422
    assert (
        client.get(
            "/api/v1/context/weather", params={"temp": "20", "weather": "x" * 33}
        ).status_code
        == 422
    )


def test_weather_accepts_legal_boundaries(client):
    low = client.get("/api/v1/context/weather", params={"temp": "-30"})
    high = client.get("/api/v1/context/weather", params={"temp": "50"})
    text = client.get(
        "/api/v1/context/weather", params={"temp": "20", "weather": "晴" * 32}
    )
    for response in (low, high, text):
        assert response.status_code == 200, response.text
        assert math.isfinite(response.json()["temp"])
    assert low.json()["temp"] == -30
    assert high.json()["temp"] == 50


# ---------------------------------------------------------------- 打卡


def test_checkin_rejects_boolean_numbers_and_keeps_log_count(client, session_factory):
    logs_before = _count(session_factory, EatingLog)
    for payload in (
        {"dish_id": True, "mode_type": "OUT_DINING"},
        {"dish_id": 1, "mode_type": "OUT_DINING", "cost_amount": True},
    ):
        response = client.post(CHECKIN_URL, json=payload, headers=H1)
        assert response.status_code == 422, (payload, response.text)
    assert _count(session_factory, EatingLog) == logs_before


def test_checkin_rejects_negative_cost_and_keeps_log_count(client, session_factory):
    logs_before = _count(session_factory, EatingLog)
    response = client.post(
        CHECKIN_URL,
        json={"dish_id": 1, "mode_type": "OUT_DINING", "cost_amount": -0.01},
        headers=H1,
    )
    assert response.status_code == 422, response.text
    assert _count(session_factory, EatingLog) == logs_before


def test_checkin_rejects_unknown_bubble(client, session_factory):
    logs_before = _count(session_factory, EatingLog)
    response = client.post(
        CHECKIN_URL,
        json={"dish_id": 1, "mode_type": "OUT_DINING", "bubbles": ["bogus_bubble"]},
        headers=H1,
    )
    assert response.status_code == 422, response.text
    assert _count(session_factory, EatingLog) == logs_before


def test_checkin_missing_dish_is_404_and_db_unchanged(client, session_factory):
    logs_before = _count(session_factory, EatingLog)
    response = client.post(
        CHECKIN_URL,
        json={"dish_id": 99999, "mode_type": "OUT_DINING"},
        headers=H1,
    )
    assert response.status_code == 404, response.text
    assert _count(session_factory, EatingLog) == logs_before


def test_checkin_mode_mismatch_is_400_and_db_unchanged(client, session_factory, db):
    dish = db.query(Dish).filter(Dish.mode_type == "OUT_DINING").first()
    other_mode = "HOME_COOKING" if dish.mode_type == "OUT_DINING" else "OUT_DINING"
    logs_before = _count(session_factory, EatingLog)
    response = client.post(
        CHECKIN_URL,
        json={"dish_id": dish.id, "mode_type": other_mode},
        headers=H1,
    )
    assert response.status_code == 400, response.text
    assert _count(session_factory, EatingLog) == logs_before


# ---------------------------------------------------------------- 冰箱与引用


def test_fridge_rejects_blank_name_and_keeps_rows(client, session_factory):
    rows_before = _count(session_factory, FridgeInventory, user_id=1)
    for payload in (
        {"ingredient_name": "   "},
        {"ingredient_name": "菜" * 33},
        {"ingredient_name": "鸡蛋", "quantity_desc": "  "},
    ):
        response = client.post(FRIDGE_URL, json=payload, headers=H1)
        assert response.status_code == 422, (payload, response.text)
    assert _count(session_factory, FridgeInventory, user_id=1) == rows_before


def test_fridge_rejects_boolean_expire_days(client, session_factory):
    rows_before = _count(session_factory, FridgeInventory, user_id=1)
    response = client.post(
        FRIDGE_URL,
        json={"ingredient_name": "鸡蛋", "expire_days": True},
        headers=H1,
    )
    assert response.status_code == 422, response.text
    assert _count(session_factory, FridgeInventory, user_id=1) == rows_before


def test_shopping_list_rejects_partially_unknown_dish_ids(client, session_factory, db):
    dish = db.query(Dish).filter(Dish.mode_type == "HOME_COOKING").first()
    fridge_before = _count(session_factory, FridgeInventory)
    response = client.post(
        SHOPPING_URL, json={"dish_ids": [dish.id, 99999]}, headers=H1
    )
    assert response.status_code == 404, response.text
    assert "99999" in response.text
    assert _count(session_factory, FridgeInventory) == fridge_before


def test_shopping_list_rejects_boolean_dish_id(client):
    response = client.post(SHOPPING_URL, json={"dish_ids": [True]}, headers=H1)
    assert response.status_code == 422, response.text


def test_red_black_bool_target_is_rejected(client, session_factory):
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == 1)
            .one()
        )
        favorites_before = _json(row.favorite_dish_ids)
    response = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": True,
            "list_type": "FAV",
            "action": "ADD",
        },
        headers=H1,
    )
    assert response.status_code == 422, response.text
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == 1)
            .one()
        )
        assert _json(row.favorite_dish_ids) == favorites_before


def test_red_black_unknown_target_is_404_and_db_unchanged(client, session_factory):
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == 1)
            .one()
        )
        favorites_before = _json(row.favorite_dish_ids)
    response = client.post(
        "/api/v1/users/1/red-black-list",
        json={
            "target_type": "DISH",
            "target_id": 99999,
            "list_type": "FAV",
            "action": "ADD",
        },
        headers=H1,
    )
    assert response.status_code == 404, response.text
    with session_factory() as session:
        row = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == 1)
            .one()
        )
        assert _json(row.favorite_dish_ids) == favorites_before


# ---------------------------------------------------------------- 房间


def test_room_rejects_boolean_numeric_inputs(client, session_factory):
    rooms_before = _count(session_factory, GroupRoom)
    for payload in (
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": True},
        {"mode_type": "OUT_DINING", "campus": "SIYUAN", "override_params": {"omega_group": True}},
    ):
        response = client.post("/api/v1/rooms/create", json=payload, headers=H1)
        assert response.status_code == 422, (payload, response.text)
    assert _count(session_factory, GroupRoom) == rooms_before
