"""多智能体仿真实验生成器（规格第七章第 3 条）—— R02 返工版。

为什么有这个文件：`algo_configs.benchmark_json` 原先是手写预置曲线，批次 4 要把它
送进实验大屏、论文第五章也会按它出图。手写曲线一旦进论文，证据口径就站不住。

**R02 返工（2026-10-24 复审判 FAIL）改了什么**

第一版是"另写一套算法再假装是实验"：自算四维余弦、自算衰减、自造满意度，
对生产代码 `recommend_single / compute_decay_weights / shortlist_candidates /
compute_group_consensus` 的调用次数是 **0**。复审用一条"昨天吃过该菜"的隔离数据
证明了语义分叉：线上衰减 0.3935、第一版仿真 0.298009。

这一版改成**真调生产算法**：
- 实验一的每一餐都由 `single_recommender.recommend_single()` 出候选与得分，
  衰减由 `time_decay.compute_decay_weights()` 在真实 `eating_logs` 上算；
- 实验二每一场都由 `group_recommender.shortlist_candidates()` 出 10 张卡、
  `member_prior_scores()` 出先验、`compute_group_consensus()` 出胜者；
- 三种策略（混合 / 纯均值 / 随机）**冻结同一场景**后再比较，不重新抽成员与候选；
- 投票按 1,000 场 × 4 人 × 10 张卡生成并落库（`group_rooms` / `room_votes`），可查；
- 所有生产函数调用都过 `CALLS` 计数器，报告里要贴出计数。

**基线组的定义**（写进论文也要这么讲）
"无衰减"基线不是"换一套公式"，而是"推荐器看不见历史"：同一个生产函数、
同样的库与数据，只把查询时钟推到 `LOOKBACK_DAYS + 1` 天之后，于是 14 天窗口内
没有任何历史 → `decay_weights` 全为 1.0。这也是生产代码在"新用户冷启动"时的
真实行为，不是特例分支。

**隔离**
不写演示库。两臂各自建独立 SQLite（`docs/review/simulation/sim_seed<seed>_<arm>.db`），
菜品/门店从演示库只读复制，人设由本脚本生成。

复现：
    python -m backend.algorithms.simulate_personas --seed 20261024 --write
    python -m backend.algorithms.simulate_personas --seed 7 --lambda-val 0.8

复验时用 `--data-dir <新目录>` 把隔离库/明细写到新位置，避免覆盖已归档证据；
`--out` 指定 benchmark JSON，默认随 `--data-dir` 落盘。
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..database import Base, SessionLocal
from ..models import (
    AlgoConfig,
    Dish,
    EatingLog,
    GroupRoom,
    Restaurant,
    RoomVote,
    User,
    UserPreference,
)
from .group_recommender import (
    compute_group_consensus,
    member_prior_scores,
    shortlist_candidates,
)
from .single_recommender import recommend_single
from .time_decay import LOOKBACK_DAYS
from .vector_spec import FEATURE_KEYS

# 规格第七章：样本口径写死，改任何一项都要同步改论文与 SSOT
PERSONAS = 200
DAYS = 60
MEALS_PER_DAY = 2
ROOMS = 1000
MEMBERS_PER_ROOM = 4
CARDS_PER_ROOM = 10
CURVE_DAYS = 14

SIM_DIR = Path("docs/review/simulation")
# 仿真的"第 0 天 08:00"，取一个过去时间点，方便和真实 eating_logs 区分
SIM_START = datetime(2026, 6, 1, 8, 0, 0)
WEATHER_TEMP = 22.0
WEATHER_TEXT = "晴"
# 主规模实验要求 40,000 张**真实合法**投票，所以缺席率在主线里是 0；
# 超时/缺席作为独立实验另跑（run_absence_experiment），不混进柱图（R2-03）。
TIMEOUT_RATE = 0.0
ABSENCE_RATE = 0.05  # 只给缺席实验用
VETO_RATE = 0.04  # 主动否决（与忌口无关，是"我不想吃"）

# 生产函数的调用计数：复审要求"拿计数证明真的调了生产代码"
CALLS: Counter = Counter()
CALL_SITES: List[str] = []


def _call(name: str, site: str, fn, *args, **kwargs):
    CALLS[name] += 1
    if site not in CALL_SITES:
        CALL_SITES.append(site)
    return fn(*args, **kwargs)


# --------------------------------------------------------------------------
# 隔离库
# --------------------------------------------------------------------------


def _new_engine(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    engine = create_engine(f"sqlite:///{path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    return engine


def _copy_catalog(src: Session, dst: Session) -> Tuple[int, int]:
    """把演示库的菜品与门店只读复制进隔离库（含 image_url 与特征向量）。"""
    restaurants = src.query(Restaurant).all()
    for row in restaurants:
        dst.add(
            Restaurant(
                id=row.id,
                name=row.name,
                source_type=row.source_type,
                category=row.category,
                avg_price=row.avg_price,
                rating=row.rating,
                longitude=row.longitude,
                latitude=row.latitude,
                distance_meters=row.distance_meters,
                address=row.address,
            )
        )
    dishes = src.query(Dish).all()
    for row in dishes:
        dst.add(
            Dish(
                id=row.id,
                name=row.name,
                mode_type=row.mode_type,
                restaurant_id=row.restaurant_id,
                cuisine_type=row.cuisine_type,
                dish_role=row.dish_role,
                price_or_cost=row.price_or_cost,
                cook_minutes=row.cook_minutes,
                appliance_tag=list(row.appliance_tag or []),
                ingredients_main=list(row.ingredients_main or []),
                ingredients_aux=list(row.ingredients_aux or []),
                recipe_steps=row.recipe_steps or "",
                feature_vector=dict(row.feature_vector or {}),
                image_url=row.image_url or "",
            )
        )
    dst.commit()
    return len(dishes), len(restaurants)


def _seed_personas(
    session: Session,
    rng: random.Random,
    count: int,
    start_index: int = 1,
) -> List[Dict[str, object]]:
    personas: List[Dict[str, object]] = []
    veto_pool = ("海鲜", "香菜", "花生", "内脏", "牛奶")
    for index in range(start_index, start_index + count):
        vector = {key: round(rng.uniform(0.05, 0.95), 3) for key in FEATURE_KEYS}
        budget = round(rng.uniform(12.0, 45.0), 1)
        veto = [rng.choice(veto_pool)] if rng.random() < 0.10 else []
        user = User(
            username=f"sim_p{index:03d}",
            nickname=f"仿真人设{index:03d}",
            avatar="",
            persona_title="仿真人设",
            is_demo_persona=True,
        )
        session.add(user)
        session.flush()
        session.add(
            UserPreference(
                user_id=user.id,
                base_vector=vector,
                default_budget=budget,
                veto_tags=veto,
                preferred_cuisines=[],
                favorite_dish_ids=[],
                blacklist_dish_ids=[],
                blacklist_restaurant_ids=[],
            )
        )
        personas.append({"user_id": user.id, "budget": budget, "vector": vector, "veto": veto})
    session.commit()
    return personas


# --------------------------------------------------------------------------
# 实验一：单人防腻（真调 recommend_single）
# --------------------------------------------------------------------------


def _weighted_pick(rng: random.Random, recs: Sequence[Dict[str, object]]) -> Dict[str, object]:
    """按 `total_score^3` 加权抽一个：得分高的更可能被吃，但不是必然。"""
    weights = [max(float(item["total_score"]), 0.0) ** 3 + 1e-6 for item in recs]
    threshold = rng.random() * sum(weights)
    cursor = 0.0
    for item, weight in zip(recs, weights):
        cursor += weight
        if cursor >= threshold:
            return item
    return recs[-1]


def _run_agent_arm(
    session: Session,
    personas: Sequence[Dict[str, object]],
    arm: str,
    seed: int,
    lambda_val: float,
    clock_shift_days: int,
    day_count: int,
    detail_file,
) -> List[float]:
    """跑 `personas × days × 2` 的决策流水，返回「按天累计的菜系重样率」。"""
    rng = random.Random(seed)
    last_cuisine: Dict[int, Optional[str]] = {int(p["user_id"]): None for p in personas}
    dup_total = 0
    meals_total = 0
    daily: List[float] = []

    for day in range(day_count):
        for meal in range(MEALS_PER_DAY):
            eaten_at = SIM_START + timedelta(days=day, hours=meal * 6)
            query_at = eaten_at + timedelta(days=clock_shift_days)
            for persona in personas:
                user_id = int(persona["user_id"])
                mode_type = "OUT_DINING" if (user_id + meal) % 2 == 0 else "HOME_COOKING"
                result = _call(
                    "recommend_single",
                    "backend/algorithms/simulate_personas.py::_run_agent_arm",
                    recommend_single,
                    session,
                    user_id,
                    mode_type,
                    budget=float(persona["budget"]),
                    weather_temp=WEATHER_TEMP,
                    weather_text=WEATHER_TEXT,
                    limit=10,
                    override_params={"lambda_decay": lambda_val},
                    now=query_at,
                )
                recs = result["recommendations"]
                if not recs:
                    detail_file.write(
                        json.dumps(
                            {
                                "arm": arm,
                                "day": day + 1,
                                "meal": meal + 1,
                                "user_id": user_id,
                                "mode_type": mode_type,
                                "skipped": "no_candidate",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    continue

                picked = _weighted_pick(rng, recs)
                previous = last_cuisine[user_id]
                duplicated = bool(previous) and previous == picked["cuisine_type"]
                if duplicated:
                    dup_total += 1
                last_cuisine[user_id] = picked["cuisine_type"]
                meals_total += 1

                session.add(
                    EatingLog(
                        user_id=user_id,
                        dish_id=int(picked["dish_id"]),
                        mode_type=mode_type,
                        cost_amount=float(picked["price"]),
                        weather_snapshot=f"{WEATHER_TEMP:.0f}°C {WEATHER_TEXT}",
                        status_bubbles=[],
                        eaten_at=eaten_at,
                    )
                )

                detail_file.write(
                    json.dumps(
                        {
                            "arm": arm,
                            "day": day + 1,
                            "meal": meal + 1,
                            "user_id": user_id,
                            "mode_type": mode_type,
                            "dish_id": int(picked["dish_id"]),
                            "dish_name": picked["name"],
                            "cuisine_type": picked["cuisine_type"],
                            "total_score": picked["total_score"],
                            "decay_weight": picked["decay_weight"],
                            "duplicated": duplicated,
                            "candidate_count": len(recs),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            # 每餐提交：既让 decay 立刻看到新流水，也避免长事务
            session.commit()
        daily.append(round(dup_total / meals_total, 4) if meals_total else 0.0)
    return daily


# --------------------------------------------------------------------------
# 实验二：群组博弈（真调 shortlist / prior / consensus）
# --------------------------------------------------------------------------


def _vote_bands_for_member(
    rng: random.Random,
    dish_ids: Sequence[int],
    prior_of_member: Dict[int, float],
) -> Dict[int, str]:
    """按「这个人面对这 10 张卡的相对偏好」给票，而不是绝对分阈值。

    为什么不用绝对阈值：先验分普遍在 80 以上，绝对阈值会把 88% 的票压成
    SUPER_LIKE / LIKE，三策略的满意度一起贴在 100 上（实测 99.93 vs 99.95），
    策略差异被天花板吃掉，柱子失去含义。真人面对 10 张卡时一定是**横向比较**的：
    总有两张最想吃、两三张随便、末尾几张要么跳过要么否决。

    规则（10 张卡时）：排名 1–2 → SUPER_LIKE；3–5 → LIKE；6–8 → PASS；
    9–10 → 各 50% 概率 VETO，否则 PASS。先验上加 N(0, 6) 扰动，
    避免同一份先验的人投出一模一样的票。票型仍是生产侧的四个合法枚举。
    """
    noisy = {
        int(dish_id): float(prior_of_member.get(int(dish_id), 0.0)) + rng.gauss(0.0, 6.0)
        for dish_id in dish_ids
    }
    ranked = sorted(noisy, key=lambda dish_id: -noisy[dish_id])
    bands: Dict[int, str] = {}
    total = len(ranked)
    for pos, dish_id in enumerate(ranked):
        if pos < 2:
            bands[dish_id] = "SUPER_LIKE"
        elif pos < min(5, total):
            bands[dish_id] = "LIKE"
        elif pos < min(8, total):
            bands[dish_id] = "PASS"
        else:
            bands[dish_id] = "VETO" if rng.random() < 0.5 else "PASS"
    return bands


def _four_member_metrics(
    report: Dict[str, object], dish_id: Optional[int]
) -> Optional[Tuple[float, float]]:
    """取某道菜在**全体成员**上的（平均满意度, 最差满意度）。

    口径（r04 锁定，R3-03）：
    - 个体 R 直接取生产报告里的原始值（SSOT 算法 3：`0.4*prior + 0.6*swipe`），
      **不在个体层面封顶**；r03 的“逐人先 `min(100, R)` 再聚合”已撤销。
    - 生产共识把 VETO 成员排除在 `satisfaction_values` 之外（它用 mask 把
      `group_score` 置 0）。柱图问的是"这桌人吃得有多满意"，否决者恰恰是最不
      满意的那位；这里从 `report["dishes"][i]["members"]` 逐个取分，4 个成员
      一个都不能少，VETO 的 0 分和缺席的 TIMEOUT 换算分都计入。
    - 柱图属于展示统计：在四人聚合之后统一 `min(100, ·)`，与 r02 一致；
      这个封顶不写回生产公式，也不改变排序用的原始分。
    """
    if dish_id is None:
        return None
    for item in report["dishes"]:  # type: ignore[index]
        if int(item["dish_id"]) != int(dish_id):
            continue
        values = [
            float(member["satisfaction"])
            for member in item["members"]  # type: ignore[index]
        ]
        if not values:
            return None
        mean_value = min(100.0, sum(values) / len(values))
        return (round(mean_value, 2), round(min(100.0, min(values)), 2))
    return None


def _run_group_phase(
    session: Session,
    personas: Sequence[Dict[str, object]],
    seed: int,
    omega_val: float,
    room_count: int,
    detail_file,
    lambda_val: float = 0.5,
    absence_rate: float = 0.0,
) -> Dict[str, object]:
    rng = random.Random(seed)
    random_stream = random.Random(seed + 1)  # 随机策略用独立随机流（CLR-03）
    member_ids_all = [int(p["user_id"]) for p in personas]
    stats: Dict[str, Dict[str, float]] = {
        "mixed": {"mean": 0.0, "least": 0.0, "n": 0.0},
        "average": {"mean": 0.0, "least": 0.0, "n": 0.0},
        "random": {"mean": 0.0, "least": 0.0, "n": 0.0},
    }
    shortfall_rooms = 0
    empty_rooms = 0
    no_consensus = 0
    votes_total = 0
    planned_votes = 0
    rooms_full_votes = 0
    bad_rooms: List[str] = []

    for index in range(room_count):
        members = rng.sample(member_ids_all, MEMBERS_PER_ROOM)
        mode_type = "OUT_DINING" if rng.random() < 0.5 else "HOME_COOKING"
        candidates = _call(
            "shortlist_candidates",
            "backend/algorithms/simulate_personas.py::_run_group_phase",
            shortlist_candidates,
            session,
            members,
            mode_type,
            top_n=CARDS_PER_ROOM,
        )
        if len(candidates) < CARDS_PER_ROOM:
            shortfall_rooms += 1
        if not candidates:
            empty_rooms += 1
            continue
        card_ids = [int(item["dish_id"]) for item in candidates]
        priors = _call(
            "member_prior_scores",
            "backend/algorithms/simulate_personas.py::_run_group_phase",
            member_prior_scores,
            session,
            members,
            card_ids,
        )

        votes: List[Dict[str, object]] = []
        for user_id in members:
            prior_of_member = {
                int(dish_id): float(score)
                for dish_id, score in (priors.get(user_id) or {}).items()
            }
            bands = _vote_bands_for_member(rng, card_ids, prior_of_member)
            for dish_id in card_ids:
                planned_votes += 1
                if absence_rate and rng.random() < absence_rate:
                    continue  # 缺席实验：没表态，结算时按 TIMEOUT 计票
                votes.append(
                    {
                        "user_id": user_id,
                        "dish_id": dish_id,
                        "vote_type": bands[int(dish_id)],
                    }
                )

        room_code = f"{index + 1:06d}"
        room = GroupRoom(
            room_code=room_code,
            host_user_id=members[0],
            mode_type=mode_type,
            status="FINISHED",
            member_user_ids=list(members),
            candidate_dish_ids=list(card_ids),
            budget=None,
            algo_params={"omega_group": omega_val, "lambda_val": lambda_val},
            created_at=SIM_START,
            deadline_at=SIM_START + timedelta(seconds=15),
        )
        session.add(room)
        for vote in votes:
            session.add(
                RoomVote(
                    room_code=room_code,
                    user_id=int(vote["user_id"]),
                    dish_id=int(vote["dish_id"]),
                    vote_type=str(vote["vote_type"]),
                    voted_at=SIM_START,
                )
            )
        votes_total += len(votes)
        expected = len(members) * CARDS_PER_ROOM
        keys = {(int(v["user_id"]), int(v["dish_id"])) for v in votes}
        if len(votes) == expected and len(keys) == expected:
            rooms_full_votes += 1
        else:
            bad_rooms.append(f"{room_code}:{len(votes)}/{expected},uniq={len(keys)}")

        reports_so_far: Dict[str, Dict[str, object]] = {}
        for name, omega in (("mixed", omega_val), ("average", 1.0)):
            report = _call(
                "compute_group_consensus",
                "backend/algorithms/simulate_personas.py::_run_group_phase",
                compute_group_consensus,
                session,
                members,
                card_ids,
                votes,
                omega_group=omega,
            )
            detail = _four_member_metrics(report, report["winner_dish_id"])
            if detail is None:
                if name == "mixed":
                    no_consensus += 1
                mean_value, least_value = 0.0, 0.0
            else:
                mean_value, least_value = detail
            stats[name]["mean"] += mean_value
            stats[name]["least"] += least_value
            stats[name]["n"] += 1
            reports_so_far[name] = report
            if name == "mixed":
                room.winner_dish_id = report["winner_dish_id"]
                room.consensus_report = report

        # 随机抽签：用独立随机流抽一张卡，再在同一份共识报告上取四人指标。
        # 抽到被否决的菜时，否决成员的 0 分会照常进入平均与最低值（R2-02）。
        chosen = random_stream.choice(card_ids)
        detail = _four_member_metrics(reports_so_far["mixed"], chosen)
        if detail is None:
            mean_value, least_value = 0.0, 0.0
        else:
            mean_value, least_value = detail
        stats["random"]["mean"] += mean_value
        stats["random"]["least"] += least_value
        stats["random"]["n"] += 1

        session.commit()
        detail_file.write(
            json.dumps(
                {
                    "room": room_code,
                    "mode_type": mode_type,
                    "members": members,
                    "cards": card_ids,
                    "votes": len(votes),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    def _avg(name: str, key: str) -> float:
        n = stats[name]["n"] or 1.0
        return round(stats[name][key] / n, 2)

    return {
        "avg_scores": [_avg("mixed", "mean"), _avg("average", "mean"), _avg("random", "mean")],
        "least_misery_scores": [
            _avg("mixed", "least"),
            _avg("average", "least"),
            _avg("random", "least"),
        ],
        "rooms": room_count,
        "shortfall_rooms": shortfall_rooms,
        "empty_rooms": empty_rooms,
        "no_consensus_rooms": no_consensus,
        "planned_votes": planned_votes,
        "votes": votes_total,
        "rooms_full_votes": rooms_full_votes,
        "bad_rooms": bad_rooms[:10],
    }


# --------------------------------------------------------------------------
# 组装
# --------------------------------------------------------------------------


def run_absence_experiment(
    src: Session,
    seed: int,
    lambda_val: float = 0.5,
    omega_val: float = 0.5,
    personas: int = PERSONAS,
    rooms: int = 200,
    data_dir: Path = SIM_DIR,
) -> Dict[str, object]:
    """缺席实验：故意让一部分人 5% 不投票，看共识与满意度怎么被拉低。

    单独一套库（`sim_seed<seed>_absence.db`）与单独文件（`absence_seed<seed>.json`），
    **不进 benchmark_json**——主规模的 40,000 票必须是满票，缺席是另一个问题（R2-03）。
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = _new_engine(data_dir / f"sim_seed{seed}_absence.db")
    SessionFactory = sessionmaker(bind=engine, future=True)
    sim_session = SessionFactory()
    try:
        _copy_catalog(src, sim_session)
        persona_rng = random.Random(seed)
        seeded = _seed_personas(sim_session, persona_rng, personas)
        detail_path = data_dir / f"absence_rooms_seed{seed}.jsonl"
        if detail_path.exists():
            detail_path.unlink()
        with detail_path.open("a", encoding="utf-8") as room_file:
            result = _run_group_phase(
                sim_session,
                seeded,
                seed + 7,
                omega_val,
                rooms,
                room_file,
                lambda_val=lambda_val,
                absence_rate=ABSENCE_RATE,
            )
    finally:
        sim_session.close()
        engine.dispose()
    return {
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "seed": seed,
        "absence_rate": ABSENCE_RATE,
        "rooms": rooms,
        "planned_votes": result["planned_votes"],
        "votes": result["votes"],
        "rooms_full_votes": result["rooms_full_votes"],
        "avg_scores": result["avg_scores"],
        "least_misery_scores": result["least_misery_scores"],
        "note": "缺席实验：与主规模同参数，仅额外注入 5% 不投票；不进 benchmark_json",
    }


def build_benchmark(
    seed: int = 20261024,
    lambda_val: float = 0.5,
    omega_val: float = 0.5,
    personas: int = PERSONAS,
    days: int = DAYS,
    rooms: int = ROOMS,
    data_dir: Path = SIM_DIR,
) -> Dict[str, object]:
    data_dir.mkdir(parents=True, exist_ok=True)
    detail_path = data_dir / f"detail_seed{seed}.jsonl"
    if detail_path.exists():
        detail_path.unlink()

    src = SessionLocal()
    try:
        if not src.query(Dish).count():
            raise RuntimeError("演示库里没有菜品，先跑 init_seed_data")

        errors: List[str] = []
        arm_curves: Dict[str, List[float]] = {}

        # 两臂各自一个隔离库：人设与随机种子相同，只差"看不看得见历史"
        for arm, clock_shift in (("ours", 0), ("baseline", LOOKBACK_DAYS + 1)):
            db_path = data_dir / f"sim_seed{seed}_{arm}.db"
            engine = _new_engine(db_path)
            SessionFactory = sessionmaker(bind=engine, future=True)
            sim_session = SessionFactory()
            try:
                dish_count, restaurant_count = _copy_catalog(src, sim_session)
                persona_rng = random.Random(seed)
                seeded = _seed_personas(sim_session, persona_rng, personas)
                with detail_path.open("a", encoding="utf-8") as detail_file:
                    daily = _run_agent_arm(
                        sim_session,
                        seeded,
                        arm,
                        seed,
                        lambda_val,
                        clock_shift,
                        days,
                        detail_file,
                    )
                arm_curves[arm] = daily
                if dish_count == 0 or restaurant_count == 0:
                    errors.append(f"{arm}: 目录为空")
            finally:
                sim_session.close()
                engine.dispose()

        # 群组实验在独立库里跑，投票落库可查
        engine = _new_engine(data_dir / f"sim_seed{seed}_groups.db")
        SessionFactory = sessionmaker(bind=engine, future=True)
        sim_session = SessionFactory()
        try:
            _copy_catalog(src, sim_session)
            persona_rng = random.Random(seed)
            seeded = _seed_personas(sim_session, persona_rng, personas)
            rooms_path = data_dir / f"rooms_seed{seed}.jsonl"
            if rooms_path.exists():
                rooms_path.unlink()
            with rooms_path.open("a", encoding="utf-8") as room_file:
                group = _run_group_phase(
                    sim_session,
                    seeded,
                    seed,
                    omega_val,
                    rooms,
                    room_file,
                    lambda_val=lambda_val,
                )
        finally:
            sim_session.close()
            engine.dispose()

        absence = run_absence_experiment(
            src,
            seed,
            lambda_val=lambda_val,
            omega_val=omega_val,
            personas=personas,
            data_dir=data_dir,
        )
        (data_dir / f"absence_seed{seed}.json").write_text(
            json.dumps(absence, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        curve = {
            "days": list(range(1, CURVE_DAYS + 1)),
            "ours_lambda_0.5": [round(v, 4) for v in arm_curves["ours"][:CURVE_DAYS]],
            "baseline_no_decay": [
                round(v, 4) for v in arm_curves["baseline"][:CURVE_DAYS]
            ],
        }
        return {
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            "sample": {
                "personas": personas,
                "days": days,
                "meals_per_day": MEALS_PER_DAY,
                "rooms": rooms,
                "members_per_room": MEMBERS_PER_ROOM,
            },
            "duplication_rate_curve": curve,
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
                "cards_per_room": CARDS_PER_ROOM,
                "calls": dict(CALLS),
                "call_sites": list(CALL_SITES),
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
                "db_files": [
                    str(data_dir / f"sim_seed{seed}_ours.db"),
                    str(data_dir / f"sim_seed{seed}_baseline.db"),
                    str(data_dir / f"sim_seed{seed}_groups.db"),
                ],
                "note": (
                    "仿真实验（200 虚拟用户 × 60 天 × 每人每天 2 餐 + 1000 场四人拼单），"
                    "非真实用户实验；候选、得分、共识全部由生产算法计算"
                ),
            },
        }
    finally:
        src.close()


def write_benchmark(payload: Dict[str, object]) -> None:
    """写回 algo_configs.benchmark_json（只写 SSOT 锁定的四个键）。"""
    stored = {k: v for k, v in payload.items() if k != "params"}
    session = SessionLocal()
    try:
        config = (
            session.query(AlgoConfig)
            .filter(AlgoConfig.config_name == "default_production")
            .first()
        )
        if config is None:
            config = AlgoConfig(config_name="default_production")
            session.add(config)
        config.benchmark_json = stored
        session.commit()
    finally:
        session.close()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="200 人 × 60 天 × 1000 场群组博弈仿真")
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--lambda-val", type=float, default=0.5)
    parser.add_argument("--omega-val", type=float, default=0.5)
    parser.add_argument("--personas", type=int, default=PERSONAS)
    parser.add_argument("--days", type=int, default=DAYS)
    parser.add_argument("--rooms", type=int, default=ROOMS)
    parser.add_argument("--write", action="store_true", help="写回 algo_configs")
    parser.add_argument("--out", default="", help="存档路径")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=SIM_DIR,
        help="隔离库与明细的输出目录（默认 docs/review/simulation；复验时指向新目录，勿覆盖旧证据）",
    )
    args = parser.parse_args(argv)

    payload = build_benchmark(
        args.seed,
        args.lambda_val,
        args.omega_val,
        personas=args.personas,
        days=args.days,
        rooms=args.rooms,
        data_dir=args.data_dir,
    )

    out_path = (
        Path(args.out)
        if args.out
        else args.data_dir / f"benchmark_seed{args.seed}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write:
        write_benchmark(payload)

    curve = payload["duplication_rate_curve"]  # type: ignore[index]
    bars = payload["group_satisfaction_bars"]  # type: ignore[index]
    params = payload["params"]  # type: ignore[index]
    print(f"out        : {out_path}")
    print(f"written    : {bool(args.write)}")
    print(f"ours d14   : {curve['ours_lambda_0.5'][-1]}")
    print(f"base d14   : {curve['baseline_no_decay'][-1]}")
    print(f"avg scores : {bars['avg_scores']}")
    print(f"least      : {bars['least_misery_scores']}")
    print(f"calls      : {params['calls']}")
    print(f"group      : {params['group']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
