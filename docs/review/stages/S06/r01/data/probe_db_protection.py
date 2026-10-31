"""S06 数据库保护摘要：受保护库哈希不变；所有写入只在 S06 隔离副本。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[6]
DATA = Path(__file__).resolve().parent
BASELINE = json.loads((DATA / "baseline.json").read_text(encoding="utf-8"))
OUT = DATA / "db_protection.json"
ISO = ROOT / "backend" / "eatwhat_s06_r01_iso.db"

PROTECTED = (
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00_r02.db",
    "backend/eatwhat_dev_pre00.db",
    "backend/eatwhat_s05_r01_iso.db",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def counts(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        payload = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "restaurants",
                "dishes_and_recipes",
                "group_rooms",
                "room_votes",
            )
            if table in tables
        }
        if "restaurants" in tables and "campus" in [
            row[1] for row in connection.execute("PRAGMA table_info(restaurants)")
        ]:
            payload["restaurant_campus"] = [
                list(row)
                for row in connection.execute(
                    "SELECT campus, COUNT(*) FROM restaurants GROUP BY campus ORDER BY campus"
                )
            ]
        return payload
    finally:
        connection.close()


def main() -> None:
    protected = {}
    all_unchanged = True
    for relative in PROTECTED:
        path = ROOT / relative
        before = BASELINE["databases"][relative]["sha256"]
        after = sha256(path)
        unchanged = before == after
        all_unchanged = all_unchanged and unchanged
        protected[relative] = {
            "sha256_before": before,
            "sha256_after": after,
            "unchanged": unchanged,
            "counts_after": counts(path),
        }

    iso_counts = counts(ISO)
    connection = sqlite3.connect(f"file:{ISO.as_posix()}?mode=ro", uri=True)
    try:
        fixture_restaurants = connection.execute(
            "SELECT campus, COUNT(*) FROM restaurants "
            "WHERE source_dataset='s06_fixture_v1' GROUP BY campus ORDER BY campus"
        ).fetchall()
        fixture_dishes = connection.execute(
            "SELECT r.campus, COUNT(*) FROM dishes_and_recipes d "
            "JOIN restaurants r ON r.id=d.restaurant_id "
            "WHERE d.source_dataset='s06_fixture_v1' GROUP BY r.campus ORDER BY r.campus"
        ).fetchall()
        index_rows = [
            row[1] for row in connection.execute("PRAGMA index_list(room_votes)")
        ]
        room_status = connection.execute(
            "SELECT status, COUNT(*) FROM group_rooms GROUP BY status ORDER BY status"
        ).fetchall()
        vote_types = connection.execute(
            "SELECT vote_type, COUNT(*) FROM room_votes GROUP BY vote_type ORDER BY vote_type"
        ).fetchall()
        isolated_rooms = connection.execute(
            "SELECT room_code, campus, status, algo_params, settled_at IS NOT NULL "
            "FROM group_rooms ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "protected": protected,
        "protected_all_unchanged": all_unchanged,
        "s06_iso": {
            "path": str(ISO.relative_to(ROOT)),
            "sha256": sha256(ISO),
            "counts": iso_counts,
            "fixture_restaurants_by_campus": fixture_restaurants,
            "fixture_dishes_by_campus": fixture_dishes,
            "room_vote_indexes": index_rows,
            "room_status": room_status,
            "vote_types": vote_types,
            "rooms": isolated_rooms,
        },
        "ok": all_unchanged,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    if not all_unchanged:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
