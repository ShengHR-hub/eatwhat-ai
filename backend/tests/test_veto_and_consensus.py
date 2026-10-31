"""F01 / F02 回归：忌口类别匹配 + 全否决不出赢家。

这两个用例对着审查报告的两条 P1：

* F01：用户忌口写「海鲜」，菜谱写「鲜虾」「虾皮」——旧实现做双向子串匹配，
  两个字符串互不包含，于是"命中忌口却照样推荐"。
* F02：全员否决时 `group_score` 全是 0.0，旧实现直接取 `reports[0]`，
  会把一道被所有人否决的菜当成"共识结果"发出去。
"""

import pytest

from backend.algorithms.group_recommender import compute_group_consensus
from backend.algorithms.single_recommender import recommend_single
from backend.algorithms.veto_rules import find_hit, hits
from backend.models import Dish, UserPreference


class _Vote:
    def __init__(self, user_id: int, dish_id: int, vote_type: str) -> None:
        self.user_id = user_id
        self.dish_id = dish_id
        self.vote_type = vote_type


# --------------------------------------------------------------------------- #
# F01：词表与匹配
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("tag", "ingredients", "expect"),
    [
        # 类别词展开到具体食材（报告点名的三个）
        ("海鲜", ["鲜虾", "姜葱"], True),
        ("海鲜", ["紫菜", "鸡蛋", "虾皮"], True),
        ("海鲜", ["虾仁", "澄面"], True),
        # 直接写具体食材也认
        ("鲜虾", ["虾仁", "澄面"], True),
        ("鱼腥草", ["折耳根", "辣椒油"], True),
        ("内脏", ["猪肝", "菠菜"], True),
        ("牛奶", ["淡奶油", "糖"], True),
        # 不能误伤：豆腐 不含「鱼豆腐」，鱼香肉丝 没有鱼
        ("海鲜", ["豆腐", "肉末", "豆瓣酱"], False),
        ("海鲜", ["猪里脊", "木耳", "胡萝卜"], False),
        # 单字「鱼」不进白名单，只认全等
        ("鱼", ["鱼香肉丝"], False),
        ("鱼", ["鱼"], True),
        # 未知标签原样匹配，不做静默丢弃
        ("秋葵", ["秋葵", "蒜"], True),
        ("秋葵", ["菠菜"], False),
        # 空忌口不影响任何菜
        ("", ["虾仁"], False),
    ],
)
def test_veto_rules_match(tag, ingredients, expect):
    assert hits(ingredients, [tag]) is expect


def test_veto_rules_report_which_token_hit():
    assert find_hit(["紫菜", "鸡蛋", "虾皮"], ["海鲜"]) == "虾皮"
    assert find_hit(["豆腐"], ["海鲜"]) is None


# --------------------------------------------------------------------------- #
# F01：接进单人推荐后，海鲜忌口不再推荐虾类
# --------------------------------------------------------------------------- #


def test_single_recommend_respects_seafood_veto(db):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == 3).one()
    assert "海鲜" in (prefs.veto_tags or []), "种子数据里 user 3 应该有海鲜忌口"

    result = recommend_single(db, user_id=3, mode_type="OUT_DINING", limit=100)
    items = result["recommendations"]
    assert items, "不应把候选全部过滤掉"

    leaked = []
    for item in items:
        dish = db.query(Dish).filter(Dish.id == item["dish_id"]).one()
        ingredients = list(dish.ingredients_main or []) + list(
            dish.ingredients_aux or []
        )
        if hits(ingredients, prefs.veto_tags):
            leaked.append((dish.id, dish.name, ingredients))

    assert leaked == [], f"这些菜命中了海鲜忌口却仍被推荐：{leaked}"


# --------------------------------------------------------------------------- #
# F02：否决项不得进入胜出集合
# --------------------------------------------------------------------------- #


def _consensus(db, votes, dish_ids=(23, 24), members=(1, 2)):
    return compute_group_consensus(db, list(members), list(dish_ids), votes)


def test_all_veto_has_no_winner(db):
    votes = [
        _Vote(1, 23, "VETO"),
        _Vote(2, 23, "VETO"),
        _Vote(1, 24, "VETO"),
        _Vote(2, 24, "VETO"),
    ]
    report = _consensus(db, votes)

    assert report["winner_dish_id"] is None, "全票否决时不该有赢家"
    assert report["has_consensus"] is False
    assert sorted(report["vetoed_dish_ids"]) == [23, 24]
    assert all(item["masked_by_veto"] for item in report["dishes"])
    assert all(item["group_score"] == 0.0 for item in report["dishes"])


def test_partial_veto_picks_from_survivors(db):
    votes = [
        _Vote(1, 23, "VETO"),
        _Vote(2, 23, "VETO"),
        _Vote(1, 24, "LIKE"),
        _Vote(2, 24, "LIKE"),
    ]
    report = _consensus(db, votes)

    assert report["winner_dish_id"] == 24
    assert report["has_consensus"] is True
    assert report["vetoed_dish_ids"] == [23]


def test_zero_score_tie_falls_back_to_smallest_dish_id(db, monkeypatch):
    """两菜同分时按 dish_id 稳定排序，不能因为排序不稳而抖动。

    真实先验分不同，所以这里把 `member_prior_scores` 打平，构造严格同分。
    """
    from backend.algorithms import group_recommender

    monkeypatch.setattr(
        group_recommender,
        "member_prior_scores",
        lambda db, member_ids, dish_ids: {
            int(uid): {int(did): 0.0 for did in dish_ids} for uid in member_ids
        },
    )
    votes = [
        _Vote(1, 23, "PASS"),
        _Vote(2, 23, "PASS"),
        _Vote(1, 24, "PASS"),
        _Vote(2, 24, "PASS"),
    ]
    report = _consensus(db, votes)

    scores = {item["dish_id"]: item["group_score"] for item in report["dishes"]}
    assert scores[23] == scores[24], "本用例要求两菜同分"
    assert report["winner_dish_id"] == 23
    assert report["has_consensus"] is True


def test_all_timeout_still_produces_winner(db):
    """一张票都没投时，全员按 TIMEOUT（60 分）计，仍会选出一道菜。

    这不是"凭空选"：60 分是明确的表态分值（SUPER_LIKE=120 / LIKE=100 /
    PASS=40 / TIMEOUT=60），只是最弱的一种。原用例名写的是
    「no_votes_at_all_means_no_consensus」，与断言正好相反，已改名并写清口径。
    """
    report = _consensus(db, [])
    assert report["has_consensus"] is True
    assert report["winner_dish_id"] is not None
