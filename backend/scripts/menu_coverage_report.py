"""输出真实门店菜单覆盖报告，供分层菜单策略验收。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "eatwhat.db"
OUT = ROOT.parent / "docs" / "review" / "final" / "MENU_COVERAGE.json"


def main() -> None:
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
        with_menu = conn.execute(
            "SELECT COUNT(DISTINCT restaurant_id) FROM dishes_and_recipes WHERE restaurant_id IS NOT NULL"
        ).fetchone()[0]
        without_menu = conn.execute(
            """SELECT COUNT(*) FROM restaurants r
               WHERE NOT EXISTS (SELECT 1 FROM dishes_and_recipes d WHERE d.restaurant_id=r.id)"""
        ).fetchone()[0]
        by_campus = conn.execute(
            """SELECT r.campus, COUNT(DISTINCT r.id), COUNT(d.id)
               FROM restaurants r
               JOIN dishes_and_recipes d ON d.restaurant_id=r.id
               GROUP BY r.campus"""
        ).fetchall()
        sources = conn.execute(
            """SELECT COALESCE(r.source_dataset,'NULL'), COUNT(*) FROM restaurants r
               WHERE NOT EXISTS (SELECT 1 FROM dishes_and_recipes d WHERE d.restaurant_id=r.id)
               GROUP BY r.source_dataset"""
        ).fetchall()
        menu_dishes = conn.execute(
            "SELECT COUNT(*) FROM dishes_and_recipes WHERE mode_type='OUT_DINING'"
        ).fetchone()[0]
    finally:
        conn.close()
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "policy": "layered",
        "restaurants_total": total,
        "restaurants_with_menu": with_menu,
        "restaurants_without_menu": without_menu,
        "out_dining_dishes": menu_dishes,
        "with_menu_by_campus": [
            {"campus": row[0] or "UNKNOWN", "restaurants": row[1], "dishes": row[2]}
            for row in by_campus
        ],
        "without_menu_sources": [
            {"source_dataset": row[0], "restaurants": row[1]} for row in sources
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
