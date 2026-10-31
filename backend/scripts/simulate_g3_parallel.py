"""G3 并行仿真：分片跑单人双臂，全量库跑群组与缺席实验。

每个分片、每个 arm 都使用独立 SQLite 与 JSONL；所有子进程只读打开同一个
source DB 复制目录。单人曲线按分片人设数加权，生产函数 CALLS 按原始计数累加。
默认参数仍是 200 人 × 60 天 × 2 餐、1000 房 × 4 人 × 10 候选，缺席实验另跑
200 房。复验示例：

    python -m backend.scripts.simulate_g3_parallel --workers 8 --shard-size 25

``--data-dir`` 必须指向本次实验自己的目录；重复运行会重建该目录内同名隔离库。
本脚本不写 source DB，也不写 algo_configs。
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import random
import sqlite3
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.algorithms import simulate_personas as sim
from backend.config import DATABASE_URL
from backend.models import Dish, EatingLog, GroupRoom, Restaurant, RoomVote, User


def _sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("G3 并行运行器要求基于文件的 SQLite DATABASE_URL")
    return Path(url.database).expanduser().resolve()


def _read_only_engine(database_url: str) -> Engine:
    """用 SQLite URI 的 mode=ro 打开源库，从驱动层阻止子进程写源库。"""
    path = _sqlite_path(database_url)
    if not path.is_file():
        raise RuntimeError(f"source DB 不存在：{path}")
    uri = f"file:{quote(path.as_posix())}?mode=ro"

    def connect() -> sqlite3.Connection:
        return sqlite3.connect(uri, uri=True, check_same_thread=False)

    return create_engine("sqlite://", creator=connect, future=True)


def _database_counts(database_url: str) -> Dict[str, int]:
    engine = _read_only_engine(database_url)
    session = sessionmaker(bind=engine, future=True)()
    try:
        return {
            "users": session.query(User).count(),
            "eating_logs": session.query(EatingLog).count(),
            "group_rooms": session.query(GroupRoom).count(),
            "room_votes": session.query(RoomVote).count(),
            "dishes": session.query(Dish).count(),
            "restaurants": session.query(Restaurant).count(),
        }
    finally:
        session.close()
        engine.dispose()


def _count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _reset_calls() -> None:
    sim.CALLS.clear()
    sim.CALL_SITES.clear()


def _call_snapshot() -> Tuple[Dict[str, int], List[str]]:
    return dict(sim.CALLS), list(sim.CALL_SITES)


def _shard_specs(personas: int, shard_size: int) -> List[Dict[str, int]]:
    if personas < sim.MEMBERS_PER_ROOM:
        raise ValueError(f"personas 至少为 {sim.MEMBERS_PER_ROOM}，才能进行四人群组实验")
    if shard_size < 1:
        raise ValueError("shard_size 必须大于 0")
    specs: List[Dict[str, int]] = []
    for shard, offset in enumerate(range(0, personas, shard_size)):
        specs.append(
            {
                "shard": shard,
                "start_index": offset + 1,
                "personas": min(shard_size, personas - offset),
            }
        )
    return specs


def _run_shard(task: Dict[str, object]) -> Dict[str, object]:
    """ProcessPool 子进程入口；task 只含可 pickle 的标量与字符串。"""
    seed = int(task["seed"])
    shard = int(task["shard"])
    start_index = int(task["start_index"])
    persona_count = int(task["personas"])
    days = int(task["days"])
    lambda_val = float(task["lambda_val"])
    source_database_url = str(task["source_database_url"])
    data_dir = Path(str(task["data_dir"]))
    shard_seed = seed + shard
    planned_calls = persona_count * days * sim.MEALS_PER_DAY

    source_engine = _read_only_engine(source_database_url)
    source = sessionmaker(bind=source_engine, future=True)()
    result: Dict[str, object] = {
        "shard": shard,
        "seed": shard_seed,
        "start_index": start_index,
        "personas": persona_count,
        "arms": {},
        "errors": [],
    }
    errors: List[str] = result["errors"]  # type: ignore[assignment]
    arms: Dict[str, object] = result["arms"]  # type: ignore[assignment]
    try:
        if not source.query(Dish).count():
            raise RuntimeError("source DB 没有菜品，先完成数据桥接")
        for arm, clock_shift in (("ours", 0), ("baseline", sim.LOOKBACK_DAYS + 1)):
            _reset_calls()
            db_path = data_dir / f"sim_seed{seed}_shard{shard:02d}_{arm}.db"
            detail_path = data_dir / f"detail_seed{seed}_shard{shard:02d}_{arm}.jsonl"
            engine = sim._new_engine(db_path)
            session = sessionmaker(bind=engine, future=True)()
            try:
                dish_count, restaurant_count = sim._copy_catalog(source, session)
                seeded = sim._seed_personas(
                    session,
                    random.Random(shard_seed),
                    persona_count,
                    start_index=start_index,
                )
                with detail_path.open("w", encoding="utf-8") as detail_file:
                    curve = sim._run_agent_arm(
                        session,
                        seeded,
                        arm,
                        shard_seed,
                        lambda_val,
                        clock_shift,
                        days,
                        detail_file,
                    )
            finally:
                session.close()
                engine.dispose()

            calls, call_sites = _call_snapshot()
            counts = _database_counts(f"sqlite:///{db_path.as_posix()}")
            detail_rows = _count_jsonl(detail_path)
            if calls.get("recommend_single", 0) != planned_calls:
                raise RuntimeError(
                    f"shard {shard} {arm} 推荐调用数异常："
                    f"{calls.get('recommend_single', 0)}/{planned_calls}"
                )
            if counts["users"] != persona_count or detail_rows != planned_calls:
                raise RuntimeError(
                    f"shard {shard} {arm} 原始行数异常："
                    f"users={counts['users']}/{persona_count}, "
                    f"detail={detail_rows}/{planned_calls}"
                )
            if counts["eating_logs"] != planned_calls:
                errors.append(
                    f"shard {shard} {arm}: eating_logs="
                    f"{counts['eating_logs']}/{planned_calls}（存在无候选跳过）"
                )
            arms[arm] = {
                "curve": curve,
                "calls": calls,
                "call_sites": call_sites,
                "planned_recommendations": planned_calls,
                "detail_rows": detail_rows,
                "db_counts": counts,
                "catalog": {"dishes": dish_count, "restaurants": restaurant_count},
                "db_file": str(db_path),
                "detail_file": str(detail_path),
            }
    finally:
        source.close()
        source_engine.dispose()
    return result


def _merge_shard_curves(
    shards: Sequence[Dict[str, object]], arm: str, days: int
) -> List[float]:
    """按每片人设数加权合并累计重样率，不按进程完成顺序或调用数加权。"""
    total_personas = sum(int(shard["personas"]) for shard in shards)
    if not shards or total_personas <= 0:
        raise ValueError("没有可合并的分片")
    merged: List[float] = []
    for day_index in range(days):
        weighted = 0.0
        for shard in shards:
            arms = shard["arms"]
            curve = arms[arm]["curve"]  # type: ignore[index]
            if len(curve) != days:
                raise ValueError(f"shard {shard['shard']} {arm} 曲线长度不是 {days}")
            weighted += float(curve[day_index]) * int(shard["personas"])
        merged.append(round(weighted / total_personas, 4))
    return merged


def _run_group_database(
    source: Session,
    seed: int,
    lambda_val: float,
    omega_val: float,
    personas: int,
    rooms: int,
    data_dir: Path,
) -> Tuple[Dict[str, object], Dict[str, int], List[str], Dict[str, int]]:
    _reset_calls()
    db_path = data_dir / f"sim_seed{seed}_groups.db"
    rooms_path = data_dir / f"rooms_seed{seed}.jsonl"
    engine = sim._new_engine(db_path)
    session = sessionmaker(bind=engine, future=True)()
    try:
        sim._copy_catalog(source, session)
        seeded = sim._seed_personas(session, random.Random(seed), personas)
        with rooms_path.open("w", encoding="utf-8") as room_file:
            group = sim._run_group_phase(
                session,
                seeded,
                seed,
                omega_val,
                rooms,
                room_file,
                lambda_val=lambda_val,
            )
    finally:
        session.close()
        engine.dispose()
    calls, call_sites = _call_snapshot()
    counts = _database_counts(f"sqlite:///{db_path.as_posix()}")
    if counts["users"] != personas or counts["group_rooms"] != rooms:
        raise RuntimeError(f"群组库原始计数异常：{counts}")
    if counts["room_votes"] != group["votes"]:
        raise RuntimeError("群组库投票行数与群组结果不一致")
    return group, calls, call_sites, counts


def _sum_calls(*call_dicts: Dict[str, int]) -> Dict[str, int]:
    total: Counter = Counter()
    for calls in call_dicts:
        total.update(calls)
    return dict(total)


def build_benchmark(
    seed: int = 20261024,
    lambda_val: float = 0.5,
    omega_val: float = 0.5,
    personas: int = sim.PERSONAS,
    days: int = sim.DAYS,
    rooms: int = sim.ROOMS,
    absence_rooms: int = 200,
    shard_size: int = 25,
    workers: int = 8,
    data_dir: Path = sim.SIM_DIR,
    source_database_url: str = DATABASE_URL,
) -> Dict[str, object]:
    if days < 1 or rooms < 1 or absence_rooms < 1 or workers < 1:
        raise ValueError("days、rooms、absence_rooms、workers 必须大于 0")
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    specs = _shard_specs(personas, shard_size)

    source_engine = _read_only_engine(source_database_url)
    source = sessionmaker(bind=source_engine, future=True)()
    try:
        source_counts = _database_counts(source_database_url)
        if not source_counts["dishes"]:
            raise RuntimeError("source DB 没有菜品，先完成数据桥接")

        tasks = [
            {
                **spec,
                "seed": seed,
                "days": days,
                "lambda_val": lambda_val,
                "source_database_url": source_database_url,
                "data_dir": str(data_dir),
            }
            for spec in specs
        ]
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
            shards = sorted(pool.map(_run_shard, tasks), key=lambda item: item["shard"])

        group, group_calls, group_sites, group_db_counts = _run_group_database(
            source,
            seed,
            lambda_val,
            omega_val,
            personas,
            rooms,
            data_dir,
        )

        _reset_calls()
        absence = sim.run_absence_experiment(
            source,
            seed,
            lambda_val=lambda_val,
            omega_val=omega_val,
            personas=personas,
            rooms=absence_rooms,
            data_dir=data_dir,
        )
        absence_calls, absence_sites = _call_snapshot()
        absence_db_path = data_dir / f"sim_seed{seed}_absence.db"
        absence_db_counts = _database_counts(f"sqlite:///{absence_db_path.as_posix()}")
        if absence_db_counts["users"] != personas or absence_db_counts["group_rooms"] != absence_rooms:
            raise RuntimeError(f"缺席库原始计数异常：{absence_db_counts}")
        if absence_db_counts["room_votes"] != absence["votes"]:
            raise RuntimeError("缺席库投票行数与缺席结果不一致")
        (data_dir / f"absence_seed{seed}.json").write_text(
            json.dumps(absence, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        arm_curves = {
            arm: _merge_shard_curves(shards, arm, days) for arm in ("ours", "baseline")
        }
        shard_calls = [
            shard["arms"][arm]["calls"]  # type: ignore[index]
            for shard in shards
            for arm in ("ours", "baseline")
        ]
        calls = _sum_calls(*shard_calls, group_calls, absence_calls)
        call_sites = list(
            dict.fromkeys(
                [
                    site
                    for shard in shards
                    for arm in ("ours", "baseline")
                    for site in shard["arms"][arm]["call_sites"]  # type: ignore[index]
                ]
                + group_sites
                + absence_sites
            )
        )
        errors = [error for shard in shards for error in shard["errors"]]  # type: ignore[index]
        if group_db_counts["room_votes"] != rooms * sim.MEMBERS_PER_ROOM * sim.CARDS_PER_ROOM:
            errors.append(
                f"主群组合法投票为 {group_db_counts['room_votes']}/"
                f"{rooms * sim.MEMBERS_PER_ROOM * sim.CARDS_PER_ROOM}"
            )

        planned_per_arm = personas * days * sim.MEALS_PER_DAY
        raw_counts = {
            "source": source_counts,
            "single": {
                "planned_recommendations_per_arm": planned_per_arm,
                "planned_recommendations_total": planned_per_arm * 2,
                "recommend_single_calls": calls.get("recommend_single", 0),
                "eating_logs_per_arm": {
                    arm: sum(
                        int(shard["arms"][arm]["db_counts"]["eating_logs"])  # type: ignore[index]
                        for shard in shards
                    )
                    for arm in ("ours", "baseline")
                },
                "detail_rows_per_arm": {
                    arm: sum(int(shard["arms"][arm]["detail_rows"]) for shard in shards)  # type: ignore[index]
                    for arm in ("ours", "baseline")
                },
            },
            "group": {
                "personas": group_db_counts["users"],
                "rooms": group_db_counts["group_rooms"],
                "expected_votes": rooms * sim.MEMBERS_PER_ROOM * sim.CARDS_PER_ROOM,
                "planned_votes": group["planned_votes"],
                "votes": group_db_counts["room_votes"],
            },
            "absence": {
                "personas": absence_db_counts["users"],
                "rooms": absence_db_counts["group_rooms"],
                "expected_votes_before_absence": (
                    absence_rooms * sim.MEMBERS_PER_ROOM * sim.CARDS_PER_ROOM
                ),
                "planned_votes": absence["planned_votes"],
                "votes": absence_db_counts["room_votes"],
            },
        }
        db_files = [
            str(shard["arms"][arm]["db_file"])  # type: ignore[index]
            for shard in shards
            for arm in ("ours", "baseline")
        ] + [str(data_dir / f"sim_seed{seed}_groups.db"), str(absence_db_path)]

        return {
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            "sample": {
                "personas": personas,
                "days": days,
                "meals_per_day": sim.MEALS_PER_DAY,
                "rooms": rooms,
                "members_per_room": sim.MEMBERS_PER_ROOM,
            },
            "duplication_rate_curve": {
                "days": list(range(1, sim.CURVE_DAYS + 1)),
                "ours_lambda_0.5": arm_curves["ours"][: sim.CURVE_DAYS],
                "baseline_no_decay": arm_curves["baseline"][: sim.CURVE_DAYS],
            },
            "group_satisfaction_bars": {
                "strategies": [
                    f"mixed_omega_{omega_val}",
                    "average_omega_1.0",
                    "random",
                ],
                "avg_scores": group["avg_scores"],
                "least_misery_scores": group["least_misery_scores"],
            },
            "params": {
                "seed": seed,
                "lambda_val": lambda_val,
                "omega_val": omega_val,
                "cards_per_room": sim.CARDS_PER_ROOM,
                "calls": calls,
                "call_sites": call_sites,
                "parallel": {
                    "workers": workers,
                    "shard_size": shard_size,
                    "shard_count": len(shards),
                    "seed_rule": "shard_seed = seed + zero_based_shard",
                    "source_database_url": source_database_url,
                    "source_read_only": True,
                },
                "shards": shards,
                "raw_counts": raw_counts,
                "group": group,
                "absence": {
                    "rooms": absence["rooms"],
                    "planned_votes": absence["planned_votes"],
                    "votes": absence["votes"],
                    "rooms_full_votes": absence["rooms_full_votes"],
                    "avg_scores": absence["avg_scores"],
                    "least_misery_scores": absence["least_misery_scores"],
                },
                "errors": errors,
                "db_files": db_files,
                "note": (
                    f"并行仿真实验（{personas} 虚拟用户 × {days} 天 × 每人每天 2 餐 + "
                    f"{rooms} 场四人拼单），非真实用户实验；候选、得分、共识全部由生产算法计算"
                ),
            },
        }
    finally:
        source.close()
        source_engine.dispose()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="G3 分片并行仿真（不写 source DB）")
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--lambda-val", type=float, default=0.5)
    parser.add_argument("--omega-val", type=float, default=0.5)
    parser.add_argument("--personas", type=int, default=sim.PERSONAS)
    parser.add_argument("--days", type=int, default=sim.DAYS)
    parser.add_argument("--rooms", type=int, default=sim.ROOMS)
    parser.add_argument("--absence-rooms", type=int, default=200)
    parser.add_argument("--shard-size", type=int, default=25, help="每片人设数，默认 25")
    parser.add_argument("--workers", type=int, default=8, help="ProcessPool 进程数，默认 8")
    parser.add_argument("--data-dir", type=Path, default=sim.SIM_DIR)
    parser.add_argument("--out", default="", help="benchmark JSON 存档路径")
    parser.add_argument(
        "--source-database-url",
        default=DATABASE_URL,
        help="只读目录源库；默认取 DATABASE_URL",
    )
    args = parser.parse_args(argv)

    payload = build_benchmark(
        seed=args.seed,
        lambda_val=args.lambda_val,
        omega_val=args.omega_val,
        personas=args.personas,
        days=args.days,
        rooms=args.rooms,
        absence_rooms=args.absence_rooms,
        shard_size=args.shard_size,
        workers=args.workers,
        data_dir=args.data_dir,
        source_database_url=args.source_database_url,
    )
    out_path = (
        Path(args.out)
        if args.out
        else args.data_dir / f"benchmark_parallel_seed{args.seed}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    curve = payload["duplication_rate_curve"]  # type: ignore[index]
    bars = payload["group_satisfaction_bars"]  # type: ignore[index]
    params = payload["params"]  # type: ignore[index]
    print(f"out        : {out_path}")
    print(f"shards     : {params['parallel']['shard_count']} (workers={args.workers})")
    print(f"ours last  : {curve['ours_lambda_0.5'][-1]}")
    print(f"base last  : {curve['baseline_no_decay'][-1]}")
    print(f"avg scores : {bars['avg_scores']}")
    print(f"least      : {bars['least_misery_scores']}")
    print(f"calls      : {params['calls']}")
    print(f"raw counts : {params['raw_counts']}")
    print(f"errors     : {params['errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
