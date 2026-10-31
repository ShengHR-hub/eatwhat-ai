"""仿真 ETL 导入：行数、人设映射、幂等替换。"""

import json
import sqlite3
from datetime import datetime

import pytest

from backend.models import SimulationMealLog, SimulationRun
from backend.scripts.import_simulation import _compute_repeat_metrics, import_simulation


def _write_fixture(tmp_path):
    data_dir = tmp_path / "g3"
    parallel = data_dir / "parallel_full"
    parallel.mkdir(parents=True)

    benchmark = {
        "generated_at": "2026-10-29T01:00:00",
        "sample": {
            "personas": 1,
            "days": 2,
            "meals_per_day": 2,
            "rooms": 1,
            "members_per_room": 2,
        },
        "params": {
            "seed": 42,
            "lambda_val": 0.5,
            "omega_val": 0.5,
            "parallel": {"shard_size": 1},
        },
        "duplication_rate_curve": {
            "days": list(range(1, 15)),
            "ours_lambda_0.5": [0.0] * 14,
            "baseline_no_decay": [0.1] * 14,
        },
        "group_satisfaction_bars": {
            "strategies": ["mixed_omega_0.5", "random"],
            "avg_scores": [90.0, 70.0],
            "least_misery_scores": [80.0, 40.0],
        },
    }
    (data_dir / "parallel_benchmark_full.json").write_text(
        json.dumps(benchmark, ensure_ascii=False), encoding="utf-8"
    )

    def rows(arm, dup):
        out = []
        for meal in (1, 2):
            out.append(
                {
                    "arm": arm,
                    "day": 1,
                    "meal": meal,
                    "user_id": 1,
                    "mode_type": "HOME_COOKING",
                    "dish_id": 100 + meal,
                    "dish_name": f"菜{arm}{meal}",
                    "cuisine_type": "家常菜",
                    "total_score": 80.0,
                    "decay_weight": 0.9,
                    "duplicated": dup,
                    "candidate_count": 10,
                }
            )
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n"

    (parallel / "detail_seed42_shard00_ours.jsonl").write_text(rows("ours", True), encoding="utf-8")
    (parallel / "detail_seed42_shard00_baseline.jsonl").write_text(
        rows("baseline", False), encoding="utf-8"
    )

    groups = parallel / "sim_seed42_groups.db"
    conn = sqlite3.connect(groups)
    conn.executescript(
        """
        create table group_rooms (
            room_code text primary key, mode_type text, member_user_ids text,
            candidate_dish_ids text, winner_dish_id integer, created_at text
        );
        create table room_votes (
            room_code text, user_id integer, dish_id integer, vote_type text, voted_at text
        );
        """
    )
    conn.execute(
        "insert into group_rooms values (?,?,?,?,?,?)",
        ("000001", "HOME_COOKING", "[1,2]", "[100,101]", 100, "2026-06-01 08:00:00"),
    )
    conn.execute(
        "insert into room_votes values (?,?,?,?,?)",
        ("000001", 1, 100, "LIKE", "2026-06-01 08:00:00"),
    )
    conn.execute(
        "insert into room_votes values (?,?,?,?,?)",
        ("000001", 2, 101, "PASS", "2026-06-01 08:00:00"),
    )
    conn.commit()
    conn.close()
    return data_dir, groups


def test_import_rows_and_persona_mapping(session_factory, tmp_path):
    data_dir, groups = _write_fixture(tmp_path)
    with session_factory() as session:
        summary = import_simulation(
            session, data_dir=data_dir, name="unit-run", groups_db=groups
        )
        assert summary["meal_rows"] == 4
        assert summary["room_rows"] == 1
        assert summary["vote_rows"] == 2

        run = session.query(SimulationRun).filter_by(name="unit-run").one()
        assert (run.meal_rows, run.room_rows, run.vote_rows) == (4, 1, 2)
        assert run.personas == 1 and run.days == 2
        logs = session.query(SimulationMealLog).filter_by(run_id=run.id).all()
        assert {log.arm for log in logs} == {"ours", "baseline"}
        assert {log.persona_id for log in logs} == {1}
        assert sum(1 for log in logs if log.duplicated) == 2


def test_import_is_idempotent_with_replace(session_factory, tmp_path):
    data_dir, groups = _write_fixture(tmp_path)
    with session_factory() as session:
        import_simulation(session, data_dir=data_dir, name="unit-run", groups_db=groups)
        with pytest.raises(RuntimeError):
            import_simulation(session, data_dir=data_dir, name="unit-run", groups_db=groups)

        summary = import_simulation(
            session, data_dir=data_dir, name="unit-run", groups_db=groups, replace=True
        )
        assert summary["inserted_meals"] == 4
        assert session.query(SimulationRun).count() == 1
        assert session.query(SimulationMealLog).count() == 4


def test_dry_run_does_not_write(session_factory, tmp_path):
    data_dir, groups = _write_fixture(tmp_path)
    with session_factory() as session:
        summary = import_simulation(
            session, data_dir=data_dir, name="dry-run", groups_db=groups, dry_run=True
        )
        assert summary["meal_rows"] == 4
        assert summary["dry_run"] is True
        assert session.query(SimulationRun).count() == 0


def test_repeat_metrics_use_14_day_window(tmp_path):
    rows_ours = [
        (1, 1, 1, "川菜"), (1, 2, 2, "粤菜"),
        (2, 1, 3, "湘菜"), (2, 2, 4, "浙菜"),
    ]
    rows_baseline = [
        (1, 1, 1, "川菜"), (1, 2, 2, "粤菜"),
        (2, 1, 1, "川菜"), (2, 2, 2, "粤菜"),
    ]

    def write(name, rows):
        path = tmp_path / name
        with path.open("w", encoding="utf-8") as handle:
            for day, meal, dish, cuisine in rows:
                handle.write(json.dumps({
                    "arm": "ours" if "ours" in name else "baseline",
                    "day": day, "meal": meal, "user_id": 1,
                    "mode_type": "HOME_COOKING", "dish_id": dish,
                    "dish_name": f"菜{dish}", "cuisine_type": cuisine,
                    "total_score": 80.0, "decay_weight": 1.0,
                    "duplicated": False, "candidate_count": 10,
                }, ensure_ascii=False) + "\n")
        return path

    files = [write("detail_seed1_shard00_ours.jsonl", rows_ours),
             write("detail_seed1_shard00_baseline.jsonl", rows_baseline)]
    metrics = _compute_repeat_metrics(files, shard_size=1)

    ours = metrics["by_arm"]["ours"]
    baseline = metrics["by_arm"]["baseline"]
    assert ours["same_dish_rate"] == 0.0
    assert baseline["same_dish_rate"] == 0.5
    assert baseline["same_cuisine_rate"] == 0.5
    assert len(metrics["daily"]["days"]) == 14
    assert metrics["daily"]["arms"]["baseline"]["same_dish"][1] == 1.0
    assert len(metrics["per_user"]["ours"]) == 1
    assert len(baseline["user_rate_box"]) == 5
