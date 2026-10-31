"""S04 数据库保护与隔离库摘要（只读）。

- 演示库 / S10 库 / 开发源库：SHA-256 与 S03 基线一致；
- S04 隔离副本：来源 SHA、当前 SHA、schema fingerprint、行数、NULL 向量计数；
- 不执行任何写操作。
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/EatWhat")
OUT = ROOT / "docs" / "review" / "stages" / "S04" / "r01" / "data"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

PROTECTED = {
    "demo": ROOT / "backend" / "eatwhat.db",
    "s10_import": ROOT / "backend" / "eatwhat_batch4.db",
    "dev_source": ROOT / "backend" / "eatwhat_dev_pre00_r02.db",
}
EXPECTED = {
    "demo": "775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b",
    "s10_import": "315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28",
    "dev_source": "b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579",
}
ISO = ROOT / "backend" / "eatwhat_s04_r01_iso.db"

TABLES = [
    "users",
    "user_preferences",
    "restaurants",
    "dishes_and_recipes",
    "fridge_inventory",
    "eating_logs",
    "group_rooms",
    "room_votes",
    "algo_configs",
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schema_fingerprint(path):
    con = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    try:
        rows = []
        for table in TABLES:
            for row in con.execute(f"pragma table_info({table})"):
                rows.append(f"{table}.{row[1]}:{row[2]}:{row[3]}")
        return hashlib.sha256("\n".join(rows).encode()).hexdigest(), len(rows)
    finally:
        con.close()


def inventory(path):
    con = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    try:
        counts = {
            table: int(con.execute(f"select count(*) from {table}").fetchone()[0])
            for table in TABLES
        }
        nulls = {
            "dishes_feature_vector_null": int(
                con.execute(
                    "select count(*) from dishes_and_recipes "
                    "where feature_vector is null"
                ).fetchone()[0]
            ),
            "dishes_deleted_at_not_null": int(
                con.execute(
                    "select count(*) from dishes_and_recipes "
                    "where deleted_at is not null"
                ).fetchone()[0]
            ),
            "restaurants_deleted_at_not_null": int(
                con.execute(
                    "select count(*) from restaurants where deleted_at is not null"
                ).fetchone()[0]
            ),
        }
        journal = con.execute("pragma journal_mode").fetchone()[0]
        return counts, nulls, journal
    finally:
        con.close()


def main():
    protected_now = {name: sha256(path) for name, path in PROTECTED.items()}
    assert protected_now == EXPECTED, protected_now

    dev_counts, dev_nulls, dev_journal = inventory(PROTECTED["dev_source"])
    iso_counts, iso_nulls, iso_journal = inventory(ISO)
    dev_schema, dev_columns = schema_fingerprint(PROTECTED["dev_source"])
    iso_schema, iso_columns = schema_fingerprint(ISO)

    result = {
        "generated_at": NOW,
        "protected": {
            name: {
                "path": str(path),
                "sha256": protected_now[name],
                "expected_sha256": EXPECTED[name],
                "unchanged": protected_now[name] == EXPECTED[name],
            }
            for name, path in PROTECTED.items()
        },
        "iso": {
            "path": str(ISO),
            "source": str(PROTECTED["dev_source"]),
            "sha256": sha256(ISO),
            "source_sha256": EXPECTED["dev_source"],
            "schema_fingerprint": iso_schema,
            "schema_columns": iso_columns,
            "counts": iso_counts,
            "null_counts": iso_nulls,
            "journal_mode": iso_journal,
        },
        "dev_source": {
            "schema_fingerprint": dev_schema,
            "schema_columns": dev_columns,
            "counts": dev_counts,
            "null_counts": dev_nulls,
            "journal_mode": dev_journal,
        },
        "schema_matches_source": iso_schema == dev_schema,
        "counts_delta": {
            table: iso_counts[table] - dev_counts[table] for table in TABLES
        },
        "passed": protected_now == EXPECTED and iso_schema == dev_schema,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "db_protection.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "protected_unchanged": all(
                    item["unchanged"] for item in result["protected"].values()
                ),
                "schema_matches_source": result["schema_matches_source"],
                "iso_counts": iso_counts,
                "iso_null_counts": iso_nulls,
                "passed": result["passed"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
