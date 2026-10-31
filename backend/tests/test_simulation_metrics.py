"""R2-02 / R3-03 回归：柱图指标在「全体四人」上取平均与最低。

返工前 `_satisfaction_of()` 直接取生产报告里的 `mean_satisfaction / least_misery`，
而生产共识把 VETO 成员的 0 分排除在 `satisfaction_values` 之外（它用 mask 把
group_score 置 0，本不需要那个均值）。柱图问的是"这桌人吃得有多满意"，
否决者恰恰是最不满意的那位——把他排除会同时抬高平均值、抬走最低值。

R3-03 锁定统计口径：个体 R 用原始值，**不在个体层面封顶**；VETO 的 0 分与
缺席的 TIMEOUT 分都进入四人分母；柱图是展示统计，四人聚合后统一 `min(100, ·)`。
`test_fixed_sample_above_100_*` 用含 R>100 的固定样本把这条边界钉死。

这里用 **conftest 播种好的演示数据**（4 个角色 + 真实菜品），
期望值由测试自己按 `0.4*prior + 0.6*swipe` 逐人重算再求均值/最小值，
不复用被测的 `_four_member_metrics`。覆盖：无否决 / 单人否决 / 多人否决 /
全否决 / 缺席（TIMEOUT）五种固定样本。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import pytest

from backend.algorithms.group_recommender import (
    PRIOR_WEIGHT,
    SWIPE_WEIGHT,
    TIMEOUT_SWIPE_SCORE,
    VOTE_SCORES,
    compute_group_consensus,
    member_prior_scores,
)
from backend.algorithms.simulate_personas import _four_member_metrics
from backend.models import Dish, User


MEMBERS = [1, 2, 3, 4]


def _fixture(db):
    """从播种数据里取 4 个角色 + 2 道外食菜，不自己造主键。"""
    users = [u.id for u in db.query(User).order_by(User.id).limit(4).all()]
    dishes = [
        d.id
        for d in db.query(Dish)
        .filter(Dish.mode_type == "OUT_DINING")
        .order_by(Dish.id)
        .limit(2)
        .all()
    ]
    assert users == MEMBERS and len(dishes) == 2
    return dishes


def _reference(
    db,
    members: Sequence[int],
    dish_id: int,
    votes: Dict[int, Optional[str]],
    priors: Dict[int, Dict[int, float]],
):
    """独立算：VETO 记 0；没表态按 TIMEOUT；其余 0.4*prior + 0.6*swipe。

    个体 R 保留原始值；聚合后再按展示口径 `min(100, ·)` 封顶。
    """
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


def _case(db, votes: Dict[int, Optional[str]]):
    target = _fixture(db)[1]
    priors = member_prior_scores(db, MEMBERS, [target])
    rows = [
        {"user_id": uid, "dish_id": target, "vote_type": vote}
        for uid, vote in votes.items()
        if vote is not None
    ]
    report = compute_group_consensus(db, MEMBERS, [target], rows, 0.5)
    got = _four_member_metrics(report, target)
    expected = _reference(db, MEMBERS, target, votes, priors)
    return got, expected


def test_no_veto_uses_all_four(db):
    got, expected = _case(db, {1: "SUPER_LIKE", 2: "LIKE", 3: "PASS", 4: "PASS"})
    # 生产把每位成员的分数存成两位小数，参考实现用未舍入值，允许半个单位内的差
    assert got == pytest.approx(expected, abs=0.02)


def test_single_veto_counts_zero_in_mean_and_min(db):
    got, expected = _case(db, {1: "SUPER_LIKE", 2: "LIKE", 3: "VETO", 4: "PASS"})
    assert got == pytest.approx(expected, abs=0.02)
    assert got[1] == 0.0, "被否决的菜最低值必须是 0"


def test_multi_veto_counts_each_zero(db):
    got, expected = _case(db, {1: "VETO", 2: "LIKE", 3: "VETO", 4: "PASS"})
    assert got == pytest.approx(expected, abs=0.02)
    assert got[1] == 0.0


def test_all_veto_yields_zero_bar(db):
    got, expected = _case(db, {1: "VETO", 2: "VETO", 3: "VETO", 4: "VETO"})
    assert got == (0.0, 0.0)
    assert got == expected


def test_absence_uses_timeout_score_in_denominator(db):
    got, expected = _case(db, {1: "SUPER_LIKE", 2: None, 3: "PASS", 4: "PASS"})
    assert got == pytest.approx(expected, abs=0.02)
    assert got[1] > 0.0, "缺席不是否决，不应被当成 0 分"


def test_fixed_sample_above_100_uses_aggregate_cap():
    """R3-03 固定样本：个体 R 不封顶，四人聚合后才 min(100, ·)。

    [0, 67.58, 97.82, 107.70] → 原始均值 68.275、最低 0；
    逐人先封顶会得到 66.35，是 r03 被退回的口径。
    """
    report = {
        "dishes": [
            {
                "dish_id": 1,
                "members": [
                    {"satisfaction": value}
                    for value in (0.0, 67.58, 97.82, 107.70)
                ],
            }
        ]
    }
    got = _four_member_metrics(report, 1)
    assert got is not None
    assert got[0] == pytest.approx(68.275, abs=0.01)
    assert got[1] == 0.0


def test_all_members_above_100_caps_only_after_aggregation():
    report = {
        "dishes": [
            {
                "dish_id": 2,
                "members": [
                    {"satisfaction": value}
                    for value in (107.0, 108.0, 109.0, 110.0)
                ],
            }
        ]
    }
    assert _four_member_metrics(report, 2) == (100.0, 100.0)
