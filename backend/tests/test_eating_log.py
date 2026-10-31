import pytest

from backend.models import Dish


def _dish(db, name: str, mode: str = "OUT_DINING") -> Dish:
    dish = (
        db.query(Dish).filter(Dish.name == name, Dish.mode_type == mode).first()
    )
    assert dish is not None
    return dish


def test_checkin_triggers_same_day_decay(client, db):
    dish = _dish(db, "麻辣香锅")
    before = client.get(
        "/api/v1/logs/stats/1", headers={"X-User-Id": "1"}
    ).json()
    response = client.post(
        "/api/v1/logs/checkin",
        json={
            "dish_id": dish.id,
            "mode_type": "OUT_DINING",
            "bubbles": ["craving_heavy"],
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["log_id"] > 0
    assert body["new_decay_weight"] == pytest.approx(0.05)

    after = client.get(
        "/api/v1/logs/stats/1", headers={"X-User-Id": "1"}
    ).json()
    assert after["meals_this_week"] == before["meals_this_week"] + 1
    assert after["weekly_expense"] == pytest.approx(
        before["weekly_expense"] + float(dish.price_or_cost), abs=0.01
    )


def test_stats_returns_cooling_board_and_pie(client, db):
    response = client.get("/api/v1/logs/stats/1", headers={"X-User-Id": "1"})
    assert response.status_code == 200
    body = response.json()
    assert body["cooling_dishes"]
    hot_dish = next(
        item for item in body["cooling_dishes"] if item["name"] == "麻辣香锅"
    )
    assert hot_dish["decay_weight"] == pytest.approx(0.05)
    assert hot_dish["cooling_percent"] == pytest.approx(95.0)
    assert hot_dish["status"] == "COOLING"
    assert body["weekly_expense"] > 0
    assert body["meals_this_week"] >= 3
    assert body["cuisine_pie_data"]
    assert all(item["value"] > 0 for item in body["cuisine_pie_data"])


def test_checkin_header_wins_over_body(client, db):
    """F07：身份以 X-User-Id 请求头为准，body 的 user_id 不能反过来压过它。"""
    dish = _dish(db, "番茄炒蛋", "HOME_COOKING")
    response = client.post(
        "/api/v1/logs/checkin",
        json={
            "user_id": 2,
            "dish_id": dish.id,
            "mode_type": "HOME_COOKING",
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200

    # 记在请求头指定的用户 1 名下
    user1 = client.get(
        "/api/v1/logs/stats/1", headers={"X-User-Id": "1"}
    ).json()
    assert any(item["dish_id"] == dish.id for item in user1["cooling_dishes"])

    # 不能同时算成用户 2 的打卡
    user2 = client.get(
        "/api/v1/logs/stats/2", headers={"X-User-Id": "2"}
    ).json()
    assert not any(item["dish_id"] == dish.id for item in user2["cooling_dishes"])

def test_checkin_mode_mismatch_returns_400(client, db):
    dish = _dish(db, "麻辣香锅")
    response = client.post(
        "/api/v1/logs/checkin",
        json={"dish_id": dish.id, "mode_type": "HOME_COOKING"},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 400


def test_checkin_unknown_dish_returns_404(client):
    response = client.post(
        "/api/v1/logs/checkin",
        json={"dish_id": 99999, "mode_type": "OUT_DINING"},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 404


def test_stats_unknown_user_returns_404(client):
    assert (
        client.get(
            "/api/v1/logs/stats/999", headers={"X-User-Id": "999"}
        ).status_code
        == 404
    )
