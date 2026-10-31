"""S06 房间投票唯一索引迁移（v2.3.6，幂等）。

只新增 `room_votes (room_code, user_id, dish_id)` 唯一索引，不改变任何已有字段
或数据。迁移前必须先检查历史重复行；有重复则中止，不建索引。

保护边界：
* 拒绝演示库、S10 独立导入库、PRE-00 开发源库、S05 隔离库（按文件身份判断）；
* 默认目标为 `backend/eatwhat_s06_r01_iso.db`，也可用 `--db` 指向明确命名的
  测试/运行副本；脚本不会自动迁移演示库。

用法（仓库根目录）：
    python -m backend.scripts.migrate_s06_room_contract
    python -m backend.scripts.migrate_s06_room_contract --db backend/eatwhat_s06_r01_iso.db
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from .migrate_pre00_runtime_schema import file_sha256, schema_fingerprint

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend" / "eatwhat_s06_r01_iso.db"
INDEX_NAME = "uq_room_votes_room_user_dish"
INDEX_COLUMNS = ("room_code", "user_id", "dish_id")

PROTECTED = (
    ("演示库", ROOT / "backend" / "eatwhat.db"),
    ("S10 独立导入库", ROOT / "backend" / "eatwhat_batch4.db"),
    ("PRE-00 开发源库", ROOT / "backend" / "eatwhat_dev_pre00_r02.db"),
    ("PRE-00 开发副本", ROOT / "backend" / "eatwhat_dev_pre00.db"),
    ("S05 隔离库", ROOT / "backend" / "eatwhat_s05_r01_iso.db"),
)


def _guard_path(db_path: Path) -> Path:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} 不存在；请先创建明确命名的目标副本")
    if not path.is_file():
        raise SystemExit(f"拒绝迁移 {path}：目标不是普通数据库文件")
    resolved = path.resolve()
    for label, protected in PROTECTED:
        if protected.exists() and os.path.samefile(resolved, protected):
            raise SystemExit(f"拒绝迁移{label} {protected.name}；S06 只允许明确命名的副本")
    return resolved


def _columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def _index_names(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        row[1]
        for row in connection.execute(f"PRAGMA index_list({table})")
        if not str(row[1]).startswith("sqlite_autoindex")
    ]


def _has_unique_index_on(connection: sqlite3.Connection, table: str) -> bool:
    """识别任意名字的唯一索引（含 create_all 生成的 sqlite_autoindex）。"""
    for row in connection.execute(f"PRAGMA index_list({table})"):
        name = row[1]
        unique = int(row[2]) == 1
        if not unique:
            continue
        columns = tuple(
            info[2] for info in connection.execute(f"PRAGMA index_info({name})")
        )
        if columns == INDEX_COLUMNS:
            return True
    return False


def _duplicates(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT room_code, user_id, dish_id, COUNT(*) AS n "
        "FROM room_votes GROUP BY room_code, user_id, dish_id "
        "HAVING COUNT(*) > 1 ORDER BY room_code, user_id, dish_id"
    ).fetchall()
    return [
        {
            "room_code": row[0],
            "user_id": row[1],
            "dish_id": row[2],
            "count": row[3],
        }
        for row in rows
    ]


def migrate(db_path: Path = DEFAULT_DB) -> dict:
    path = _guard_path(db_path)
    sha_before = file_sha256(path)
    fingerprint_before = schema_fingerprint(path)

    connection = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        if "room_votes" not in tables:
            raise RuntimeError("缺少 room_votes 表，迁移中止")
        columns = _columns(connection, "room_votes")
        missing = sorted(set(INDEX_COLUMNS) - set(columns))
        if missing:
            raise RuntimeError(f"room_votes 缺少列 {missing}，迁移中止")

        duplicates = _duplicates(connection)
        if duplicates:
            return {
                "script": "migrate_s06_room_contract.py",
                "db": str(path),
                "sha256_before": sha_before,
                "sha256_after": file_sha256(path),
                "ok": False,
                "reason": "duplicate_room_votes",
                "duplicates": duplicates,
                "index_created": False,
                "index_present": False,
            }

        if _has_unique_index_on(connection, "room_votes"):
            return {
                "script": "migrate_s06_room_contract.py",
                "db": str(path),
                "sha256_before": sha_before,
                "sha256_after": sha_before,
                "schema_fingerprint_before": fingerprint_before,
                "schema_fingerprint_after": fingerprint_before,
                "ok": True,
                "reason": "unique_index_already_present",
                "duplicates": [],
                "index_created": False,
                "index_present": True,
                "row_count": connection.execute(
                    "SELECT COUNT(*) FROM room_votes"
                ).fetchone()[0],
                "idempotent": True,
            }

        row_count_before = connection.execute(
            "SELECT COUNT(*) FROM room_votes"
        ).fetchone()[0]
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                f"CREATE UNIQUE INDEX {INDEX_NAME} "
                "ON room_votes (room_code, user_id, dish_id)"
            )
            row_count_after = connection.execute(
                "SELECT COUNT(*) FROM room_votes"
            ).fetchone()[0]
            if row_count_after != row_count_before:
                raise RuntimeError(
                    f"行数变化 {row_count_before} -> {row_count_after}，回滚"
                )
            foreign_key_check = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if foreign_key_check:
                raise RuntimeError(f"外键校验失败 {foreign_key_check}，回滚")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        index_present = INDEX_NAME in _index_names(connection, "room_votes")
        if not index_present:
            raise RuntimeError("唯一索引创建后回读失败")
        return {
            "script": "migrate_s06_room_contract.py",
            "db": str(path),
            "sha256_before": sha_before,
            "sha256_after": file_sha256(path),
            "schema_fingerprint_before": fingerprint_before,
            "schema_fingerprint_after": schema_fingerprint(path),
            "ok": True,
            "reason": "index_created",
            "duplicates": [],
            "index_created": True,
            "index_present": True,
            "row_count": row_count_after,
            "idempotent": False,
        }
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="S06 room_votes 唯一索引迁移（幂等，不改数据）"
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
    if not report.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
