"""S06 真实 REST/WS 序列（隔离库 8026）。

覆盖：建房/校区/10 候选、跨校区 409、join 重算、WS 403、非房主开局、
重复/非法/迟到投票、早结算、快照恢复、重复 GET 幂等、ω 建房冻结、
全员 0 票、全员否决。所有写入只落在 backend/eatwhat_s06_r02_iso.db。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import websockets
from websockets.exceptions import InvalidStatus

BASE = "http://127.0.0.1:8026"
WS_BASE = "ws://127.0.0.1:8026"
ROOT = Path(__file__).resolve().parents[6]
DB = ROOT / "backend" / "eatwhat_s06_r02_iso.db"
OUT = Path(__file__).resolve().parent / "rest_ws_sequence.json"
H1 = {"X-User-Id": "1"}
H2 = {"X-User-Id": "2"}
H3 = {"X-User-Id": "3"}

sys.stdout.reconfigure(encoding="utf-8")

steps: list[dict] = []
traces: dict[str, list[str]] = {}


def record(name: str, **detail):
    entry = {
        "at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "step": name,
        **detail,
    }
    steps.append(entry)
    print(f"[{name}] ok")
    return entry


def require(condition, message: str):
    if not condition:
        raise AssertionError(message)


def db_connect(readonly: bool = True):
    if readonly:
        return sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=10)
    connection = sqlite3.connect(DB, timeout=10)
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def fixture_ids() -> dict:
    connection = db_connect()
    try:
        rows = connection.execute(
            "SELECT r.campus, d.id FROM dishes_and_recipes d "
            "JOIN restaurants r ON r.id=d.restaurant_id "
            "WHERE d.source_dataset='s06_fixture_v1'"
        ).fetchall()
    finally:
        connection.close()
    result = {"SIYUAN": set(), "JIANDA_YANTA": set()}
    for campus, dish_id in rows:
        result[campus].add(dish_id)
    return result


def set_omega(value: float) -> None:
    connection = db_connect(readonly=False)
    try:
        connection.execute(
            "UPDATE algo_configs SET omega_group=? WHERE config_name='default_production'",
            (value,),
        )
        connection.commit()
    finally:
        connection.close()


def room_row(code: str) -> dict:
    connection = db_connect()
    try:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM group_rooms WHERE room_code=?", (code,)
        ).fetchone()
        votes = connection.execute(
            "SELECT user_id, dish_id, vote_type FROM room_votes WHERE room_code=?",
            (code,),
        ).fetchall()
    finally:
        connection.close()
    if row is None:
        return {}
    payload = dict(row)
    payload["votes"] = [dict(item) for item in votes]
    return payload


async def recv_until(ws, want: str, trace_key: str, timeout: float = 20.0, predicate=None):
    deadline = time.monotonic() + timeout
    seen = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"{trace_key}: timeout waiting {want}, seen {seen[-20:]}")
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        message = json.loads(raw)
        kind = message.get("type")
        seen.append(kind)
        traces.setdefault(trace_key, []).append(kind)
        if kind == want and (predicate is None or predicate(message)):
            return message


def connect(code: str, user_id: int):
    return websockets.connect(
        f"{WS_BASE}/ws/room/{code}/{user_id}", open_timeout=5, close_timeout=5
    )


async def run_single_member_room(code: str, vote_type: str = "LIKE", trace_key: str = "") -> dict:
    async with connect(code, 1) as host:
        await recv_until(host, "ROOM_STATE", trace_key or f"{code}-host")
        await host.send(json.dumps({"type": "START_SWIPING"}))
        started = await recv_until(host, "START_SWIPING", trace_key or f"{code}-host")
        for candidate in started["candidates"]:
            await host.send(
                json.dumps(
                    {
                        "type": "SUBMIT_VOTE",
                        "dish_id": candidate["dish_id"],
                        "vote_type": vote_type,
                    }
                )
            )
        return await recv_until(
            host, "CONSENSUS_REVEAL", trace_key or f"{code}-host"
        )


async def main() -> None:
    client = httpx.Client(trust_env=False, timeout=20)
    fixture = fixture_ids()
    require(len(fixture["SIYUAN"]) == 12, "SIYUAN fixture 应为 12 道")
    require(len(fixture["JIANDA_YANTA"]) == 12, "JIANDA fixture 应为 12 道")

    health = client.get(f"{BASE}/health")
    require(health.status_code == 200, health.text)
    record("health", status=health.status_code, body=health.json())

    missing_campus = client.post(
        f"{BASE}/api/v1/rooms/create", json={"mode_type": "OUT_DINING"}, headers=H1
    )
    require(missing_campus.status_code == 422, "缺 campus 必须 422")
    record("create_missing_campus_422", status=missing_campus.status_code)

    caotang = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "JIANDA_CAOTANG"},
        headers=H1,
    )
    require(caotang.status_code == 422, "草堂未开放必须 422")
    record("create_caotang_422", status=caotang.status_code)

    created = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={
            "mode_type": "OUT_DINING",
            "campus": "SIYUAN",
            "budget": 40,
            "override_params": {"omega_group": 0.9},
        },
        headers=H1,
    )
    require(created.status_code == 200, created.text)
    room = created.json()
    code = room["room_code"]
    require(len(code) == 6 and code.isdigit(), "房间码必须 6 位数字")
    require(room["campus"] == "SIYUAN", "房间校区应为 SIYUAN")
    require(room["omega_group"] == 0.9, "建房 override ω 应为 0.9")
    require(len(room["candidates"]) == 10, "应下发 10 道候选")
    require(
        {item["dish_id"] for item in room["candidates"]} <= fixture["SIYUAN"],
        "SIYUAN 房间候选必须全部来自 SIYUAN fixture",
    )
    require(
        all(item["name"].startswith("S06思源固定菜") for item in room["candidates"]),
        "SIYUAN 房间不得混入其它校区/NULL 门店",
    )
    record(
        "create_siyuan_room",
        room_code=code,
        campus=room["campus"],
        omega_group=room["omega_group"],
        candidate_count=len(room["candidates"]),
        candidate_ids=[item["dish_id"] for item in room["candidates"]],
        candidate_names=[item["name"] for item in room["candidates"]],
    )

    jianada = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "JIANDA_YANTA", "budget": 40},
        headers=H1,
    )
    require(jianada.status_code == 200, jianada.text)
    jianada_body = jianada.json()
    require(
        {item["dish_id"] for item in jianada_body["candidates"]}
        <= fixture["JIANDA_YANTA"],
        "JIANDA 房间候选必须全部来自 JIANDA fixture",
    )
    require(
        all(item["name"].startswith("S06建大固定菜") for item in jianada_body["candidates"]),
        "JIANDA 房间不得混入思源/NULL 门店",
    )
    record(
        "create_jianda_room",
        room_code=jianada_body["room_code"],
        candidate_count=len(jianada_body["candidates"]),
        candidate_ids=[item["dish_id"] for item in jianada_body["candidates"]],
    )

    home = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "HOME_COOKING", "campus": "SIYUAN"},
        headers=H1,
    )
    require(home.status_code == 200, home.text)
    require(len(home.json()["candidates"]) == 10, "下厨共享菜谱应有 10 候选")
    record(
        "create_home_room",
        room_code=home.json()["room_code"],
        candidate_count=len(home.json()["candidates"]),
    )

    cross = client.post(
        f"{BASE}/api/v1/rooms/{code}/join",
        json={"campus": "JIANDA_YANTA"},
        headers=H2,
    )
    require(cross.status_code == 409, "跨校区 join 必须 409")
    after_cross = room_row(code)
    require([int(i) for i in json.loads(after_cross["member_user_ids"])] == [1], "409 不得写成员")
    record("cross_campus_join_409", status=cross.status_code, detail=cross.text)

    missing_join_campus = client.post(
        f"{BASE}/api/v1/rooms/{code}/join", json={}, headers=H2
    )
    require(missing_join_campus.status_code == 422, "join 缺 campus 必须 422")
    record("join_missing_campus_422", status=missing_join_campus.status_code)

    joined = client.post(
        f"{BASE}/api/v1/rooms/{code}/join", json={"campus": "SIYUAN"}, headers=H2
    )
    require(joined.status_code == 200, joined.text)
    joined_body = joined.json()
    require([m["user_id"] for m in joined_body["members"]] == [1, 2], "成员应为 [1,2]")
    require(len(joined_body["candidates"]) == 10, "join 后应重算并保持 10 候选")
    require(
        {item["dish_id"] for item in joined_body["candidates"]} <= fixture["SIYUAN"],
        "join 重算后仍必须同校区",
    )
    record(
        "join_siyuan_member",
        members=[m["user_id"] for m in joined_body["members"]],
        candidate_count=len(joined_body["candidates"]),
    )

    try:
        async with connect(code, 3):
            raise AssertionError("未 join 的 WS 必须被拒绝")
    except InvalidStatus as exc:
        require(exc.response.status_code == 403, f"WS 应为 403，实际 {exc.response.status_code}")
        record("ws_non_member_403", status=exc.response.status_code)

    async with connect(code, 1) as host, connect(code, 2) as guest:
        await recv_until(host, "ROOM_STATE", "flow-host")
        await recv_until(guest, "ROOM_STATE", "flow-guest")

        await guest.send(json.dumps({"type": "START_SWIPING"}))
        non_host_error = await recv_until(guest, "ERROR", "flow-guest")
        require("房主" in non_host_error["detail"], "非房主开局必须被拒")
        record("non_host_start_rejected", detail=non_host_error["detail"])

        await host.send(json.dumps({"type": "START_SWIPING"}))
        host_started = await recv_until(host, "START_SWIPING", "flow-host")
        guest_started = await recv_until(guest, "START_SWIPING", "flow-guest")
        require(host_started["deadline_at"], "START 必须下发服务端截止时间")
        require(host_started["omega_group"] == 0.9, "START 应携带冻结 ω")
        candidates = host_started["candidates"]
        require(len(candidates) == 10, "开局应有 10 张卡")
        dish_ids = [item["dish_id"] for item in candidates]
        record(
            "host_start",
            deadline_at=host_started["deadline_at"],
            remaining_ms=host_started["remaining_ms"],
            candidate_ids=dish_ids,
        )

        first = dish_ids[0]
        await host.send(
            json.dumps({"type": "SUBMIT_VOTE", "dish_id": first, "vote_type": "LIKE"})
        )
        progress = await recv_until(
            host,
            "PROGRESS_UPDATE",
            "flow-host",
            predicate=lambda m: m["progress"].get("1") == 1,
        )
        await host.send(
            json.dumps(
                {"type": "SUBMIT_VOTE", "dish_id": first, "vote_type": "SUPER_LIKE"}
            )
        )
        progress_again = await recv_until(
            host,
            "PROGRESS_UPDATE",
            "flow-host",
            predicate=lambda m: m["progress"].get("1") == 1,
        )
        require(progress_again["progress"].get("1") == 1, "重复投票不得增加进度")
        record("duplicate_vote_last_write_wins", progress=progress_again["progress"])

        await host.send(
            json.dumps({"type": "SUBMIT_VOTE", "dish_id": first, "vote_type": "TIMEOUT"})
        )
        timeout_error = await recv_until(host, "ERROR", "flow-host")
        require("投票格式" in timeout_error["detail"], "客户端 TIMEOUT 必须拒绝")
        record("client_timeout_rejected", detail=timeout_error["detail"])

        await host.send(
            json.dumps({"type": "SUBMIT_VOTE", "dish_id": 999999, "vote_type": "LIKE"})
        )
        candidate_error = await recv_until(host, "ERROR", "flow-host")
        require("候选" in candidate_error["detail"], "非候选菜必须拒绝")
        record("non_candidate_vote_rejected", detail=candidate_error["detail"])

        for dish_id in dish_ids[1:]:
            await host.send(
                json.dumps(
                    {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "LIKE"}
                )
            )
        await recv_until(
            host,
            "PROGRESS_UPDATE",
            "flow-host",
            predicate=lambda m: m["progress"].get("1") == 10,
        )

        for dish_id in dish_ids:
            await guest.send(
                json.dumps(
                    {"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "PASS"}
                )
            )
        reveal = await recv_until(host, "CONSENSUS_REVEAL", "flow-host")
        guest_reveal = await recv_until(guest, "CONSENSUS_REVEAL", "flow-guest")
        require(reveal["winner_dish_id"] == guest_reveal["winner_dish_id"], "两端赢家必须一致")
        require(reveal["winner_dish_id"] in dish_ids, "赢家必须属于本房候选")
        require(reveal["has_consensus"] is True, "无否决时应存在共识")
        require(reveal["report"]["omega_group"] == 0.9, "结算必须使用建房冻结的 ω")
        record(
            "consensus_reveal",
            winner_dish_id=reveal["winner_dish_id"],
            winner_name=(reveal.get("winner") or {}).get("name"),
            has_consensus=reveal["has_consensus"],
            omega_group=reveal["report"]["omega_group"],
            group_score=next(
                item["group_score"]
                for item in reveal["report"]["dishes"]
                if item["dish_id"] == reveal["winner_dish_id"]
            ),
        )

    snapshot = client.get(f"{BASE}/api/v1/rooms/{code}", headers=H1)
    require(snapshot.status_code == 200, snapshot.text)
    snap = snapshot.json()
    require(snap["status"] == "FINISHED", "结算后状态应为 FINISHED")
    require(snap["winner_dish_id"] is not None, "快照应有赢家")
    require(snap["consensus_report"]["dishes"], "快照应带完整报告")
    require(len(snap["my_votes"]) == 10, "快照应恢复本人 10 票")
    require(snap["members"][0]["progress"] == 10, "快照应恢复进度 10/10")
    require(snap["campus"] == "SIYUAN", "快照应带校区")
    require(snap["omega_group"] == 0.9, "快照应带冻结 ω")
    record(
        "snapshot_after_finish",
        status=snap["status"],
        winner_dish_id=snap["winner_dish_id"],
        my_votes=len(snap["my_votes"]),
        progress=snap["members"][0]["progress"],
        campus=snap["campus"],
        omega_group=snap["omega_group"],
    )

    repeat = client.get(f"{BASE}/api/v1/rooms/{code}", headers=H1).json()
    require(repeat["consensus_report"] == snap["consensus_report"], "重复 GET 不得改报告")
    require(repeat["winner_dish_id"] == snap["winner_dish_id"], "重复 GET 不得改赢家")
    row = room_row(code)
    require(row["status"] == "FINISHED" and row["settled_at"], "数据库应已结算")
    require(len(row["votes"]) == 20, "应恰好 20 条唯一票")
    require(
        len({(v["user_id"], v["dish_id"]) for v in row["votes"]}) == 20,
        "票必须按 (user,dish) 唯一",
    )
    record(
        "repeat_get_idempotent",
        vote_count=len(row["votes"]),
        unique_vote_count=len({(v["user_id"], v["dish_id"]) for v in row["votes"]}),
        settled_at=row["settled_at"],
    )

    async with connect(code, 1) as host:
        state = await recv_until(host, "ROOM_STATE", "reconnect-host")
        restored = state["snapshot"]
        require(restored["status"] == "FINISHED", "重连快照应为 FINISHED")
        require(restored["winner_dish_id"] == snap["winner_dish_id"], "重连快照赢家一致")
        require(restored["consensus_report"] == snap["consensus_report"], "重连快照报告一致")
        require(len(restored["my_votes"]) == 10, "重连快照应恢复本人票")
        require(restored["campus"] == "SIYUAN" and restored["omega_group"] == 0.9, "重连快照字段")
    record("reconnect_room_state_restored")

    # ω 建房冻结：先 0.7，建房后改 0.1，结算仍必须是 0.7。
    set_omega(0.7)
    frozen = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": 40},
        headers=H1,
    )
    require(frozen.status_code == 200, frozen.text)
    frozen_body = frozen.json()
    require(frozen_body["omega_group"] == 0.7, "建房应冻结 DB 的 0.7")
    set_omega(0.1)
    frozen_reveal = await run_single_member_room(
        frozen_body["room_code"], trace_key="omega-frozen"
    )
    require(
        frozen_reveal["report"]["omega_group"] == 0.7,
        "结算不得回读建房后的 DB ω",
    )
    record(
        "omega_frozen_at_create",
        room_code=frozen_body["room_code"],
        snapshot_omega=frozen_body["omega_group"],
        db_omega_after_create=0.1,
        settle_omega=frozen_reveal["report"]["omega_group"],
    )

    override = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={
            "mode_type": "OUT_DINING",
            "campus": "SIYUAN",
            "budget": 40,
            "override_params": {"omega_group": 0.2},
        },
        headers=H1,
    )
    require(override.status_code == 200, override.text)
    override_body = override.json()
    require(override_body["omega_group"] == 0.2, "请求 override 应优先")
    override_reveal = await run_single_member_room(
        override_body["room_code"], trace_key="omega-override"
    )
    require(override_reveal["report"]["omega_group"] == 0.2, "结算应使用 override 0.2")
    record(
        "omega_request_override",
        room_code=override_body["room_code"],
        snapshot_omega=override_body["omega_group"],
        settle_omega=override_reveal["report"]["omega_group"],
    )

    single = client.post(
        f"{BASE}/api/v1/recommend/single",
        json={
            "mode_type": "OUT_DINING",
            "limit": 3,
            "override_params": {"omega_group": 0.95},
        },
        headers=H1,
    )
    require(single.status_code == 200, single.text)
    connection = db_connect()
    try:
        config_value = connection.execute(
            "SELECT omega_group FROM algo_configs WHERE config_name='default_production'"
        ).fetchone()[0]
        room_params = connection.execute(
            "SELECT algo_params FROM group_rooms WHERE room_code=?",
            (override_body["room_code"],),
        ).fetchone()[0]
    finally:
        connection.close()
    require(abs(config_value - 0.1) < 1e-9, "单人 override 不得写 AlgoConfig")
    require(json.loads(room_params) == {"omega_group": 0.2}, "单人 override 不得改房间快照")
    record(
        "single_override_isolated",
        single_status=single.status_code,
        algo_config_omega=config_value,
        room_algo_params=json.loads(room_params),
    )

    # 全员 0 票：截止后按内部 TIMEOUT=60 结算，room_votes 不落 TIMEOUT。
    zero = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": 40},
        headers=H1,
    ).json()
    zero_code = zero["room_code"]
    client.post(
        f"{BASE}/api/v1/rooms/{zero_code}/join",
        json={"campus": "SIYUAN"},
        headers=H2,
    )
    async with connect(zero_code, 1) as host:
        await recv_until(host, "ROOM_STATE", "zero-host")
        await host.send(json.dumps({"type": "START_SWIPING"}))
        await recv_until(host, "START_SWIPING", "zero-host")
        await asyncio.sleep(16)
        zero_snap = client.get(f"{BASE}/api/v1/rooms/{zero_code}", headers=H1).json()
    require(zero_snap["status"] == "FINISHED", "0 票也应到点结算")
    require(zero_snap["winner_dish_id"] is not None, "0 票仍按先验+缺席分选赢家")
    require(
        all(
            member["vote_type"] == "TIMEOUT"
            for dish in zero_snap["consensus_report"]["dishes"]
            for member in dish["members"]
        ),
        "未投票成员应为内部 TIMEOUT",
    )
    zero_row = room_row(zero_code)
    require(len(zero_row["votes"]) == 0, "TIMEOUT 不得落 room_votes")
    record(
        "zero_votes_settle",
        room_code=zero_code,
        winner_dish_id=zero_snap["winner_dish_id"],
        stored_votes=len(zero_row["votes"]),
    )

    # 全员否决：无赢家、无共识。
    veto = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": 40},
        headers=H1,
    ).json()
    veto_reveal = await run_single_member_room(
        veto["room_code"], vote_type="VETO", trace_key="veto-host"
    )
    require(veto_reveal["winner_dish_id"] is None, "全员否决不得有赢家")
    require(veto_reveal["has_consensus"] is False, "全员否决应为无共识")
    veto_snap = client.get(
        f"{BASE}/api/v1/rooms/{veto['room_code']}", headers=H1
    ).json()
    require(veto_snap["winner_dish"] is None, "快照不得伪造赢家")
    record(
        "all_veto_no_consensus",
        room_code=veto["room_code"],
        winner_dish_id=veto_snap["winner_dish_id"],
        has_consensus=veto_snap["has_consensus"],
        vetoed=len(veto_snap["consensus_report"]["vetoed_dish_ids"]),
    )

    # 截止后投票：等定时器结算后再投票，必须被拒。
    late = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": 40},
        headers=H1,
    ).json()
    async with connect(late["room_code"], 1) as host:
        await recv_until(host, "ROOM_STATE", "late-host")
        await host.send(json.dumps({"type": "START_SWIPING"}))
        started = await recv_until(host, "START_SWIPING", "late-host")
        await asyncio.sleep(16)
        await host.send(
            json.dumps(
                {
                    "type": "SUBMIT_VOTE",
                    "dish_id": started["candidates"][0]["dish_id"],
                    "vote_type": "LIKE",
                }
            )
        )
        late_error = await recv_until(host, "ERROR", "late-host")
    require("结束" in late_error["detail"] or "到点" in late_error["detail"], "截止后投票必须拒绝")
    require(room_row(late["room_code"])["status"] == "FINISHED", "迟到投票不得改变结算")
    record("late_vote_rejected", detail=late_error["detail"])

    client.close()
    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "database": str(DB),
        "fixture_counts": {key: len(value) for key, value in fixture.items()},
        "steps": steps,
        "traces": traces,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "steps": len(steps), "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
