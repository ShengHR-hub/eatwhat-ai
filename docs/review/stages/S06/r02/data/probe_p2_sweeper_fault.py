"""P2-S06-01 真实隔离服务复验（无 WS 客户端、无定时器的过期房间）。

1. 直接向隔离库插入一个 SWIPING、已过截止的房间（没有 START，因此没有内存定时器）；
2. 用独立 SQLite `BEGIN EXCLUSIVE` 覆盖至少两轮 sweeper，制造扫描级瞬态故障；
3. 释放后不再向房间发任何 HTTP/WS 请求，只读 DB 确认 sweeper 已恢复并结算；
4. 服务日志必须出现先 `room_sweeper_failed`、后 `room_sweep_settled(room_code)`。
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

BASE = "http://127.0.0.1:8026"
ROOT = Path(__file__).resolve().parents[6]
DB = ROOT / "backend" / "eatwhat_s06_r02_iso.db"
SERVER_LOG = Path(__file__).resolve().parents[1] / "logs" / "05_backend_start.log"
OUT = Path(__file__).resolve().parent / "p2_sweeper_fault.json"

sys.stdout.reconfigure(encoding="utf-8")
ROOM_CODE = "970002"


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fixture_dish_ids(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(
        "SELECT id FROM dishes_and_recipes WHERE source_dataset='s06_fixture_v1' "
        "ORDER BY id LIMIT 10"
    ).fetchall()
    return [int(row[0]) for row in rows]


def insert_overdue_room() -> dict:
    connection = sqlite3.connect(DB, timeout=10)
    try:
        connection.execute("PRAGMA busy_timeout=10000")
        existing = connection.execute(
            "SELECT 1 FROM group_rooms WHERE room_code=?", (ROOM_CODE,)
        ).fetchone()
        if existing:
            raise SystemExit(f"{ROOM_CODE} 已存在；请换用新的 r02 隔离库")
        dish_ids = fixture_dish_ids(connection)
        assert len(dish_ids) == 10, dish_ids
        now = utcnow_naive()
        deadline = now + timedelta(seconds=3)
        connection.execute(
            "INSERT INTO group_rooms "
            "(room_code, host_user_id, mode_type, status, member_user_ids, "
            "candidate_dish_ids, winner_dish_id, consensus_report, budget, "
            "deadline_at, settled_at, created_at, algo_params, campus) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                ROOM_CODE,
                1,
                "OUT_DINING",
                "SWIPING",
                json.dumps([1]),
                json.dumps(dish_ids),
                None,
                None,
                None,
                deadline.isoformat(sep=" "),
                None,
                now.isoformat(sep=" "),
                json.dumps({"omega_group": 0.5}),
                "SIYUAN",
            ),
        )
        connection.commit()
        return {
            "room_code": ROOM_CODE,
            "deadline_at": deadline.isoformat(sep=" "),
            "candidate_dish_ids": dish_ids,
            "timer_scheduled": False,
            "ws_client_connected": False,
        }
    finally:
        connection.close()


def read_room() -> dict:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        room = connection.execute(
            "SELECT status, deadline_at, settled_at, winner_dish_id, consensus_report "
            "FROM group_rooms WHERE room_code=?",
            (ROOM_CODE,),
        ).fetchone()
        votes = connection.execute(
            "SELECT COUNT(*) FROM room_votes WHERE room_code=?", (ROOM_CODE,)
        ).fetchone()[0]
    finally:
        connection.close()
    payload = dict(room)
    payload["vote_count"] = votes
    return payload


def read_new_log(offset: int) -> str:
    with open(SERVER_LOG, "r", encoding="utf-8", errors="replace") as handle:
        handle.seek(offset)
        return handle.read()


def main() -> None:
    client = httpx.Client(trust_env=False, timeout=10)
    health = client.get(f"{BASE}/health")
    assert health.status_code == 200, health.text
    client.close()

    log_offset = SERVER_LOG.stat().st_size
    inserted = insert_overdue_room()

    lock_code = (
        "import sqlite3,time\n"
        f"c=sqlite3.connect(r'{DB.as_posix()}', timeout=30)\n"
        "c.execute('BEGIN EXCLUSIVE')\n"
        "print('locked', flush=True)\n"
        "time.sleep(30)\n"
        "c.rollback(); c.close()\n"
        "print('released', flush=True)\n"
    )
    holder = subprocess.Popen(
        [sys.executable, "-c", lock_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert holder.stdout is not None
    locked_line = holder.stdout.readline().strip()
    assert locked_line == "locked", locked_line
    locked_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()

    # 截止 3s；锁 30s，覆盖多轮 5s sweeper；释放后再等 12s。
    time.sleep(45)
    holder.wait(timeout=10)
    stdout_rest = holder.stdout.read() if holder.stdout is not None else ""
    stderr_text = holder.stderr.read() if holder.stderr is not None else ""
    released_line = (
        "released" if "released" in stdout_rest else stdout_rest.strip() or "exited"
    )
    released_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()

    after = read_room()
    assert after["status"] == "FINISHED", f"sweeper 恢复后应结算，实际 {after['status']}"
    assert after["settled_at"], "settled_at 必须有值"
    assert after["settled_at"] > after["deadline_at"], "结算必须晚于截止"
    assert after["winner_dish_id"], "应产生赢家"
    assert after["consensus_report"], "应写完整报告"
    assert after["vote_count"] == 0, "0 票房间不应出现 TIMEOUT 票"

    log_text = read_new_log(log_offset)
    failure_pos = log_text.find("room_sweeper_failed")
    settled_pos = log_text.find("room_sweep_settled")
    assert failure_pos >= 0, "本轮服务日志应出现扫描级异常"
    assert settled_pos >= 0, "本轮服务日志应出现后续周期成功结算"
    assert failure_pos < settled_pos, "必须先失败、后恢复"
    assert ROOM_CODE in log_text[settled_pos:], "成功结算日志应包含本房间码"

    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "room_code": ROOM_CODE,
        "deadline_at": inserted["deadline_at"],
        "candidate_dish_ids": inserted["candidate_dish_ids"],
        "timer_scheduled": False,
        "ws_client_connected": False,
        "lock_locked_at": locked_at,
        "lock_released_at": released_at,
        "locked_line": locked_line,
        "released_line": released_line,
        "lock_holder_stderr": stderr_text.strip(),
        "database_after_without_client_request": after,
        "server_log": {
            "path": str(SERVER_LOG),
            "log_offset": log_offset,
            "room_sweeper_failed_at": failure_pos,
            "room_sweep_settled_at": settled_pos,
            "failure_before_recovery": failure_pos < settled_pos,
            "room_code_in_settled_log": ROOM_CODE in log_text[settled_pos:],
        },
        "ok": True,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
