"""G2：创建明确命名的空白 S10 导入库（不复制演示数据）。"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTECTED = [
    ROOT / "backend" / "eatwhat.db",
    ROOT / "backend" / "eatwhat_batch4.db",
    ROOT / "backend" / "eatwhat_g1_s07_iso.db",
    ROOT / "backend" / "eatwhat_g2_s10_full.db",
    ROOT / "backend" / "eatwhat_g2_s10_smoke.db",
    ROOT / "backend" / "eatwhat_g2_bridge_iso.db",
]


def main() -> None:
    target = Path(sys.argv[1]).resolve()
    if target.exists():
        raise SystemExit(f"目标已存在，拒绝覆盖：{target}")
    for item in PROTECTED:
        if item.exists() and item.resolve() == target:
            raise SystemExit(f"拒绝写受保护库：{target}")
    if not target.name.startswith("eatwhat_g2_"):
        raise SystemExit("目标必须是明确命名的 G2 库")

    from backend import models  # noqa: F401
    from backend.database import Base
    from backend.scripts import migrate_s10_data_schema as migration
    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{target.as_posix()}")
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    report = migration.migrate(target)
    connection = sqlite3.connect(str(target))
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("restaurants", "dishes_and_recipes", "users", "eating_logs", "group_rooms")
        }
        columns = {
            table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
            for table in ("restaurants", "dishes_and_recipes", "group_rooms")
        }
    finally:
        connection.close()
    payload = {
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "target": str(target),
        "migration": report,
        "tables": tables,
        "counts": counts,
        "columns": columns,
    }
    out = Path(__file__).resolve().parent / f"{target.stem}_schema.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"target": str(target), "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
