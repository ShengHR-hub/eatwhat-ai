"""S01 身份与资源归属专项回归（F07）。

契约（MASTER_SPEC v2.3.5 第五章 0）：
* 所有需要用户上下文的 /api/v1 请求必须带 X-User-Id；
* X-User-Id 必须解析为已存在的用户，未知用户 404；
* 缺失 / 空 / 非整数 / 0 / 负数 / 超范围身份都是明确 4xx，不回退用户 1；
* body/query 的 user_id、host_user_id 不能覆盖请求头，冲突以请求头为准并记日志；
* 路径 user_id 与请求头冲突沿用现有 403 语义（SSOT 未裁决，作为设计缺口记录）；
* 房间 GET/WS 只对已 join 的成员开放；非房主不能开局。
"""

import logging

import pytest

from backend.models import EatingLog, FridgeInventory, GroupRoom, UserPreference


def _prefs_snapshot(db, user_id: int) -> dict:
    prefs = (
        db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    )
    return {
        "budget": prefs.default_budget,
        "veto": list(prefs.veto_tags or []),
        "favorite": list(prefs.favorite_dish_ids or []),
        "black_dish": list(prefs.blacklist_dish_ids or []),
        "black_restaurant": list(prefs.blacklist_restaurant_ids or []),
    }


def _fridge_snapshot(db, user_id: int) -> list:
    rows = (
        db.query(FridgeInventory)
        .filter(FridgeInventory.user_id == user_id)
        .order_by(FridgeInventory.ingredient_name)
        .all()
    )
    return [
        (row.ingredient_name, row.category, row.quantity_desc, row.expire_days)
        for row in rows
    ]


def _log_ids(db, user_id: int) -> list:
    return [
        row.id
        for row in db.query(EatingLog)
        .filter(EatingLog.user_id == user_id)
        .order_by(EatingLog.id)
        .all()
    ]


def _home_dish_id(db) -> int:
    from backend.models import Dish

    dish = (
        db.query(Dish)
        .filter(Dish.mode_type == "HOME_COOKING", Dish.name == "番茄炒蛋")
        .first()
    )
    assert dish is not None
    return dish.id


def _assert_ws_rejected(client, url: str, **kwargs) -> None:
    with pytest.raises(Exception) as excinfo:
        with client.websocket_connect(url, **kwargs):
            pass
    err = excinfo.value
    assert (
        "403" in str(err)
        or getattr(err, "code", None) in (403, 1008)
        or "403" in repr(err)
    ), f"期望握手被拒，实际 {type(err).__name__}: {err}"


@pytest.fixture()
def room_env(monkeypatch, session_factory, campus_seed):
    from backend.routers import group_room

    monkeypatch.setattr(group_room, "SessionLocal", session_factory)
    group_room.hub.rooms.clear()
    group_room.hub.timers.clear()
    yield
    for task in list(group_room.hub.timers.values()):
        if not task.done():
            task.cancel()
    group_room.hub.rooms.clear()
    group_room.hub.timers.clear()


# ————————————————————— 公开入口 —————————————————————


def test_public_endpoints_work_without_identity(client):
    for path in (
        "/health",
        "/api/v1/users/demo-list",
        "/api/v1/context/weather",
        "/api/v1/catalog/dishes?ids=1",
        "/api/v1/catalog/restaurants?ids=1",
    ):
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)


def test_demo_list_is_not_bound_to_current_user(client):
    without = client.get("/api/v1/users/demo-list").json()
    as_user_3 = client.get(
        "/api/v1/users/demo-list", headers={"X-User-Id": "3"}
    ).json()
    assert without == as_user_3
    assert {row["id"] for row in without} == {1, 2, 3, 4}


# ————————————————————— 缺失 / 非法 / 未知身份 —————————————————————


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "/api/v1/users/1/profile", None),
        ("put", "/api/v1/users/1/preferences", {"default_budget": 30}),
        (
            "post",
            "/api/v1/users/1/red-black-list",
            {
                "target_type": "DISH",
                "target_id": 24,
                "list_type": "BLACK",
                "action": "ADD",
            },
        ),
        ("post", "/api/v1/recommend/single", {"mode_type": "OUT_DINING", "campus": "SIYUAN"}),
        (
            "post",
            "/api/v1/logs/checkin",
            {"dish_id": 1, "mode_type": "OUT_DINING"},
        ),
        ("get", "/api/v1/logs/stats/1", None),
        ("get", "/api/v1/fridge/1", None),
        (
            "post",
            "/api/v1/fridge/1",
            {"ingredient_name": "鸡蛋", "action": "ADD"},
        ),
        ("post", "/api/v1/fridge/shopping-list", {"dish_ids": [61]}),
        ("post", "/api/v1/rooms/create", {"mode_type": "OUT_DINING", "campus": "SIYUAN"}),
        ("post", "/api/v1/rooms/000000/join", {"campus": "SIYUAN"}),
        ("get", "/api/v1/rooms/000000", None),
    ],
)
def test_private_endpoints_reject_missing_identity(client, method, path, body):
    kwargs = {"json": body} if method != "get" else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 422, (path, response.status_code, response.text)


@pytest.mark.parametrize("value", ["abc", "", "0", "-1", "1.5", str(2**70)])
def test_invalid_identity_values_are_rejected(client, value):
    response = client.post(
        "/api/v1/recommend/single",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": value},
    )
    assert response.status_code == 422, (value, response.status_code, response.text)
    assert response.status_code != 200


def test_unknown_identity_returns_404_on_all_entry_shapes(client):
    cases = [
        ("get", "/api/v1/users/999/profile", None),
        ("put", "/api/v1/users/999/preferences", {"default_budget": 30}),
        (
            "post",
            "/api/v1/users/999/red-black-list",
            {
                "target_type": "DISH",
                "target_id": 24,
                "list_type": "BLACK",
                "action": "ADD",
            },
        ),
        ("post", "/api/v1/recommend/single", {"mode_type": "OUT_DINING", "campus": "SIYUAN"}),
        ("post", "/api/v1/logs/checkin", {"dish_id": 1, "mode_type": "OUT_DINING"}),
        ("get", "/api/v1/logs/stats/999", None),
        ("get", "/api/v1/fridge/999", None),
        ("post", "/api/v1/fridge/999", {"ingredient_name": "鸡蛋"}),
        ("post", "/api/v1/fridge/shopping-list", {"dish_ids": [61]}),
        ("post", "/api/v1/rooms/create", {"mode_type": "OUT_DINING", "campus": "SIYUAN"}),
        ("post", "/api/v1/rooms/000000/join", {"campus": "SIYUAN"}),
        ("get", "/api/v1/rooms/000000", None),
    ]
    for method, path, body in cases:
        kwargs = {"json": body} if method != "get" else {}
        response = getattr(client, method)(
            path, headers={"X-User-Id": "999"}, **kwargs
        )
        assert response.status_code == 404, (path, response.status_code, response.text)


def test_missing_and_invalid_identity_are_logged(client, caplog):
    with caplog.at_level(logging.WARNING, logger="eatwhat.identity"):
        client.post("/api/v1/recommend/single", json={"mode_type": "OUT_DINING", "campus": "SIYUAN"})
        client.post(
            "/api/v1/recommend/single",
            json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
            headers={"X-User-Id": "abc"},
        )
        client.post(
            "/api/v1/recommend/single",
            json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
            headers={"X-User-Id": "999"},
        )
    text = caplog.text
    assert "reason=missing_header" in text
    assert "reason=invalid_header" in text
    assert "reason=unknown_user" in text


# ————————————————————— 路径型跨用户读写 —————————————————————


def test_header_cannot_read_other_users_private_paths(client, session_factory):
    db = session_factory()
    try:
        before = {
            2: {
                "prefs": _prefs_snapshot(db, 2),
                "fridge": _fridge_snapshot(db, 2),
                "logs": _log_ids(db, 2),
            }
        }
    finally:
        db.close()

    for path in (
        "/api/v1/users/2/profile",
        "/api/v1/logs/stats/2",
        "/api/v1/fridge/2",
    ):
        response = client.get(path, headers={"X-User-Id": "1"})
        assert response.status_code == 403, (path, response.status_code, response.text)
        assert "不能操作其他用户的资源" in response.text

    db = session_factory()
    try:
        assert _prefs_snapshot(db, 2) == before[2]["prefs"]
        assert _fridge_snapshot(db, 2) == before[2]["fridge"]
        assert _log_ids(db, 2) == before[2]["logs"]
    finally:
        db.close()


def test_header_cannot_write_other_users_private_paths(client, session_factory):
    db = session_factory()
    try:
        before = _prefs_snapshot(db, 2)
        fridge_before = _fridge_snapshot(db, 2)
        logs_before = _log_ids(db, 2)
        dish_id = _home_dish_id(db)
    finally:
        db.close()

    requests = [
        (
            "put",
            "/api/v1/users/2/preferences",
            {"default_budget": 99, "veto_tags": ["花生"]},
        ),
        (
            "post",
            "/api/v1/users/2/red-black-list",
            {
                "target_type": "DISH",
                "target_id": dish_id,
                "list_type": "BLACK",
                "action": "ADD",
            },
        ),
        (
            "post",
            "/api/v1/fridge/2",
            {"ingredient_name": "越权食材", "action": "ADD"},
        ),
    ]
    for method, path, body in requests:
        response = getattr(client, method)(
            path, json=body, headers={"X-User-Id": "1"}
        )
        assert response.status_code == 403, (path, response.status_code, response.text)

    db = session_factory()
    try:
        assert _prefs_snapshot(db, 2) == before
        assert _fridge_snapshot(db, 2) == fridge_before
        assert _log_ids(db, 2) == logs_before
        assert (
            db.query(FridgeInventory)
            .filter(FridgeInventory.ingredient_name == "越权食材")
            .count()
            == 0
        )
    finally:
        db.close()


def test_path_conflict_is_logged(client, caplog):
    with caplog.at_level(logging.WARNING, logger="eatwhat.identity"):
        response = client.get(
            "/api/v1/fridge/2", headers={"X-User-Id": "1"}
        )
    assert response.status_code == 403
    assert "reason=path_header_mismatch" in caplog.text
    assert "path_user_id=2" in caplog.text


# ————————————————————— body 身份冲突 —————————————————————


def test_checkin_body_user_id_cannot_write_other_user(
    client, session_factory, caplog
):
    db = session_factory()
    try:
        dish_id = _home_dish_id(db)
        user2_before = _log_ids(db, 2)
        user1_before = _log_ids(db, 1)
    finally:
        db.close()

    with caplog.at_level(logging.WARNING, logger="eatwhat.identity"):
        response = client.post(
            "/api/v1/logs/checkin",
            json={
                "user_id": 2,
                "dish_id": dish_id,
                "mode_type": "HOME_COOKING",
            },
            headers={"X-User-Id": "1"},
        )
    assert response.status_code == 200, response.text

    db = session_factory()
    try:
        assert _log_ids(db, 2) == user2_before
        after_user1 = _log_ids(db, 1)
        assert len(after_user1) == len(user1_before) + 1
    finally:
        db.close()
    assert "identity_conflict" in caplog.text
    assert "field=user_id" in caplog.text
    assert "resolution=header" in caplog.text


def test_recommend_body_user_id_uses_header_identity(client):
    """用户 1 黑榜有白切鸡饭；body 写 2 不能把身份换成用户 2。"""
    response = client.post(
        "/api/v1/recommend/single",
        json={"user_id": 2, "mode_type": "OUT_DINING", "campus": "SIYUAN", "limit": 100},
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200, response.text
    names = {item["name"] for item in response.json()["recommendations"]}
    assert "白切鸡饭" not in names
    assert "凉拌折耳根" not in names


def test_shopping_list_body_user_id_uses_header_fridge(client):
    body = {"user_id": 2, "dish_ids": [61]}
    as_user_1_conflict = client.post(
        "/api/v1/fridge/shopping-list", json=body, headers={"X-User-Id": "1"}
    )
    as_user_1 = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": [61]},
        headers={"X-User-Id": "1"},
    )
    as_user_2 = client.post(
        "/api/v1/fridge/shopping-list",
        json={"dish_ids": [61]},
        headers={"X-User-Id": "2"},
    )
    assert as_user_1_conflict.status_code == 200
    assert as_user_1_conflict.json() == as_user_1.json()
    assert as_user_1.json() != as_user_2.json()


# ————————————————————— 房间 REST —————————————————————


def test_room_create_body_host_cannot_override_header(
    client, session_factory, room_env, caplog
):
    with caplog.at_level(logging.WARNING, logger="eatwhat.identity"):
        response = client.post(
            "/api/v1/rooms/create",
            json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "host_user_id": 2},
            headers={"X-User-Id": "1"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["host_user_id"] == 1
    assert [m["user_id"] for m in body["members"]] == [1]

    db = session_factory()
    try:
        room = db.query(GroupRoom).filter(GroupRoom.room_code == body["room_code"]).first()
        assert room.host_user_id == 1
        assert list(room.member_user_ids) == [1]
        assert (
            db.query(GroupRoom).filter(GroupRoom.host_user_id == 2).count() == 0
        )
    finally:
        db.close()
    assert "identity_conflict" in caplog.text
    assert "field=host_user_id" in caplog.text
    assert "resolution=header" in caplog.text


def test_room_join_body_user_id_cannot_override_header(client, room_env):
    created = client.post(
        "/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    assert created.status_code == 200
    code = created.json()["room_code"]

    conflict = client.post(
        f"/api/v1/rooms/{code}/join",
        json={"user_id": 2, "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    assert conflict.status_code == 200
    assert [m["user_id"] for m in conflict.json()["members"]] == [1]

    second = client.post(
        f"/api/v1/rooms/{code}/join",
        json={"user_id": 1, "campus": "SIYUAN"},
        headers={"X-User-Id": "2"},
    )
    assert second.status_code == 200
    assert [m["user_id"] for m in second.json()["members"]] == [1, 2]

    repeated = client.post(
        f"/api/v1/rooms/{code}/join", json={"campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )
    assert repeated.status_code == 200
    assert [m["user_id"] for m in repeated.json()["members"]] == [1, 2]


def test_room_get_is_member_only(client, session_factory, room_env):
    created = client.post(
        "/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    assert created.status_code == 200
    code = created.json()["room_code"]

    outsider = client.get(f"/api/v1/rooms/{code}", headers={"X-User-Id": "2"})
    assert outsider.status_code == 403
    assert "还没加入" in outsider.text or "不是房间成员" in outsider.text
    assert created.json()["candidates"][0]["name"] not in outsider.text

    host_view = client.get(f"/api/v1/rooms/{code}", headers={"X-User-Id": "1"})
    assert host_view.status_code == 200
    assert host_view.json()["room_code"] == code

    joined = client.post(
        f"/api/v1/rooms/{code}/join", json={"campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )
    assert joined.status_code == 200
    member_view = client.get(f"/api/v1/rooms/{code}", headers={"X-User-Id": "2"})
    assert member_view.status_code == 200


def test_non_host_cannot_start_room(client, room_env):
    created = client.post(
        "/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    code = created.json()["room_code"]
    client.post(f"/api/v1/rooms/{code}/join", json={"campus": "SIYUAN"}, headers={"X-User-Id": "2"})

    with client.websocket_connect(f"/ws/room/{code}/2") as guest:
        while True:
            message = guest.receive_json()
            if message.get("type") == "ROOM_STATE":
                break
        guest.send_json({"type": "START_SWIPING"})
        while True:
            message = guest.receive_json()
            if message.get("type") == "ERROR":
                assert "房主" in message["detail"]
                break


# ————————————————————— WebSocket —————————————————————


def test_ws_rejects_unknown_user_and_non_member(client, room_env):
    created = client.post(
        "/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    code = created.json()["room_code"]

    _assert_ws_rejected(client, f"/ws/room/{code}/999")
    _assert_ws_rejected(client, f"/ws/room/{code}/2")


def test_ws_rejects_path_header_conflict(client, room_env):
    created = client.post(
        "/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    code = created.json()["room_code"]
    _assert_ws_rejected(
        client,
        f"/ws/room/{code}/1",
        headers={"X-User-Id": "2"},
    )


def test_ws_accepts_joined_member(client, room_env):
    created = client.post(
        "/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN"},
        headers={"X-User-Id": "1"},
    )
    code = created.json()["room_code"]
    client.post(f"/api/v1/rooms/{code}/join", json={"campus": "SIYUAN"}, headers={"X-User-Id": "2"})

    with client.websocket_connect(f"/ws/room/{code}/2") as guest:
        while True:
            message = guest.receive_json()
            if message.get("type") == "ROOM_STATE":
                snapshot = message["snapshot"]
                assert snapshot["room_code"] == code
                assert snapshot["host_user_id"] == 1
                assert [m["user_id"] for m in snapshot["members"]] == [1, 2]
                break
