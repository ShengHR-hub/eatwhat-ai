"""复制 S06 隔离库（只读源库 -> 新副本），并记录来源/目标身份。"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[6]
SOURCE = ROOT / "backend" / "eatwhat_dev_pre00_r02.db"
TARGET = ROOT / "backend" / "eatwhat_s06_r02_iso.db"
OUT = Path(__file__).resolve().parent / "db_provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def state(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        return {
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "counts": {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "users",
                    "restaurants",
                    "dishes_and_recipes",
                    "eating_logs",
                    "group_rooms",
                    "room_votes",
                    "algo_configs",
                )
                if table in tables
            },
            "columns": {
                table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                for table in ("restaurants", "group_rooms", "room_votes")
                if table in tables
            },
        }
    finally:
        connection.close()


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"源库不存在：{SOURCE}")
    if TARGET.exists():
        raise SystemExit(f"目标已存在，拒绝覆盖：{TARGET}")
    source_before = state(SOURCE)
    shutil.copy2(SOURCE, TARGET)
    target_after = state(TARGET)
    payload = {
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "source": {"path": str(SOURCE.relative_to(ROOT)), **source_before},
        "target": {"path": str(TARGET.relative_to(ROOT)), **target_after},
        "same_sha256": source_before["sha256"] == target_after["sha256"],
        "source_unchanged_after_copy": sha256(SOURCE) == source_before["sha256"],
    }
    if not payload["same_sha256"]:
        raise SystemExit("复制后 SHA 不一致")
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
