"""S05/r01 DB protection + final-state proof.

Compares protected databases against the baseline capture, checks the iso DB
schema/data after the final browser run, and verifies the final check-in row.
Read-only on every database.
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"D:\EatWhat")
OUT = ROOT / "docs/review/stages/S05/r01"
ISO = ROOT / "backend/eatwhat_s05_r01_iso.db"
PROTECTED = [
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00_r02.db",
]
CST = timezone(timedelta(hours=8))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            r[0]
            for r in con.execute(
                "select name from sqlite_master where type='table'"
            )
        ]
        return {
            t: con.execute(f"select count(*) from {t}").fetchone()[0]
            for t in (
                "users",
                "restaurants",
                "dishes_and_recipes",
                "user_preferences",
                "fridge_inventory",
                "eating_logs",
                "group_rooms",
                "room_votes",
                "algo_configs",
            )
            if t in tables
        }
    finally:
        con.close()


def main() -> int:
    baseline = json.loads((OUT / "data/baseline.json").read_text(encoding="utf-8"))
    baseline_hashes = {db["path"]: db["sha256"] for db in baseline["protected_databases"]}
    pre = json.loads((OUT / "data/pre_final_counts.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser_evidence.json").read_text(encoding="utf-8"))
    checkin = browser["phases"]["checkin"]

    after = {p: sha(ROOT / p) for p in PROTECTED}
    unchanged = {p: after[p] == baseline_hashes[p] for p in PROTECTED}

    con = sqlite3.connect(f"file:{ISO.as_posix()}?mode=ro", uri=True)
    try:
        dish_cols = {
            row[1]: {"type": row[2], "notnull": row[3]}
            for row in con.execute("PRAGMA table_info(dishes_and_recipes)")
        }
        rest_cols = {
            row[1]: {"type": row[2], "notnull": row[3]}
            for row in con.execute("PRAGMA table_info(restaurants)")
        }
        iso_counts = counts(ISO)
        latest_logs = [
            {
                "id": r[0],
                "user_id": r[1],
                "dish_id": r[2],
                "cost_amount": r[3],
                "eaten_at": r[4],
            }
            for r in con.execute(
                "select id,user_id,dish_id,cost_amount,eaten_at from eating_logs"
                " order by id desc limit 3"
            )
        ]
        sentinel_users = con.execute(
            "select count(*) from users where id=99 or username='s05_sentinel'"
        ).fetchone()[0]
    finally:
        con.close()

    latest = latest_logs[0]
    expected_dish = int(checkin["dish"]["id"])
    expected_log_count = pre["counts"]["eating_logs"] + 1
    checks = {
        "protected_hashes_unchanged": all(unchanged.values()),
        "protected_detail": unchanged,
        "demo_counts": counts(ROOT / PROTECTED[0]),
        "s10_counts": counts(ROOT / PROTECTED[1]),
        "dev_source_counts": counts(ROOT / PROTECTED[2]),
        "iso_schema": {
            "allergen_tags_present": "allergen_tags" in dish_cols,
            "deleted_at_present": "deleted_at" in dish_cols,
            "feature_vector_nullable": dish_cols.get("feature_vector", {}).get("notnull") == 0,
            "campus_present": "campus" in rest_cols,
        },
        "iso_counts_before_final_run": pre["counts"],
        "iso_counts_after_final_run": iso_counts,
        "eatings_logs_increment_exactly_one": iso_counts["eating_logs"] == expected_log_count,
        "latest_log": latest,
        "latest_log_matches_ui_checkin": latest["user_id"] == 1
        and latest["dish_id"] == expected_dish,
        "latest_log_cost_matches_ui": abs(float(latest["cost_amount"]) - float(checkin["delta"]["expense"])) < 1e-6,
        "no_sentinel_user": sentinel_users == 0,
        "groups_and_votes_zero": iso_counts["group_rooms"] == 0 and iso_counts["room_votes"] == 0,
        "browser_verdicts": browser["verdicts"],
        "controlled_errors_explained": {
            "5xx_injected_by_cdp_fetch": [
                n for n in browser["network"] if n["status"] == 500
            ],
            "offline_failures": [
                n for n in browser["network"] if n.get("failed")
            ],
        },
    }
    verdict = all(
        [
            checks["protected_hashes_unchanged"],
            checks["iso_schema"]["allergen_tags_present"],
            checks["iso_schema"]["deleted_at_present"],
            checks["iso_schema"]["feature_vector_nullable"],
            checks["iso_schema"]["campus_present"],
            checks["eatings_logs_increment_exactly_one"],
            checks["latest_log_matches_ui_checkin"],
            checks["latest_log_cost_matches_ui"],
            checks["no_sentinel_user"],
            checks["groups_and_votes_zero"],
        ]
    )
    result = {
        "generated_at": datetime.now(CST).isoformat(),
        "iso_database": {
            "path": str(ISO),
            "sha256": sha(ISO),
            "created_from": "backend/eatwhat_dev_pre00_r02.db (byte-identical copy, see 02_iso_db_provenance.log)",
            "database_url_env": "sqlite:///D:/EatWhat/backend/eatwhat_s05_r01_iso.db",
        },
        "protected_databases": [
            {
                "path": p,
                "sha256_baseline": baseline_hashes[p],
                "sha256_after": after[p],
                "unchanged": unchanged[p],
            }
            for p in PROTECTED
        ],
        "checks": checks,
        "verdict": bool(verdict),
    }
    (OUT / "data/db_protection.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
