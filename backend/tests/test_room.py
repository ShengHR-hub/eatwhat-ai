"""模块 4 多人干饭房间：REST + WebSocket 协议回归。

v2.3.2 契约（审查 F03/F04/F05/F11）：
* `POST /api/v1/rooms/create` 带 budget，建房即出 10 道候选；房间码是 6 位数字
* 未 join 就连 WS → **HTTP 403**
* 状态只有 WAITING / SWIPING / FINISHED
* 截止时间落库，断线/刷新都能结算；FINISHED 后禁改票；快照能恢复现场

测试注意：
* `group_room` 里的后台任务不走 `Depends(get_db)`，模块内部直接用 `SessionLocal`，
  测试替换成内存库 session_factory，避免污染 `backend/eatwhat.db`。
* 内存库是 `StaticPool`（单连接共享），两个 WebSocket 同时写会互相踩事务、丢行，
  所以「全员划完即刻结算」用单人房测，双人房只测同步与到点结算。
"""

import time

import pytest
from starlette.websockets import WebSocketDisconnect

from backend.routers import group_room


@pytest.fixture()
def room_env(monkeypatch, session_factory, campus_seed):
    monkeypatch.setattr(group_room, "SessionLocal", session_factory)
    group_room.hub.rooms.clear()
    group_room.hub.timers.clear()
    yield
    for task in list(group_room.hub.timers.values()):
        if not task.done():
            task.cancel()
    group_room.hub.rooms.clear()
    group_room.hub.timers.clear()


def _create(client, mode="OUT_DINING", budget=None, campus="SIYUAN"):
    payload = {"mode_type": mode, "campus": campus}
    if budget is not None:
        payload["budget"] = budget
    response = client.post(
        "/api/v1/rooms/create", json=payload, headers={"X-User-Id": "1"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _drain_until(ws, want, limit=400):
    """吞掉广播，直到收到目标类型；超过上限就失败并说明收到了什么。"""
    seen = []
    for _ in range(limit):
        message = ws.receive_json()
        seen.append(message.get("type"))
        if message.get("type") == want:
            return message
    raise AssertionError(f"没等到 {want}，只收到 {seen}")


def test_create_room_contract(client, room_env):
    room = _create(client, budget=40)
    assert len(room["room_code"]) == 6 and room["room_code"].isdigit()
    assert room["status"] == "WAITING"
    assert room["host_user_id"] == 1
    assert [m["user_id"] for m in room["members"]] == [1]
    assert room["members"][0]["is_host"] is True
    assert room["swipe_seconds"] == 15
    assert room["budget"] == 40
    # F11：候选在建房时就算好
    assert len(room["candidates"]) == 10
    assert room["candidate_count"] == 10
    assert all(c["name"] for c in room["candidates"])
    # 预算软上限：候选价格不超过 40 * 1.25
    assert all(c["price"] <= 50 for c in room["candidates"])


def test_join_room_is_idempotent_and_keeps_candidates(client, room_env):
    room = _create(client)
    code = room["room_code"]
    # F07：身份以请求头为准，第二个人必须带自己的 X-User-Id
    first = client.post(
        f"/api/v1/rooms/{code}/join", json={"user_id": 2, "campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )
    assert first.status_code == 200
    body = first.json()
    assert [m["user_id"] for m in body["members"]] == [1, 2]
    assert len(body["candidates"]) == 10

    again = client.post(
        f"/api/v1/rooms/{code}/join", json={"user_id": 2, "campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )
    assert again.status_code == 200
    assert len(again.json()["members"]) == 2


def test_join_unknown_room_404(client, room_env):
    response = client.post(
        "/api/v1/rooms/000000/join", json={"user_id": 2, "campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )
    assert response.status_code == 404


def test_ws_without_join_is_403(client, room_env):
    """F11：未 join 的握手必须被 HTTP 403 拒绝。"""
    room = _create(client)
    code = room["room_code"]
    with pytest.raises(Exception) as excinfo:
        with client.websocket_connect(f"/ws/room/{code}/2"):
            pass
    err = excinfo.value
    assert (
        "403" in str(err)
        or getattr(err, "code", None) == 403
        or "403" in repr(err)
    ), f"期望 403，实际拿到 {type(err).__name__}: {err}"


def test_host_swipes_alone_and_gets_consensus(client, room_env):
    """单人房：10 张划完的那一刻就结算，不用等倒计时。"""
    room = _create(client)
    code = room["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        state = _drain_until(host, "ROOM_STATE")["snapshot"]
        assert state["status"] == "WAITING"
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        candidates = started["candidates"]
        assert len(candidates) == 10
        assert started["swipe_seconds"] == 15
        assert started["deadline_at"], "截止时间要由服务端下发"

        dish_ids = [c["dish_id"] for c in candidates]
        for index, dish_id in enumerate(dish_ids):
            host.send_json(
                {
                    "type": "SUBMIT_VOTE",
                    "dish_id": dish_id,
                    "vote_type": "VETO" if index == 0 else "LIKE",
                }
            )

        reveal = _drain_until(host, "CONSENSUS_REVEAL")
        assert reveal["winner_dish_id"] in dish_ids
        assert reveal["winner"]["dish_id"] == reveal["winner_dish_id"]
        assert reveal["report"]["dishes"], "共识报告要有每道菜的得分"
        veto_row = next(
            row for row in reveal["report"]["dishes"] if row["dish_id"] == dish_ids[0]
        )
        assert veto_row["masked_by_veto"] is True
        assert veto_row["group_score"] == 0.0

    snapshot = client.get(
        f"/api/v1/rooms/{code}", headers={"X-User-Id": "1"}
    ).json()
    assert snapshot["status"] == "FINISHED"
    assert snapshot["winner_dish_id"] == reveal["winner_dish_id"]
    assert snapshot["winner_dish"]["dish_id"] == reveal["winner_dish_id"]
    assert snapshot["consensus_report"]["dishes"]
    assert snapshot["members"][0]["progress"] == 10
    assert snapshot["my_votes"], "F05：快照要能恢复本人已投票"


def test_two_members_sync_progress_and_timer_settles(client, room_env, monkeypatch):
    monkeypatch.setattr(group_room, "SWIPE_SECONDS", 1)
    room = _create(client)
    code = room["room_code"]
    client.post(
        f"/api/v1/rooms/{code}/join", json={"user_id": 2, "campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        with client.websocket_connect(f"/ws/room/{code}/2") as guest:
            _drain_until(guest, "ROOM_STATE")
            _drain_until(host, "MEMBER_SYNC")

            host.send_json({"type": "START_SWIPING"})
            started = _drain_until(host, "START_SWIPING")
            _drain_until(guest, "START_SWIPING")

            first_dish = started["candidates"][0]["dish_id"]
            guest.send_json(
                {"type": "SUBMIT_VOTE", "dish_id": first_dish, "vote_type": "LIKE"}
            )
            progress = _drain_until(host, "PROGRESS_UPDATE")
            assert progress["user_id"] == 2
            assert progress["progress"]["2"] == 1

            reveal = _drain_until(host, "CONSENSUS_REVEAL")
            assert reveal["winner_dish_id"] in [
                c["dish_id"] for c in started["candidates"]
            ]


def test_only_host_can_start(client, room_env):
    room = _create(client)
    code = room["room_code"]
    client.post(
        f"/api/v1/rooms/{code}/join", json={"user_id": 2, "campus": "SIYUAN"}, headers={"X-User-Id": "2"}
    )

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        with client.websocket_connect(f"/ws/room/{code}/2") as guest:
            _drain_until(guest, "ROOM_STATE")
            _drain_until(host, "MEMBER_SYNC")

            guest.send_json({"type": "START_SWIPING"})
            error = _drain_until(guest, "ERROR")
            assert "房主" in error["detail"]


def test_votes_after_finish_are_rejected(client, room_env):
    """F04：结算后不许再改票。"""
    room = _create(client)
    code = room["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        dish_ids = [c["dish_id"] for c in started["candidates"]]
        for dish_id in dish_ids:
            host.send_json(
                {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "LIKE"}
            )
        _drain_until(host, "CONSENSUS_REVEAL")

        host.send_json(
            {"type": "SUBMIT_VOTE", "dish_id": dish_ids[0], "vote_type": "VETO"}
        )
        error = _drain_until(host, "ERROR")
        assert "结束" in error["detail"]


def test_settlement_survives_all_disconnects(client, room_env, monkeypatch):
    """F03：最后一个人断开不取消结算，到点后 GET 必须看到 FINISHED。"""
    monkeypatch.setattr(group_room, "SWIPE_SECONDS", 1)
    room = _create(client)
    code = room["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        _drain_until(host, "START_SWIPING")
        host.send_json(
            {
                "type": "SUBMIT_VOTE",
                "dish_id": client.get(
                    f"/api/v1/rooms/{code}", headers={"X-User-Id": "1"}
                ).json()["candidates"][0]["dish_id"],
                "vote_type": "LIKE",
            }
        )
        _drain_until(host, "PROGRESS_UPDATE")
    # 连接全部断开，谁都不在线
    time.sleep(1.4)
    snapshot = client.get(
        f"/api/v1/rooms/{code}", headers={"X-User-Id": "1"}
    ).json()
    assert snapshot["status"] == "FINISHED", "断线后仍必须按截止时间结算"
    assert snapshot["consensus_report"] is not None


def test_snapshot_exposes_deadline_for_recovery(client, room_env):
    """F05：SWIPING 阶段的快照要带上截止时间与本人票，刷新才能恢复。"""
    room = _create(client)
    code = room["room_code"]
    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        host.send_json(
            {
                "type": "SUBMIT_VOTE",
                "dish_id": started["candidates"][0]["dish_id"],
                "vote_type": "LIKE",
            }
        )
        _drain_until(host, "PROGRESS_UPDATE")

        snapshot = client.get(
            f"/api/v1/rooms/{code}", headers={"X-User-Id": "1"}
        ).json()
        assert snapshot["status"] == "SWIPING"
        assert snapshot["deadline_at"]
        assert snapshot["remaining_ms"] > 0
        assert len(snapshot["candidates"]) == 10
        assert snapshot["my_votes"]


def test_bad_votes_are_rejected(client, room_env):
    room = _create(client)
    code = room["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        _drain_until(host, "START_SWIPING")

        host.send_json({"type": "SUBMIT_VOTE", "dish_id": 99999, "vote_type": "LIKE"})
        error = _drain_until(host, "ERROR")
        assert "候选" in error["detail"]

        host.send_json({"type": "SUBMIT_VOTE", "dish_id": 1, "vote_type": "MAYBE"})
        error = _drain_until(host, "ERROR")
        assert "投票格式" in error["detail"]

        host.send_json({"type": "DANCE"})
        error = _drain_until(host, "ERROR")
        assert "未知指令" in error["detail"]

def test_omega_group_follows_algo_config(client, session_factory):
    """审查 F10：群组 ω 读 algo_configs，且建房快照优先。"""
    from backend.models import AlgoConfig, GroupRoom
    from backend.routers import group_room

    session = session_factory()
    try:
        config = (
            session.query(AlgoConfig)
            .filter(AlgoConfig.config_name == "default_production")
            .first()
        )
        assert config is not None
        config.omega_group = 0.83
        session.commit()

        plain_room = GroupRoom(room_code="000001", host_user_id=1, mode_type="OUT_DINING")
        assert abs(group_room._omega_group(session, plain_room) - 0.83) < 1e-9

        # 建房快照优先于 DB 配置：沙盒里调过的 ω 必须能带进这一局
        snapshot_room = GroupRoom(
            room_code="000002",
            host_user_id=1,
            mode_type="OUT_DINING",
            algo_params={"omega_group": 0.2},
        )
        assert abs(group_room._omega_group(session, snapshot_room) - 0.2) < 1e-9

        # 没有配置行时回退默认值，而不是崩掉（跑完把配置行放回去，避免污染同库其它用例）
        session.query(AlgoConfig).delete()
        session.commit()
        try:
            assert abs(group_room._omega_group(session, plain_room) - 0.5) < 1e-9
        finally:
            session.add(AlgoConfig(config_name="default_production", omega_group=0.5))
            session.commit()
    finally:
        session.close()


def test_room_snapshots_override_params_at_create(client, session_factory):
    """F10/v2.3.6：override_params 在建房那一刻冻结，且群组只保存 omega_group。"""
    from backend.models import GroupRoom
    from backend.routers.group_room import _omega_group

    response = client.post(
        "/api/v1/rooms/create",
        json={
            "mode_type": "OUT_DINING",
            "campus": "SIYUAN",
            "override_params": {"omega_group": 0.9, "lambda_decay": 1.4},
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    code = response.json()["room_code"]
    assert response.json()["omega_group"] == 0.9

    session = session_factory()
    try:
        room = session.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        assert room.algo_params == {"omega_group": 0.9}
        assert abs(_omega_group(session, room) - 0.9) < 1e-9
    finally:
        session.close()


def test_room_rejects_bad_override_params(client):
    response = client.post(
        "/api/v1/rooms/create",
        json={
            "mode_type": "OUT_DINING",
            "campus": "SIYUAN",
            "override_params": {"omega_group": 3.0},
        },
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 422





def test_two_members_full_votes_settle_once(client, room_env, session_factory):
    """两人各投满 10 票 → 早结算只发生一次，且票数完整。

    独立审查指出：此前「全员划完即刻结算」只用单人房测过，
    真实双人路径（_maybe_settle_early）从未在两人各有 10 票的情况下验证。
    这里不走双 WS（内存库是 StaticPool，两个连接会互相踩事务），
    直接构造 20 条票后调早结算，覆盖判定 + 抢锁 + 幂等三段。
    """
    import asyncio

    from backend.models import GroupRoom, RoomVote, utcnow

    room = _create(client)
    code = room["room_code"]
    client.post(
        f"/api/v1/rooms/{code}/join",
        json={"user_id": 2, "campus": "SIYUAN"},
        headers={"X-User-Id": "2"},
    )

    with session_factory() as db:
        row = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        dish_ids = [int(i) for i in row.candidate_dish_ids]
        row.status = "SWIPING"
        row.started_at = utcnow()
        row.deadline_at = utcnow() + __import__("datetime").timedelta(seconds=15)
        for uid in (1, 2):
            for dish_id in dish_ids:
                db.add(
                    RoomVote(
                        room_code=code,
                        user_id=uid,
                        dish_id=dish_id,
                        vote_type="LIKE",
                        voted_at=utcnow(),
                    )
                )
        db.commit()
        assert db.query(RoomVote).filter(RoomVote.room_code == code).count() == 20

    first = asyncio.run(group_room._maybe_settle_early(code))
    assert first is True, "两人都投满后应立即结算"

    second = asyncio.run(group_room._maybe_settle_early(code))
    assert second is False, "已结算的房间再次调用必须幂等返回 False"

    with session_factory() as db:
        row = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        assert row.status == "FINISHED"
        assert row.settled_at is not None
        assert row.consensus_report is not None
        assert row.winner_dish_id is not None
        # 结算不改写票：20 条必须原样保留
        assert db.query(RoomVote).filter(RoomVote.room_code == code).count() == 20


def test_early_settle_waits_when_one_member_incomplete(client, room_env, session_factory):
    """只有一个人投满时不结算——否则会把另一个人的票当成超时。"""
    import asyncio

    from backend.models import GroupRoom, RoomVote, utcnow

    room = _create(client)
    code = room["room_code"]
    client.post(
        f"/api/v1/rooms/{code}/join",
        json={"user_id": 2, "campus": "SIYUAN"},
        headers={"X-User-Id": "2"},
    )

    with session_factory() as db:
        row = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        dish_ids = [int(i) for i in row.candidate_dish_ids]
        row.status = "SWIPING"
        row.started_at = utcnow()
        row.deadline_at = utcnow() + __import__("datetime").timedelta(seconds=15)
        # 只有 1 号投满
        for dish_id in dish_ids:
            db.add(
                RoomVote(
                    room_code=code,
                    user_id=1,
                    dish_id=dish_id,
                    vote_type="LIKE",
                    voted_at=utcnow(),
                )
            )
        db.commit()

    assert asyncio.run(group_room._maybe_settle_early(code)) is False

    with session_factory() as db:
        row = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        assert row.status == "SWIPING"
        assert row.settled_at is None
