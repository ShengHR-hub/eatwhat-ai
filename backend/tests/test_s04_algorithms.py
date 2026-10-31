"""S04 四算法与决策红线：独立期望值。

纪律
----
* 本文件的 expected 一律由手算公式或本文件内的独立小实现给出，**不调用**
  `veto_rules.hits`、`group_recommender`、`time_decay`、`combo_optimizer`
  等被测生产函数来生成期望值。
* 数据全部写入 `conftest.py` 的 `sqlite://` 内存库；不触碰演示库。
* 覆盖 F01 / F02 与 S04-C1～C4；N04（NULL 向量）的消费策略待用户裁决后
  在单独用例中补齐。
"""

import math
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from backend.algorithms.combo_optimizer import build_shopping_list, optimize_combo
from backend.algorithms.group_recommender import (
    compute_group_consensus,
    shortlist_candidates,
)
from backend.algorithms.single_recommender import recommend_single
from backend.algorithms.time_decay import compute_decay_weights
from backend.models import Dish, EatingLog, Restaurant, User, UserPreference

FEATURE_KEYS = (
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
)

NEUTRAL = {key: 0.5 for key in FEATURE_KEYS}


def _vec(**overrides):
    base = {key: 0.0 for key in FEATURE_KEYS}
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# 隔离库构造工具
# --------------------------------------------------------------------------- #


def _make_user(
    db,
    username,
    vector,
    *,
    budget=25.0,
    veto=(),
    fav=(),
    black=(),
    black_rest=(),
):
    user = User(
        username=username,
        nickname=username,
        avatar="",
        persona_title="",
        is_demo_persona=False,
    )
    db.add(user)
    db.flush()
    db.add(
        UserPreference(
            user_id=user.id,
            base_vector=dict(vector),
            default_budget=budget,
            veto_tags=list(veto),
            preferred_cuisines=[],
            favorite_dish_ids=list(fav),
            blacklist_dish_ids=list(black),
            blacklist_restaurant_ids=list(black_rest),
        )
    )
    db.commit()
    return int(user.id)


def _make_restaurant(db, name, distance=100):
    restaurant = Restaurant(
        name=name,
        source_type="CANTEEN",
        category="S04测试",
        distance_meters=distance,
    )
    db.add(restaurant)
    db.commit()
    return int(restaurant.id)


def _make_dish(
    db,
    name,
    *,
    mode="OUT_DINING",
    role="MEAT",
    price=10.0,
    vector=NEUTRAL,
    mains=(),
    aux=(),
    cuisine="S04测试菜系",
    restaurant_id=None,
    appliance=("炒锅",),
    cook=10,
):
    dish = Dish(
        name=name,
        mode_type=mode,
        restaurant_id=restaurant_id,
        cuisine_type=cuisine,
        dish_role=role,
        price_or_cost=price,
        cook_minutes=cook,
        appliance_tag=list(appliance),
        ingredients_main=list(mains),
        ingredients_aux=list(aux),
        recipe_steps="",
        feature_vector=dict(vector) if vector is not None else None,
        image_url="",
    )
    db.add(dish)
    db.commit()
    return int(dish.id)


def _ids(result):
    return {int(item["dish_id"]) for item in result["recommendations"]}


# --------------------------------------------------------------------------- #
# A. F01：忌口别名 / 主辅料 / 误判反例 / 单人与群组同口径
# --------------------------------------------------------------------------- #


def test_s04_veto_alias_covers_main_and_aux_without_false_positives(db):
    """expected 为名称集合硬编码：不经过 veto_rules 生成。

    正例：鲜虾、虾皮（辅料）、螃蟹、扇贝、鱼（单字精确）、草鱼（词尾）、蚝油（辅料）。
    反例：鱼香肉丝（无鱼）、豆腐（不能用「鱼豆腐」反向包含）、党参（「参」不是海鲜）。
    """
    uid = _make_user(db, "s04_veto_alias", NEUTRAL, veto=["海鲜"])
    keep = {"S04鱼香肉丝", "S04麻婆豆腐", "S04党参鸡汤"}
    drop = {
        "S04海鲜鲜虾",
        "S04海鲜虾皮",
        "S04海鲜螃蟹",
        "S04海鲜扇贝",
        "S04海鲜鱼",
        "S04海鲜草鱼",
        "S04海鲜蚝油",
    }
    ids = {}
    ids["S04海鲜鲜虾"] = _make_dish(
        db, "S04海鲜鲜虾", mains=["鲜虾"], aux=["姜"]
    )
    ids["S04海鲜虾皮"] = _make_dish(
        db, "S04海鲜虾皮", mains=["紫菜", "鸡蛋"], aux=["虾皮", "盐"]
    )
    ids["S04海鲜螃蟹"] = _make_dish(
        db, "S04海鲜螃蟹", mains=["螃蟹"], aux=["姜"]
    )
    ids["S04海鲜扇贝"] = _make_dish(
        db, "S04海鲜扇贝", mains=["扇贝", "粉丝"], aux=["蒜"]
    )
    ids["S04海鲜鱼"] = _make_dish(
        db, "S04海鲜鱼", mains=["鱼"], aux=["姜"]
    )
    ids["S04海鲜草鱼"] = _make_dish(
        db, "S04海鲜草鱼", mains=["草鱼"], aux=["豆芽"]
    )
    ids["S04海鲜蚝油"] = _make_dish(
        db, "S04海鲜蚝油", mains=["生菜"], aux=["蚝油", "蒜"]
    )
    ids["S04鱼香肉丝"] = _make_dish(
        db,
        "S04鱼香肉丝",
        mains=["猪里脊", "木耳", "胡萝卜"],
        aux=["豆瓣酱", "醋", "葱姜蒜"],
    )
    ids["S04麻婆豆腐"] = _make_dish(
        db,
        "S04麻婆豆腐",
        mains=["豆腐", "肉末"],
        aux=["豆瓣酱", "花椒", "葱姜蒜"],
    )
    ids["S04党参鸡汤"] = _make_dish(
        db, "S04党参鸡汤", mains=["鸡肉", "党参"], aux=["姜", "盐"]
    )
    name_by_id = {dish_id: name for name, dish_id in ids.items()}
    controlled_ids = set(ids.values())

    single = recommend_single(db, uid, "OUT_DINING", limit=200)
    single_names = {
        name_by_id[dish_id] for dish_id in _ids(single) & controlled_ids
    }
    assert single_names == keep, f"单人漏判/误判：{sorted(single_names)}"
    assert drop.isdisjoint(single_names)

    shortlist = shortlist_candidates(db, [uid], "OUT_DINING", top_n=200)
    shortlist_ids = {int(item["dish_id"]) for item in shortlist}
    shortlist_names = {
        name_by_id[dish_id] for dish_id in shortlist_ids & controlled_ids
    }
    assert shortlist_names == keep, f"群组初筛漏判/误判：{sorted(shortlist_names)}"
    assert single_names == shortlist_names


def test_s04_specific_tag_does_not_expand_to_category():
    """D-S04-02：具体标签只匹配自身/明确同义词组，不跨类别。"""
    from backend.algorithms.veto_rules import hits

    # 鲜虾：虾类同义词命中；鱼/蟹/贝不命中。
    assert hits(["鲜虾"], ["鲜虾"]) is True
    assert hits(["虾仁"], ["鲜虾"]) is True
    assert hits(["虾皮"], ["鲜虾"]) is True
    assert hits(["鲈鱼"], ["鲜虾"]) is False
    assert hits(["螃蟹"], ["鲜虾"]) is False
    assert hits(["扇贝"], ["鲜虾"]) is False
    assert hits(["生蚝"], ["鲜虾"]) is False

    # 鲈鱼：不扩大到草鱼/三文鱼。
    assert hits(["鲈鱼"], ["鲈鱼"]) is True
    assert hits(["海鲈鱼"], ["鲈鱼"]) is True
    assert hits(["草鱼"], ["鲈鱼"]) is False
    assert hits(["三文鱼"], ["鲈鱼"]) is False

    # 牛肉：不扩大到羊肉/猪肉。
    assert hits(["牛腩"], ["牛肉"]) is True
    assert hits(["肥牛"], ["牛肉"]) is True
    assert hits(["羊肉"], ["牛肉"]) is False
    assert hits(["猪肉"], ["牛肉"]) is False

    # 未知文本只精确匹配。
    assert hits(["秋葵"], ["秋葵"]) is True
    assert hits(["菠菜"], ["秋葵"]) is False


def test_s04_category_tags_expand_only_within_their_own_group():
    """D-S04-02：五项类别标签各自展开，不跨类别。"""
    from backend.algorithms.veto_rules import hits

    assert hits(["鲈鱼"], ["海鲜"]) is True
    assert hits(["螃蟹"], ["海鲜"]) is True
    assert hits(["扇贝"], ["海鲜"]) is True

    assert hits(["紫菜"], ["海味"]) is True
    assert hits(["鲈鱼"], ["海味"]) is False

    assert hits(["猪肝"], ["内脏"]) is True
    assert hits(["牛肉"], ["内脏"]) is False

    assert hits(["淡奶油"], ["牛奶"]) is True
    assert hits(["辣椒"], ["牛奶"]) is False

    assert hits(["辣椒"], ["辣"]) is True
    assert hits(["牛奶"], ["辣"]) is False


def test_s04_specific_tag_parity_single_and_shortlist(db):
    """复核报告最小复现：鲜虾只排虾类；海鲜类别仍排整类。"""
    shrimp = _make_dish(db, "S04具体鲜虾", mains=["鲜虾"])
    shrimp_syn = _make_dish(db, "S04具体虾仁", mains=["虾仁"])
    fish = _make_dish(db, "S04具体鲈鱼", mains=["鲈鱼"])
    crab = _make_dish(db, "S04具体螃蟹", mains=["螃蟹"])
    scallop = _make_dish(db, "S04具体扇贝", mains=["扇贝"])
    veg = _make_dish(db, "S04具体青菜", mains=["青菜"])
    controlled = {shrimp, shrimp_syn, fish, crab, scallop, veg}
    expected_specific = {fish, crab, scallop, veg}

    uid = _make_user(db, "s04_specific_tag", NEUTRAL, veto=["鲜虾"])
    single = recommend_single(db, uid, "OUT_DINING", limit=200)
    assert _ids(single) & controlled == expected_specific
    shortlist = shortlist_candidates(db, [uid], "OUT_DINING", top_n=200)
    shortlist_ids = {int(item["dish_id"]) for item in shortlist}
    assert shortlist_ids & controlled == expected_specific
    assert _ids(single) & controlled == shortlist_ids & controlled

    category_uid = _make_user(
        db, "s04_specific_tag_category", NEUTRAL, veto=["海鲜"]
    )
    category_single = recommend_single(
        db, category_uid, "OUT_DINING", limit=200
    )
    assert _ids(category_single) & controlled == {veg}
    category_shortlist = shortlist_candidates(
        db, [category_uid], "OUT_DINING", top_n=200
    )
    category_ids = {int(item["dish_id"]) for item in category_shortlist}
    assert category_ids & controlled == {veg}


def test_s04_unknown_tag_is_exact_only():
    """D-S04-02：未知文本只做规范化后的全等匹配，不做子串/前后缀包含。"""
    from backend.algorithms.veto_rules import explain, find_hit, hits

    assert hits(["秋葵"], ["秋葵"]) is True
    assert hits(["秋葵炒蛋"], ["秋葵"]) is False
    assert hits(["秋葵籽"], ["秋葵"]) is False
    assert hits(["核桃"], ["核桃"]) is True
    assert hits(["核桃仁"], ["核桃"]) is False
    assert hits(["核桃碎"], ["核桃"]) is False
    assert hits(["核桃"], ["核桃仁"]) is False
    assert find_hit(["核桃仁"], ["核桃"]) is None
    assert explain(["核桃仁"], ["核桃"])["matched"] is False


def test_s04_unknown_tag_parity_single_and_shortlist(db):
    walnut = _make_dish(db, "S04未知核桃", mains=["核桃"])
    walnut_kernel = _make_dish(db, "S04未知核桃仁", mains=["核桃仁"])
    shrimp = _make_dish(db, "S04未知鲜虾", mains=["鲜虾"])
    veg = _make_dish(db, "S04未知青菜", mains=["青菜"])
    controlled = {walnut, walnut_kernel, shrimp, veg}
    expected = {walnut_kernel, shrimp, veg}

    uid = _make_user(db, "s04_unknown_tag", NEUTRAL, veto=["核桃"])
    single = recommend_single(db, uid, "OUT_DINING", limit=200)
    assert _ids(single) & controlled == expected
    shortlist = shortlist_candidates(db, [uid], "OUT_DINING", top_n=200)
    shortlist_ids = {int(item["dish_id"]) for item in shortlist}
    assert shortlist_ids & controlled == expected
    assert _ids(single) & controlled == shortlist_ids & controlled


def test_s04_veto_explain_uses_same_matching_rules():
    """`explain` 必须与 `hits` 同源，包括词尾规则，不能维护第二套匹配。"""
    from backend.algorithms.veto_rules import explain, hits

    assert hits(["草鱼"], ["海鲜"]) is True
    # 去掉「参」词尾后，海参/刺参仍由别名表覆盖，党参/人参不被误判。
    assert hits(["海参"], ["海鲜"]) is True
    assert hits(["刺参"], ["海鲜"]) is True
    assert hits(["党参"], ["海鲜"]) is False
    assert explain(["草鱼"], ["海鲜"]) == {
        "matched": True,
        "tag": "海鲜",
        "ingredient": "草鱼",
    }
    assert explain(["豆腐"], ["海鲜"]) == {
        "matched": False,
        "tag": None,
        "ingredient": None,
    }


def test_s04_veto_and_blacklists_share_semantics_between_single_and_shortlist(db):
    """忌口、菜品黑榜、门店黑榜三类硬过滤在两条入口上同口径。

    把三张被排除的菜同时放进收藏，并用 alpha=1 的权重覆盖，证明收藏/权重
    不能绕过硬约束。
    """
    ok_store = _make_restaurant(db, "S04正常门店")
    blocked_store = _make_restaurant(db, "S04黑榜门店")
    seafood = _make_dish(
        db, "S04硬约束海鲜", mains=["鲜虾"], restaurant_id=ok_store
    )
    black_dish = _make_dish(
        db, "S04硬约束黑榜菜", mains=["牛肉"], restaurant_id=ok_store
    )
    blocked_store_dish = _make_dish(
        db, "S04硬约束门店菜", mains=["土豆"], restaurant_id=blocked_store
    )
    clean = _make_dish(
        db, "S04硬约束青菜", mains=["青菜"], restaurant_id=ok_store
    )
    uid = _make_user(
        db,
        "s04_hard_filters",
        NEUTRAL,
        veto=["海鲜"],
        fav=[seafood, black_dish, blocked_store_dish],
        black=[black_dish],
        black_rest=[blocked_store],
    )
    controlled_ids = {seafood, black_dish, blocked_store_dish, clean}
    expected = {clean}

    single = recommend_single(db, uid, "OUT_DINING", limit=200)
    assert _ids(single) & controlled_ids == expected

    weighted = recommend_single(
        db,
        uid,
        "OUT_DINING",
        limit=200,
        override_params={
            "alpha_taste": 1.0,
            "beta_weather": 0.0,
            "gamma_budget": 0.0,
            "delta_status": 0.0,
        },
    )
    assert _ids(weighted) & controlled_ids == expected

    shortlist = shortlist_candidates(db, [uid], "OUT_DINING", top_n=200)
    shortlist_ids = {int(item["dish_id"]) for item in shortlist}
    assert shortlist_ids & controlled_ids == expected
    assert _ids(single) & controlled_ids == shortlist_ids & controlled_ids


def test_s04_group_shortlist_uses_union_of_members_veto_and_blacklists(db):
    seafood = _make_dish(db, "S04联合海鲜", mains=["鲜虾"])
    cilantro = _make_dish(
        db, "S04联合香菜", mains=["牛肉"], aux=["香菜"]
    )
    black_dish = _make_dish(db, "S04联合黑榜", mains=["猪肉"])
    clean_a = _make_dish(db, "S04联合青菜", mains=["青菜"])
    clean_b = _make_dish(db, "S04联合豆腐", mains=["豆腐"])
    ua = _make_user(db, "s04_union_a", NEUTRAL, veto=["海鲜"])
    ub = _make_user(
        db, "s04_union_b", NEUTRAL, veto=["香菜"], black=[black_dish]
    )

    single_a = recommend_single(db, ua, "OUT_DINING", limit=200)
    single_b = recommend_single(db, ub, "OUT_DINING", limit=200)
    # 单人各自只认自己的忌口：A 保留香菜菜、B 保留海鲜菜。
    assert cilantro in _ids(single_a)
    assert seafood not in _ids(single_a)
    assert seafood in _ids(single_b)
    assert cilantro not in _ids(single_b)
    assert black_dish not in _ids(single_b)

    shortlist = shortlist_candidates(db, [ua, ub], "OUT_DINING", top_n=200)
    controlled = {seafood, cilantro, black_dish, clean_a, clean_b}
    shortlist_ids = {int(item["dish_id"]) for item in shortlist}
    assert shortlist_ids & controlled == {clean_a, clean_b}


def test_s04_broke_end_month_budget_filter_cannot_be_bypassed_by_favorite(db):
    pricey = _make_dish(db, "S04超预算最爱", price=30.0, mains=["牛肉"])
    cheap = _make_dish(db, "S04预算内", price=10.0, mains=["青菜"])
    uid = _make_user(
        db, "s04_budget_hard", NEUTRAL, budget=12.0, fav=[pricey]
    )
    result = recommend_single(
        db,
        uid,
        "OUT_DINING",
        budget=12.0,
        bubbles=["broke_end_month"],
        limit=200,
    )
    controlled = {pricey, cheap}
    assert _ids(result) & controlled == {cheap}


# --------------------------------------------------------------------------- #
# B. F02：固定票矩阵与群组共识
# --------------------------------------------------------------------------- #


def _cos100(left, right):
    """独立实现：余弦相似度映射到 0~100，不调用 vector_spec。"""
    a = [float(left[key]) for key in FEATURE_KEYS]
    b = [float(right[key]) for key in FEATURE_KEYS]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return round(max(0.0, min(1.0, dot / (norm_a * norm_b))) * 100.0, 2)


def _r(prior, swipe):
    return 0.4 * prior + 0.6 * swipe


def _group(rs, omega):
    return omega * (sum(rs) / len(rs)) + (1.0 - omega) * min(rs)


def _vote(user_id, dish_id, vote_type):
    return {"user_id": user_id, "dish_id": dish_id, "vote_type": vote_type}


def _consensus_fixture(db):
    vectors = {
        "u1": _vec(spicy_level=1.0),
        "u2": _vec(oily_level=1.0),
        "u3": _vec(spicy_level=0.6, oily_level=0.8),
        "u4": _vec(spicy_level=0.8, oily_level=0.6),
    }
    users = {
        name: _make_user(db, f"s04_consensus_{name}", vector)
        for name, vector in vectors.items()
    }
    dishes = {
        "d1": _make_dish(db, "S04共识甲", vector=_vec(spicy_level=1.0)),
        "d2": _make_dish(db, "S04共识乙", vector=_vec(oily_level=1.0)),
        "d3": _make_dish(
            db, "S04共识丙", vector=_vec(spicy_level=0.6, oily_level=0.8)
        ),
        "d5": _make_dish(
            db, "S04共识丁", vector=_vec(spicy_level=0.6, oily_level=0.8)
        ),
    }
    priors = {
        "d1": {
            "u1": _cos100(vectors["u1"], _vec(spicy_level=1.0)),
            "u2": _cos100(vectors["u2"], _vec(spicy_level=1.0)),
            "u3": _cos100(vectors["u3"], _vec(spicy_level=1.0)),
            "u4": _cos100(vectors["u4"], _vec(spicy_level=1.0)),
        },
        "d2": {
            "u1": _cos100(vectors["u1"], _vec(oily_level=1.0)),
            "u2": _cos100(vectors["u2"], _vec(oily_level=1.0)),
            "u3": _cos100(vectors["u3"], _vec(oily_level=1.0)),
            "u4": _cos100(vectors["u4"], _vec(oily_level=1.0)),
        },
        "d3": {
            "u1": _cos100(vectors["u1"], _vec(spicy_level=0.6, oily_level=0.8)),
            "u2": _cos100(vectors["u2"], _vec(spicy_level=0.6, oily_level=0.8)),
            "u3": _cos100(vectors["u3"], _vec(spicy_level=0.6, oily_level=0.8)),
            "u4": _cos100(vectors["u4"], _vec(spicy_level=0.6, oily_level=0.8)),
        },
    }
    priors["d5"] = dict(priors["d3"])
    return users, dishes, priors


def test_s04_vote_scale_mapping_matches_ssot():
    """划卡分唯一刻度：120 / 100 / 40；VETO 不映射为分值，只做掩码。"""
    from backend.algorithms.vector_spec import VOTE_SCORES

    assert VOTE_SCORES["SUPER_LIKE"] == 120.0
    assert VOTE_SCORES["LIKE"] == 100.0
    assert VOTE_SCORES["PASS"] == 40.0


def test_s04_all_veto_has_no_winner_and_is_explainable(db):
    users, dishes, _ = _consensus_fixture(db)
    member_ids = [users["u1"], users["u2"], users["u3"], users["u4"]]
    candidate_ids = [dishes["d1"], dishes["d2"]]
    votes = [
        _vote(uid, dish_id, "VETO")
        for uid in member_ids
        for dish_id in candidate_ids
    ]
    report = compute_group_consensus(
        db, member_ids, candidate_ids, votes, omega_group=0.5
    )
    assert report["winner_dish_id"] is None
    assert report["has_consensus"] is False
    assert sorted(report["vetoed_dish_ids"]) == sorted(candidate_ids)
    assert all(item["masked_by_veto"] for item in report["dishes"])
    assert all(item["group_score"] == 0.0 for item in report["dishes"])


def test_s04_partial_veto_picks_survivor_and_veto_cannot_be_resurrected(db):
    users, dishes, priors = _consensus_fixture(db)
    member_ids = [users["u1"], users["u2"], users["u3"], users["u4"]]
    d1, d2 = dishes["d1"], dishes["d2"]
    # d1 拿到三张高分票，但 u4 一票否决；d2 全员 PASS。
    votes = [
        _vote(users["u1"], d1, "SUPER_LIKE"),
        _vote(users["u2"], d1, "SUPER_LIKE"),
        _vote(users["u3"], d1, "SUPER_LIKE"),
        _vote(users["u4"], d1, "VETO"),
        _vote(users["u1"], d2, "PASS"),
        _vote(users["u2"], d2, "PASS"),
        _vote(users["u3"], d2, "PASS"),
        _vote(users["u4"], d2, "PASS"),
    ]
    report = compute_group_consensus(
        db, member_ids, [d1, d2], votes, omega_group=0.5
    )
    assert report["winner_dish_id"] == d2
    assert report["has_consensus"] is True
    assert report["vetoed_dish_ids"] == [d1]
    d1_report = next(item for item in report["dishes"] if item["dish_id"] == d1)
    assert d1_report["masked_by_veto"] is True
    assert d1_report["group_score"] == 0.0

    rs = [_r(priors["d2"][name], 40.0) for name in ("u1", "u2", "u3", "u4")]
    d2_report = next(item for item in report["dishes"] if item["dish_id"] == d2)
    assert d2_report["group_score"] == pytest.approx(_group(rs, 0.5), abs=0.01)
    assert d2_report["mean_satisfaction"] == pytest.approx(
        sum(rs) / len(rs), abs=0.01
    )
    assert d2_report["least_misery"] == pytest.approx(min(rs), abs=0.01)


def test_s04_four_member_formula_and_omega_endpoints(db):
    users, dishes, priors = _consensus_fixture(db)
    member_ids = [users["u1"], users["u2"], users["u3"], users["u4"]]
    dish = dishes["d1"]
    votes = [
        _vote(users["u1"], dish, "SUPER_LIKE"),
        _vote(users["u2"], dish, "LIKE"),
        _vote(users["u3"], dish, "PASS"),
        _vote(users["u4"], dish, "SUPER_LIKE"),
    ]
    swipes = {"u1": 120.0, "u2": 100.0, "u3": 40.0, "u4": 120.0}
    rs = [_r(priors["d1"][name], swipes[name]) for name in ("u1", "u2", "u3", "u4")]
    assert rs == [112.0, 60.0, 48.0, 104.0]
    mean = sum(rs) / len(rs)
    least = min(rs)

    for omega, expected in (
        (0.0, least),
        (0.5, _group(rs, 0.5)),
        (1.0, mean),
    ):
        report = compute_group_consensus(
            db, member_ids, [dish], votes, omega_group=omega
        )
        item = report["dishes"][0]
        assert item["mean_satisfaction"] == pytest.approx(mean, abs=0.01)
        assert item["least_misery"] == pytest.approx(least, abs=0.01)
        assert item["group_score"] == pytest.approx(expected, abs=0.01)
        assert report["winner_dish_id"] == dish


def test_s04_veto_member_is_zeroed_and_excluded_from_mean_least(db):
    users, dishes, priors = _consensus_fixture(db)
    member_ids = [users["u1"], users["u2"], users["u3"], users["u4"]]
    dish = dishes["d1"]
    votes = [
        _vote(users["u1"], dish, "SUPER_LIKE"),
        _vote(users["u2"], dish, "LIKE"),
        _vote(users["u3"], dish, "PASS"),
        _vote(users["u4"], dish, "VETO"),
    ]
    report = compute_group_consensus(
        db, member_ids, [dish], votes, omega_group=0.5
    )
    item = report["dishes"][0]
    non_veto_rs = [
        _r(priors["d1"][name], swipe)
        for name, swipe in (("u1", 120.0), ("u2", 100.0), ("u3", 40.0))
    ]
    assert item["mean_satisfaction"] == pytest.approx(
        sum(non_veto_rs) / len(non_veto_rs), abs=0.01
    )
    assert item["least_misery"] == pytest.approx(min(non_veto_rs), abs=0.01)
    assert item["group_score"] == 0.0
    veto_member = next(
        member for member in item["members"] if member["user_id"] == users["u4"]
    )
    assert veto_member["vote_type"] == "VETO"
    assert veto_member["satisfaction"] == 0.0


def test_s04_survivor_tie_is_stable(db):
    """存活候选同分稳定性（本样本同分值为 52.8，不是 0）。

    合法非空成员下，未被 VETO 的最低票为 PASS=40（缺席 60），先验在 [0,100]，
    因此个体 R >= 0.4*0 + 0.6*40 = 24，群组 G 也 >= 24；零分只属于被 VETO
    掩码的候选，存活集按掩码筛选，不按分数筛选。本用例只验证同分时按 dish_id
    稳定取小，不为凑“零分”构造空成员等非法房间输入。
    """
    users, dishes, priors = _consensus_fixture(db)
    member_ids = [users["u1"], users["u2"], users["u3"], users["u4"]]
    d3, d5 = dishes["d3"], dishes["d5"]
    votes = [
        _vote(uid, dish_id, "PASS")
        for uid in member_ids
        for dish_id in (d3, d5)
    ]
    report = compute_group_consensus(
        db, member_ids, [d5, d3], votes, omega_group=0.5
    )
    scores = {item["dish_id"]: item["group_score"] for item in report["dishes"]}
    rs = [_r(priors["d3"][name], 40.0) for name in ("u1", "u2", "u3", "u4")]
    expected_tie = _group(rs, 0.5)
    assert expected_tie == pytest.approx(52.8, abs=0.01)
    assert scores[d3] == scores[d5] == pytest.approx(52.8, abs=0.01)
    assert scores[d3] > 0
    assert report["winner_dish_id"] == d3  # 同分按 dish_id 稳定取小
    assert report["has_consensus"] is True


def test_s04_no_votes_uses_documented_timeout_semantics(db):
    """无票（全员缺席）= TIMEOUT=60，属当前实现口径；SSOT 未定义，S06 负责房间级语义。

    expected 由固定假设（缺席 60 分）+ 手算 R/mean/least/G 得到。
    """
    users, dishes, priors = _consensus_fixture(db)
    member_ids = [users["u1"], users["u2"], users["u3"], users["u4"]]
    dish = dishes["d1"]
    report = compute_group_consensus(db, member_ids, [dish], [], omega_group=0.5)
    rs = [_r(priors["d1"][name], 60.0) for name in ("u1", "u2", "u3", "u4")]
    item = report["dishes"][0]
    assert item["mean_satisfaction"] == pytest.approx(
        sum(rs) / len(rs), abs=0.01
    )
    assert item["least_misery"] == pytest.approx(min(rs), abs=0.01)
    assert item["group_score"] == pytest.approx(_group(rs, 0.5), abs=0.01)
    assert report["winner_dish_id"] == dish
    assert report["has_consensus"] is True


# --------------------------------------------------------------------------- #
# C. 公式与边界：衰减 / 权重归一化 / 排序与封顶
# --------------------------------------------------------------------------- #


def _decay(lam, dt_exact, dt_similar):
    """独立实现 SSOT 算法 1。"""
    if dt_exact == 0:
        return 0.05
    exact = 1.0 if dt_exact is None else 1.0 - math.exp(-lam * dt_exact)
    similar = (
        1.0
        if dt_similar is None
        else 1.0 - 0.4 * math.exp(-lam * dt_similar)
    )
    return max(0.0, min(1.0, exact * similar))


def _log(db, user_id, dish_id, eaten_at):
    db.add(
        EatingLog(
            user_id=user_id,
            dish_id=dish_id,
            mode_type="OUT_DINING",
            cost_amount=0.0,
            weather_snapshot="",
            status_bubbles=[],
            eaten_at=eaten_at,
        )
    )
    db.commit()


def test_s04_time_decay_formula_and_exact_boundaries(db):
    now = datetime(2026, 10, 26, 12, 0, 0)
    dishes = {
        "exact": _make_dish(
            db, "S04衰减同菜", cuisine="S04衰减甲", mains=["S04甲料"]
        ),
        "similar": _make_dish(
            db, "S04衰减同系", cuisine="S04衰减甲", mains=["S04乙料"]
        ),
        "target_mix": _make_dish(
            db, "S04衰减混合", cuisine="S04衰减混合", mains=["S04混合料"]
        ),
        "mix_exact": _make_dish(
            db, "S04衰减混合同菜", cuisine="S04衰减混合", mains=["S04混合甲"]
        ),
        "mix_similar": _make_dish(
            db, "S04衰减混合同系", cuisine="S04衰减混合", mains=["S04混合乙"]
        ),
        "same_day_target": _make_dish(
            db, "S04衰减当日", cuisine="S04衰减当日", mains=["S04当日料"]
        ),
        "same_day_other": _make_dish(
            db, "S04衰减当日同系", cuisine="S04衰减当日", mains=["S04当日乙"]
        ),
        "fourteen": _make_dish(
            db, "S04衰减十四", cuisine="S04衰减十四", mains=["S04十四料"]
        ),
        "fifteen": _make_dish(
            db, "S04衰减十五", cuisine="S04衰减十五", mains=["S04十五料"]
        ),
        "fresh": _make_dish(
            db, "S04衰减无记录", cuisine="S04衰减无记录", mains=["S04无料"]
        ),
        "unrelated_log": _make_dish(
            db, "S04衰减无关记录", cuisine="S04衰减无关乙", mains=["S04无关料"]
        ),
        "unrelated_target": _make_dish(
            db, "S04衰减无关目标", cuisine="S04衰减无关甲", mains=["S04目标料"]
        ),
    }

    def obj(key):
        return db.query(Dish).filter(Dish.id == dishes[key]).one()

    # 同日同菜：强制 0.05（即使还有同菜系记录）。
    uid_day0 = _make_user(db, "s04_decay_day0", NEUTRAL)
    _log(db, uid_day0, dishes["exact"], now)
    _log(db, uid_day0, dishes["similar"], now)
    weight = compute_decay_weights(
        db, uid_day0, [obj("exact")], lambda_decay=0.5, now=now
    )[dishes["exact"]]
    assert weight == pytest.approx(0.05, abs=1e-4)

    # 精确 3 天 + 同菜系 1 天。
    uid_mix = _make_user(db, "s04_decay_mix", NEUTRAL)
    _log(db, uid_mix, dishes["target_mix"], now - timedelta(days=3))
    _log(db, uid_mix, dishes["mix_similar"], now - timedelta(days=1))
    weight = compute_decay_weights(
        db, uid_mix, [obj("target_mix")], lambda_decay=0.5, now=now
    )[dishes["target_mix"]]
    assert weight == pytest.approx(_decay(0.5, 3, 1), abs=5e-5)

    # 只有同菜系且同日：dt_exact=None, dt_similar=0 → 0.6。
    uid_sim = _make_user(db, "s04_decay_sim", NEUTRAL)
    _log(db, uid_sim, dishes["same_day_other"], now)
    weight = compute_decay_weights(
        db, uid_sim, [obj("same_day_target")], lambda_decay=0.5, now=now
    )[dishes["same_day_target"]]
    assert weight == pytest.approx(_decay(0.5, None, 0), abs=5e-5)
    assert weight == pytest.approx(0.6, abs=5e-5)

    # 14 天边界：仍在窗口内，按公式轻微衰减；15 天：窗口外 → 1.0。
    uid_14 = _make_user(db, "s04_decay_14", NEUTRAL)
    _log(db, uid_14, dishes["fourteen"], now - timedelta(days=14))
    weight = compute_decay_weights(
        db, uid_14, [obj("fourteen")], lambda_decay=0.5, now=now
    )[dishes["fourteen"]]
    assert weight == pytest.approx(_decay(0.5, 14, None), abs=5e-5)
    assert 0.99 < weight < 1.0

    uid_15 = _make_user(db, "s04_decay_15", NEUTRAL)
    _log(db, uid_15, dishes["fifteen"], now - timedelta(days=15))
    weight = compute_decay_weights(
        db, uid_15, [obj("fifteen")], lambda_decay=0.5, now=now
    )[dishes["fifteen"]]
    assert weight == 1.0

    # 无记录 / 无关记录 → 1.0。
    uid_none = _make_user(db, "s04_decay_none", NEUTRAL)
    weight = compute_decay_weights(
        db, uid_none, [obj("fresh")], lambda_decay=0.5, now=now
    )[dishes["fresh"]]
    assert weight == 1.0

    uid_unrelated = _make_user(db, "s04_decay_unrelated", NEUTRAL)
    _log(db, uid_unrelated, dishes["unrelated_log"], now)
    weight = compute_decay_weights(
        db, uid_unrelated, [obj("unrelated_target")], lambda_decay=0.5, now=now
    )[dishes["unrelated_target"]]
    assert weight == 1.0

    # λ=1 的同一样本。
    uid_lambda = _make_user(db, "s04_decay_lambda", NEUTRAL)
    _log(db, uid_lambda, dishes["target_mix"], now - timedelta(days=3))
    _log(db, uid_lambda, dishes["mix_similar"], now - timedelta(days=1))
    weight = compute_decay_weights(
        db, uid_lambda, [obj("target_mix")], lambda_decay=1.0, now=now
    )[dishes["target_mix"]]
    assert weight == pytest.approx(_decay(1.0, 3, 1), abs=5e-5)


def _budget_score(price, budget):
    if price <= budget:
        return 85.0 + 15.0 * (1.0 - price / budget)
    return 85.0 * math.exp(-3.0 * (price - budget) / budget)


def _weather_score(vector, temp_c):
    # 20℃、晴：SSOT 天气目标 temp_fit=0.35, soup_level=0.65。
    if temp_c <= 5:
        target = (0.05, 0.95)
    elif temp_c <= 12:
        target = (0.15, 0.85)
    elif temp_c <= 20:
        target = (0.35, 0.65)
    elif temp_c <= 28:
        target = (0.60, 0.35)
    else:
        target = (0.90, 0.15)
    diff = 0.6 * abs(vector["temp_fit"] - target[0]) + 0.4 * abs(
        vector["soup_level"] - target[1]
    )
    return 100.0 * (1.0 - diff)


def test_s04_single_formula_weight_normalization_and_display_cap(db):
    vector = {
        "spicy_level": 0.85,
        "oily_level": 0.75,
        "soup_level": 0.5,
        "temp_fit": 0.5,
        "satiety_level": 0.5,
        "prep_speed": 0.5,
        "social_fit": 0.5,
        "comfort_level": 0.5,
    }
    dish = _make_dish(
        db,
        "S04公式菜",
        price=10.0,
        vector=vector,
        mains=["S04公式料"],
        cuisine="S04公式菜系",
    )
    uid = _make_user(db, "s04_formula", vector, budget=25.0)

    result = recommend_single(
        db,
        uid,
        "OUT_DINING",
        budget=25.0,
        bubbles=["craving_heavy"],
        weather_temp=20.0,
        weather_text="晴",
        limit=200,
    )
    item = next(
        entry for entry in result["recommendations"] if entry["dish_id"] == dish
    )

    # 手算：alpha 0.50 + 默认 beta .25 / gamma .20 / delta .20，和 1.15。
    weights = {
        "alpha_taste": 0.50 / 1.15,
        "beta_weather": 0.25 / 1.15,
        "gamma_budget": 0.20 / 1.15,
        "delta_status": 0.20 / 1.15,
    }
    for key, value in weights.items():
        assert result["params_used"][key] == pytest.approx(value, abs=1e-4)
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-9)

    taste = 100.0
    weather = _weather_score(vector, 20.0)
    budget = _budget_score(10.0, 25.0)
    status = 100.0  # craving_heavy 目标 spicy .85 / oily .75 与本菜一致
    raw = (
        weights["alpha_taste"] * taste
        + weights["beta_weather"] * weather
        + weights["gamma_budget"] * budget
        + weights["delta_status"] * status
    )
    assert item["radar_5d"] == pytest.approx(
        {
            "taste": taste,
            "weather": weather,
            "budget": budget,
            "freshness": 100.0,
            "status": status,
        },
        abs=0.01,
    )
    assert item["decay_weight"] == 1.0
    assert item["raw_score"] == pytest.approx(raw, abs=1e-4)
    assert item["total_score"] == pytest.approx(round(min(100.0, raw), 1))

    # 收藏 1.15x：原始分仍按未封顶值排序，展示封顶 100。
    prefs = db.query(UserPreference).filter(UserPreference.user_id == uid).one()
    prefs.favorite_dish_ids = [dish]
    db.commit()
    boosted = recommend_single(
        db,
        uid,
        "OUT_DINING",
        budget=25.0,
        bubbles=["craving_heavy"],
        weather_temp=20.0,
        weather_text="晴",
        limit=200,
    )
    boosted_item = next(
        entry for entry in boosted["recommendations"] if entry["dish_id"] == dish
    )
    assert boosted_item["raw_score"] == pytest.approx(raw * 1.15, abs=1e-4)
    assert boosted_item["total_score"] == 100.0


def test_s04_sort_uses_raw_score_when_display_values_tie(db):
    vector = _vec(spicy_level=1.0)
    favorite = _make_dish(db, "S04排序收藏", vector=vector, price=10.0)
    plain = _make_dish(db, "S04排序普通", vector=vector, price=10.0)
    uid = _make_user(
        db, "s04_sort", vector, budget=100.0, fav=[favorite]
    )
    result = recommend_single(
        db,
        uid,
        "OUT_DINING",
        budget=100.0,
        limit=200,
        override_params={
            "alpha_taste": 1.0,
            "beta_weather": 0.0,
            "gamma_budget": 0.0,
            "delta_status": 0.0,
        },
    )
    order = [entry["dish_id"] for entry in result["recommendations"]]
    assert order.index(favorite) < order.index(plain)
    by_id = {entry["dish_id"]: entry for entry in result["recommendations"]}
    assert by_id[favorite]["total_score"] == 100.0
    assert by_id[plain]["total_score"] == 100.0
    assert by_id[favorite]["raw_score"] == pytest.approx(115.0, abs=1e-4)
    assert by_id[plain]["raw_score"] == pytest.approx(100.0, abs=1e-4)


def test_s04_weight_normalization_fallbacks(db):
    dish = _make_dish(db, "S04归一化菜", vector=NEUTRAL)
    uid = _make_user(db, "s04_weights", NEUTRAL, budget=25.0)

    zeroed = recommend_single(
        db,
        uid,
        "OUT_DINING",
        limit=10,
        override_params={
            "alpha_taste": 0.0,
            "beta_weather": 0.0,
            "gamma_budget": 0.0,
            "delta_status": 0.0,
        },
    )
    assert zeroed["params_used"]["alpha_taste"] == pytest.approx(0.35)
    assert zeroed["params_used"]["beta_weather"] == pytest.approx(0.25)
    assert zeroed["params_used"]["gamma_budget"] == pytest.approx(0.20)
    assert zeroed["params_used"]["delta_status"] == pytest.approx(0.20)

    single_weight = recommend_single(
        db,
        uid,
        "OUT_DINING",
        limit=10,
        override_params={
            "alpha_taste": 2.0,
            "beta_weather": 0.0,
            "gamma_budget": 0.0,
            "delta_status": 0.0,
        },
    )
    assert single_weight["params_used"]["alpha_taste"] == 1.0
    assert single_weight["params_used"]["beta_weather"] == 0.0
    assert single_weight["params_used"]["gamma_budget"] == 0.0
    assert single_weight["params_used"]["delta_status"] == 0.0

    broke = recommend_single(
        db,
        uid,
        "OUT_DINING",
        budget=50.0,
        bubbles=["broke_end_month"],
        limit=10,
    )
    assert broke["params_used"]["alpha_taste"] == pytest.approx(0.35 / 1.35, abs=1e-4)
    assert broke["params_used"]["beta_weather"] == pytest.approx(0.25 / 1.35, abs=1e-4)
    assert broke["params_used"]["gamma_budget"] == pytest.approx(0.55 / 1.35, abs=1e-4)
    assert broke["params_used"]["delta_status"] == pytest.approx(0.20 / 1.35, abs=1e-4)


# --------------------------------------------------------------------------- #
# D. 套餐：Top-20、预算、油腻度、无解、采购合并、lazy_one_pot
# --------------------------------------------------------------------------- #


def _item(dish_id, role, price, score, oily):
    return {
        "dish_id": dish_id,
        "name": f"S04组合-{dish_id}",
        "dish_role": role,
        "price": price,
        "score": score,
        "oily_level": oily,
    }


def test_s04_combo_enumerates_only_top20_before_role_grouping():
    candidates = [
        _item(index, "MEAT", 1.0, 100.0 - index, 0.1) for index in range(1, 11)
    ] + [
        _item(index, "VEG", 1.0, 100.0 - index, 0.1) for index in range(11, 21)
    ] + [_item(21, "SOUP", 1.0, 1.0, 0.1)]
    assert optimize_combo(candidates, budget=100.0) is None


def test_s04_combo_budget_and_oily_boundaries():
    candidates = [
        _item(1, "MEAT", 10.0, 80.0, 0.65),
        _item(2, "VEG", 5.0, 60.0, 0.65),
        _item(3, "SOUP", 5.0, 40.0, 0.65),
    ]
    exact = optimize_combo(candidates, budget=20.0)
    assert exact is not None
    assert exact["total_price"] == pytest.approx(20.0)
    assert exact["avg_oily_level"] == pytest.approx(0.65)
    assert optimize_combo(candidates, budget=19.99) is None

    over_oily = [
        _item(1, "MEAT", 10.0, 80.0, 0.6500001),
        _item(2, "VEG", 5.0, 60.0, 0.65),
        _item(3, "SOUP", 5.0, 40.0, 0.65),
    ]
    assert optimize_combo(over_oily, budget=100.0) is None


def test_s04_combo_hard_constraints_beat_score_and_missing_role():
    candidates = [
        _item(1, "MEAT", 10.0, 999.0, 0.95),  # 高分但荤素合计油腻超限
        _item(2, "MEAT", 10.0, 10.0, 0.2),
        _item(3, "VEG", 5.0, 50.0, 0.95),
        _item(4, "SOUP", 5.0, 40.0, 0.2),
    ]
    result = optimize_combo(candidates, budget=100.0)
    assert result is not None
    assert {dish["dish_id"] for dish in result["dishes"]} == {2, 3, 4}
    assert result["avg_oily_level"] <= 0.65

    assert optimize_combo(candidates[:2] + candidates[3:], budget=100.0) is None


def test_s04_shopping_list_merges_dedupes_and_skips_expired_stock(db):
    now = datetime(2026, 10, 26, 12, 0, 0)
    first = _make_dish(
        db,
        "S04采购甲",
        mode="HOME_COOKING",
        role="ONE_MEAL",
        mains=["S04番茄", "S04鸡蛋"],
        aux=["S04盐"],
    )
    second = _make_dish(
        db,
        "S04采购乙",
        mode="HOME_COOKING",
        role="ONE_MEAL",
        mains=["S04番茄", "S04土豆"],
        aux=["S04油"],
    )
    third = _make_dish(
        db,
        "S04采购丙",
        mode="HOME_COOKING",
        role="ONE_MEAL",
        mains=["S04鸡蛋", "S04牛肉"],
        aux=[],
    )
    uid = _make_user(db, "s04_shopping", NEUTRAL)
    from backend.models import FridgeInventory

    db.add_all(
        [
            FridgeInventory(
                user_id=uid,
                ingredient_name="S04番茄",
                category="新鲜果蔬",
                quantity_desc="适量",
                expire_days=5,
                created_at=now,
            ),
            FridgeInventory(
                user_id=uid,
                ingredient_name="S04鸡蛋",
                category="肉禽蛋奶",
                quantity_desc="适量",
                expire_days=5,
                created_at=now,
            ),
            FridgeInventory(
                user_id=uid,
                ingredient_name="S04牛肉",
                category="肉禽蛋奶",
                quantity_desc="适量",
                expire_days=1,
                created_at=now - timedelta(days=2),
            ),
            FridgeInventory(
                user_id=uid,
                ingredient_name="S04葱",
                category="新鲜果蔬",
                quantity_desc="适量",
                expire_days=5,
                created_at=now,
            ),
        ]
    )
    db.commit()

    result = build_shopping_list(db, uid, [first, second, third, first], now=now)
    owned = result["owned_ingredients"]
    to_buy = result["to_buy_ingredients"]
    assert len(owned) == len(set(owned))
    assert len(to_buy) == len(set(to_buy))
    assert set(owned) == {"S04番茄", "S04鸡蛋"}
    assert set(to_buy) == {"S04盐", "S04土豆", "S04油", "S04牛肉"}
    assert set(owned).isdisjoint(to_buy)
    assert "S04牛肉" not in owned  # 过期库存不抵扣
    assert "S04葱" not in owned and "S04葱" not in to_buy


def test_s04_lazy_one_pot_has_no_speed_threshold(db):
    result = recommend_single(
        db, 2, "HOME_COOKING", bubbles=["lazy_one_pot"], limit=100
    )
    ids = _ids(result)
    slow_one_pot = (
        db.query(Dish).filter(Dish.name == "一锅出番茄牛腩").one()
    )
    slow_rice = (
        db.query(Dish)
        .filter(Dish.name == "电饭煲红烧肉", Dish.mode_type == "HOME_COOKING")
        .first()
    )
    fast_cold = (
        db.query(Dish)
        .filter(Dish.name == "凉拌黄瓜", Dish.mode_type == "HOME_COOKING")
        .first()
    )
    fast_fryer = (
        db.query(Dish)
        .filter(Dish.name == "空气炸锅鸡翅", Dish.mode_type == "HOME_COOKING")
        .first()
    )

    assert slow_one_pot.feature_vector["prep_speed"] < 0.5
    assert slow_one_pot.id in ids, "一锅出低速度菜必须保留（无速度门槛）"
    if slow_rice is not None:
        assert slow_rice.feature_vector["prep_speed"] < 0.5
        assert slow_rice.id in ids
    if fast_cold is not None:
        assert fast_cold.feature_vector["prep_speed"] >= 0.8
        assert fast_cold.id not in ids, "免开火凉拌不在白名单"
    if fast_fryer is not None:
        assert fast_fryer.id not in ids, "空气炸锅不在白名单"

    allowed = {"电饭煲", "一锅出"}
    for item in result["recommendations"]:
        dish = db.query(Dish).filter(Dish.id == item["dish_id"]).one()
        tags = dish.appliance_tag if isinstance(dish.appliance_tag, list) else []
        assert set(tags) & allowed


# --------------------------------------------------------------------------- #
# E. N04 / D-S04-01（方案 A）：NULL 向量不进入候选、先验与结算
# --------------------------------------------------------------------------- #


def test_s04_null_vector_excluded_from_single_and_shortlist(db):
    uid = _make_user(db, "s04_null_user", NEUTRAL)
    tagged = _make_dish(
        db, "S04已打标对照", vector=NEUTRAL, price=0.0, mains=["S04对照料"]
    )
    unlabeled = _make_dish(
        db, "S04未打标菜", vector=None, price=0.0, mains=["S04未打标料"]
    )
    null_count = (
        db.query(Dish)
        .filter(
            Dish.mode_type == "OUT_DINING",
            Dish.feature_vector.is_(None),
        )
        .count()
    )
    assert null_count == 1, f"隔离库应有 1 道 NULL 向量菜，实际 {null_count}"

    single = recommend_single(db, uid, "OUT_DINING", limit=200)
    single_ids = _ids(single)
    assert tagged in single_ids
    assert unlabeled not in single_ids, "NULL 向量菜不得进入单人推荐"

    shortlist = shortlist_candidates(db, [uid], "OUT_DINING", top_n=200)
    shortlist_ids = {int(item["dish_id"]) for item in shortlist}
    assert tagged in shortlist_ids
    assert unlabeled not in shortlist_ids, "NULL 向量菜不得进入群组初筛"


def test_s04_null_vector_excluded_from_priors_and_consensus(db):
    uid = _make_user(db, "s04_null_group", NEUTRAL)
    tagged = _make_dish(
        db, "S04群组已打标", vector=NEUTRAL, mains=["S04群组料"]
    )
    unlabeled = _make_dish(
        db, "S04群组未打标", vector=None, mains=["S04群组未打标料"]
    )
    from backend.algorithms.group_recommender import member_prior_scores

    priors = member_prior_scores(db, [uid], [tagged, unlabeled])
    assert unlabeled not in priors[uid]
    assert priors[uid][tagged] == pytest.approx(100.0, abs=0.01)

    candidate_ids = [tagged, unlabeled]
    excluded_count = sum(
        1
        for dish_id in candidate_ids
        if db.query(Dish).filter(Dish.id == dish_id).one().feature_vector is None
    )
    assert excluded_count == 1, "证据：本样本有 1 道 NULL 候选被排除"

    votes = [
        _vote(uid, tagged, "LIKE"),
        _vote(uid, unlabeled, "LIKE"),
    ]
    report = compute_group_consensus(
        db, [uid], candidate_ids, votes, omega_group=0.5
    )
    assert [item["dish_id"] for item in report["dishes"]] == [tagged]
    assert report["winner_dish_id"] == tagged
    assert report["has_consensus"] is True
    assert report["dishes"][0]["group_score"] == pytest.approx(100.0, abs=0.01)


def test_s04_null_only_candidates_keep_existing_empty_semantics():
    """只有 NULL 向量候选时：单人空结果、初筛空列表、群组无共识，不反向补菜。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from backend.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        uid = _make_user(session, "s04_null_only", NEUTRAL)
        unlabeled = _make_dish(
            session, "S04唯一未打标", vector=None, mains=["S04唯一料"]
        )

        single = recommend_single(
            session, uid, "OUT_DINING", limit=10, combo_mode=True
        )
        assert single["recommendations"] == []
        assert single["combo"] is None

        assert shortlist_candidates(
            session, [uid], "OUT_DINING", top_n=10
        ) == []

        report = compute_group_consensus(
            session,
            [uid],
            [unlabeled],
            [_vote(uid, unlabeled, "LIKE")],
            omega_group=0.5,
        )
        assert report["winner_dish_id"] is None
        assert report["has_consensus"] is False
        assert report["dishes"] == []
        null_count = (
            session.query(Dish)
            .filter(
                Dish.mode_type == "OUT_DINING",
                Dish.feature_vector.is_(None),
            )
            .count()
        )
        assert null_count == 1, "证据：唯一候选就是被排除的 NULL 菜"
    finally:
        session.close()
        engine.dispose()


def test_s04_combo_module_is_documented_as_role_enumeration():
    source = (
        Path(__file__).resolve().parents[1]
        / "algorithms"
        / "combo_optimizer.py"
    ).read_text(encoding="utf-8")
    assert "改进背包" not in source
    assert "动态规划" not in source
    assert "Top-20" in source or "Top-N" in source
