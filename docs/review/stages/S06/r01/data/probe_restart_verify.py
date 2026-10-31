"""重启测试第二步：先只读数据库证明已结算，再 GET 快照；不先发任何房间请求。"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

BASE = "http://127.0.0.1:8025"
ROOT = Path(__file__).resolve().parents[6]
DB = ROOT / "backend" / "eatwhat_s06_r01_iso.db"
ROOM_FILE = Path(__file__).resolve().parent / "restart_room.json"
OUT = Path(__file__).resolve().parent / "restart_flow.json"
H1 = {"X-User-Id": "1"}

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    prepared = json.loads(ROOM_FILE.read_text(encoding="utf-8"))
    code = prepared["room_code"]

    # 关键顺序：先只读 DB，确认没有任何客户端请求时已经结算。
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT status, settled_at, winner_dish_id, consensus_report, deadline_at "
            "FROM group_rooms WHERE room_code=?",
            (code,),
        ).fetchone()
        votes = connection.execute(
            "SELECT user_id, dish_id, vote_type FROM room_votes WHERE room_code=?",
            (code,),
        ).fetchall()
    finally:
        connection.close()

    assert row is not None, "房间不存在"
    assert row["status"] == "FINISHED", f"重启后应已结算，实际 {row['status']}"
    assert row["settled_at"], "settled_at 必须有值"
    assert row["winner_dish_id"], "重启结算应产生赢家"
    report = json.loads(row["consensus_report"])
    assert report["dishes"], "重启结算应写完整报告"
    assert len(votes) == 1, f"重启不应新增/丢失票，实际 {len(votes)}"

    client = httpx.Client(trust_env=False, timeout=20)
    snapshot = client.get(f"{BASE}/api/v1/rooms/{code}", headers=H1)
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert body["status"] == "FINISHED"
    assert body["winner_dish_id"] == row["winner_dish_id"]
    assert body["consensus_report"] == report
    assert len(body["my_votes"]) == 1
    client.close()

    payload = {
        "verified_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "room_code": code,
        "database_before_any_client_request": {
            "status": row["status"],
            "settled_at": row["settled_at"],
            "deadline_at": row["deadline_at"],
            "winner_dish_id": row["winner_dish_id"],
            "report_dish_count": len(report["dishes"]),
            "vote_count": len(votes),
            "votes": [dict(item) for item in votes],
        },
        "http_snapshot": {
            "status": body["status"],
            "winner_dish_id": body["winner_dish_id"],
            "my_votes": len(body["my_votes"]),
            "campus": body["campus"],
            "omega_group": body["omega_group"],
        },
        "ok": True,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
