"""S05/r01 database isolation sentinel.

Proves the running backend (:8000) reads/writes backend/eatwhat_s05_r01_iso.db,
not the demo DB or the S10 import DB.

Steps
1. insert sentinel user 99 + preferences directly into the iso DB
2. GET  /api/v1/users/99/profile            -> must echo the sentinel nickname
3. POST /api/v1/logs/checkin (user 99)      -> must add exactly one iso row
4. GET  /api/v1/logs/stats/99               -> meals_this_week == 1
5. remove sentinel rows from the iso DB
6. re-hash demo / S10 / dev-source DBs     -> unchanged

Only the iso copy is written. Demo/S10/dev-source DBs are opened read-only
for hashing and counting.
"""

import hashlib
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"D:\EatWhat")
ISO = ROOT / "backend/eatwhat_s05_r01_iso.db"
PROTECTED = [
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00_r02.db",
]
BASE = "http://127.0.0.1:8000/api/v1"
CST = timezone(timedelta(hours=8))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_counts(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return {
            t: con.execute(f"select count(*) from {t}").fetchone()[0]
            for t in ("users", "user_preferences", "eating_logs")
        }
    finally:
        con.close()


def api(path: str, *, method="GET", body=None, user=99):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "X-User-Id": str(user)},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def main() -> int:
    before_protected = {p: sha(ROOT / p) for p in PROTECTED}
    iso_sha_before = sha(ISO)
    before_iso = row_counts(ISO)

    con = sqlite3.connect(ISO)
    try:
        con.execute("delete from eating_logs where user_id=99")
        con.execute("delete from user_preferences where user_id=99")
        con.execute("delete from users where id=99")
        con.execute(
            "insert into users (id, username, nickname, avatar, persona_title, is_demo_persona, created_at)"
            " values (99,'s05_sentinel','S05哨兵','🧪','隔离哨兵',1,datetime('now'))"
        )
        con.execute(
            "insert into user_preferences (user_id, base_vector, default_budget, veto_tags,"
            " preferred_cuisines, favorite_dish_ids, blacklist_dish_ids, blacklist_restaurant_ids)"
            " values (99,?,25.0,'[]','[]','[]','[]','[]')",
            (
                json.dumps(
                    {
                        "spicy_level": 0.5,
                        "oily_level": 0.5,
                        "soup_level": 0.5,
                        "temp_fit": 0.5,
                        "satiety_level": 0.5,
                        "prep_speed": 0.5,
                        "social_fit": 0.5,
                        "comfort_level": 0.5,
                    }
                ),
            ),
        )
        con.commit()
        dish_id, mode_type = con.execute(
            "select id, mode_type from dishes_and_recipes order by id limit 1"
        ).fetchone()
    finally:
        con.close()

    profile_status, profile = api("/users/99/profile")
    checkin_status, checkin = api(
        "/logs/checkin",
        method="POST",
        body={
            "dish_id": dish_id,
            "mode_type": mode_type,
            "bubbles": [],
            "cost_amount": 12.5,
            "weather_snapshot": "哨兵",
        },
    )
    stats_status, stats = api("/logs/stats/99")
    after_iso = row_counts(ISO)
    after_protected = {p: sha(ROOT / p) for p in PROTECTED}
    demo_counts_before = row_counts(ROOT / PROTECTED[0])

    con = sqlite3.connect(ISO)
    try:
        con.execute("delete from eating_logs where user_id=99")
        con.execute("delete from user_preferences where user_id=99")
        con.execute("delete from users where id=99")
        con.commit()
    finally:
        con.close()
    cleaned_iso = row_counts(ISO)

    result = {
        "generated_at": datetime.now(CST).isoformat(),
        "backend": "http://127.0.0.1:8000",
        "database_url_env": "sqlite:///D:/EatWhat/backend/eatwhat_s05_r01_iso.db",
        "iso_db": {
            "path": str(ISO),
            "sha256_before_probe": iso_sha_before,
            "counts_before": before_iso,
            "counts_after_probe": after_iso,
            "counts_after_cleanup": cleaned_iso,
            "sha256_after_cleanup": sha(ISO),
        },
        "protected_before": before_protected,
        "protected_after": after_protected,
        "protected_unchanged": before_protected == after_protected,
        "demo_counts_after": demo_counts_before,
        "sentinel_user_inserted_directly_into_iso": True,
        "profile_status": profile_status,
        "profile_nickname": profile.get("nickname"),
        "checkin_status": checkin_status,
        "checkin_log_id": checkin.get("log_id"),
        "stats_status": stats_status,
        "stats_meals_this_week": stats.get("meals_this_week"),
        "verdict": (
            profile_status == 200
            and profile.get("nickname") == "S05哨兵"
            and checkin_status == 200
            and stats.get("meals_this_week") == 1
            and after_iso["eating_logs"] == before_iso["eating_logs"] + 1
            and demo_counts_before["eating_logs"] == 9
            and before_protected == after_protected
        ),
    }
    result["iso_db"]["sha256_before_probe"] = iso_sha_before
    (ROOT / "docs/review/stages/S05/r01/data/db_isolation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
