"""给建大雁塔复制一套外食 fixture 门店/菜品，解决建大无推荐。

只复制当前挂在思源门店上的 OUT_DINING fixture 菜品及其门店；
门店名加“建大 · ”前缀，避免与思源混淆。重复执行会跳过已存在的建大外食菜品。
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "eatwhat.db"
OUT = ROOT.parent / "docs" / "review" / "final" / "JIENDA_FIXTURE_CLONE.json"


def main() -> None:
    backup = DB.with_name(f"{DB.stem}_backup_before_jianda_{datetime.now():%Y%m%d_%H%M%S}{DB.suffix}")
    shutil.copy2(DB, backup)
    conn = sqlite3.connect(DB)
    try:
        existing = conn.execute(
            """SELECT COUNT(*) FROM dishes_and_recipes d
               JOIN restaurants r ON r.id=d.restaurant_id
               WHERE d.mode_type='OUT_DINING' AND r.campus='JIANDA_YANTA'"""
        ).fetchone()[0]
        if existing:
            print(json.dumps({"skipped": True, "existing": existing}, ensure_ascii=False))
            return

        source_restaurants = conn.execute(
            """SELECT DISTINCT r.* FROM restaurants r
               JOIN dishes_and_recipes d ON d.restaurant_id=r.id
               WHERE d.mode_type='OUT_DINING' AND r.campus='SIYUAN'"""
        ).fetchall()
        columns = [row[1] for row in conn.execute("PRAGMA table_info(restaurants)")]
        source_ids = [row[columns.index("id")] for row in source_restaurants]
        name_idx = columns.index("name")
        campus_idx = columns.index("campus")
        mapping = {}
        id_idx = columns.index("id")
        for row in source_restaurants:
            values = list(row)
            values[id_idx] = None
            values[name_idx] = f"建大 · {values[name_idx]}"
            values[campus_idx] = "JIANDA_YANTA"
            placeholders = ",".join("?" for _ in columns)
            cursor = conn.execute(
                f"INSERT INTO restaurants ({','.join(columns)}) VALUES ({placeholders})",
                values,
            )
            mapping[row[columns.index("id")]] = cursor.lastrowid

        dish_columns = [row[1] for row in conn.execute("PRAGMA table_info(dishes_and_recipes)")]
        dish_rows = conn.execute(
            f"SELECT * FROM dishes_and_recipes WHERE mode_type='OUT_DINING' AND restaurant_id IN ({','.join('?' for _ in source_ids)})",
            source_ids,
        ).fetchall()
        dish_id_idx = dish_columns.index("id")
        restaurant_idx = dish_columns.index("restaurant_id")
        source_idx = dish_columns.index("source_dataset") if "source_dataset" in dish_columns else None
        for row in dish_rows:
            values = list(row)
            values[dish_id_idx] = None
            values[restaurant_idx] = mapping[row[restaurant_idx]]
            if source_idx is not None:
                values[source_idx] = "fixture_jianda_clone"
            placeholders = ",".join("?" for _ in dish_columns)
            conn.execute(
                f"INSERT INTO dishes_and_recipes ({','.join(dish_columns)}) VALUES ({placeholders})",
                values,
            )
        conn.commit()
        counts = {
            "restaurants": conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0],
            "dishes": conn.execute("SELECT COUNT(*) FROM dishes_and_recipes").fetchone()[0],
            "jianda_out_dishes": conn.execute(
                """SELECT COUNT(*) FROM dishes_and_recipes d
                   JOIN restaurants r ON r.id=d.restaurant_id
                   WHERE d.mode_type='OUT_DINING' AND r.campus='JIANDA_YANTA'"""
            ).fetchone()[0],
        }
    finally:
        conn.close()
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "backup": str(backup),
        "cloned_restaurants": len(mapping),
        "cloned_dishes": len(dish_rows),
        "counts": counts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
