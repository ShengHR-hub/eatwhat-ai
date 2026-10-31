"""R3-01 真实 CLI 反例：只重定向数据库/快照路径，不替换守卫/清库/播种函数。

每个用例使用独立 SQLite 副本和快照副本，记录运行前后的逻辑摘要与快照哈希。
输出：docs/review/stages/PC01/r04/data/seed-results.json
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PACK = Path(__file__).resolve().parents[1]
WORK = PACK / "data" / "seed-probe"
LOGS = PACK / "logs"
BASE_SNAPSHOT = ROOT / "backend" / "scripts" / "benchmark_snapshot.json"


def _payload(generated_at: str, d14: float = 0.0091) -> dict:
    return {
        "generated_at": generated_at,
        "sample": {
            "personas": 200,
            "days": 60,
            "meals_per_day": 2,
            "rooms": 1000,
            "members_per_room": 4,
        },
        "duplication_rate_curve": {
            "days": list(range(1, 15)),
            "ours_lambda_0.5": [d14] * 14,
            "baseline_no_decay": [0.2927] * 14,
        },
        "group_satisfaction_bars": {
            "strategies": ["mixed_omega_0.5", "average_omega_1.0", "random"],
            "avg_scores": [93.81, 94.1, 73.43],
            "least_misery_scores": [74.68, 73.4, 40.37],
        },
    }


def _write_json(path: Path, payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _db_summary(path: Path) -> dict:
    con = sqlite3.connect(path)
    try:
        tables = {
            "users": "users",
            "user_preferences": "user_preferences",
            "restaurants": "restaurants",
            "dishes": "dishes_and_recipes",
            "eating_logs": "eating_logs",
            "fridge_inventory": "fridge_inventory",
            "algo_configs": "algo_configs",
            "group_rooms": "group_rooms",
            "room_votes": "room_votes",
        }
        counts = {
            name: con.execute(f"select count(*) from {table}").fetchone()[0]
            for name, table in tables.items()
        }
        row = con.execute(
            "select benchmark_json from algo_configs where config_name='default_production'"
        ).fetchone()
        benchmark = json.loads(row[0]) if row and row[0] else None
        users = [r[0] for r in con.execute("select username from users order by id")]
        dishes = [r[0] for r in con.execute("select name from dishes_and_recipes order by id")]
        facts = {
            "counts": counts,
            "benchmark_generated_at": benchmark.get("generated_at") if benchmark else None,
            "benchmark_sha256": hashlib.sha256(
                json.dumps(benchmark, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if benchmark
            else None,
            "usernames": users,
            "dish_names_sha256": hashlib.sha256(
                "\n".join(dishes).encode("utf-8")
            ).hexdigest(),
        }
        facts["logical_sha256"] = hashlib.sha256(
            json.dumps(facts, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return facts
    finally:
        con.close()


def _set_db_generated_at(path: Path, generated_at: str) -> None:
    con = sqlite3.connect(path)
    try:
        row = con.execute(
            "select benchmark_json from algo_configs where config_name='default_production'"
        ).fetchone()
        payload = json.loads(row[0])
        payload["generated_at"] = generated_at
        con.execute(
            "update algo_configs set benchmark_json=? where config_name='default_production'",
            (json.dumps(payload, ensure_ascii=False),),
        )
        con.commit()
    finally:
        con.close()


def _snapshot_state(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    return {
        "exists": True,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "generated_at": payload.get("generated_at"),
        "keys": sorted(payload),
    }


def _run_cli(db_path: Path, args: list[str]) -> tuple[int, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "backend.scripts.init_seed_data", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
    )
    raw = (proc.stdout or b"") + (proc.stderr or b"")
    try:
        output = raw.decode("utf-8")
    except UnicodeDecodeError:
        output = raw.decode("gbk", errors="replace")
    return proc.returncode, output


def _case(
    name,
    expect,
    args,
    snapshot,
    db_generated_at=None,
    incoming=None,
    snapshot_missing=False,
):
    case_dir = WORK / name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    db_path = case_dir / "case.sqlite"
    shutil.copy2(WORK / "base.sqlite", db_path)
    if db_generated_at:
        _set_db_generated_at(db_path, db_generated_at)
    snapshot_path = case_dir / "benchmark_snapshot.json"
    if snapshot_missing:
        snapshot_path = case_dir / "missing_snapshot.json"
    elif snapshot is not None:
        _write_json(snapshot_path, snapshot)
    incoming_path = None
    if incoming is not None:
        incoming_path = case_dir / "incoming.json"
    cli_args = list(args)
    if snapshot_missing or snapshot is not None:
        cli_args += ["--snapshot", str(snapshot_path)]
    if incoming_path is not None:
        _write_json(incoming_path, incoming)
        cli_args += ["--benchmark-from", str(incoming_path)]

    db_before = _db_summary(db_path)
    snap_before = _snapshot_state(snapshot_path)
    code, output = _run_cli(db_path, cli_args)
    db_after = _db_summary(db_path)
    snap_after = _snapshot_state(snapshot_path)

    db_same = db_before["logical_sha256"] == db_after["logical_sha256"]
    snap_same = snap_before.get("sha256") == snap_after.get("sha256")
    expected_db_same = name not in {"full_output_with_params", "allow_stale_refresh", "repeat_run"}
    expected_snap_same = name not in {
        "full_output_with_params",
        "allow_stale_refresh",
        "repeat_run",
    }
    ok = (
        code == expect
        and (db_same == expected_db_same)
        and (snap_same == expected_snap_same)
    )
    output_lines = output.strip().splitlines()
    result = {
        "case": name,
        "exit": code,
        "expect_exit": expect,
        "pass": ok,
        "db_unchanged": db_same,
        "snapshot_unchanged": snap_same,
        "db_before": db_before,
        "db_after": db_after,
        "snapshot_before": snap_before,
        "snapshot_after": snap_after,
        "output": output_lines[:8],
        "output_tail": output_lines[-4:],
    }
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: exit {code} (expect {expect})")
    for line in result["output"]:
        print(f"    {line}")
    return result


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if WORK.exists():
        shutil.rmtree(WORK)
    LOGS.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True)

    base_snapshot = json.loads(BASE_SNAPSHOT.read_text(encoding="utf-8"))
    base_common = {
        key: base_snapshot[key]
        for key in (
            "sample",
            "duplication_rate_curve",
            "group_satisfaction_bars",
        )
    }
    now = datetime.now().replace(microsecond=0).isoformat()
    fresh = {"generated_at": now, **base_common}

    base_snapshot_path = WORK / "base_snapshot.json"
    _write_json(base_snapshot_path, fresh)
    base_db = WORK / "base.sqlite"
    code, output = _run_cli(base_db, ["--force", "--snapshot", str(base_snapshot_path)])
    base_seed_exit = code
    if code != 0:
        print(f"[FAIL] base seed failed: {output}")
        return 1
    print(f"[PASS] base seed: exit 0; {output.strip().splitlines()[-1]}")

    results = []
    results.append(
        _case(
            "invalid_generated_at",
            1,
            ["--force"],
            {**base_common, "generated_at": "zz-not-a-date"},
        )
    )
    results.append(
        _case(
            "timezone_aware_older",
            1,
            ["--force"],
            {**base_common, "generated_at": "2026-10-24T23:00:00+08:00"},
            db_generated_at="2026-10-24T16:00:00+00:00",
        )
    )
    bad_curve = {
        **base_common,
        "generated_at": "2026-10-24T23:00:00+08:00",
        "sample": {
            "personas": 0,
            "days": 60,
            "meals_per_day": 2,
            "rooms": -1,
            "members_per_room": 4,
        },
        "duplication_rate_curve": {
            "days": [14] * 14,
            "ours_lambda_0.5": ["NOT_A_NUMBER"] * 14,
            "baseline_no_decay": [0.29] * 14,
        },
    }
    results.append(_case("illegal_sample_curve", 1, ["--force"], bad_curve))
    results.append(
        _case(
            "plain_stale_no_incoming",
            1,
            ["--force"],
            {**base_common, "generated_at": "2026-10-24T09:00:00"},
            db_generated_at="2026-10-25T09:00:00",
        )
    )
    results.append(
        _case(
            "missing_snapshot",
            1,
            ["--force"],
            None,
            snapshot_missing=True,
        )
    )
    results.append(
        _case(
            "rejected_incoming_keeps_target",
            1,
            ["--force"],
            {**base_common, "generated_at": "2026-10-24T00:00:00+00:00"},
            db_generated_at="2026-10-24T20:00:00+00:00",
            incoming={**base_common, "generated_at": "2026-10-24T12:00:00+00:00"},
        )
    )
    full_output = dict(fresh)
    full_output["params"] = {"seed": 20261024, "calls": {"recommend_single": 48000}}
    results.append(
        _case(
            "full_output_with_params",
            0,
            ["--force"],
            {**base_common, "generated_at": "2026-10-24T00:00:00+00:00"},
            db_generated_at="2026-10-24T00:00:00+00:00",
            incoming=full_output,
        )
    )
    # 连续执行：同一个目标快照再播一次，不应被自己判成“旧快照”
    repeat_dir = WORK / "repeat_run"
    if repeat_dir.exists():
        shutil.rmtree(repeat_dir)
    shutil.copytree(WORK / "full_output_with_params", repeat_dir)
    repeat_db = repeat_dir / "case.sqlite"
    repeat_snapshot = repeat_dir / "benchmark_snapshot.json"
    db_before = _db_summary(repeat_db)
    snap_before = _snapshot_state(repeat_snapshot)
    code, output = _run_cli(
        repeat_db, ["--force", "--snapshot", str(repeat_snapshot)]
    )
    db_after = _db_summary(repeat_db)
    snap_after = _snapshot_state(repeat_snapshot)
    ok = (
        code == 0
        and snap_before["sha256"] == snap_after["sha256"]
        and db_before["benchmark_sha256"] == db_after["benchmark_sha256"]
    )
    print(f"[{'PASS' if ok else 'FAIL'}] repeat_run: exit {code} (expect 0)")
    repeat_lines = output.strip().splitlines()
    results.append(
        {
            "case": "repeat_run",
            "exit": code,
            "expect_exit": 0,
            "pass": ok,
            "db_unchanged": db_before["logical_sha256"] == db_after["logical_sha256"],
            "snapshot_unchanged": snap_before["sha256"] == snap_after["sha256"],
            "db_before": db_before,
            "db_after": db_after,
            "snapshot_before": snap_before,
            "snapshot_after": snap_after,
            "output": repeat_lines[:8],
            "output_tail": repeat_lines[-4:],
        }
    )
    results.append(
        _case(
            "allow_stale_refresh",
            0,
            ["--force", "--allow-stale-benchmark"],
            {**base_common, "generated_at": "2026-10-24T00:00:00+00:00"},
            db_generated_at="2026-10-24T20:00:00+00:00",
            incoming={**base_common, "generated_at": "2026-10-24T12:00:00+00:00"},
        )
    )

    passed = all(item["pass"] for item in results)
    out_path = PACK / "data" / "seed-results.json"
    out_path.write_text(
        json.dumps(
            {
                "generated_at": now,
                "base_seed_exit": base_seed_exit,
                "cases": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out_path}; {'ALL PASS' if passed else 'HAS FAILURES'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
