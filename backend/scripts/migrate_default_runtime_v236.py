"""把默认演示库补齐到 v2.3.6 运行 schema。

只加列/索引并回填演示数据的标记，不删除表、不重写历史行；执行前自动备份。
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "eatwhat.db"

COLUMNS = {
    "restaurants": {
        "source_dataset": "VARCHAR(64)",
        "source_record_id": "VARCHAR(64)",
        "source_url": "VARCHAR(255)",
        "data_version": "VARCHAR(64)",
        "is_synthetic": "BOOLEAN",
        "deleted_at": "DATETIME",
        "campus": "VARCHAR(32)",
    },
    "dishes_and_recipes": {
        "allergen_tags": "JSON",
        "tagging_status": "VARCHAR(16)",
        "tagging_error": "TEXT",
        "llm_meta": "JSON",
        "source_dataset": "VARCHAR(64)",
        "source_record_id": "VARCHAR(64)",
        "source_url": "VARCHAR(255)",
        "data_version": "VARCHAR(64)",
        "is_synthetic": "BOOLEAN",
        "deleted_at": "DATETIME",
    },
    "group_rooms": {"campus": "VARCHAR(32)"},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    db = args.db.resolve()
    if not db.is_file():
        raise SystemExit(f"数据库不存在：{db}")
    backup = db.with_name(f"{db.stem}_backup_before_g4_{datetime.now():%Y%m%d_%H%M%S}{db.suffix}")
    shutil.copy2(db, backup)
    connection = sqlite3.connect(db)
    added = []
    try:
        for table, columns in COLUMNS.items():
            existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, kind in columns.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
                    added.append(f"{table}.{name}")
        connection.execute(
            "UPDATE dishes_and_recipes SET tagging_status = CASE "
            "WHEN feature_vector IS NOT NULL THEN 'SUCCESS' ELSE 'PENDING' END "
            "WHERE tagging_status IS NULL"
        )
        # 原实现把所有 campus 为 NULL 的门店一律改成 SIYUAN，违反 v2.3.3
        # 「缺失保持 NULL」与 v2.3.4 双校区隔离：来源是建大但没写校区的店
        # 会被算进思源，外食推荐、大屏统计、群组拼桌全部跨校区污染，且不可回滚。
        # 现在保持 NULL，只统计数量供人工确认。
        unassigned = connection.execute(
            "SELECT COUNT(*) FROM restaurants WHERE campus IS NULL"
        ).fetchone()[0]
        if unassigned:
            print(
                f"[campus] {unassigned} 家门店未分配校区，保持 NULL；"
                "如需归属请按坐标或来源单独处理，不再一刀切改成 SIYUAN。"
            )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_room_votes_room_user_dish "
            "ON room_votes(room_code, user_id, dish_id)"
        )
        connection.commit()
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "dishes_and_recipes", "restaurants", "eating_logs", "group_rooms", "room_votes")
        }
    finally:
        connection.close()
    print({"db": str(db), "backup": str(backup), "added": added, "counts": counts})


if __name__ == "__main__":
    main()
