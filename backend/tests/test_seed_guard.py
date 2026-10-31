"""R2-01 / R3-01 回归：破坏性播种之前必须完成快照校验与新旧比较。

返工前 `BENCHMARK_JSON` 在模块导入时就读盘，`main()` 拿到 `--force` 直接清表，
于是「旧快照覆盖掉库里较新的曲线」是静默发生的（exit 0）。

R3-01 追加的边界：
- `generated_at` 真正解析为时刻，带时区的时间先归一化再比较，禁止字典序；
- sample / curve / 策略身份做类型、范围、日序校验，bool 不能冒充整数；
- incoming 的校验与比较全部通过后才写目标快照，拒绝路径不改库也不改快照；
- 完整仿真输出（四键 + `params`）可以导入，但落盘只保留四键。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models import AlgoConfig, Base, User
from backend.scripts import init_seed_data as seed
from backend.scripts.init_seed_data import (
    BENCHMARK_KEYS,
    BenchmarkSnapshotError,
    ensure_benchmark_ready,
    load_benchmark,
)


def _payload(generated_at: str, d14: float = 0.01) -> dict:
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
            "baseline_no_decay": [0.29] * 14,
        },
        "group_satisfaction_bars": {
            "strategies": ["mixed_omega_0.5", "average_omega_1.0", "random"],
            "avg_scores": [93.8, 94.1, 81.1],
            "least_misery_scores": [74.6, 73.4, 61.7],
        },
    }


@pytest.fixture()
def env(tmp_path):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    db.add(User(id=1, username="u1", nickname="U1", avatar="", persona_title=""))
    db.commit()
    snapshot = tmp_path / "benchmark_snapshot.json"
    yield db, snapshot, tmp_path
    db.close()
    engine.dispose()


def _write_newer_db_curve(db, generated_at: str, d14: float):
    db.query(AlgoConfig).delete()
    db.add(
        AlgoConfig(
            config_name="default_production",
            lambda_decay=0.5,
            omega_group=0.5,
            alpha_taste=0.35,
            beta_weather=0.25,
            gamma_budget=0.20,
            delta_status=0.20,
            benchmark_json=_payload(generated_at, d14),
        )
    )
    db.commit()


def _db_benchmark(db):
    row = (
        db.query(AlgoConfig)
        .filter(AlgoConfig.config_name == "default_production")
        .one_or_none()
    )
    return copy.deepcopy(row.benchmark_json) if row else None


def _write(path: Path, payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    return text


def test_stale_snapshot_cannot_overwrite_newer_db(env):
    """库里是较新的曲线，快照是旧的 → 必须在清库前拒绝。"""
    db, snapshot, _ = env
    _write_newer_db_curve(db, "2026-10-25T09:00:00", 0.0091)
    _write(snapshot, _payload("2026-10-24T09:00:00", 0.1234))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert "拒绝用旧快照覆盖较新的库内曲线" in str(err.value)
    assert db.query(User).count() == 1


def test_missing_snapshot_aborts_before_clear(env):
    db, snapshot, _ = env
    with pytest.raises(BenchmarkSnapshotError):
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert db.query(User).count() == 1


def test_refresh_failure_keeps_previous_snapshot(env):
    """新快照结构不合法 → 抛错，且原快照内容保持不变（不写半成品）。"""
    db, snapshot, tmp_path = env
    good = _payload("2026-10-24T09:00:00", 0.01)
    original = _write(snapshot, good)
    broken = copy.deepcopy(good)
    broken["duplication_rate_curve"]["ours_lambda_0.5"] = [0.01] * 5
    incoming = tmp_path / "incoming.json"
    _write(incoming, broken)

    with pytest.raises(BenchmarkSnapshotError):
        ensure_benchmark_ready(db, snapshot_path=snapshot, incoming_path=incoming)
    assert snapshot.read_text(encoding="utf-8") == original


def test_refresh_then_repeat_is_idempotent(env):
    """同一份新快照连续刷新两次：都成功，内容稳定。"""
    db, snapshot, tmp_path = env
    _write(snapshot, _payload("2026-10-24T09:00:00", 0.02))
    incoming = tmp_path / "incoming.json"
    _write(incoming, _payload("2026-10-24T10:00:00", 0.0091))

    first = ensure_benchmark_ready(
        db, snapshot_path=snapshot, incoming_path=incoming
    )
    second = ensure_benchmark_ready(
        db, snapshot_path=snapshot, incoming_path=incoming
    )
    assert first["generated_at"] == second["generated_at"] == "2026-10-24T10:00:00"
    assert (
        load_benchmark(snapshot)["duplication_rate_curve"]["ours_lambda_0.5"][0]
        == 0.0091
    )


def test_invalid_generated_at_rejected_without_touching_anything(env):
    db, snapshot, _ = env
    text = _write(snapshot, _payload("zz-not-a-date", 0.01))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert "不是合法的 ISO 8601 时间" in str(err.value)
    assert snapshot.read_text(encoding="utf-8") == text
    assert db.query(User).count() == 1


def test_timezone_aware_stale_snapshot_rejected(env):
    """DB 16:00Z 比快照 23:00+08:00（15:00Z）新一小时：归一化后必须拒绝。"""
    db, snapshot, _ = env
    _write_newer_db_curve(db, "2026-10-24T16:00:00+00:00", 0.0091)
    text = _write(snapshot, _payload("2026-10-24T23:00:00+08:00", 0.1234))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert "拒绝用旧快照覆盖较新的库内曲线" in str(err.value)
    assert snapshot.read_text(encoding="utf-8") == text
    assert db.query(User).count() == 1


def _mutate_sample(payload):
    payload["sample"]["personas"] = 0
    payload["sample"]["rooms"] = -1


def _mutate_bool_int(payload):
    payload["sample"]["personas"] = True


def _mutate_curve_days(payload):
    payload["duplication_rate_curve"]["days"] = [14] * 14


def _mutate_curve_days_short(payload):
    payload["duplication_rate_curve"]["days"] = list(range(1, 14))


def _mutate_curve_text(payload):
    payload["duplication_rate_curve"]["ours_lambda_0.5"] = ["NOT_A_NUMBER"] * 14


def _mutate_curve_range(payload):
    payload["duplication_rate_curve"]["ours_lambda_0.5"] = [1.2] * 14


def _mutate_curve_nan(payload):
    payload["duplication_rate_curve"]["ours_lambda_0.5"] = [float("nan")] * 14


def _mutate_strategy(payload):
    payload["group_satisfaction_bars"]["strategies"][0] = "not_a_strategy"


def _mutate_bar_length(payload):
    payload["group_satisfaction_bars"]["avg_scores"] = [93.8, 94.1]


def _mutate_bar_range(payload):
    payload["group_satisfaction_bars"]["avg_scores"][0] = 101.0


@pytest.mark.parametrize(
    "mutate",
    [
        _mutate_sample,
        _mutate_bool_int,
        _mutate_curve_days,
        _mutate_curve_days_short,
        _mutate_curve_text,
        _mutate_curve_range,
        _mutate_curve_nan,
        _mutate_strategy,
        _mutate_bar_length,
        _mutate_bar_range,
    ],
)
def test_structural_and_numeric_violations_are_rejected(env, mutate):
    db, snapshot, _ = env
    payload = _payload("2026-10-24T09:00:00", 0.01)
    mutate(payload)
    text = _write(snapshot, payload)

    with pytest.raises(BenchmarkSnapshotError):
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert snapshot.read_text(encoding="utf-8") == text
    assert db.query(User).count() == 1


def test_malformed_db_generated_at_is_rejected(env):
    db, snapshot, _ = env
    _write_newer_db_curve(db, "also-not-a-time", 0.01)
    _write(snapshot, _payload("2026-10-24T09:00:00", 0.01))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert "库内 benchmark.generated_at" in str(err.value)
    assert db.query(User).count() == 1


def test_allow_stale_does_not_hide_malformed_db_time(env):
    db, snapshot, _ = env
    _write_newer_db_curve(db, "not-a-time", 0.01)
    _write(snapshot, _payload("2026-10-24T09:00:00", 0.01))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot, allow_stale=True)
    assert "库内 benchmark.generated_at" in str(err.value)
    assert db.query(User).count() == 1


def test_missing_db_generated_at_is_rejected(env):
    db, snapshot, _ = env
    db.query(AlgoConfig).delete()
    db.add(AlgoConfig(config_name="default_production", benchmark_json={"sample": {}}))
    db.commit()
    _write(snapshot, _payload("2026-10-24T09:00:00", 0.01))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot)
    assert "generated_at 缺失" in str(err.value)
    assert db.query(User).count() == 1


def test_full_simulation_output_with_params_is_accepted_and_stripped(env):
    """完整仿真输出（四键 + params）可导入；落盘不能带 params。"""
    db, snapshot, tmp_path = env
    _write(snapshot, _payload("2026-10-24T09:00:00", 0.02))
    full = _payload("2026-10-24T10:00:00", 0.0091)
    full["params"] = {"seed": 7, "calls": {"recommend_single": 48000}}
    incoming = tmp_path / "simulation_output.json"
    _write(incoming, full)

    result = ensure_benchmark_ready(
        db, snapshot_path=snapshot, incoming_path=incoming
    )
    assert set(result) == BENCHMARK_KEYS
    stored = json.loads(snapshot.read_text(encoding="utf-8"))
    assert set(stored) == BENCHMARK_KEYS
    assert "params" not in stored


def test_rejected_incoming_never_overwrites_snapshot_or_db(env):
    """目标 00:00、incoming 12:00、库 20:00：拒绝，且三者都不变。"""
    db, snapshot, tmp_path = env
    _write_newer_db_curve(db, "2026-10-24T20:00:00+00:00", 0.0091)
    original = _write(snapshot, _payload("2026-10-24T00:00:00+00:00", 0.02))
    db_before = _db_benchmark(db)
    incoming = tmp_path / "incoming.json"
    _write(incoming, _payload("2026-10-24T12:00:00+00:00", 0.0091))

    with pytest.raises(BenchmarkSnapshotError) as err:
        ensure_benchmark_ready(db, snapshot_path=snapshot, incoming_path=incoming)
    assert "拒绝用旧快照覆盖较新的库内曲线" in str(err.value)
    assert snapshot.read_text(encoding="utf-8") == original
    assert _db_benchmark(db) == db_before
    assert db.query(User).count() == 1


def test_allow_stale_only_bypasses_db_comparison(env):
    """显式例外只跳过“比库内旧”，结构与时间校验仍然生效。"""
    db, snapshot, tmp_path = env
    _write_newer_db_curve(db, "2026-10-24T20:00:00+00:00", 0.0091)
    _write(snapshot, _payload("2026-10-24T00:00:00+00:00", 0.02))
    incoming = tmp_path / "incoming.json"
    _write(incoming, _payload("2026-10-24T12:00:00+00:00", 0.0091))

    result = ensure_benchmark_ready(
        db,
        snapshot_path=snapshot,
        incoming_path=incoming,
        allow_stale=True,
    )
    assert result["generated_at"] == "2026-10-24T12:00:00+00:00"
    assert load_benchmark(snapshot)["generated_at"] == result["generated_at"]

    broken = _payload("2026-10-24T13:00:00+00:00", 0.0091)
    broken["duplication_rate_curve"]["days"] = [14] * 14
    bad_incoming = tmp_path / "bad_incoming.json"
    _write(bad_incoming, broken)
    before = snapshot.read_text(encoding="utf-8")
    with pytest.raises(BenchmarkSnapshotError):
        ensure_benchmark_ready(
            db,
            snapshot_path=snapshot,
            incoming_path=bad_incoming,
            allow_stale=True,
        )
    assert snapshot.read_text(encoding="utf-8") == before


def test_snapshot_with_params_is_not_a_valid_stored_snapshot(env):
    db, snapshot, _ = env
    payload = _payload("2026-10-24T09:00:00", 0.01)
    payload["params"] = {"seed": 1}
    _write(snapshot, payload)

    with pytest.raises(BenchmarkSnapshotError):
        load_benchmark(snapshot)
    assert db.query(User).count() == 1
