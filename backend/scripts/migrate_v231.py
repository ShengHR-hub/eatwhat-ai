"""v2.3.1 数据层迁移：appliance_tag 单值 → JSON 数组，新增 blacklist_restaurant_ids。

用法（在仓库根目录）：

    python -m backend.scripts.migrate_v231

幂等：列已存在 / 值已是数组时不做任何改动。
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "eatwhat.db"


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _as_list(value: str) -> str:
    """把历史单值（'炒锅'）转成 JSON 数组文本（'["炒锅"]'），已是数组则原样返回。"""
    text = (value or "").strip()
    if text.startswith("["):
        return text
    items = [item for item in text.split(",") if item.strip()]
    if not items:
        items = ["炒锅"]
    return json.dumps(items, ensure_ascii=False)


def migrate(db_path: Path = DB_PATH) -> dict:
    if not db_path.exists():
        return {"skipped": True, "reason": f"{db_path} 不存在"}

    conn = sqlite3.connect(db_path)
    try:
        report = {}

        pref_cols = _columns(conn, "user_preferences")
        if "blacklist_restaurant_ids" not in pref_cols:
            conn.execute(
                "ALTER TABLE user_preferences "
                "ADD COLUMN blacklist_restaurant_ids JSON NOT NULL DEFAULT '[]'"
            )
            report["added_column"] = "blacklist_restaurant_ids"
        conn.execute(
            "UPDATE user_preferences SET blacklist_restaurant_ids = '[]' "
            "WHERE blacklist_restaurant_ids IS NULL"
        )

        dish_cols = _columns(conn, "dishes_and_recipes")
        if "appliance_tag" in dish_cols:
            rows = conn.execute(
                "SELECT id, appliance_tag FROM dishes_and_recipes"
            ).fetchall()
            changed = 0
            for dish_id, value in rows:
                new_value = _as_list(value)
                if new_value != value:
                    conn.execute(
                        "UPDATE dishes_and_recipes SET appliance_tag = ? WHERE id = ?",
                        (new_value, dish_id),
                    )
                    changed += 1
            report["appliance_tag_converted"] = changed

        conn.commit()
        report["ok"] = True
        return report
    finally:
        conn.close()


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False, indent=2))
