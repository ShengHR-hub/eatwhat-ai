"""把 G3 离线仿真结果导入独立的 simulation_* 表。

数据源（默认 docs/review/consolidated/G3/data）：
* parallel_benchmark_full.json              —— 样本、参数、重样率曲线、群组满意度
* parallel_full/detail_seed*_shard*_*.jsonl —— 48,000 条逐餐推荐明细（ours / baseline）
* parallel_full/sim_seed*_groups.db         —— 1,000 房间、40,000 张原始投票

只写 simulation_runs / simulation_meal_logs / simulation_rooms /
simulation_room_votes / simulation_group_results，不碰真实业务表。

用法：
    python -m backend.scripts.import_simulation --dry-run
    python -m backend.scripts.import_simulation --replace
    python -m backend.scripts.import_simulation --database-url sqlite:///tmp.db
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional

from sqlalchemy import create_engine, delete, insert
from sqlalchemy.orm import Session, sessionmaker

from ..models import (
    SimulationGroupResult,
    SimulationMealLog,
    SimulationRoom,
    SimulationRoomVote,
    SimulationRun,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "docs/review/consolidated/G3/data"
DETAIL_RE = re.compile(r"detail_seed(\d+)_shard(\d+)_(ours|baseline)\.jsonl$")


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _chunks(items: Iterable[dict], size: int) -> Iterator[list[dict]]:
    batch: list[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _shard_size(benchmark: dict, files: list[Path]) -> int:
    parallel = (benchmark.get("params") or {}).get("parallel") or {}
    if parallel.get("shard_size"):
        return int(parallel["shard_size"])
    personas = int((benchmark.get("sample") or {}).get("personas") or 0)
    shards = len({DETAIL_RE.search(p.name).group(2) for p in files if DETAIL_RE.search(p.name)})
    return max(1, personas // shards) if personas and shards else 25


def _iter_meals(path: Path, shard: int, shard_size: int) -> Iterator[dict]:
    arm = DETAIL_RE.search(path.name).group(3)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            user_id = int(row.get("user_id") or 0)
            # shard 内的 user_id 是 1..25；映射成 1..200 的全局人设编号。
            persona_id = shard * shard_size + user_id if user_id <= shard_size else user_id
            yield {
                "arm": arm,
                "persona_id": persona_id,
                "day": int(row.get("day") or 0),
                "meal": int(row.get("meal") or 0),
                "mode_type": str(row.get("mode_type") or "")[:16],
                "dish_id": int(row.get("dish_id") or 0),
                "dish_name": str(row.get("dish_name") or "")[:128],
                "cuisine_type": str(row.get("cuisine_type") or "")[:64],
                "total_score": float(row.get("total_score") or 0.0),
                "decay_weight": float(row.get("decay_weight") or 0.0),
                "duplicated": bool(row.get("duplicated")),
                "candidate_count": int(row.get("candidate_count") or 0),
            }


def _read_rooms(groups_db: Path) -> Iterator[dict]:
    conn = sqlite3.connect(f"file:{groups_db.as_posix()}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "select room_code, mode_type, member_user_ids, candidate_dish_ids, "
            "winner_dish_id, created_at from group_rooms order by room_code"
        )
        for code, mode_type, members, cards, winner, created in cur:
            yield {
                "room_code": str(code)[:10],
                "mode_type": str(mode_type)[:16],
                "member_user_ids": json.loads(members or "[]"),
                "candidate_dish_ids": json.loads(cards or "[]"),
                "winner_dish_id": int(winner) if winner is not None else None,
                "votes_count": 0,
                "created_at": _parse_dt(created),
            }
    finally:
        conn.close()


def _read_votes(groups_db: Path) -> Iterator[dict]:
    conn = sqlite3.connect(f"file:{groups_db.as_posix()}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "select room_code, user_id, dish_id, vote_type, voted_at from room_votes"
        )
        for code, user_id, dish_id, vote_type, voted_at in cur:
            yield {
                "room_code": str(code)[:10],
                "user_id": int(user_id),
                "dish_id": int(dish_id),
                "vote_type": str(vote_type)[:16],
                "voted_at": _parse_dt(voted_at),
            }
    finally:
        conn.close()


def _count_lines(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            total += sum(1 for line in handle if line.strip())
    return total


def _sqlite_count(groups_db: Path, table: str) -> int:
    conn = sqlite3.connect(f"file:{groups_db.as_posix()}?mode=ro", uri=True)
    try:
        return int(conn.execute(f"select count(*) from {table}").fetchone()[0])
    finally:
        conn.close()


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def _summarize(values: list[float], prefix: str) -> dict:
    if not values:
        return {
            f"{prefix}_mean": 0.0,
            f"{prefix}_sd": 0.0,
            f"{prefix}_min": 0.0,
            f"{prefix}_max": 0.0,
            f"{prefix}_p10": 0.0,
            f"{prefix}_p50": 0.0,
            f"{prefix}_p90": 0.0,
            f"{prefix}_box": [0.0, 0.0, 0.0, 0.0, 0.0],
        }
    ordered = sorted(float(v) for v in values)
    mean = sum(ordered) / len(ordered)
    sd = (sum((v - mean) ** 2 for v in ordered) / len(ordered)) ** 0.5
    return {
        f"{prefix}_mean": round(mean, 6),
        f"{prefix}_sd": round(sd, 6),
        f"{prefix}_min": round(ordered[0], 6),
        f"{prefix}_max": round(ordered[-1], 6),
        f"{prefix}_p10": round(_quantile(ordered, 0.10), 6),
        f"{prefix}_p50": round(_quantile(ordered, 0.50), 6),
        f"{prefix}_p90": round(_quantile(ordered, 0.90), 6),
        f"{prefix}_box": [
            round(ordered[0], 6),
            round(_quantile(ordered, 0.25), 6),
            round(_quantile(ordered, 0.50), 6),
            round(_quantile(ordered, 0.75), 6),
            round(ordered[-1], 6),
        ],
    }


def _compute_repeat_metrics(
    detail_files: list[Path], shard_size: int, window_days: int = 14
) -> dict:
    """从逐餐明细重算「14 天窗口同菜 / 同菜系重样」。

    原 benchmark 的 duplication_rate_curve 是「和上一餐同菜系」，本系统
    结构性地避开连续同菜系，图上恒为 0，展示性弱。这里改用 14 天窗口
    内是否再次选择同一 dish_id / cuisine_type，既符合防腻语义，也有
    200 个用户的真实分布。
    """
    by_arm: dict[str, dict[int, list[tuple]]] = defaultdict(lambda: defaultdict(list))
    for path in detail_files:
        match = DETAIL_RE.search(path.name)
        if not match:
            continue
        arm = match.group(3)
        shard = int(match.group(2))
        for row in _iter_meals(path, shard, shard_size):
            dish_id = int(row["dish_id"])
            if dish_id <= 0:
                continue
            persona_id = int(row["persona_id"])
            by_arm[arm][persona_id].append(
                (int(row["day"]), int(row["meal"]), dish_id, str(row["cuisine_type"]))
            )

    days = list(range(1, 15))
    result = {
        "window_days": window_days,
        "definition": (
            "同一用户在 14 天窗口内再次选择同一 dish_id / cuisine_type；"
            "窗口含当天更早的餐，不含当前餐。"
        ),
        "by_arm": {},
        "daily": {"days": days, "arms": {}},
        "per_user": {},
    }

    for arm, users in sorted(by_arm.items()):
        meals_by_day: Counter = Counter()
        dish_by_day: Counter = Counter()
        cuisine_by_day: Counter = Counter()
        total = dish_repeat = cuisine_repeat = 0
        user_rates: list[float] = []
        user_counts: list[int] = []

        for _, sequence in users.items():
            sequence.sort(key=lambda item: (item[0], item[1]))
            history: list[tuple] = []
            user_repeat = user_meals = 0
            for day, _meal, dish_id, cuisine in sequence:
                meals_by_day[day] += 1
                total += 1
                user_meals += 1
                window = [item for item in history if day - item[0] <= window_days]
                if window:
                    if any(item[1] == dish_id for item in window):
                        dish_repeat += 1
                        dish_by_day[day] += 1
                        user_repeat += 1
                    if cuisine and any(item[2] == cuisine for item in window):
                        cuisine_repeat += 1
                        cuisine_by_day[day] += 1
                history.append((day, dish_id, cuisine))
            user_rates.append(user_repeat / user_meals if user_meals else 0.0)
            user_counts.append(user_repeat)

        rates = _summarize(user_rates, "user_rate")
        counts = _summarize([float(v) for v in user_counts], "repeat_meals")
        result["by_arm"][arm] = {
            "meals": total,
            "users": len(users),
            "same_dish": dish_repeat,
            "same_dish_rate": round(dish_repeat / total, 6) if total else 0.0,
            "same_cuisine": cuisine_repeat,
            "same_cuisine_rate": round(cuisine_repeat / total, 6) if total else 0.0,
            **rates,
            **counts,
        }
        result["daily"]["arms"][arm] = {
            "same_dish": [
                round(dish_by_day[day] / meals_by_day[day], 6)
                if meals_by_day[day]
                else 0.0
                for day in days
            ],
            "same_cuisine": [
                round(cuisine_by_day[day] / meals_by_day[day], 6)
                if meals_by_day[day]
                else 0.0
                for day in days
            ],
        }
        result["per_user"][arm] = [round(rate, 6) for rate in user_rates]

    return result


def import_simulation(
    session: Session,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    name: Optional[str] = None,
    replace: bool = False,
    dry_run: bool = False,
    groups_db: Optional[Path] = None,
    benchmark_path: Optional[Path] = None,
    batch_size: int = 5000,
) -> dict:
    data_dir = Path(data_dir)
    benchmark_path = Path(benchmark_path or data_dir / "parallel_benchmark_full.json")
    groups_db = Path(groups_db or data_dir / "parallel_full" / "sim_seed20261029_groups.db")
    if not benchmark_path.exists():
        raise FileNotFoundError(f"benchmark 不存在：{benchmark_path}")
    if not groups_db.exists():
        raise FileNotFoundError(f"群组仿真库不存在：{groups_db}")

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    sample = benchmark.get("sample") or {}
    params = benchmark.get("params") or {}
    seed = int(params.get("seed") or 20261029)
    run_name = name or f"g3-full-{seed}"

    detail_files = sorted(
        p for p in (data_dir / "parallel_full").glob("detail_*.jsonl")
        if DETAIL_RE.search(p.name)
    )
    if not detail_files:
        raise FileNotFoundError("没有找到 detail_*.jsonl")
    shard_size = _shard_size(benchmark, detail_files)
    meal_rows = _count_lines(detail_files)
    room_rows = _sqlite_count(groups_db, "group_rooms")
    vote_rows = _sqlite_count(groups_db, "room_votes")
    repeat_metrics = _compute_repeat_metrics(detail_files, shard_size)

    curve = benchmark.get("duplication_rate_curve") or {}
    bars = benchmark.get("group_satisfaction_bars") or {}
    strategies = list(bars.get("strategies") or [])
    averages = list(bars.get("avg_scores") or [])
    least = list(bars.get("least_misery_scores") or [])
    if not (len(strategies) == len(averages) == len(least)):
        raise ValueError("group_satisfaction_bars 三个数组长度不一致")

    summary = {
        "name": run_name,
        "seed": seed,
        "personas": int(sample.get("personas") or 0),
        "days": int(sample.get("days") or 0),
        "meals_per_day": int(sample.get("meals_per_day") or 0),
        "rooms": room_rows,
        "members_per_room": int(sample.get("members_per_room") or 0),
        "meal_rows": meal_rows,
        "room_rows": room_rows,
        "vote_rows": vote_rows,
        "group_strategies": len(strategies),
        "detail_files": len(detail_files),
        "repeat_summary": {
            arm: {
                key: item[key]
                for key in (
                    "same_dish_rate",
                    "same_cuisine_rate",
                    "user_rate_mean",
                    "user_rate_sd",
                    "user_rate_min",
                    "user_rate_max",
                )
            }
            for arm, item in repeat_metrics["by_arm"].items()
        },
    }
    if dry_run:
        summary["dry_run"] = True
        return summary

    existing = session.query(SimulationRun).filter(SimulationRun.name == run_name).first()
    if existing is not None:
        if not replace:
            raise RuntimeError(f"run 已存在：{run_name}；需要覆盖请加 --replace")
        for model in (SimulationRoomVote, SimulationRoom, SimulationMealLog, SimulationGroupResult):
            session.execute(delete(model).where(model.run_id == existing.id))
        session.delete(existing)
        session.flush()

    run = SimulationRun(
        name=run_name,
        seed=seed,
        personas=summary["personas"],
        days=summary["days"],
        meals_per_day=summary["meals_per_day"],
        rooms_count=room_rows,
        members_per_room=summary["members_per_room"],
        lambda_decay=params.get("lambda_val"),
        omega_group=params.get("omega_val"),
        generated_at=_parse_dt(benchmark.get("generated_at")),
        source_dir=str(data_dir),
        metrics={
            "duplication_rate_curve": curve,
            "params": params,
            "repeat_metrics": repeat_metrics,
            "source": {
                "benchmark": benchmark_path.name,
                "groups_db": groups_db.name,
                "detail_files": [p.name for p in detail_files],
            },
        },
        meal_rows=0,
        room_rows=0,
        vote_rows=0,
    )
    session.add(run)
    session.flush()

    inserted_meals = 0
    for path in detail_files:
        shard = int(DETAIL_RE.search(path.name).group(2))
        for batch in _chunks(_iter_meals(path, shard, shard_size), batch_size):
            for row in batch:
                row["run_id"] = run.id
            session.execute(insert(SimulationMealLog), batch)
            inserted_meals += len(batch)

    inserted_rooms = 0
    for batch in _chunks(_read_rooms(groups_db), batch_size):
        for row in batch:
            row["run_id"] = run.id
        session.execute(insert(SimulationRoom), batch)
        inserted_rooms += len(batch)

    # 房间表先落库后补 votes_count，保证列表接口无需再扫 4 万票。
    vote_counts: dict[str, int] = {}
    inserted_votes = 0
    for batch in _chunks(_read_votes(groups_db), batch_size):
        for row in batch:
            row["run_id"] = run.id
            vote_counts[row["room_code"]] = vote_counts.get(row["room_code"], 0) + 1
        session.execute(insert(SimulationRoomVote), batch)
        inserted_votes += len(batch)
    for code, count in vote_counts.items():
        session.query(SimulationRoom).filter(
            SimulationRoom.run_id == run.id, SimulationRoom.room_code == code
        ).update({SimulationRoom.votes_count: count}, synchronize_session=False)

    for strategy, avg, least_score in zip(strategies, averages, least):
        session.add(
            SimulationGroupResult(
                run_id=run.id,
                strategy=str(strategy)[:64],
                avg_score=float(avg),
                least_misery_score=float(least_score),
            )
        )

    run.meal_rows = inserted_meals
    run.room_rows = inserted_rooms
    run.vote_rows = inserted_votes
    session.commit()

    summary.update(
        {
            "run_id": run.id,
            "inserted_meals": inserted_meals,
            "inserted_rooms": inserted_rooms,
            "inserted_votes": inserted_votes,
        }
    )
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="导入 G3 仿真结果到 simulation_* 表")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--name", default=None)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--groups-db", type=Path, default=None)
    parser.add_argument("--benchmark", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)

    if args.database_url:
        engine = create_engine(args.database_url, future=True)
        factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        session = factory()
        close = True
    else:
        from ..database import SessionLocal

        session = SessionLocal()
        close = True

    try:
        summary = import_simulation(
            session,
            data_dir=args.data_dir,
            name=args.name,
            replace=args.replace,
            dry_run=args.dry_run,
            groups_db=args.groups_db,
            benchmark_path=args.benchmark,
            batch_size=args.batch_size,
        )
    finally:
        if close:
            session.close()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
