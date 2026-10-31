"""SQLite → PostgreSQL 数据搬家。

为什么不用 pgloader / ogr2ogr：那类工具假设两边结构一致，而我们的旧 SQLite
有三处历史漂移（见 docs/BACKEND_DEPLOYMENT_PLAN.md §8），必须逐列转换。
自己写一遍，转换规则就在代码里，答辩时能指着说清楚。

用法：

    # 1) 先看要搬多少，不写目标库
    python -m backend.scripts.sqlite_to_postgres \
        --target postgresql+psycopg://eatwhat:pass@127.0.0.1:5433/eatwhat --dry-run

    # 2) 真搬（目标库必须已 alembic upgrade head，且是空的）
    python -m backend.scripts.sqlite_to_postgres \
        --target postgresql+psycopg://eatwhat:pass@127.0.0.1:5433/eatwhat

    # 3) 只核对行数
    python -m backend.scripts.sqlite_to_postgres \
        --target postgresql+psycopg://eatwhat:pass@127.0.0.1:5433/eatwhat --verify

设计约束：
- **保留主键**：业务代码、房间号、投票记录都靠 id 互相关联，重新编号会断链。
- **按外键顺序插入**：用 SQLAlchemy metadata 的拓扑排序，不手写顺序。
- **搬完重置序列**：PG 的自增序列不会因为显式插入 id 而前进，不 setval 的话
  下一条 INSERT 会撞主键。
- **不做隐式清库**：目标表非空就报错退出，要重搬必须显式 --truncate。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..config import DATABASE_URL
from ..database import Base
from .. import models  # noqa: F401  注册全部表

BATCH_SIZE = 500

# 旧 SQLite 里这三处与模型不一致，必须转换（其余列原样搬）：
#   dishes_and_recipes.appliance_tag : VARCHAR 存 JSON 字符串 → JSON 数组
#   dishes_and_recipes.feature_vector: NOT NULL → 允许 NULL（历史约束过严）
#   room_votes 唯一索引 → 唯一约束（语义相同，结构对齐）
JSON_COLUMNS = {
    "dishes_and_recipes": {"appliance_tag", "ingredients_main", "ingredients_aux",
                           "feature_vector", "allergen_tags", "llm_meta"},
    "user_preferences": {"base_vector", "veto_tags", "preferred_cuisines",
                         "favorite_dish_ids", "blacklist_dish_ids",
                         "blacklist_restaurant_ids"},
    "group_rooms": {"member_user_ids", "candidate_dish_ids", "consensus_report", "algo_params"},
    "eating_logs": {"status_bubbles"},
    "algo_configs": {"benchmark_json"},
}


def _coerce_json(value: Any) -> Any:
    """把 SQLite 里的文本变成合法 JSON 文本。

    旧库 appliance_tag 存的是 '["\\u7092\\u9505"]' 这种 JSON 字符串，
    直接塞进 PG 的 json 列也能过；但历史上也可能有人存了裸文本（"炒锅"），
    那种就不是合法 JSON，要包成 ["炒锅"] 才不会让整批插入失败。
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    text_value = str(value)
    try:
        return json.dumps(json.loads(text_value), ensure_ascii=False)
    except (ValueError, TypeError):
        return json.dumps([text_value], ensure_ascii=False)


def _build_select(table: sa.Table) -> str:
    cols = ", ".join(f'"{c.name}"' for c in table.columns)
    return f'SELECT {cols} FROM "{table.name}"'


def _cast_placeholder(column: sa.Column, index: int) -> str:
    """生成占位符 + 显式类型转换，避免 psycopg 猜错类型。

    注意用命名参数 ``:v0`` 而不是 ``%s``：SQLAlchemy 的 text() 在 psycopg
    方言下会把裸 ``%`` 当转义符，``%s`` 会被写成 ``%%s`` 直接语法错误。
    """
    name = f":v{index}"
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        python_type = str
    if isinstance(column.type, sa.JSON):
        return f"CAST({name} AS json)"
    if python_type is bool:
        return f"CAST({name} AS boolean)"
    if column.type.__class__.__name__ in {"DateTime", "TIMESTAMP", "Date"}:
        return f"CAST({name} AS timestamp)"
    return name


def _prepare_value(table: str, column: sa.Column, raw: Any) -> Any:
    if raw is None:
        return None
    if column.name in JSON_COLUMNS.get(table, set()) or isinstance(column.type, sa.JSON):
        return _coerce_json(raw)
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return raw
    if python_type is bool:
        # SQLite 存 0/1；PG 布尔列只认 true/false
        return bool(raw)
    return raw


def _table_counts_sqlite(source: Engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    with source.connect() as conn:
        for table in Base.metadata.sorted_tables:
            counts[table.name] = conn.execute(
                text(f'SELECT COUNT(*) FROM "{table.name}"')
            ).scalar_one()
    return counts


def _table_counts_target(target: Engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    with target.connect() as conn:
        for table in Base.metadata.sorted_tables:
            exists = conn.execute(
                text("SELECT to_regclass(:name)"), {"name": f'public."{table.name}"'}
            ).scalar()
            counts[table.name] = (
                conn.execute(text(f'SELECT COUNT(*) FROM "{table.name}"')).scalar_one()
                if exists
                else -1
            )
    return counts


def migrate(source: Engine, target: Engine, *, truncate: bool, dry_run: bool) -> int:
    tables = list(Base.metadata.sorted_tables)  # 已按外键依赖排序

    with target.connect() as tconn:
        existing = _table_counts_target(target)
        missing = [name for name, n in existing.items() if n < 0]
        if missing:
            print(f"[x] 目标库缺表：{missing}\n    先跑 alembic upgrade head", file=sys.stderr)
            return 2
        non_empty = {name: n for name, n in existing.items() if n > 0}
        if non_empty and not truncate:
            print(f"[x] 目标库非空：{non_empty}\n    确认要覆盖请加 --truncate", file=sys.stderr)
            return 2

    if dry_run:
        counts = _table_counts_sqlite(source)
        print("== dry-run：只统计，不写入 ==")
        for table in tables:
            print(f"  {table.name:<22} {counts[table.name]:>7} 行")
        print(f"  合计 {sum(counts.values())} 行")
        return 0

    if truncate:
        names = ", ".join(f'"{t.name}"' for t in reversed(tables))
        with target.begin() as tconn:
            tconn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        print("[i] 已清空目标表（RESTART IDENTITY）")

    with source.connect() as sconn:
        for table in tables:
            rows = sconn.execute(text(_build_select(table))).mappings().all()
            if not rows:
                print(f"  {table.name:<22} 0 行（跳过）")
                continue

            columns = [c for c in table.columns]
            placeholders = ", ".join(
                _cast_placeholder(column, i) for i, column in enumerate(columns)
            )
            col_names = ", ".join(f'"{c.name}"' for c in columns)
            insert_sql = text(
                f'INSERT INTO "{table.name}" ({col_names}) VALUES ({placeholders})'
            )

            payload: list[dict[str, Any]] = []
            for row in rows:
                payload.append(
                    {
                        f"v{i}": _prepare_value(table.name, column, row[column.name])
                        for i, column in enumerate(columns)
                    }
                )

            with target.begin() as tconn:
                for start in range(0, len(payload), BATCH_SIZE):
                    tconn.execute(insert_sql, payload[start : start + BATCH_SIZE])

            print(f"  {table.name:<22} {len(payload)} 行")

    # 显式插入了 id，PG 的序列还停在 1，不重置下一条 INSERT 必然撞主键
    with target.begin() as tconn:
        for table in tables:
            id_col = table.columns.get("id")
            if id_col is None or not isinstance(id_col.type, sa.Integer):
                continue
            tconn.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM \"{table.name}\"), 1), "
                    f"(SELECT COUNT(*) > 0 FROM \"{table.name}\"))"
                )
            )
    print("[i] 已重置自增序列")
    return 0


def verify(source: Engine, target: Engine) -> int:
    src = _table_counts_sqlite(source)
    dst = _table_counts_target(target)
    bad = 0
    print("== 行数核对 ==")
    for name, count in src.items():
        got = dst.get(name, -1)
        flag = "OK " if got == count else "!! "
        if got != count:
            bad += 1
        print(f"  {flag}{name:<22} sqlite={count:>7}  pg={got:>7}")
    if bad:
        print(f"[x] {bad} 张表行数不一致")
        return 1
    print("[✓] 全部一致")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 数据搬家")
    parser.add_argument("--source", default=DATABASE_URL, help="源库（默认取 config.DATABASE_URL）")
    parser.add_argument("--target", required=True, help="目标库，必须是 postgresql+psycopg://")
    parser.add_argument("--truncate", action="store_true", help="先清空目标表再搬")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写")
    parser.add_argument("--verify", action="store_true", help="只核对行数")
    args = parser.parse_args(argv)

    if not args.source.startswith("sqlite"):
        print("[x] 源库必须是 sqlite", file=sys.stderr)
        return 2
    if not args.target.startswith("postgresql"):
        print("[x] 目标库必须是 postgresql+psycopg://", file=sys.stderr)
        return 2

    source = create_engine(args.source, future=True)
    target = create_engine(args.target, future=True)

    if args.verify:
        return verify(source, target)
    return migrate(source, target, truncate=args.truncate, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
