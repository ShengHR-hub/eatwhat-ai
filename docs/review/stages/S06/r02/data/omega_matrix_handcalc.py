"""S06 固定投票矩阵的手算证据（不调用任何生产算法函数）。"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "omega_matrix.json"

# 构造：u1/u2 仅 spicy=1；u3/u4 仅 soup=1。
# A 仅 oily=1 -> 与四人先验都为 0；B 仅 spicy=1 -> u1/u2 先验 100，u3/u4 先验 0。
PRIOR_A = {"u1": 0.0, "u2": 0.0, "u3": 0.0, "u4": 0.0}
PRIOR_B = {"u1": 100.0, "u2": 100.0, "u3": 0.0, "u4": 0.0}
VOTES_A = {"u1": "LIKE", "u2": "LIKE", "u3": "LIKE", "u4": "LIKE"}
VOTES_B = {
    "u1": "SUPER_LIKE",
    "u2": "SUPER_LIKE",
    "u3": "PASS",
    "u4": "PASS",
}
SWIPE = {"SUPER_LIKE": 120.0, "LIKE": 100.0, "PASS": 40.0}


def individual(prior: float, vote_type: str) -> float:
    return 0.4 * prior + 0.6 * SWIPE[vote_type]


def aggregate(values: list[float], omega: float) -> dict:
    mean = sum(values) / len(values)
    least = min(values)
    return {
        "mean": round(mean, 4),
        "least": round(least, 4),
        "group_score": round(omega * mean + (1.0 - omega) * least, 4),
    }


def main() -> None:
    members = ["u1", "u2", "u3", "u4"]
    r_a = [individual(PRIOR_A[name], VOTES_A[name]) for name in members]
    r_b = [individual(PRIOR_B[name], VOTES_B[name]) for name in members]
    table = {}
    for omega in (0.0, 0.5, 1.0):
        a = aggregate(r_a, omega)
        b = aggregate(r_b, omega)
        winner = "A" if a["group_score"] >= b["group_score"] else "B"
        table[str(omega)] = {
            "A": a,
            "B": b,
            "winner": winner,
            "winner_score": max(a["group_score"], b["group_score"]),
        }
    payload = {
        "purpose": "S06 固定投票矩阵：ω 两端与中间值的独立手算，不使用生产函数",
        "formula": "R=0.4*prior+0.6*swipe; G=omega*mean(R)+(1-omega)*min(R)",
        "swipe_scores": SWIPE,
        "users": {
            "u1": "仅 spicy_level=1",
            "u2": "仅 spicy_level=1",
            "u3": "仅 soup_level=1",
            "u4": "仅 soup_level=1",
        },
        "dishes": {
            "A": "仅 oily_level=1（与四人先验均为 0）",
            "B": "仅 spicy_level=1（u1/u2 先验 100，u3/u4 先验 0）",
        },
        "votes": {"A": VOTES_A, "B": VOTES_B},
        "R": {"A": r_a, "B": r_b},
        "table": table,
        "veto_case": "任一成员对候选投 VETO -> Mask=0，G=0；全员 VETO -> winner=None, has_consensus=False",
        "test": "backend/tests/test_s06_room_contract.py::test_fixed_omega_matrix_room_level",
        "ok": table["0.0"]["winner"] == "A"
        and table["0.5"]["winner"] == "A"
        and table["1.0"]["winner"] == "B"
        and table["0.0"]["B"]["group_score"] == 24.0
        and table["0.5"]["B"]["group_score"] == 46.0
        and table["1.0"]["B"]["group_score"] == 68.0
        and table["0.0"]["A"]["group_score"] == 60.0
        and table["1.0"]["A"]["group_score"] == 60.0,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
