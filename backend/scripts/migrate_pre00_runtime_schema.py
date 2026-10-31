"""PRE-00 运行库兼容迁移：把旧演示库副本升到当前 models.py 的可空 schema。

边界（PRE_S10_REMEDIATION_PLAN.md §3 PRE-00）：
- 只迁移**明确命名的开发运行库副本**，默认 `backend/eatwhat_dev_pre00.db`；
- 拒绝写演示库 `backend/eatwhat.db` 与 S10 独立导入库 `backend/eatwhat_batch4.db`；
  拒绝按**文件身份**（`os.path.samefile`）判断，硬链接、符号链接、大小写/短路径别名
  与直接路径一样被拦截，不依赖字符串路径比较；
- 只新增可空列、把 `dishes_and_recipes.feature_vector` 放宽为可空，不改变已有字段语义，
  不回填历史行的 `is_synthetic` / `campus`；
- 整个迁移在单个事务内完成，任何一步失败都回滚，原文件逻辑状态不变；
- 幂等：重复执行不产生任何写入，schema 与文件 SHA 不变。

用法（仓库根目录）：

    python -m backend.scripts.migrate_pre00_runtime_schema
    python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_pre00.db

SQLite 不能原地取消 NOT NULL，`feature_vector` 需要按当前模型重建表（复制全部行与索引）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_DB = (ROOT / "backend" / "eatwhat.db").resolve()
BATCH4_DB = (ROOT / "backend" / "eatwhat_batch4.db").resolve()
DEFAULT_DB = ROOT / "backend" / "eatwhat_dev_pre00.db"

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

# 与 backend/models.py::Dish 一致；重建只用于把 feature_vector 放宽为可空。
DISH_COLUMNS = (
    "id",
    "name",
    "mode_type",
    "restaurant_id",
    "cuisine_type",
    "dish_role",
    "price_or_cost",
    "cook_minutes",
    "appliance_tag",
    "ingredients_main",
    "ingredients_aux",
    "recipe_steps",
    "feature_vector",
    "image_url",
    "allergen_tags",
    "tagging_status",
    "tagging_error",
    "llm_meta",
    "source_dataset",
    "source_record_id",
    "source_url",
    "data_version",
    "is_synthetic",
    "deleted_at",
)

DISH_REBUILD_DDL = """
CREATE TABLE _pre00_dishes_and_recipes_new (
    id INTEGER NOT NULL,
    name VARCHAR(128) NOT NULL,
    mode_type VARCHAR(16) NOT NULL,
    restaurant_id INTEGER,
    cuisine_type VARCHAR(64),
    dish_role VARCHAR(16) NOT NULL,
    price_or_cost FLOAT,
    cook_minutes INTEGER,
    appliance_tag JSON NOT NULL,
    ingredients_main JSON NOT NULL,
    ingredients_aux JSON NOT NULL,
    recipe_steps TEXT,
    feature_vector JSON,
    image_url VARCHAR(255),
    allergen_tags JSON,
    tagging_status VARCHAR(16),
    tagging_error TEXT,
    llm_meta JSON,
    source_dataset VARCHAR(64),
    source_record_id VARCHAR(64),
    source_url VARCHAR(255),
    data_version VARCHAR(64),
    is_synthetic BOOLEAN,
    deleted_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
)
"""

DISH_INDEXES = (
    ("ix_dishes_and_recipes_name", "dishes_and_recipes", "name", False),
    ("ix_dishes_and_recipes_mode_type", "dishes_and_recipes", "mode_type", False),
    ("ix_dishes_and_recipes_cuisine_type", "dishes_and_recipes", "cuisine_type", False),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_fingerprint(db_path: Path) -> str:
    connection = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        payload = []
        for table in tables:
            columns = [
                (row[1], row[2], row[3], row[5])
                for row in connection.execute(f"PRAGMA table_info({table})")
            ]
            indexes = sorted(
                row[1]
                for row in connection.execute(f"PRAGMA index_list({table})")
                if not str(row[1]).startswith("sqlite_autoindex")
            )
            payload.append((table, columns, indexes))
    finally:
        connection.close()
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _table_columns(connection: sqlite3.Connection, table: str) -> dict[str, tuple]:
    return {row[1]: row for row in connection.execute(f"PRAGMA table_info({table})")}


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _guard_path(db_path: Path) -> Path:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} 不存在；请先创建明确命名的开发运行库副本")
    if not path.is_file():
        raise SystemExit(f"拒绝迁移 {path}：目标不是普通数据库文件")
    resolved = path.resolve()
    protected = (
        ("演示库", DEMO_DB),
        ("S10 独立导入库", BATCH4_DB),
    )
    for label, protected_path in protected:
        # 按文件身份拒绝：同一 inode/FileIndex 的硬链接、符号链接与路径别名都不能绕过。
        if protected_path.exists() and os.path.samefile(resolved, protected_path):
            raise SystemExit(
                f"拒绝迁移{label} {protected_path.name}；"
                "PRE-00 只允许改开发运行库副本"
            )
    return resolved


def _rebuild_dishes(connection: sqlite3.Connection, existing_columns: list[str]) -> None:
    unknown = sorted(set(existing_columns) - set(DISH_COLUMNS))
    if unknown:
        raise RuntimeError(f"dishes_and_recipes 出现未知列 {unknown}，拒绝重建以免丢数据")

    connection.execute(DISH_REBUILD_DDL)
    copy_columns = [name for name in DISH_COLUMNS if name in existing_columns]
    column_list = ", ".join(f'"{name}"' for name in copy_columns)
    connection.execute(
        f"INSERT INTO _pre00_dishes_and_recipes_new ({column_list}) "
        f"SELECT {column_list} FROM dishes_and_recipes"
    )
    connection.execute("DROP TABLE dishes_and_recipes")
    connection.execute(
        "ALTER TABLE _pre00_dishes_and_recipes_new RENAME TO dishes_and_recipes"
    )
    for name, table, column, unique in DISH_INDEXES:
        connection.execute(
            f"CREATE {'UNIQUE ' if unique else ''}INDEX IF NOT EXISTS {name} "
            f"ON {table} ({column})"
        )


def migrate(db_path: Path = DEFAULT_DB) -> dict:
    path = _guard_path(db_path)
    sha_before = file_sha256(path)
    fingerprint_before = schema_fingerprint(path)

    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        tables = _tables(connection)
        missing_tables = sorted(set(NEW_COLUMNS) - tables)
        if missing_tables:
            raise RuntimeError(f"缺少数据表 {missing_tables}，迁移中止")

        row_counts_before = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in NEW_COLUMNS
        }
        current = {
            table: _table_columns(connection, table) for table in NEW_COLUMNS
        }
        added = [
            f"{table}.{column}"
            for table, columns in NEW_COLUMNS.items()
            for column in columns
            if column not in current[table]
        ]
        feature_notnull = int(current["dishes_and_recipes"]["feature_vector"][3]) != 0
        rebuild = feature_notnull

        if not added and not rebuild:
            report = {
                "script": "migrate_pre00_runtime_schema.py",
                "script_version": "pre00_runtime_v2",
                "db": str(path),
                "sha256_before": sha_before,
                "sha256_after": sha_before,
                "schema_fingerprint_before": fingerprint_before,
                "schema_fingerprint_after": fingerprint_before,
                "feature_vector_nullable_before": not feature_notnull,
                "feature_vector_nullable_after": not feature_notnull,
                "added_columns": [],
                "rebuilt_tables": [],
                "row_counts": row_counts_before,
                "foreign_key_check": [],
                "idempotent": True,
                "ok": True,
            }
            return report

        connection.execute("BEGIN IMMEDIATE")
        try:
            for table, columns in NEW_COLUMNS.items():
                for column, ddl in columns.items():
                    if column in current[table]:
                        continue
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"
                    )

            if rebuild:
                _rebuild_dishes(connection, list(current["dishes_and_recipes"]))

            row_counts_after = {
                table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in NEW_COLUMNS
            }
            if row_counts_after != row_counts_before:
                raise RuntimeError(
                    f"行数变化 {row_counts_before} -> {row_counts_after}，回滚"
                )
            foreign_key_check = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_check:
                raise RuntimeError(f"外键校验失败 {foreign_key_check}，回滚")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    reader = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        after = _table_columns(reader, "dishes_and_recipes")
    finally:
        reader.close()
    report = {
        "script": "migrate_pre00_runtime_schema.py",
        "script_version": "pre00_runtime_v2",
        "db": str(path),
        "sha256_before": sha_before,
        "sha256_after": file_sha256(path),
        "schema_fingerprint_before": fingerprint_before,
        "schema_fingerprint_after": schema_fingerprint(path),
        "feature_vector_nullable_before": not feature_notnull,
        "feature_vector_nullable_after": int(after["feature_vector"][3]) == 0,
        "added_columns": added,
        "rebuilt_tables": ["dishes_and_recipes"] if rebuild else [],
        "row_counts": row_counts_after,
        "foreign_key_check": [],
        "idempotent": False,
        "ok": True,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PRE-00 开发运行库可空 schema 兼容迁移（幂等）"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    try:
        report = migrate(args.db)
    except Exception as exc:  # noqa: BLE001 - CLI 需要非零退出码与结构化原因
        print(
            json.dumps(
                {"ok": False, "db": str(args.db), "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1) from exc
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
