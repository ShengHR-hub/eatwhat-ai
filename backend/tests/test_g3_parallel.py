"""G3 并行仿真：分片合并、原始计数、全局编号与确定性回归。"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.algorithms import simulate_personas as sim
from backend.database import Base
from backend.models import Restaurant, User
from backend.scripts.init_seed_data import seed_all
from backend.scripts.simulate_g3_parallel import (
    _database_counts,
    _merge_shard_curves,
    _shard_specs,
    _sum_calls,
    build_benchmark,
)


def _source_database(tmp_path: Path) -> str:
    path = tmp_path / "source.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    try:
        seed_all(session)
        session.query(Restaurant).update({Restaurant.campus: "SIYUAN"})
        session.commit()
    finally:
        session.close()
        engine.dispose()
    return f"sqlite:///{path.as_posix()}"


def _usernames(database_file: str) -> list[str]:
    with sqlite3.connect(database_file) as connection:
        return [row[0] for row in connection.execute("SELECT username FROM users ORDER BY id")]


def _stable_shard_fields(shards: list[dict]) -> list[dict]:
    return [
        {
            "shard": shard["shard"],
            "seed": shard["seed"],
            "start_index": shard["start_index"],
            "personas": shard["personas"],
            "arms": {
                arm: {
                    key: value
                    for key, value in shard["arms"][arm].items()
                    if key not in {"db_file", "detail_file"}
                }
                for arm in ("ours", "baseline")
            },
            "errors": shard["errors"],
        }
        for shard in shards
    ]


def test_seed_personas_start_index_preserves_default_and_global_names(tmp_path):
    engine = sim._new_engine(tmp_path / "personas.db")
    session = sessionmaker(bind=engine, future=True)()
    try:
        sim._seed_personas(session, random.Random(7), 2)
        sim._seed_personas(session, random.Random(9), 2, start_index=3)
        assert [user.username for user in session.query(User).order_by(User.id)] == [
            "sim_p001",
            "sim_p002",
            "sim_p003",
            "sim_p004",
        ]
    finally:
        session.close()
        engine.dispose()


def test_default_partition_has_eight_shards_and_complete_global_offsets():
    specs = _shard_specs(200, 25)
    assert len(specs) == 8
    assert specs[0] == {"shard": 0, "start_index": 1, "personas": 25}
    assert specs[-1] == {"shard": 7, "start_index": 176, "personas": 25}
    assert sum(spec["personas"] for spec in specs) == 200
    assert _shard_specs(8, 3) == [
        {"shard": 0, "start_index": 1, "personas": 3},
        {"shard": 1, "start_index": 4, "personas": 3},
        {"shard": 2, "start_index": 7, "personas": 2},
    ]


def test_curve_merge_weights_personas_and_calls_are_summed():
    shards = [
        {
            "shard": 0,
            "personas": 3,
            "arms": {"ours": {"curve": [0.1, 0.2]}},
        },
        {
            "shard": 1,
            "personas": 1,
            "arms": {"ours": {"curve": [0.5, 0.4]}},
        },
    ]
    assert _merge_shard_curves(shards, "ours", 2) == [0.2, 0.25]
    assert _sum_calls(
        {"recommend_single": 24, "shortlist_candidates": 1},
        {"recommend_single": 24, "member_prior_scores": 1},
        {"compute_group_consensus": 2},
    ) == {
        "recommend_single": 48,
        "shortlist_candidates": 1,
        "member_prior_scores": 1,
        "compute_group_consensus": 2,
    }


def test_parallel_build_counts_and_determinism(tmp_path):
    source_url = _source_database(tmp_path)
    source_counts_before = _database_counts(source_url)
    common = {
        "seed": 7123,
        "personas": 4,
        "days": 1,
        "rooms": 1,
        "absence_rooms": 1,
        "shard_size": 2,
        "workers": 2,
        "source_database_url": source_url,
    }

    first = build_benchmark(data_dir=tmp_path / "first", **common)
    second = build_benchmark(data_dir=tmp_path / "second", **common)

    assert set(first) == {
        "generated_at",
        "sample",
        "duplication_rate_curve",
        "group_satisfaction_bars",
        "params",
    }
    params = first["params"]
    assert params["parallel"]["shard_count"] == 2
    assert [shard["start_index"] for shard in params["shards"]] == [1, 3]
    assert params["calls"] == {
        "recommend_single": 16,
        "shortlist_candidates": 2,
        "member_prior_scores": 2,
        "compute_group_consensus": 4,
    }
    assert params["raw_counts"]["single"] == {
        "planned_recommendations_per_arm": 8,
        "planned_recommendations_total": 16,
        "recommend_single_calls": 16,
        "eating_logs_per_arm": {"ours": 8, "baseline": 8},
        "detail_rows_per_arm": {"ours": 8, "baseline": 8},
    }
    assert params["raw_counts"]["group"]["personas"] == 4
    assert params["raw_counts"]["group"]["votes"] == 40
    assert params["raw_counts"]["absence"]["personas"] == 4
    assert params["raw_counts"]["absence"]["rooms"] == 1
    assert len(params["db_files"]) == 6
    for shard in params["shards"]:
        for arm in ("ours", "baseline"):
            assert _usernames(shard["arms"][arm]["db_file"]) == (
                ["sim_p001", "sim_p002"]
                if shard["shard"] == 0
                else ["sim_p003", "sim_p004"]
            )

    for key in ("duplication_rate_curve", "group_satisfaction_bars"):
        assert first[key] == second[key]
    for key in ("calls", "group", "absence", "raw_counts", "errors"):
        assert first["params"][key] == second["params"][key]
    assert _stable_shard_fields(first["params"]["shards"]) == _stable_shard_fields(
        second["params"]["shards"]
    )
    assert _database_counts(source_url) == source_counts_before
