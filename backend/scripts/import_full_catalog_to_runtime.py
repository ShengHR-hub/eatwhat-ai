"""把 S10 全量门店/菜谱导入正常演示库，保留现有用户与流水。

只复制目录表，不改 users / eating_logs / group_rooms；ID 重新映射，避免覆盖现有 1..100。
重复执行会按 source_dataset 检测并跳过已导入目录。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "eatwhat_g2_s10_full.db"
DEFAULT_TARGET = ROOT / "eatwhat.db"
OUT = ROOT.parent / "docs" / "review" / "final" / "FULL_CATALOG_IMPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shared_columns(connection: sqlite3.Connection, table: str, source_schema: str) -> list[str]:
    source = [row[1] for row in connection.execute(f"PRAGMA {source_schema}.table_info({table})")]
    target = [row[1] for row in connection.execute(f"PRAGMA main.table_info({table})")]
    return [name for name in source if name in target and name != "id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    source = args.source.resolve()
    target = args.target.resolve()
    if not source.is_file() or not target.is_file():
        raise SystemExit("source/target 数据库不存在")
    if source == target:
        raise SystemExit("source 与 target 不能相同")

    source_sha_before = sha256(source)
    backup = target.with_name(f"{target.stem}_backup_before_catalog_{datetime.now():%Y%m%d_%H%M%S}{target.suffix}")
    shutil.copy2(target, backup)
    connection = sqlite3.connect(target)
    connection.execute("ATTACH DATABASE ? AS src", (str(source),))
    added = {}
    try:
        restaurant_source_count = connection.execute(
            "SELECT COUNT(*) FROM main.restaurants WHERE source_dataset LIKE 'amap_place_around_%'"
        ).fetchone()[0]
        dish_source_count = connection.execute(
            "SELECT COUNT(*) FROM main.dishes_and_recipes WHERE source_dataset = 'synthetic_recipe_v1'"
        ).fetchone()[0]

        if restaurant_source_count:
            added["restaurants"] = 0
            added["restaurants_skipped_existing"] = restaurant_source_count
        else:
            target_max = connection.execute("SELECT COALESCE(MAX(id), 0) FROM main.restaurants").fetchone()[0]
            source_min = connection.execute("SELECT MIN(id) FROM src.restaurants").fetchone()[0]
            offset = target_max + 1 - source_min
            columns = shared_columns(connection, "restaurants", "src")
            sql = f"INSERT INTO main.restaurants (id, {', '.join(columns)}) SELECT id + ?, {', '.join(columns)} FROM src.restaurants"
            before = connection.execute("SELECT COUNT(*) FROM main.restaurants").fetchone()[0]
            connection.execute(sql, (offset,))
            after = connection.execute("SELECT COUNT(*) FROM main.restaurants").fetchone()[0]
            added["restaurants"] = after - before
            added["restaurant_id_offset"] = offset

        if dish_source_count:
            added["dishes"] = 0
            added["dishes_skipped_existing"] = dish_source_count
        else:
            target_max = connection.execute("SELECT COALESCE(MAX(id), 0) FROM main.dishes_and_recipes").fetchone()[0]
            source_min = connection.execute("SELECT MIN(id) FROM src.dishes_and_recipes").fetchone()[0]
            offset = target_max + 1 - source_min
            columns = shared_columns(connection, "dishes_and_recipes", "src")
            sql = f"INSERT INTO main.dishes_and_recipes (id, {', '.join(columns)}) SELECT id + ?, {', '.join(columns)} FROM src.dishes_and_recipes"
            before = connection.execute("SELECT COUNT(*) FROM main.dishes_and_recipes").fetchone()[0]
            connection.execute(sql, (offset,))
            after = connection.execute("SELECT COUNT(*) FROM main.dishes_and_recipes").fetchone()[0]
            added["dishes"] = after - before
            added["dish_id_offset"] = offset

        connection.commit()
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM main.{table}").fetchone()[0]
            for table in ("users", "restaurants", "dishes_and_recipes", "eating_logs", "group_rooms", "room_votes")
        }
        campus = {
            row[0] or "NULL": row[1]
            for row in connection.execute("SELECT campus, COUNT(*) FROM main.restaurants GROUP BY campus")
        }
    finally:
        connection.close()

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": str(source),
        "source_sha256": sha256(source),
        "source_unchanged": sha256(source) == source_sha_before,
        "target": str(target),
        "backup": str(backup),
        "added": added,
        "counts": counts,
        "campus": campus,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
