"""R3-03 固定样本：独立复算四人满意度，锁定“原始 R、聚合后封顶”口径。

不修改演示库：在内存 SQLite 里播种演示角色/菜品，调用生产共识取报告，
期望值由本脚本按 `0.4*prior + 0.6*swipe` 逐人重算，不使用被测 helper。

输出：docs/review/stages/PC01/r04/data/fixed_samples.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.algorithms.group_recommender import (
    PRIOR_WEIGHT,
    SWIPE_WEIGHT,
    TIMEOUT_SWIPE_SCORE,
    VOTE_SCORES,
    compute_group_consensus,
    member_prior_scores,
)
from backend.algorithms.simulate_personas import _four_member_metrics
from backend.models import Base, Dish, User
from backend.scripts.init_seed_data import load_benchmark, seed_all

PACK = Path(__file__).resolve().parents[1]
MEMBERS = [1, 2, 3, 4]
CASES = {
    "no_veto": {1: "SUPER_LIKE", 2: "LIKE", 3: "PASS", 4: "PASS"},
    "single_veto": {1: "SUPER_LIKE", 2: "LIKE", 3: "VETO", 4: "PASS"},
    "multi_veto": {1: "VETO", 2: "LIKE", 3: "VETO", 4: "PASS"},
    "all_veto": {1: "VETO", 2: "VETO", 3: "VETO", 4: "VETO"},
    "one_absent": {1: "SUPER_LIKE", 2: None, 3: "PASS", 4: "PASS"},
}
R_GT_100 = [0.0, 67.58, 97.82, 107.70]


def _reference(
    members: Sequence[int],
    dish_id: int,
    votes: Dict[int, Optional[str]],
    priors: Dict[int, Dict[int, float]],
):
    """独立算：VETO=0；缺席=TIMEOUT；个体 R 原始值；聚合后 min(100, ·)。"""
    values: List[float] = []
    for uid in members:
        vote = votes.get(uid)
        if vote == "VETO":
            values.append(0.0)
            continue
        swipe = VOTE_SCORES.get(vote, TIMEOUT_SWIPE_SCORE) if vote else TIMEOUT_SWIPE_SCORE
        prior = priors.get(uid, {}).get(dish_id, 0.0)
        values.append(PRIOR_WEIGHT * prior + SWIPE_WEIGHT * swipe)
    mean_value = min(100.0, sum(values) / len(values))
    least_value = min(100.0, min(values))
    return round(mean_value, 2), round(least_value, 2)


def main() -> int:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        seed_all(db, benchmark=load_benchmark())
        users = [u.id for u in db.query(User).order_by(User.id).limit(4).all()]
        dishes = [
            d.id
            for d in db.query(Dish)
            .filter(Dish.mode_type == "OUT_DINING")
            .order_by(Dish.id)
            .limit(2)
            .all()
        ]
        assert users == MEMBERS, users
        assert len(dishes) == 2, dishes
        target = dishes[1]
        priors = member_prior_scores(db, MEMBERS, [target])

        results = []
        for name, votes in CASES.items():
            rows = [
                {"user_id": uid, "dish_id": target, "vote_type": vote}
                for uid, vote in votes.items()
                if vote is not None
            ]
            report = compute_group_consensus(db, MEMBERS, [target], rows, 0.5)
            got = _four_member_metrics(report, target)
            expected = _reference(MEMBERS, target, votes, priors)
            match = (
                got is not None
                and abs(got[0] - expected[0]) <= 0.02
                and abs(got[1] - expected[1]) <= 0.02
            )
            results.append(
                {
                    "case": name,
                    "dish_id": target,
                    "votes": {str(k): v for k, v in votes.items()},
                    "got": list(got) if got else None,
                    "expected_raw_r_aggregate_cap": list(expected),
                    "match_tolerance": 0.02,
                    "match": match,
                }
            )

        report = {
            "dish_id": 0,
            "members": [{"satisfaction": value} for value in R_GT_100],
        }
        got = _four_member_metrics(
            {"dishes": [{"dish_id": 0, "members": report["members"]}]}, 0
        )
        per_person_cap = round(sum(min(100.0, v) for v in R_GT_100) / 4, 2)
        fixed = {
            "values": R_GT_100,
            "got": list(got) if got else None,
            "expected_raw_mean_then_cap": [round(sum(R_GT_100) / 4, 2), 0.0],
            "per_person_cap_counterexample": [per_person_cap, 0.0],
        }

        payload = {
            "definition": {
                "individual_R": "0.4*prior + 0.6*swipe（原始值，不逐人封顶）",
                "veto": 0.0,
                "absence": f"TIMEOUT swipe={TIMEOUT_SWIPE_SCORE}",
                "aggregation": "四人平均/最小值算完后统一 min(100, ·)",
            },
            "cases": results,
            "r_gt_100_fixed_sample": fixed,
        }
        out = PACK / "data" / "fixed_samples.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        all_match = all(item["match"] for item in results)
        r_ok = (
            got is not None
            and abs(got[0] - 68.275) <= 0.01
            and got[1] == 0.0
            and abs(per_person_cap - 66.35) <= 0.01
        )
        return 0 if all_match and r_ok else 1
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
