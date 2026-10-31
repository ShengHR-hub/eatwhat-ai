"""P2-S06-02 真实 REST/WS 复验：既有成员在 SWIPING/FINISHED 重复 join 必须 400。"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import websockets

BASE = "http://127.0.0.1:8026"
WS_BASE = "ws://127.0.0.1:8026"
ROOT = Path(__file__).resolve().parents[6]
DB = ROOT / "backend" / "eatwhat_s06_r02_iso.db"
OUT = Path(__file__).resolve().parent / "p2_join_state.json"
H1 = {"X-User-Id": "1"}
H2 = {"X-User-Id": "2"}

sys.stdout.reconfigure(encoding="utf-8")


def row(code: str) -> dict:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        room = connection.execute(
            "SELECT * FROM group_rooms WHERE room_code=?", (code,)
        ).fetchone()
        votes = connection.execute(
            "SELECT COUNT(*) FROM room_votes WHERE room_code=?", (code,)
        ).fetchone()[0]
    finally:
        connection.close()
    payload = dict(room)
    payload["vote_count"] = votes
    return payload


def force_due(code: str) -> None:
    connection = sqlite3.connect(DB, timeout=10)
    try:
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute(
            "UPDATE group_rooms SET deadline_at=? WHERE room_code=?",
            (
                (
                    datetime.now(timezone.utc).replace(tzinfo=None)
                    - timedelta(seconds=1)
                ).isoformat(sep=" "),
                code,
            ),
        )
        connection.commit()
    finally:
        connection.close()


async def recv_until(ws, want, timeout=15):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if message.get("type") == want:
            return message


async def main() -> None:
    client = httpx.Client(trust_env=False, timeout=20)
    created = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": 40},
        headers=H1,
    )
    assert created.status_code == 200, created.text
    code = created.json()["room_code"]
    joined = client.post(
        f"{BASE}/api/v1/rooms/{code}/join",
        json={"campus": "SIYUAN"},
        headers=H2,
    )
    assert joined.status_code == 200, joined.text

    async with websockets.connect(f"{WS_BASE}/ws/room/{code}/1") as host:
        await recv_until(host, "ROOM_STATE")
        await host.send(json.dumps({"type": "START_SWIPING"}))
        started = await recv_until(host, "START_SWIPING")
        candidates = [item["dish_id"] for item in started["candidates"]]
        before_swiping = row(code)

        swiping_join = client.post(
            f"{BASE}/api/v1/rooms/{code}/join",
            json={"campus": "SIYUAN"},
            headers=H2,
        )
        assert swiping_join.status_code == 400, swiping_join.text
        assert "开始" in swiping_join.text
        after_swiping = row(code)
        assert after_swiping["member_user_ids"] == before_swiping["member_user_ids"]
        assert after_swiping["candidate_dish_ids"] == before_swiping["candidate_dish_ids"]
        assert after_swiping["vote_count"] == 0

        force_due(code)
        snapshot = client.get(f"{BASE}/api/v1/rooms/{code}", headers=H1)
        assert snapshot.status_code == 200, snapshot.text
        snap = snapshot.json()
        assert snap["status"] == "FINISHED"
        before_finished_join = row(code)

        member_join = client.post(
            f"{BASE}/api/v1/rooms/{code}/join",
            json={"campus": "SIYUAN"},
            headers=H2,
        )
        assert member_join.status_code == 400, member_join.text
        host_join = client.post(
            f"{BASE}/api/v1/rooms/{code}/join",
            json={"campus": "SIYUAN"},
            headers=H1,
        )
        assert host_join.status_code == 400, host_join.text
        after_finished_join = row(code)
        assert after_finished_join["member_user_ids"] == before_finished_join["member_user_ids"]
        assert after_finished_join["candidate_dish_ids"] == before_finished_join["candidate_dish_ids"]
        assert after_finished_join["vote_count"] == before_finished_join["vote_count"]
        assert after_finished_join["winner_dish_id"] == before_finished_join["winner_dish_id"]
        assert after_finished_join["consensus_report"] == before_finished_join["consensus_report"]

    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "room_code": code,
        "swiping_join_status": swiping_join.status_code,
        "finished_member_join_status": member_join.status_code,
        "finished_host_join_status": host_join.status_code,
        "members_before_swiping": before_swiping["member_user_ids"],
        "members_after_swiping_join": after_swiping["member_user_ids"],
        "members_after_finished_join": after_finished_join["member_user_ids"],
        "candidates_before": candidates,
        "vote_count_before": before_swiping["vote_count"],
        "vote_count_after": after_finished_join["vote_count"],
        "status_after": snap["status"],
        "winner_dish_id": snap["winner_dish_id"],
        "no_side_effects": True,
        "ok": True,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
