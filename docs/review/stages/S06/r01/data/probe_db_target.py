"""启动前验证 DATABASE_URL 确实指向 S06 隔离库，而不是任何受保护库。"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[6]
EXPECTED = ROOT / "backend" / "eatwhat_s06_r01_iso.db"
PROTECTED = (
    ROOT / "backend" / "eatwhat.db",
    ROOT / "backend" / "eatwhat_batch4.db",
    ROOT / "backend" / "eatwhat_dev_pre00_r02.db",
    ROOT / "backend" / "eatwhat_dev_pre00.db",
    ROOT / "backend" / "eatwhat_s05_r01_iso.db",
)
OUT = Path(__file__).resolve().parent / "db_target_probe.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 S06 隔离库目标")
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="运行期已产生房间/票时跳过“启动前为空”断言（仍校验路径/schema/fixture）",
    )
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    raw = os.environ.get("DATABASE_URL", "")
    checks: list[dict] = []

    def check(name: str, ok: bool, detail=None):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    check("database_url_set", bool(raw), raw)
    if not raw:
        raise SystemExit("DATABASE_URL 未设置；拒绝在未知库上启动/取证")
    url = make_url(raw)
    check("driver_is_sqlite", url.drivername.startswith("sqlite"), url.drivername)
    database = Path(url.database or "")
    resolved = database.resolve()
    check("target_exists", resolved.exists(), str(resolved))
    if not resolved.exists():
        raise SystemExit(f"目标库不存在：{resolved}")
    expected = EXPECTED.resolve()
    check("target_is_s06_iso", resolved == expected, str(resolved))
    for protected in PROTECTED:
        if protected.exists():
            check(
                f"not_samefile_{protected.name}",
                not os.path.samefile(resolved, protected),
                str(protected),
            )

    connection = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        required_tables = {
            "users",
            "restaurants",
            "dishes_and_recipes",
            "group_rooms",
            "room_votes",
            "algo_configs",
        }
        check("required_tables", required_tables <= tables, sorted(tables))
        columns = {
            table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
            for table in ("restaurants", "group_rooms", "room_votes")
            if table in tables
        }
        check(
            "group_rooms_runtime_columns",
            {"campus", "algo_params", "deadline_at", "settled_at"}
            <= set(columns.get("group_rooms", [])),
            columns.get("group_rooms"),
        )
        check(
            "restaurants_campus_column",
            "campus" in columns.get("restaurants", []),
            columns.get("restaurants"),
        )
        unique_on_votes = False
        for row in connection.execute("PRAGMA index_list(room_votes)"):
            if int(row[2]) != 1:
                continue
            index_columns = tuple(
                info[2] for info in connection.execute(f"PRAGMA index_info({row[1]})")
            )
            if index_columns == ("room_code", "user_id", "dish_id"):
                unique_on_votes = True
        check("room_votes_unique_index", unique_on_votes)

        fixture_restaurants = connection.execute(
            "SELECT campus, COUNT(*) FROM restaurants "
            "WHERE source_dataset='s06_fixture_v1' GROUP BY campus ORDER BY campus"
        ).fetchall()
        fixture_dishes = connection.execute(
            "SELECT r.campus, COUNT(*) FROM dishes_and_recipes d "
            "JOIN restaurants r ON r.id=d.restaurant_id "
            "WHERE d.source_dataset='s06_fixture_v1' GROUP BY r.campus ORDER BY r.campus"
        ).fetchall()
        null_dishes = connection.execute(
            "SELECT COUNT(*) FROM dishes_and_recipes d "
            "JOIN restaurants r ON r.id=d.restaurant_id "
            "WHERE d.source_dataset='s06_fixture_v1' AND d.feature_vector IS NULL"
        ).fetchone()[0]
        seed_null = connection.execute(
            "SELECT COUNT(*) FROM restaurants "
            "WHERE source_dataset IS NULL AND campus IS NULL"
        ).fetchone()[0]
        check(
            "fixture_siyuan_12_dishes",
            dict(fixture_dishes).get("SIYUAN") == 12,
            fixture_dishes,
        )
        check(
            "fixture_jianda_12_dishes",
            dict(fixture_dishes).get("JIANDA_YANTA") == 12,
            fixture_dishes,
        )
        check(
            "fixture_6_restaurants_per_campus",
            dict(fixture_restaurants)
            == {"JIANDA_YANTA": 6, "SIYUAN": 6},
            fixture_restaurants,
        )
        check("fixture_vectors_not_null", null_dishes == 0, null_dishes)
        check("seed_null_restaurants_20", seed_null == 20, seed_null)

        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "group_rooms", "room_votes", "algo_configs")
        }
        check("users_4", counts["users"] == 4, counts)
        if args.allow_existing:
            check("rooms_existing_recorded", True, counts)
            check("votes_existing_recorded", True, counts)
        else:
            check("no_preexisting_rooms", counts["group_rooms"] == 0, counts)
            check("no_preexisting_votes", counts["room_votes"] == 0, counts)
        config = connection.execute(
            "SELECT config_name, omega_group FROM algo_configs"
        ).fetchall()
    finally:
        connection.close()

    payload = {
        "database_url": raw,
        "resolved_path": str(resolved),
        "phase": "post" if args.allow_existing else "pre",
        "counts": counts,
        "algo_configs": config,
        "checks": checks,
        "ok": all(item["ok"] for item in checks),
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
