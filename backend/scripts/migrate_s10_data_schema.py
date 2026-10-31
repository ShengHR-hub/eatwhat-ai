"""S10 数据层迁移：为批次 4 导入库补齐 v2.3.3/v2.3.4 可空字段与幂等唯一索引。

边界：
- 只允许写明确命名的批次 4 导入库，默认 `backend/eatwhat_batch4.db`；
- 拒绝写演示库 `backend/eatwhat.db`；
- 只新增可空列 / 索引，不改变既有字段语义，重复执行无副作用。
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from backend.database import Base
from backend import models  # noqa: F401  注册全部表

ROOT = Path(__file__).resolve().parents[2]
DEMO_DB = (ROOT / "backend" / "eatwhat.db").resolve()
DEFAULT_DB = ROOT / "backend" / "eatwhat_batch4.db"

NEW_COLUMNS = {
    "restaurants": {
        "source_dataset": "VARCHAR(64)",
        "source_record_id": "VARCHAR(64)",
        "source_url": "VARCHAR(255)",
        "data_version": "VARCHAR(64)",
        "is_synthetic": "BOOLEAN",
        "deleted_at": "DATETIME",
        "campus": "VARCHAR(32)",
    },
    "dishes_and_recipes": {
        "allergen_tags": "JSON",
        "tagging_status": "VARCHAR(16)",
        "tagging_error": "TEXT",
        "llm_meta": "JSON",
        "source_dataset": "VARCHAR(64)",
        "source_record_id": "VARCHAR(64)",
        "source_url": "VARCHAR(255)",
        "data_version": "VARCHAR(64)",
        "is_synthetic": "BOOLEAN",
        "deleted_at": "DATETIME",
    },
    "group_rooms": {
        "campus": "VARCHAR(32)",
    },
}

UNIQUE_INDEXES = {
    # 同一来源数据集 + 校区 + 原始记录 ID 只允许一行；SQLite 对 NULL 不冲突，
    # 因此历史演示行（来源字段为 NULL）不受影响。
    "ux_restaurants_source": (
        "restaurants",
        "source_type, campus, source_dataset, source_record_id",
    ),
    "ux_dishes_source": (
        "dishes_and_recipes",
        "source_dataset, source_record_id",
    ),
}


def ensure_target(db_path: Path) -> Path:
    path = Path(db_path).resolve()
    if path == DEMO_DB:
        raise SystemExit("拒绝迁移演示库 backend/eatwhat.db；请使用独立批次 4 导入库")
    return path


def migrate(db_path: Path) -> dict:
    path = ensure_target(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)

    added = []
    existing = []
    with engine.begin() as conn:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        for table, columns in NEW_COLUMNS.items():
            if table not in tables:
                raise RuntimeError(f"缺少数据表 {table}，迁移中止")
            current = {row[1]: row for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for column, ddl in columns.items():
                if column in current:
                    existing.append(f"{table}.{column}")
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                added.append(f"{table}.{column}")

        # feature_vector 仅放宽为可空；SQLite 无法原地取消 NOT NULL，
        # 旧结构必须换新导入库，不能静默继续。
        feature_row = next(
            row
            for row in conn.execute(text("PRAGMA table_info(dishes_and_recipes)"))
            if row[1] == "feature_vector"
        )
        if int(feature_row[3]) != 0:
            raise RuntimeError(
                "dishes_and_recipes.feature_vector 仍为 NOT NULL；"
                "SQLite 不能原地放宽，请使用新建的批次 4 导入库"
            )

        indexes_added = []
        for name, (table, columns) in UNIQUE_INDEXES.items():
            names = {row[1] for row in conn.execute(text(f"PRAGMA index_list({table})"))}
            if name in names:
                existing.append(f"index:{name}")
                continue
            conn.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {name} "
                    f"ON {table} ({columns})"
                )
            )
            indexes_added.append(name)

    report = {
        "script": "migrate_s10_data_schema.py",
        "script_version": "s10_schema_v1",
        "db": str(path),
        "added_columns": added,
        "existing_columns": existing,
        "added_indexes": indexes_added,
        "idempotent": len(added) == 0 and len(indexes_added) == 0,
        "tables": sorted(Base.metadata.tables),
    }
    engine.dispose()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="S10 批次 4 导入库 schema 迁移（幂等）")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    report = migrate(args.db)
    text_report = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text_report + "\n", encoding="utf-8")
    print(text_report)


if __name__ == "__main__":
    main()
