"""G1 数据库保护探针：只读计算哈希与行数。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / "db_protection.json"

DATABASES = {
    "demo_eatwhat": ROOT / "backend" / "eatwhat.db",
    "s10_import_batch4": ROOT / "backend" / "eatwhat_batch4.db",
    "dev_pre00": ROOT / "backend" / "eatwhat_dev_pre00.db",
    "dev_pre00_r02": ROOT / "backend" / "eatwhat_dev_pre00_r02.db",
    "s05_r01_iso": ROOT / "backend" / "eatwhat_s05_r01_iso.db",
    "s06_r01_iso": ROOT / "backend" / "eatwhat_s06_r01_iso.db",
    "s06_r02_iso": ROOT / "backend" / "eatwhat_s06_r02_iso.db",
    "g1_target": ROOT / "backend" / "eatwhat_g1_s07_iso.db",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def state(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "users",
                "restaurants",
                "dishes_and_recipes",
                "eating_logs",
                "group_rooms",
                "room_votes",
                "fridge_inventory",
            )
            if table in tables
        }
        campus = {}
        if "restaurants" in tables:
            try:
                for row in connection.execute(
                    "SELECT COALESCE(campus, 'NULL'), COUNT(*) FROM restaurants GROUP BY campus"
                ):
                    campus[row[0]] = row[1]
            except sqlite3.OperationalError:
                campus = {"column_missing": True}
        return {"sha256": sha256(path), "size": path.stat().st_size, "counts": counts, "restaurant_campus": campus}
    finally:
        connection.close()


def main() -> None:
    baseline = OUT.parent / "db_baseline.json"
    current = {}
    for name, path in DATABASES.items():
        if not path.exists():
            current[name] = {"missing": True, "path": str(path)}
            continue
        current[name] = {"path": str(path), **state(path)}

    baseline_data = json.loads(baseline.read_text(encoding="utf-8")) if baseline.exists() else {}
    protected = [name for name in DATABASES if name != "g1_target"]
    unchanged = {
        name: baseline_data.get(name, {}).get("sha256") == current[name].get("sha256")
        for name in protected
        if not current[name].get("missing")
    }
    payload = {
        "checked_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "databases": current,
        "protected_unchanged_vs_baseline": unchanged,
        "all_protected_unchanged": all(unchanged.values()) if unchanged else None,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("protected_unchanged_vs_baseline", "all_protected_unchanged")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
