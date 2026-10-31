"""G2 BRIDGE-10：把 S10 导入库的数据以显式导入边界挂到运行时副本。

边界：
* 源：`backend/eatwhat_batch4.db`（S10 独立导入库，只读 ATTACH）；
* 模板：`backend/eatwhat_g1_s07_iso.db`（G1 隔离运行库，含演示用户/日志/冰箱）；
* 目标：`backend/eatwhat_g2_bridge_iso.db`（G2 明确命名副本，唯一写入目标）；
* 不把 S10 大库直接当首页演示库；演示用户/日志/库存仍来自模板；
* 重复执行按唯一来源键去重，不增加重复行。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE = ROOT / "backend" / "eatwhat_batch4.db"
TEMPLATE = ROOT / "backend" / "eatwhat_g1_s07_iso.db"
TARGET = ROOT / "backend" / "eatwhat_g2_bridge_iso.db"
OUT = ROOT / "docs" / "review" / "consolidated" / "G2" / "data" / "bridge_provenance.json"
CAMPUSES = ("SIYUAN", "JIANDA_YANTA")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def columns(connection: sqlite3.Connection, table: str, schema: str = "main") -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA {schema}.table_info({table})")]


def transfer(connection: sqlite3.Connection, table: str, where: str = "") -> int:
    source_columns = columns(connection, table, "s10")
    target_columns = columns(connection, table)
    shared = [name for name in source_columns if name in target_columns and name != "id"]
    column_sql = ", ".join(shared)
    sql = f"INSERT OR IGNORE INTO main.{table} ({column_sql}) SELECT {column_sql} FROM s10.{table}"
    if where:
        sql += f" WHERE {where}"
    before = connection.execute(f"SELECT COUNT(*) FROM main.{table}").fetchone()[0]
    connection.execute(sql)
    connection.commit()
    after = connection.execute(f"SELECT COUNT(*) FROM main.{table}").fetchone()[0]
    return after - before


def main() -> None:
    parser = argparse.ArgumentParser(description="G2 运行时桥接（显式导入边界）")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--skip-recipes", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    template = args.template.resolve()
    target = args.target.resolve()
    if not (
        target.name.startswith("eatwhat_g2_bridge_")
        or target.name.startswith("eatwhat_g3_bridge_")
    ) or target.suffix != ".db":
        raise SystemExit("目标必须是明确命名的 G2/G3 桥接隔离库（eatwhat_g2_bridge_* / eatwhat_g3_bridge_*.db）")
    out = args.out.resolve()
    for item in (source, template):
        if not item.exists():
            raise SystemExit(f"缺少输入库：{item}")
    if source == target or template == target:
        raise SystemExit("目标不能与源库/模板相同")

    source_sha_before = sha256(source)
    template_sha_before = sha256(template)
    created = False
    if not target.exists():
        shutil.copy2(template, target)
        created = True
    if sha256(target) != template_sha_before and created:
        raise SystemExit("复制后目标与模板不一致")

    from backend.scripts import migrate_s10_data_schema as migration

    migration_report = migration.migrate(target)

    connection = sqlite3.connect(target)
    try:
        connection.execute("ATTACH DATABASE ? AS s10", (str(source),))
        campus_filter = "'" + "','".join(CAMPUSES) + "'"
        added_restaurants = transfer(connection, "restaurants", f"campus IN ({campus_filter})")
        added_dishes = 0 if args.skip_recipes else transfer(connection, "dishes_and_recipes")
        stats = {}
        for campus in CAMPUSES:
            stats[campus] = {
                "s10_amap": connection.execute(
                    "SELECT COUNT(*) FROM restaurants WHERE campus=? AND source_type='AMAP_POI' AND source_dataset LIKE 'amap_%'",
                    (campus,),
                ).fetchone()[0],
                "s10_canteen": connection.execute(
                    "SELECT COUNT(*) FROM restaurants WHERE campus=? AND source_type='CANTEEN' AND source_dataset='synthetic_canteen_v1'",
                    (campus,),
                ).fetchone()[0],
                "g1_fixture_restaurants": connection.execute(
                    "SELECT COUNT(*) FROM restaurants WHERE campus=? AND source_dataset='g1_fixture_v1'",
                    (campus,),
                ).fetchone()[0],
            }
        stats["NULL"] = {
            "seed_restaurants": connection.execute(
                "SELECT COUNT(*) FROM restaurants WHERE campus IS NULL"
            ).fetchone()[0]
        }
        stats["by_dataset"] = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT COALESCE(source_dataset,'NULL'), COUNT(*) FROM restaurants GROUP BY source_dataset"
            )
        }
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "users",
                "restaurants",
                "dishes_and_recipes",
                "eating_logs",
                "fridge_inventory",
                "group_rooms",
                "room_votes",
            )
        }
        added_before_counts = {
            "restaurants": added_restaurants,
            "dishes_and_recipes": added_dishes,
        }
    finally:
        connection.close()

    payload = {
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "source": str(source),
        "source_sha256": sha256(source),
        "source_sha256_before": source_sha_before,
        "template": str(template),
        "template_sha256": template_sha_before,
        "target": str(target),
        "target_sha256": sha256(target),
        "target_created_from_template": created,
        "migration": migration_report,
        "added_rows_this_run": added_before_counts,
        "counts": counts,
        "campus_stats": stats,
        "source_unchanged": sha256(source) == source_sha_before,
        "template_unchanged": sha256(template) == template_sha_before,
        "rollback": "删除 backend/eatwhat_g2_bridge_iso.db 即可；源库与模板均为只读使用",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("target", "added_rows_this_run", "campus_stats", "source_unchanged", "template_unchanged")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
