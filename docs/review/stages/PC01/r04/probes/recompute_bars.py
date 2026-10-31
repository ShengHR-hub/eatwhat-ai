"""R3-03 快速复算：用已归档的 40,000 票 groups DB，按新口径重算三策略柱值。

单人不变量（曲线）不受 `_four_member_metrics` 影响；本脚本只重算群组实验，
用于和全量 r04 输出交叉核对。只读打开归档库，不写演示库。

输出：docs/review/stages/PC01/r04/data/bars_recomputed.json
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.algorithms.group_recommender import compute_group_consensus
from backend.algorithms.simulate_personas import _four_member_metrics

PACK = Path(__file__).resolve().parents[1]
OLD = ROOT / "docs" / "review" / "simulation"


def _json_col(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return json.loads(value)


def recompute(groups_db: Path, seed: int, omega: float) -> dict:
    engine = create_engine(
        f"sqlite:///file:{groups_db.as_posix()}?mode=ro&uri=true",
        future=True,
    )
    Session = sessionmaker(bind=engine, future=True)
    db = Session()
    stats = {
        "mixed": {"mean": 0.0, "least": 0.0, "n": 0},
        "average": {"mean": 0.0, "least": 0.0, "n": 0},
        "random": {"mean": 0.0, "least": 0.0, "n": 0},
    }
    random_stream = random.Random(seed + 1)
    rooms = db.execute(
        text(
            "select room_code, member_user_ids, candidate_dish_ids, algo_params "
            "from group_rooms order by room_code"
        )
    ).all()
    for room_code, members_raw, cards_raw, params_raw in rooms:
        members = _json_col(members_raw)
        cards = _json_col(cards_raw)
        params = json.loads(params_raw) if isinstance(params_raw, str) else (params_raw or {})
        room_omega = float(params.get("omega_group", omega))
        votes = [
            {"user_id": int(uid), "dish_id": int(did), "vote_type": str(vt)}
            for uid, did, vt in db.execute(
                text(
                    "select user_id, dish_id, vote_type from room_votes "
                    "where room_code=:code"
                ),
                {"code": room_code},
            ).all()
        ]
        reports = {}
        for name, value in (("mixed", room_omega), ("average", 1.0)):
            report = compute_group_consensus(db, members, cards, votes, omega_group=value)
            detail = _four_member_metrics(report, report["winner_dish_id"])
            if detail is None:
                detail = (0.0, 0.0)
            stats[name]["mean"] += detail[0]
            stats[name]["least"] += detail[1]
            stats[name]["n"] += 1
            reports[name] = report
        chosen = random_stream.choice(cards)
        detail = _four_member_metrics(reports["mixed"], chosen) or (0.0, 0.0)
        stats["random"]["mean"] += detail[0]
        stats["random"]["least"] += detail[1]
        stats["random"]["n"] += 1
    db.close()
    engine.dispose()
    for item in stats.values():
        item["mean"] = round(item["mean"] / item["n"], 2)
        item["least"] = round(item["least"] / item["n"], 2)
    return {
        "groups_db": str(groups_db),
        "seed": seed,
        "rooms": len(rooms),
        "avg_scores": [stats["mixed"]["mean"], stats["average"]["mean"], stats["random"]["mean"]],
        "least_misery_scores": [
            stats["mixed"]["least"],
            stats["average"]["least"],
            stats["random"]["least"],
        ],
    }


def main() -> int:
    results = {
        "seed20261024": recompute(
            OLD / "sim_seed20261024_groups.db", 20261024, 0.5
        ),
        "seed7": recompute(OLD / "sim_seed7_groups.db", 7, 0.6),
    }
    out = PACK / "data" / "bars_recomputed.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
