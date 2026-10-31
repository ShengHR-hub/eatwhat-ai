"""把 `group_rooms` 升到 v2.3.2 契约（幂等，可反复跑）。

审查报告 F03/F05/F11 要求：
    * deadline_at  服务端截止时间落库，断线/重启/刷新都能结算
    * settled_at   结算幂等标记
    * budget       建房时的预算

SQLite 的 ALTER TABLE 不支持 IF NOT EXISTS，所以先查 PRAGMA 再补列。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "eatwhat.db"

COLUMNS = [
    ("budget", "FLOAT"),
    ("deadline_at", "DATETIME"),
    ("settled_at", "DATETIME"),
    ("algo_params", "JSON"),
]


def main() -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(group_rooms)")}
        added = []
        for name, ddl in COLUMNS:
            if name in existing:
                continue
            conn.execute(f"ALTER TABLE group_rooms ADD COLUMN {name} {ddl}")
            added.append(name)
        # 历史数据：已经 REVEALED 的房间按新枚举统一成 FINISHED
        migrated = conn.execute(
            "UPDATE group_rooms SET status = 'FINISHED' WHERE status = 'REVEALED'"
        ).rowcount
        conn.commit()
        return {"added_columns": added, "status_migrated": migrated, "ok": True}
    finally:
        conn.close()


if __name__ == "__main__":
    print(main())
