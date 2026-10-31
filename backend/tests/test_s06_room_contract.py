"""S06：多人后端协议与参数链专项（v2.3.6）。

覆盖用户 2026-10-27 裁决：
* 校区严格过滤：外食只取同校区门店，NULL/缺失门店排除；跨校区 join 409；
* 历史 NULL 房间仅 WAITING 首个 join 绑定并同事务重算，0 候选回滚拒绝；
* join 重算全员硬约束；MEMBER_SYNC 带最新候选；
* 客户端 TIMEOUT 拒绝；缺席=内部 60；重复投票 last-write-wins；
* ω 建房冻结、只存 omega_group、快照/报告可追溯；
* 原子结算、重复结算幂等、失败回滚、重启/无客户端扫描；
* 固定投票矩阵手算 ω=0/0.5/1 的分数与赢家。
"""

import asyncio
import contextlib
import sqlite3
import threading
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.algorithms.vector_spec import FEATURE_KEYS
from backend.database import Base
from backend.models import (
    AlgoConfig,
    Dish,
    GroupRoom,
    Restaurant,
    RoomVote,
    User,
    UserPreference,
)
from backend.routers import group_room
from backend.routers.group_room import utcnow
from backend.scripts import migrate_s06_room_contract

H1 = {"X-User-Id": "1"}
H2 = {"X-User-Id": "2"}


@pytest.fixture()
def room_env(monkeypatch, session_factory, campus_seed):
    monkeypatch.setattr(group_room, "SessionLocal", session_factory)
    group_room.hub.rooms.clear()
    group_room.hub.timers.clear()
    with group_room._room_locks_guard:
        group_room._room_locks.clear()
    yield
    for task in list(group_room.hub.timers.values()):
        if not task.done():
            task.cancel()
    group_room.hub.rooms.clear()
    group_room.hub.timers.clear()
    with group_room._room_locks_guard:
        group_room._room_locks.clear()


def _create(client, **overrides):
    payload = {"mode_type": "OUT_DINING", "campus": "SIYUAN"}
    payload.update(overrides)
    return client.post("/api/v1/rooms/create", json=payload, headers=H1)


def _join(client, code, user_id=2, campus="SIYUAN"):
    return client.post(
        f"/api/v1/rooms/{code}/join",
        json={"campus": campus},
        headers={"X-User-Id": str(user_id)},
    )


def _drain_until(ws, want, limit=400, predicate=None):
    seen = []
    for _ in range(limit):
        message = ws.receive_json()
        seen.append(message.get("type"))
        if message.get("type") == want and (predicate is None or predicate(message)):
            return message
    raise AssertionError(f"没等到 {want}，只收到 {seen}")


def _vec(**overrides):
    vector = {key: 0.0 for key in FEATURE_KEYS}
    vector.update(overrides)
    return vector


def _set_all_campus(session_factory, value):
    with session_factory() as session:
        session.query(Restaurant).update({Restaurant.campus: value})
        session.commit()


def _restaurant_dish_ids(session, restaurant_id):
    return {
        row.id
        for row in session.query(Dish)
        .filter(Dish.restaurant_id == restaurant_id)
        .all()
    }


# ————————————————————— 建房 / 校区 —————————————————————


def test_create_requires_campus_and_echoes_snapshot(client, room_env):
    missing = client.post(
        "/api/v1/rooms/create", json={"mode_type": "OUT_DINING"}, headers=H1
    )
    assert missing.status_code == 422

    caotang = _create(client, campus="JIANDA_CAOTANG")
    assert caotang.status_code == 422

    response = _create(client, budget=40)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["room_code"]) == 6 and body["room_code"].isdigit()
    assert body["campus"] == "SIYUAN"
    assert body["omega_group"] == 0.5
    assert body["status"] == "WAITING"
    assert len(body["candidates"]) == 10
    assert all(c["price"] <= 50 for c in body["candidates"])


def test_out_dining_campus_filter_is_strict(client, room_env, session_factory):
    with session_factory() as session:
        restaurants = session.query(Restaurant).order_by(Restaurant.id).all()
        siyuan = restaurants[0]
        null_store = restaurants[1]
        session.query(Restaurant).update({Restaurant.campus: "JIANDA_YANTA"})
        siyuan.campus = "SIYUAN"
        null_store.campus = None
        session.commit()
        siyuan_dish_ids = _restaurant_dish_ids(session, siyuan.id)
        null_dish_ids = _restaurant_dish_ids(session, null_store.id)
        assert siyuan_dish_ids and null_dish_ids

    siyuan_room = _create(client).json()
    siyuan_candidates = {c["dish_id"] for c in siyuan_room["candidates"]}
    assert siyuan_candidates == siyuan_dish_ids
    assert not (siyuan_candidates & null_dish_ids)

    jianada_room = _create(client, campus="JIANDA_YANTA").json()
    jianada_candidates = {c["dish_id"] for c in jianada_room["candidates"]}
    assert len(jianada_candidates) == 10
    assert not (jianada_candidates & siyuan_dish_ids)
    assert not (jianada_candidates & null_dish_ids)

    # NULL 门店一律排除：全 NULL 时外食房间 0 候选；下厨共享不受影响。
    _set_all_campus(session_factory, None)
    empty = _create(client).json()
    assert empty["candidates"] == []
    assert empty["candidate_count"] == 0
    home = _create(client, mode_type="HOME_COOKING").json()
    assert len(home["candidates"]) == 10


def test_join_cross_campus_409_and_idempotent(client, room_env, session_factory):
    code = _create(client).json()["room_code"]

    cross = _join(client, code, campus="JIANDA_YANTA")
    assert cross.status_code == 409
    assert "跨校区" in cross.text
    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        assert [int(i) for i in room.member_user_ids] == [1]

    same = _join(client, code)
    assert same.status_code == 200, same.text
    assert [m["user_id"] for m in same.json()["members"]] == [1, 2]

    again = _join(client, code)
    assert again.status_code == 200
    assert [m["user_id"] for m in again.json()["members"]] == [1, 2]

    existing_cross = _join(client, code, campus="JIANDA_YANTA")
    assert existing_cross.status_code == 409


def test_join_recomputes_all_member_constraints(client, room_env, session_factory):
    host_room = _create(client).json()
    code = host_room["room_code"]
    host_ids = [c["dish_id"] for c in host_room["candidates"]]
    blacklisted = host_ids[0]

    with session_factory() as session:
        prefs = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == 2)
            .one()
        )
        prefs.veto_tags = ["辣椒"]
        prefs.blacklist_dish_ids = [blacklisted]
        session.commit()

    joined = _join(client, code)
    assert joined.status_code == 200, joined.text
    candidates = joined.json()["candidates"]
    assert blacklisted not in {c["dish_id"] for c in candidates}
    assert len(candidates) == 10, "成员约束过滤后应从剩余池补足 10 道"

    with session_factory() as session:
        for candidate in candidates:
            dish = session.query(Dish).filter(Dish.id == candidate["dish_id"]).one()
            ingredients = set(dish.ingredients_main or []) | set(
                dish.ingredients_aux or []
            )
            assert "辣椒" not in ingredients
            assert dish.id != blacklisted


def test_member_sync_carries_latest_candidates(client, room_env):
    code = _create(client).json()["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        joined = _join(client, code)
        assert joined.status_code == 200

        sync = _drain_until(
            host,
            "MEMBER_SYNC",
            predicate=lambda m: len(m.get("members", [])) == 2,
        )
        assert sync["candidate_count"] == len(sync["candidates"])
        assert sync["candidate_count"] == 10
        assert sync["campus"] == "SIYUAN"


def test_ws_connect_does_not_write_members(client, room_env, session_factory):
    code = _create(client).json()["room_code"]

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/room/{code}/2"):
            pass

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        assert [int(i) for i in room.member_user_ids] == [1]


# ————————————————————— 投票语义 —————————————————————


def test_duplicate_vote_last_write_wins_and_timeout_rejected(
    client, room_env, session_factory
):
    code = _create(client).json()["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        dish_id = started["candidates"][0]["dish_id"]

        host.send_json(
            {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "LIKE"}
        )
        first = _drain_until(host, "PROGRESS_UPDATE")
        assert first["progress"][str(1)] == 1

        host.send_json(
            {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "SUPER_LIKE"}
        )
        second = _drain_until(host, "PROGRESS_UPDATE")
        assert second["progress"][str(1)] == 1, "重复投票不得增加进度"

        host.send_json(
            {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "TIMEOUT"}
        )
        timeout_error = _drain_until(host, "ERROR")
        assert "投票格式" in timeout_error["detail"]

        host.send_json(
            {"type": "SUBMIT_VOTE", "dish_id": 999999, "vote_type": "LIKE"}
        )
        candidate_error = _drain_until(host, "ERROR")
        assert "候选" in candidate_error["detail"]

    with session_factory() as session:
        rows = session.query(RoomVote).filter_by(room_code=code).all()
        assert len(rows) == 1
        assert rows[0].dish_id == dish_id
        assert rows[0].vote_type == "SUPER_LIKE"
        assert all(row.vote_type != "TIMEOUT" for row in rows)


def test_vote_rejected_in_waiting_and_after_deadline(
    client, room_env, session_factory
):
    code = _create(client).json()["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "SUBMIT_VOTE", "dish_id": 1, "vote_type": "LIKE"})
        waiting_error = _drain_until(host, "ERROR")
        assert "还没开始" in waiting_error["detail"]

        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        dish_id = started["candidates"][0]["dish_id"]

        with session_factory() as session:
            room = session.query(GroupRoom).filter_by(room_code=code).one()
            room.deadline_at = utcnow() - timedelta(seconds=1)
            session.commit()

        host.send_json(
            {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "LIKE"}
        )
        late_error = _drain_until(host, "ERROR")
        assert "到点" in late_error["detail"]

    with session_factory() as session:
        assert session.query(RoomVote).filter_by(room_code=code).count() == 0

    snapshot = client.get(f"/api/v1/rooms/{code}", headers=H1).json()
    assert snapshot["status"] == "FINISHED"
    assert snapshot["consensus_report"] is not None


def test_zero_votes_settle_with_internal_timeout(
    client, room_env, session_factory
):
    code = _create(client).json()["room_code"]
    assert _join(client, code).status_code == 200

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        _drain_until(host, "START_SWIPING")

        with session_factory() as session:
            room = session.query(GroupRoom).filter_by(room_code=code).one()
            room.deadline_at = utcnow() - timedelta(seconds=1)
            session.commit()

        snapshot = client.get(f"/api/v1/rooms/{code}", headers=H1).json()

    assert snapshot["status"] == "FINISHED"
    report = snapshot["consensus_report"]
    assert snapshot["winner_dish_id"] is not None
    assert report["has_consensus"] is True
    member_votes = {
        member["user_id"]: member["vote_type"]
        for dish in report["dishes"]
        for member in dish["members"]
    }
    assert set(member_votes) == {1, 2}
    assert set(member_votes.values()) == {"TIMEOUT"}
    with session_factory() as session:
        assert session.query(RoomVote).filter_by(room_code=code).count() == 0


def test_all_veto_has_no_winner_in_snapshot(client, room_env):
    code = _create(client).json()["room_code"]
    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        for candidate in started["candidates"]:
            host.send_json(
                {
                    "type": "SUBMIT_VOTE",
                    "dish_id": candidate["dish_id"],
                    "vote_type": "VETO",
                }
            )
        reveal = _drain_until(host, "CONSENSUS_REVEAL")
        assert reveal["winner_dish_id"] is None
        assert reveal["has_consensus"] is False

    snapshot = client.get(f"/api/v1/rooms/{code}", headers=H1).json()
    assert snapshot["status"] == "FINISHED"
    assert snapshot["winner_dish_id"] is None
    assert snapshot["winner_dish"] is None
    assert snapshot["has_consensus"] is False
    assert sorted(snapshot["consensus_report"]["vetoed_dish_ids"]) == sorted(
        c["dish_id"] for c in snapshot["candidates"]
    )


# ————————————————————— 结算 / 恢复 —————————————————————


def test_settlement_idempotent_and_snapshot_recovery(client, room_env, session_factory):
    code = _create(client).json()["room_code"]

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        for candidate in started["candidates"]:
            host.send_json(
                {
                    "type": "SUBMIT_VOTE",
                    "dish_id": candidate["dish_id"],
                    "vote_type": "LIKE",
                }
            )
        reveal = _drain_until(host, "CONSENSUS_REVEAL")

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        settled_at = room.settled_at
        report = room.consensus_report
        winner = room.winner_dish_id
        assert settled_at is not None
        assert group_room._settle(session, room) is None

    first = client.get(f"/api/v1/rooms/{code}", headers=H1).json()
    second = client.get(f"/api/v1/rooms/{code}", headers=H1).json()
    assert first["consensus_report"] == second["consensus_report"]
    assert first["winner_dish_id"] == second["winner_dish_id"] == reveal["winner_dish_id"]
    assert first["status"] == second["status"] == "FINISHED"

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        assert room.settled_at == settled_at
        assert room.consensus_report == report
        assert room.winner_dish_id == winner
        assert session.query(RoomVote).filter_by(room_code=code).count() == 10

    # 重连不依赖广播：ROOM_STATE 必须能恢复赢家、报告、本人票与冻结的 ω。
    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        state = _drain_until(host, "ROOM_STATE")["snapshot"]
        assert state["status"] == "FINISHED"
        assert state["winner_dish_id"] == reveal["winner_dish_id"]
        assert state["consensus_report"]["dishes"]
        assert state["my_votes"]
        assert state["members"][0]["progress"] == 10
        assert state["campus"] == "SIYUAN"
        assert state["omega_group"] == 0.5


def test_sweeper_continues_after_scan_error(monkeypatch):
    """P2-S06-01：扫描级异常一次后，sweeper 必须继续下一周期。"""
    calls = []
    broadcasts = []
    done = asyncio.Event()

    def fake_sweep():
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            raise RuntimeError("transient scan failure")
        if len(calls) == 2:
            done.set()
            return [("960001", {"type": "CONSENSUS_REVEAL", "room_code": "960001"})]
        return []

    async def fake_broadcast(code, payload):
        broadcasts.append((code, payload))

    monkeypatch.setattr(group_room, "settle_overdue_rooms", fake_sweep)
    monkeypatch.setattr(group_room.hub, "broadcast", fake_broadcast)

    async def scenario():
        task = asyncio.create_task(group_room.room_sweeper(interval=0))
        try:
            await asyncio.wait_for(done.wait(), timeout=2)
            await asyncio.sleep(0.05)
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())
    assert len(calls) >= 2, "第一次扫描异常后必须继续调用下一次扫描"
    assert broadcasts == [
        ("960001", {"type": "CONSENSUS_REVEAL", "room_code": "960001"})
    ]


def test_sweep_isolates_single_room_failure(monkeypatch, room_env, session_factory):
    """P2-S06-01：单个房间失败不阻断同轮其它房间。"""
    with session_factory() as session:
        for code in ("960001", "960002"):
            session.add(
                GroupRoom(
                    room_code=code,
                    host_user_id=1,
                    mode_type="OUT_DINING",
                    status="SWIPING",
                    member_user_ids=[1],
                    candidate_dish_ids=[],
                    budget=None,
                    campus="SIYUAN",
                    deadline_at=utcnow() - timedelta(seconds=1),
                )
            )
        session.commit()

    def fake_settle(db, room):
        if room.room_code == "960001":
            raise RuntimeError("boom")
        return {"type": "CONSENSUS_REVEAL", "room_code": room.room_code}

    monkeypatch.setattr(group_room, "_settle_if_due", fake_settle)
    settled = group_room.settle_overdue_rooms()
    assert [code for code, _ in settled] == ["960002"]


def test_existing_member_join_rejected_after_start_and_finish(
    client, room_env, session_factory
):
    """P2-S06-02：既有成员在 SWIPING/FINISHED 重复 join 必须 400，且无副作用。"""
    code = _create(client).json()["room_code"]
    assert _join(client, code).status_code == 200

    with client.websocket_connect(f"/ws/room/{code}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        candidate_ids = [item["dish_id"] for item in started["candidates"]]

        swiping_join = _join(client, code)
        assert swiping_join.status_code == 400
        assert "开始" in swiping_join.text

        with session_factory() as session:
            room = session.query(GroupRoom).filter_by(room_code=code).one()
            assert [int(i) for i in room.member_user_ids] == [1, 2]
            assert [int(i) for i in room.candidate_dish_ids] == candidate_ids
            assert session.query(RoomVote).filter_by(room_code=code).count() == 0

        with session_factory() as session:
            room = session.query(GroupRoom).filter_by(room_code=code).one()
            room.deadline_at = utcnow() - timedelta(seconds=1)
            session.commit()

        snapshot = client.get(f"/api/v1/rooms/{code}", headers=H1).json()
        assert snapshot["status"] == "FINISHED"

        finished_join = _join(client, code)
        assert finished_join.status_code == 400
        host_join = client.post(
            f"/api/v1/rooms/{code}/join",
            json={"campus": "SIYUAN"},
            headers=H1,
        )
        assert host_join.status_code == 400

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        assert [int(i) for i in room.member_user_ids] == [1, 2]
        assert [int(i) for i in room.candidate_dish_ids] == candidate_ids
        assert session.query(RoomVote).filter_by(room_code=code).count() == 0
        assert room.winner_dish_id == snapshot["winner_dish_id"]
        assert room.consensus_report == snapshot["consensus_report"]


def test_settle_failure_leaves_swiping(monkeypatch, room_env, session_factory):
    with session_factory() as session:
        dish_ids = [
            row.id
            for row in session.query(Dish)
            .filter(Dish.mode_type == "OUT_DINING")
            .limit(2)
            .all()
        ]
        room = GroupRoom(
            room_code="930001",
            host_user_id=1,
            mode_type="OUT_DINING",
            status="SWIPING",
            member_user_ids=[1, 2],
            candidate_dish_ids=dish_ids,
            budget=None,
            algo_params={"omega_group": 0.5},
            campus="SIYUAN",
            deadline_at=utcnow() - timedelta(seconds=1),
        )
        session.add(room)
        session.commit()

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(group_room, "compute_group_consensus", boom)
    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code="930001").one()
        with pytest.raises(RuntimeError):
            group_room._settle(session, room)

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code="930001").one()
        assert room.status == "SWIPING"
        assert room.settled_at is None
        assert room.consensus_report is None
        assert room.winner_dish_id is None


def test_settle_race_writes_once(tmp_path, session_factory):
    # 用文件库验证两个独立 session 竞争时只有一份报告落库。
    db_path = (tmp_path / "s06_race.db").as_posix()
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with factory() as session:
        from backend.scripts.init_seed_data import seed_all

        seed_all(session)
        dish_ids = [
            row.id
            for row in session.query(Dish)
            .filter(Dish.mode_type == "OUT_DINING")
            .limit(2)
            .all()
        ]
        room = GroupRoom(
            room_code="930002",
            host_user_id=1,
            mode_type="OUT_DINING",
            status="SWIPING",
            member_user_ids=[1, 2],
            candidate_dish_ids=dish_ids,
            budget=None,
            algo_params={"omega_group": 0.5},
            campus="SIYUAN",
            deadline_at=utcnow() - timedelta(seconds=1),
        )
        session.add(room)
        session.add_all(
            [
                RoomVote(
                    room_code="930002",
                    user_id=uid,
                    dish_id=dish_id,
                    vote_type="LIKE" if uid == 1 else "PASS",
                    voted_at=utcnow(),
                )
                for uid in (1, 2)
                for dish_id in dish_ids
            ]
        )
        session.commit()

    barrier = threading.Barrier(2)
    results = []
    lock = threading.Lock()

    def worker():
        session = factory()
        try:
            room = session.query(GroupRoom).filter_by(room_code="930002").one()
            barrier.wait()
            payload = group_room._settle(session, room)
            with lock:
                results.append(payload)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len([item for item in results if item is not None]) == 1
    with factory() as session:
        room = session.query(GroupRoom).filter_by(room_code="930002").one()
        assert room.status == "FINISHED"
        assert room.settled_at is not None
        assert room.consensus_report is not None
        assert session.query(RoomVote).filter_by(room_code="930002").count() == 4
    engine.dispose()


def test_restart_sweep_settles_without_clients(client, room_env, session_factory):
    code = _create(client).json()["room_code"]
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

    # 模拟进程重启：内存连接与定时器全部丢失，只剩数据库里的截止时间。
    for task in list(group_room.hub.timers.values()):
        if not task.done():
            task.cancel()
    group_room.hub.timers.clear()
    group_room.hub.rooms.clear()

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        room.deadline_at = utcnow() - timedelta(seconds=1)
        session.commit()

    settled = group_room.settle_overdue_rooms()
    assert [item[0] for item in settled] == [code]

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=code).one()
        assert room.status == "FINISHED"
        assert room.settled_at is not None
        assert room.consensus_report is not None
        assert room.winner_dish_id is not None


# ————————————————————— ω 参数链 —————————————————————


def test_omega_frozen_at_create_and_single_override_isolated(
    client, room_env, session_factory
):
    with session_factory() as session:
        config = session.query(AlgoConfig).filter_by(
            config_name="default_production"
        ).one()
        config.omega_group = 0.8
        session.commit()

    first = _create(client).json()
    assert first["omega_group"] == 0.8
    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=first["room_code"]).one()
        assert room.algo_params == {"omega_group": 0.8}
        config = session.query(AlgoConfig).filter_by(
            config_name="default_production"
        ).one()
        config.omega_group = 0.1
        session.commit()

    with client.websocket_connect(f"/ws/room/{first['room_code']}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        started = _drain_until(host, "START_SWIPING")
        for candidate in started["candidates"]:
            host.send_json(
                {
                    "type": "SUBMIT_VOTE",
                    "dish_id": candidate["dish_id"],
                    "vote_type": "LIKE",
                }
            )
        reveal = _drain_until(host, "CONSENSUS_REVEAL")
    assert reveal["report"]["omega_group"] == 0.8, "结算不得回读建房后的 DB 变化"

    override = _create(client, override_params={"omega_group": 0.2}).json()
    assert override["omega_group"] == 0.2
    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(
            room_code=override["room_code"]
        ).one()
        assert room.algo_params == {"omega_group": 0.2}
        config = session.query(AlgoConfig).filter_by(
            config_name="default_production"
        ).one()
        config.omega_group = 0.9
        session.commit()

    response = client.post(
        "/api/v1/recommend/single",
        json={
            "mode_type": "OUT_DINING",
            "campus": "SIYUAN",
            "override_params": {"omega_group": 0.95},
            "limit": 3,
        },
        headers=H1,
    )
    assert response.status_code == 200, response.text
    with session_factory() as session:
        config = session.query(AlgoConfig).filter_by(
            config_name="default_production"
        ).one()
        assert config.omega_group == 0.9
        room = session.query(GroupRoom).filter_by(
            room_code=override["room_code"]
        ).one()
        assert room.algo_params == {"omega_group": 0.2}


def test_fixed_omega_matrix_room_level(room_env, session_factory):
    """固定矩阵：A 全员 LIKE；B 两人超喜欢、两人都行。期望值由本测试手算。"""
    with session_factory() as session:
        vectors = {
            "u1": _vec(spicy_level=1.0),
            "u2": _vec(spicy_level=1.0),
            "u3": _vec(soup_level=1.0),
            "u4": _vec(soup_level=1.0),
        }
        user_ids = {}
        for index, (name, vector) in enumerate(vectors.items(), start=1):
            user = User(username=f"s06_matrix_{name}", nickname=name)
            session.add(user)
            session.flush()
            session.add(UserPreference(user_id=user.id, base_vector=vector))
            user_ids[name] = user.id
        dish_a = Dish(
            name="S06矩阵A",
            mode_type="OUT_DINING",
            dish_role="ONE_MEAL",
            price_or_cost=10.0,
            feature_vector=_vec(oily_level=1.0),
        )
        dish_b = Dish(
            name="S06矩阵B",
            mode_type="OUT_DINING",
            dish_role="ONE_MEAL",
            price_or_cost=10.0,
            feature_vector=_vec(spicy_level=1.0),
        )
        session.add_all([dish_a, dish_b])
        session.flush()
        candidate_ids = [dish_a.id, dish_b.id]
        members = [user_ids[name] for name in ("u1", "u2", "u3", "u4")]
        session.commit()

        rooms = {}
        for omega in (0.0, 0.5, 1.0):
            code = f"94{int(omega * 100):04d}"
            room = GroupRoom(
                room_code=code,
                host_user_id=members[0],
                mode_type="OUT_DINING",
                status="SWIPING",
                member_user_ids=members,
                candidate_dish_ids=candidate_ids,
                budget=None,
                algo_params={"omega_group": omega},
                campus="SIYUAN",
                deadline_at=utcnow() - timedelta(seconds=1),
            )
            session.add(room)
            session.flush()
            for member in members:
                session.add(
                    RoomVote(
                        room_code=code,
                        user_id=member,
                        dish_id=dish_a.id,
                        vote_type="LIKE",
                        voted_at=utcnow(),
                    )
                )
            session.add_all(
                [
                    RoomVote(
                        room_code=code,
                        user_id=members[0],
                        dish_id=dish_b.id,
                        vote_type="SUPER_LIKE",
                        voted_at=utcnow(),
                    ),
                    RoomVote(
                        room_code=code,
                        user_id=members[1],
                        dish_id=dish_b.id,
                        vote_type="SUPER_LIKE",
                        voted_at=utcnow(),
                    ),
                    RoomVote(
                        room_code=code,
                        user_id=members[2],
                        dish_id=dish_b.id,
                        vote_type="PASS",
                        voted_at=utcnow(),
                    ),
                    RoomVote(
                        room_code=code,
                        user_id=members[3],
                        dish_id=dish_b.id,
                        vote_type="PASS",
                        voted_at=utcnow(),
                    ),
                ]
            )
            session.commit()
            rooms[omega] = room

        # 独立手算（不调用被测函数生成期望值）。
        swipe = {"LIKE": 100.0, "SUPER_LIKE": 120.0, "PASS": 40.0}

        def individual(prior, vote_type):
            return 0.4 * prior + 0.6 * swipe[vote_type]

        rs_a = [individual(0.0, "LIKE") for _ in range(4)]
        rs_b = [
            individual(100.0, "SUPER_LIKE"),
            individual(100.0, "SUPER_LIKE"),
            individual(0.0, "PASS"),
            individual(0.0, "PASS"),
        ]

        def group_score(values, omega):
            return omega * (sum(values) / len(values)) + (1.0 - omega) * min(values)

        expected = {
            0.0: {dish_a.id: group_score(rs_a, 0.0), dish_b.id: group_score(rs_b, 0.0)},
            0.5: {dish_a.id: group_score(rs_a, 0.5), dish_b.id: group_score(rs_b, 0.5)},
            1.0: {dish_a.id: group_score(rs_a, 1.0), dish_b.id: group_score(rs_b, 1.0)},
        }
        expected_winner = {0.0: dish_a.id, 0.5: dish_a.id, 1.0: dish_b.id}

        for omega, room in rooms.items():
            payload = group_room._settle(session, room)
            assert payload is not None
            report = payload["report"]
            assert report["omega_group"] == omega
            by_dish = {item["dish_id"]: item for item in report["dishes"]}
            assert by_dish[dish_a.id]["mean_satisfaction"] == pytest.approx(60.0, abs=0.01)
            assert by_dish[dish_a.id]["least_misery"] == pytest.approx(60.0, abs=0.01)
            assert by_dish[dish_b.id]["mean_satisfaction"] == pytest.approx(68.0, abs=0.01)
            assert by_dish[dish_b.id]["least_misery"] == pytest.approx(24.0, abs=0.01)
            for dish_id, value in expected[omega].items():
                assert by_dish[dish_id]["group_score"] == pytest.approx(value, abs=0.01)
            assert report["winner_dish_id"] == expected_winner[omega]


# ————————————————————— 历史 NULL 房间 / START 守卫 —————————————————————


def test_legacy_null_room_binds_on_first_join(client, room_env, session_factory):
    with session_factory() as session:
        room = GroupRoom(
            room_code="950001",
            host_user_id=1,
            mode_type="OUT_DINING",
            status="WAITING",
            member_user_ids=[1],
            candidate_dish_ids=[],
            budget=None,
            campus=None,
        )
        session.add(room)
        session.commit()

    response = _join(client, "950001")
    assert response.status_code == 200, response.text
    assert response.json()["campus"] == "SIYUAN"
    assert [m["user_id"] for m in response.json()["members"]] == [1, 2]
    assert len(response.json()["candidates"]) == 10

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code="950001").one()
        assert room.campus == "SIYUAN"


def test_legacy_null_room_rejects_binding_when_no_candidates(
    client, room_env, session_factory
):
    _set_all_campus(session_factory, None)
    with session_factory() as session:
        room = GroupRoom(
            room_code="950002",
            host_user_id=1,
            mode_type="OUT_DINING",
            status="WAITING",
            member_user_ids=[1],
            candidate_dish_ids=[],
            budget=None,
            campus=None,
        )
        session.add(room)
        session.commit()

    response = _join(client, "950002")
    assert response.status_code == 409
    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code="950002").one()
        assert room.campus is None
        assert [int(i) for i in room.member_user_ids] == [1]


def test_legacy_null_room_not_waiting_rejects_join(
    client, room_env, session_factory
):
    with session_factory() as session:
        room = GroupRoom(
            room_code="950003",
            host_user_id=1,
            mode_type="OUT_DINING",
            status="SWIPING",
            member_user_ids=[1],
            candidate_dish_ids=[],
            budget=None,
            campus=None,
        )
        session.add(room)
        session.commit()

    response = _join(client, "950003")
    assert response.status_code == 400
    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code="950003").one()
        assert [int(i) for i in room.member_user_ids] == [1]


def test_start_guarded_by_candidates_and_state(
    client, room_env, session_factory
):
    _set_all_campus(session_factory, None)
    empty = _create(client).json()
    assert empty["candidates"] == []

    with client.websocket_connect(f"/ws/room/{empty['room_code']}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        error = _drain_until(host, "ERROR")
        assert "没有满足" in error["detail"]

    with session_factory() as session:
        room = session.query(GroupRoom).filter_by(room_code=empty["room_code"]).one()
        assert room.status == "WAITING"

    _set_all_campus(session_factory, "SIYUAN")
    normal = _create(client).json()
    with client.websocket_connect(f"/ws/room/{normal['room_code']}/1") as host:
        _drain_until(host, "ROOM_STATE")
        host.send_json({"type": "START_SWIPING"})
        _drain_until(host, "START_SWIPING")
        host.send_json({"type": "START_SWIPING"})
        error = _drain_until(host, "ERROR")
        assert "已经开始" in error["detail"]
        late_join = _join(client, normal["room_code"], user_id=2)
        assert late_join.status_code == 400


# ————————————————————— 迁移 —————————————————————


def _minimal_room_votes_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE room_votes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "room_code VARCHAR(10) NOT NULL, "
            "user_id INTEGER NOT NULL, "
            "dish_id INTEGER NOT NULL, "
            "vote_type VARCHAR(16) NOT NULL, "
            "voted_at DATETIME)"
        )
        connection.commit()
    finally:
        connection.close()


def test_migrate_creates_unique_index_and_is_idempotent(tmp_path):
    path = tmp_path / "s06_migrate_clean.db"
    _minimal_room_votes_db(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "INSERT INTO room_votes (room_code,user_id,dish_id,vote_type) "
            "VALUES ('900001',1,1,'LIKE'),('900001',2,1,'PASS')"
        )
        connection.commit()
    finally:
        connection.close()

    first = migrate_s06_room_contract.migrate(path)
    assert first["ok"] is True
    assert first["index_created"] is True
    assert first["index_present"] is True
    assert first["row_count"] == 2

    second = migrate_s06_room_contract.migrate(path)
    assert second["ok"] is True
    assert second["idempotent"] is True
    assert second["sha256_before"] == second["sha256_after"]


def test_migrate_aborts_on_duplicate_votes(tmp_path):
    path = tmp_path / "s06_migrate_dup.db"
    _minimal_room_votes_db(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "INSERT INTO room_votes (room_code,user_id,dish_id,vote_type) "
            "VALUES ('900001',1,1,'LIKE'),('900001',1,1,'PASS')"
        )
        connection.commit()
    finally:
        connection.close()

    before = migrate_s06_room_contract.file_sha256(path)
    report = migrate_s06_room_contract.migrate(path)
    assert report["ok"] is False
    assert report["reason"] == "duplicate_room_votes"
    assert report["duplicates"][0]["count"] == 2
    assert report["index_present"] is False
    assert migrate_s06_room_contract.file_sha256(path) == before


def test_migrate_refuses_protected_dbs():
    with pytest.raises(SystemExit):
        migrate_s06_room_contract.migrate(
            migrate_s06_room_contract.ROOT / "backend" / "eatwhat.db"
        )
