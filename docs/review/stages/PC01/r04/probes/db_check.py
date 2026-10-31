"""R02/R3-03 数据身份核对：演示库、快照、存档、隔离库逐点一致 + DB 清单。

只读打开所有数据库；不写演示库。输出：
- docs/review/stages/PC01/r04/data/db_benchmark_check.json
- docs/review/stages/PC01/r04/data/db_inventory.json
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PACK = Path(__file__).resolve().parents[1]
ARCHIVE = PACK / "data" / "benchmark_seed20261024.json"
ARCHIVE7 = PACK / "data" / "benchmark_seed7.json"
SNAP = ROOT / "backend" / "scripts" / "benchmark_snapshot.json"
DEMO = ROOT / "backend" / "eatwhat.db"
R04 = PACK / "data"
OLD = ROOT / "docs" / "review" / "simulation"
KEYS = (
    "generated_at",
    "sample",
    "duplication_rate_curve",
    "group_satisfaction_bars",
)


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _one(con: sqlite3.Connection, sql: str):
    row = con.execute(sql).fetchone()
    return row[0] if row else None


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _db_stats(path: Path) -> dict:
    stats = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return stats
    stats["bytes"] = path.stat().st_size
    stats["sha256"] = _sha(path)
    con = _ro(path)
    try:
        for table in (
            "users",
            "user_preferences",
            "restaurants",
            "dishes_and_recipes",
            "eating_logs",
            "fridge_inventory",
            "algo_configs",
            "group_rooms",
            "room_votes",
        ):
            try:
                stats[table] = _one(con, f"select count(*) from {table}")
            except sqlite3.OperationalError:
                stats[table] = None
        try:
            stats["distinct_log_days"] = _one(
                con, "select count(distinct substr(eaten_at,1,10)) from eating_logs"
            )
            stats["distinct_log_users"] = _one(
                con, "select count(distinct user_id) from eating_logs"
            )
        except sqlite3.OperationalError:
            pass
        if stats.get("group_rooms"):
            stats["votes_per_room_min"] = _one(
                con, "select min(c) from (select count(*) c from room_votes group by room_code)"
            )
            stats["votes_per_room_max"] = _one(
                con, "select max(c) from (select count(*) c from room_votes group by room_code)"
            )
            stats["unique_vote_keys"] = _one(
                con, "select count(*) from (select distinct room_code,user_id,dish_id from room_votes)"
            )
    finally:
        con.close()
    return stats


def _detail_stats(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    lines = 0
    arms = {}
    days = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            lines += 1
            row = json.loads(line)
            arm = row.get("arm", "groups")
            arms[arm] = arms.get(arm, 0) + 1
            if "day" in row:
                days.add(row["day"])
    return {"exists": True, "lines": lines, "arms": arms, "days": sorted(days)}


def main() -> int:
    report = {}
    archive_full = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    archive = {key: archive_full[key] for key in KEYS}
    snapshot = json.loads(SNAP.read_text(encoding="utf-8"))
    con = _ro(DEMO)
    try:
        row = con.execute(
            "select benchmark_json from algo_configs where config_name='default_production'"
        ).fetchone()
        db_benchmark = json.loads(row[0]) if row and row[0] else None
        demo_counts = {
            table: _one(con, f"select count(*) from {table}")
            for table in (
                "users",
                "restaurants",
                "dishes_and_recipes",
                "eating_logs",
                "group_rooms",
                "room_votes",
            )
        }
    finally:
        con.close()

    logical_state = {
        "counts": demo_counts,
        "benchmark": db_benchmark,
    }
    report["demo_db"] = {
        "path": str(DEMO),
        "file_sha256": _sha(DEMO),
        "logical_sha256": hashlib.sha256(
            json.dumps(logical_state, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "counts": demo_counts,
        "benchmark_keys": sorted(db_benchmark) if db_benchmark else None,
        "benchmark_generated_at": db_benchmark.get("generated_at") if db_benchmark else None,
        "db_equals_archive": db_benchmark == archive,
        "db_equals_snapshot": db_benchmark == snapshot,
        "archive_equals_snapshot": archive == snapshot,
        "benchmark": db_benchmark,
    }
    report["archive_seed20261024"] = {
        "path": str(ARCHIVE),
        "stored_keys": sorted(archive),
        "source_keys": sorted(archive_full),
        "sample": archive.get("sample"),
        "bars": archive.get("group_satisfaction_bars"),
        "calls": archive_full.get("params", {}).get("calls"),
    }
    if ARCHIVE7.exists():
        archive7_full = json.loads(ARCHIVE7.read_text(encoding="utf-8"))
        archive7 = {key: archive7_full[key] for key in KEYS}
        report["archive_seed7"] = {
            "path": str(ARCHIVE7),
            "stored_keys": sorted(archive7),
            "source_keys": sorted(archive7_full),
            "sample": archive7.get("sample"),
            "bars": archive7.get("group_satisfaction_bars"),
            "calls": archive7_full.get("params", {}).get("calls"),
        }

    sim = R04 / "sim_seed20261024"
    report["detail_seed20261024"] = _detail_stats(
        sim / "detail_seed20261024.jsonl"
    )
    report["detail_seed7"] = _detail_stats(R04 / "sim_seed7" / "detail_seed7.jsonl")
    report["r04_dbs"] = {
        name: _db_stats(sim / name)
        for name in (
            "sim_seed20261024_ours.db",
            "sim_seed20261024_baseline.db",
            "sim_seed20261024_groups.db",
            "sim_seed20261024_absence.db",
        )
    }
    report["r04_seed7_dbs"] = {
        name: _db_stats(R04 / "sim_seed7" / name)
        for name in (
            "sim_seed7_ours.db",
            "sim_seed7_baseline.db",
            "sim_seed7_groups.db",
            "sim_seed7_absence.db",
        )
    }
    report["absence_seed20261024"] = json.loads(
        (sim / "absence_seed20261024.json").read_text(encoding="utf-8")
    )
    report["absence_seed7"] = json.loads(
        (R04 / "sim_seed7" / "absence_seed7.json").read_text(encoding="utf-8")
    )

    inventory = []
    for path in sorted(OLD.glob("sim_seed*.db")):
        item = _db_stats(path)
        item["status"] = (
            "truncated/deprecated"
            if path.name == "sim_seed20261024_ours.db"
            else "complete (r03 archive)"
        )
        inventory.append(item)
    for path in sorted(R04.glob("sim_seed*/*.db")):
        item = _db_stats(path)
        item["status"] = "complete (r04 rerun)"
        inventory.append(item)
    report["inventory"] = inventory

    out1 = PACK / "data" / "db_benchmark_check.json"
    out2 = PACK / "data" / "db_inventory.json"
    out1.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out2.write_text(
        json.dumps({"generated_at": report["demo_db"]["benchmark_generated_at"], "databases": inventory}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(
        {
            "demo_counts": demo_counts,
            "db_equals_archive": report["demo_db"]["db_equals_archive"],
            "db_equals_snapshot": report["demo_db"]["db_equals_snapshot"],
            "archive_equals_snapshot": report["demo_db"]["archive_equals_snapshot"],
            "bars": report["archive_seed20261024"]["bars"],
            "detail": report["detail_seed20261024"],
            "groups": report["r04_dbs"]["sim_seed20261024_groups.db"],
            "absence": report["absence_seed20261024"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    ok = (
        report["demo_db"]["db_equals_archive"]
        and report["demo_db"]["db_equals_snapshot"]
        and demo_counts["group_rooms"] == 0
        and demo_counts["room_votes"] == 0
        and report["detail_seed20261024"]["lines"] == 48000
        and report["r04_dbs"]["sim_seed20261024_groups.db"]["room_votes"] == 40000
        and report["r04_dbs"]["sim_seed20261024_groups.db"]["votes_per_room_min"] == 40
        and report["r04_dbs"]["sim_seed20261024_groups.db"]["votes_per_room_max"] == 40
    )
    print(f"\nwrote {out1}\nwrote {out2}\n{'OK' if ok else 'CHECK FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
