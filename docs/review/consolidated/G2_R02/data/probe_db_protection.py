"""G2 数据库保护探针：受保护库只读，G2 目标库记录现状。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parent
OUT = BASE / "db_protection.json"

DATABASES = {
    "demo_eatwhat": ROOT / "backend" / "eatwhat.db",
    "s10_import_batch4": ROOT / "backend" / "eatwhat_batch4.db",
    "dev_pre00": ROOT / "backend" / "eatwhat_dev_pre00.db",
    "dev_pre00_r02": ROOT / "backend" / "eatwhat_dev_pre00_r02.db",
    "s05_r01_iso": ROOT / "backend" / "eatwhat_s05_r01_iso.db",
    "s06_r01_iso": ROOT / "backend" / "eatwhat_s06_r01_iso.db",
    "s06_r02_iso": ROOT / "backend" / "eatwhat_s06_r02_iso.db",
    "g1_target": ROOT / "backend" / "eatwhat_g1_s07_iso.db",
    "g2_s10_smoke": ROOT / "backend" / "eatwhat_g2_s10_smoke.db",
    "g2_s10_full": ROOT / "backend" / "eatwhat_g2_s10_full.db",
    "g2_bridge": ROOT / "backend" / "eatwhat_g2_bridge_iso.db",
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
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
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
        shaped = {}
        if "restaurants" in tables:
            try:
                shaped = {
                    "|".join("NULL" if value is None else str(value) for value in row[:3]): row[3]
                    for row in connection.execute(
                        "SELECT campus, source_type, source_dataset, COUNT(*) FROM restaurants "
                        "GROUP BY campus, source_type, source_dataset"
                    )
                }
            except sqlite3.OperationalError:
                shaped = {"column_missing": True}
        dishes = {}
        if "dishes_and_recipes" in tables:
            try:
                dishes = {
                    "|".join("NULL" if value is None else str(value) for value in row[:2]): row[2]
                    for row in connection.execute(
                        "SELECT mode_type, tagging_status, COUNT(*) FROM dishes_and_recipes "
                        "GROUP BY mode_type, tagging_status"
                    )
                }
            except sqlite3.OperationalError:
                dishes = {"column_missing": True}
        return {"sha256": sha256(path), "size": path.stat().st_size, "counts": counts, "restaurant_shape": shaped, "dish_status": dishes}
    finally:
        connection.close()


def main() -> None:
    baseline = json.loads((BASE / "db_baseline.json").read_text(encoding="utf-8"))
    current = {}
    for name, path in DATABASES.items():
        if path.exists():
            current[name] = {"path": str(path), **state(path)}
        else:
            current[name] = {"path": str(path), "missing": True}
    protected = [name for name in DATABASES if not name.startswith("g2_")]
    unchanged = {
        name: baseline["databases"].get(name, {}).get("sha256") == current[name].get("sha256")
        for name in protected
        if not current[name].get("missing")
    }
    s09_manifest = ROOT / "docs/review/stages/S09/r04/SOURCE_MANIFEST.json"
    payload = {
        "checked_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "databases": current,
        "protected_unchanged_vs_baseline": unchanged,
        "all_protected_unchanged": all(unchanged.values()),
        "s09_manifest_sha256": sha256(s09_manifest),
        "s09_manifest_unchanged": sha256(s09_manifest) == baseline["s09_manifest_sha256"],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("protected_unchanged_vs_baseline", "all_protected_unchanged", "s09_manifest_unchanged")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
