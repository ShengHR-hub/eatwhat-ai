"""算法 3：融合最小痛苦策略（Least Misery）的群组协同博弈（MASTER_SPEC v2.3.2 第四章）。"""

from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from sqlalchemy.orm import Session

from ..models import Dish, Restaurant, UserPreference
from .veto_rules import hits as veto_hits
from .vector_spec import (
    DEFAULT_FEATURE_VECTOR,
    TIMEOUT_SWIPE_SCORE,
    VOTE_SCORES,
    mean_vector,
    normalize_vector,
    similarity_to_100,
)

PRIOR_WEIGHT = 0.4
SWIPE_WEIGHT = 0.6


def _ingredient_set(values: Optional[Iterable[str]]) -> set[str]:
    return {str(v).strip() for v in (values or []) if str(v).strip()}


def _hit_veto(ingredients: set[str], veto_tags: Iterable[str]) -> bool:
    """F01 修复：与单人推荐共用 `veto_rules`，避免两份规则各自漂移。"""
    return veto_hits(ingredients, veto_tags)


def _load_preferences(
    db: Session, member_ids: Sequence[int]
) -> Dict[int, UserPreference]:
    if not member_ids:
        return {}
    rows = (
        db.query(UserPreference)
        .filter(UserPreference.user_id.in_(list(member_ids)))
        .all()
    )
    return {row.user_id: row for row in rows}


def _member_vector(prefs: Optional[UserPreference]) -> Dict[str, float]:
    if prefs is None:
        return dict(DEFAULT_FEATURE_VECTOR)
    return normalize_vector(prefs.base_vector)


def shortlist_candidates(
    db: Session,
    member_ids: Sequence[int],
    mode_type: str,
    top_n: int = 10,
    max_distance_meters: Optional[int] = None,
    budget: Optional[float] = None,
    campus: Optional[str] = None,
) -> List[Dict[str, object]]:
    """阶段一：按全体成员忌口/黑榜并集过滤，以 base_vector 均值选 Top-N。

    `budget`：v2.3.2 契约（规格第 315 行）建房时带预算，外食候选只保留
    价格不超过预算 1.25 倍的菜；下厨模式按成本同样处理。

    `campus`：v2.3.6 起外食候选严格按 `restaurant.campus == campus` 过滤；
    NULL 门店、无门店或找不到门店的外食菜品一律排除，不得默认共享。
    下厨菜谱共享，不做校区过滤。`campus=None` 只用于历史房间未绑定校区的
    过渡读取/独立算法测试，不表示“跨校区共享”。
    """
    member_ids = [int(uid) for uid in member_ids]
    preferences = _load_preferences(db, member_ids)
    veto_union: set[str] = set()
    blacklist_union: set[int] = set()
    restaurant_blacklist_union: set[int] = set()
    for prefs in preferences.values():
        veto_union.update(str(tag) for tag in (prefs.veto_tags or []))
        blacklist_union.update(int(i) for i in (prefs.blacklist_dish_ids or []))
        # v2.3.1：群组取全体成员两类黑榜的并集
        restaurant_blacklist_union.update(
            int(i) for i in (getattr(prefs, "blacklist_restaurant_ids", None) or [])
        )
    mean_member_vector = mean_vector(
        [_member_vector(preferences.get(uid)) for uid in member_ids]
    )

    # 软删除必须在这里挡住：后台 DELETE 只写 deleted_at，
    # 少了这个过滤，下架的菜/店照样会被推荐（独立审查 2026-10-31 P2）。
    dishes = (
        db.query(Dish)
        .filter(Dish.mode_type == mode_type, Dish.deleted_at.is_(None))
        .order_by(Dish.id)
        .all()
    )
    restaurant_map: Dict[int, Restaurant] = {}
    if mode_type == "OUT_DINING":
        restaurant_map = {
            r.id: r
            for r in db.query(Restaurant).filter(Restaurant.deleted_at.is_(None)).all()
        }

    scored: List[Dict[str, object]] = []
    for dish in dishes:
        if dish.id in blacklist_union:
            continue
        # D-S04-01（方案 A）：未打标菜品不进入群组初筛候选。
        if dish.feature_vector is None:
            continue
        if (
            mode_type == "OUT_DINING"
            and dish.restaurant_id is not None
            and int(dish.restaurant_id) in restaurant_blacklist_union
        ):
            continue
        # v2.3.6：外食候选严格按校区过滤；NULL/缺失门店不默认共享给任一校区。
        if campus is not None and mode_type == "OUT_DINING":
            store = (
                restaurant_map.get(int(dish.restaurant_id))
                if dish.restaurant_id is not None
                else None
            )
            if store is None or store.campus is None or str(store.campus) != str(campus):
                continue
        ingredients = _ingredient_set(dish.ingredients_main) | _ingredient_set(
            dish.ingredients_aux
        )
        if _hit_veto(ingredients, veto_union):
            continue
        # 建房时带来的预算：软上限（1.25 倍），别把候选池一刀切空
        if budget is not None and float(budget) > 0:
            price = float(dish.price_or_cost or 0.0)
            if price > float(budget) * 1.25:
                continue
        if max_distance_meters is not None and mode_type == "OUT_DINING":
            restaurant = restaurant_map.get(dish.restaurant_id)
            if restaurant is not None and (restaurant.distance_meters or 0) > max_distance_meters:
                continue
        vector = normalize_vector(dish.feature_vector)
        scored.append(
            {
                "dish_id": dish.id,
                "name": dish.name,
                "prior_score": similarity_to_100(mean_member_vector, vector),
                "feature_vector": vector,
                "price": float(dish.price_or_cost or 0.0),
            }
        )
    scored.sort(key=lambda item: (-float(item["prior_score"]), int(item["dish_id"])))
    return scored[: max(1, top_n)]


def member_prior_scores(
    db: Session,
    member_ids: Sequence[int],
    dish_ids: Sequence[int],
) -> Dict[int, Dict[int, float]]:
    preferences = _load_preferences(db, member_ids)
    # D-S04-01（方案 A）：NULL 向量不参与先验计算，也不返回 0.5 默认分。
    dishes = (
        db.query(Dish)
        .filter(Dish.id.in_(list(dish_ids)), Dish.feature_vector.isnot(None))
        .all()
    )
    result: Dict[int, Dict[int, float]] = {}
    for uid in member_ids:
        vector = _member_vector(preferences.get(int(uid)))
        result[int(uid)] = {
            dish.id: similarity_to_100(vector, normalize_vector(dish.feature_vector))
            for dish in dishes
        }
    return result


def _vote_attributes(vote: object) -> tuple[int, int, str]:
    if isinstance(vote, Mapping):
        return int(vote["user_id"]), int(vote["dish_id"]), str(vote["vote_type"])
    return int(vote.user_id), int(vote.dish_id), str(vote.vote_type)


def compute_group_consensus(
    db: Session,
    member_ids: Sequence[int],
    candidate_dish_ids: Sequence[int],
    votes: Sequence[object],
    omega_group: float = 0.5,
) -> Dict[str, object]:
    """阶段二：R = 0.4*prior + 0.6*swipe；G = Mask_veto*(ω*mean + (1-ω)*min)。

    D-S04-01（方案 A）：`feature_vector IS NULL` 的候选不参与先验/结算，也不能
    在候选不足时回退成 0.5 默认向量参与竞争。被排除数量只在测试与证据中记录，
    不改变既有响应契约。
    """
    member_ids = [int(uid) for uid in member_ids]
    dish_ids = [int(i) for i in candidate_dish_ids]
    omega_group = max(0.0, min(1.0, float(omega_group)))
    vote_map: Dict[tuple[int, int], str] = {}
    for vote in votes:
        uid, dish_id, vote_type = _vote_attributes(vote)
        vote_map[(uid, dish_id)] = vote_type.upper()

    dish_rows = db.query(Dish).filter(Dish.id.in_(dish_ids)).all()
    dishes = {
        dish.id: dish for dish in dish_rows if dish.feature_vector is not None
    }
    priors = member_prior_scores(db, member_ids, list(dishes.keys()))

    reports: List[Dict[str, object]] = []
    for dish_id in dish_ids:
        if dish_id not in dishes:
            continue
        member_reports: List[Dict[str, object]] = []
        satisfaction_values: List[float] = []
        masked = False
        for uid in member_ids:
            vote_type = vote_map.get((uid, dish_id), "TIMEOUT")
            if vote_type == "VETO":
                # SSOT：VETO 只作为淘汰掩码，不参与任何分值映射。
                masked = True
                satisfaction = 0.0
            else:
                swipe = VOTE_SCORES.get(vote_type, TIMEOUT_SWIPE_SCORE)
                prior = priors.get(uid, {}).get(dish_id, 0.0)
                satisfaction = PRIOR_WEIGHT * prior + SWIPE_WEIGHT * swipe
                satisfaction_values.append(satisfaction)
            member_reports.append(
                {
                    "user_id": uid,
                    "satisfaction": round(satisfaction, 2),
                    "vote_type": vote_type,
                }
            )

        mean_satisfaction = (
            sum(satisfaction_values) / len(satisfaction_values)
            if satisfaction_values
            else 0.0
        )
        least_misery = min(satisfaction_values) if satisfaction_values else 0.0
        group_score = (
            0.0
            if masked
            else omega_group * mean_satisfaction
            + (1.0 - omega_group) * least_misery
        )
        reports.append(
            {
                "dish_id": dish_id,
                "group_score": round(group_score, 2),
                "mean_satisfaction": round(mean_satisfaction, 2),
                "least_misery": round(least_misery, 2),
                "masked_by_veto": masked,
                "members": member_reports,
            }
        )

    reports.sort(
        key=lambda item: (-float(item["group_score"]), int(item["dish_id"]))
    )
    # F02 修复：被否决的菜必须退出胜出集合。
    # 历史实现直接取 reports[0]，而 masked_by_veto 的菜 group_score 恒为 0.0，
    # 当所有候选都被否决时，排序后仍会"选"出一道全票否决的菜 —— 语义上是错的。
    eligible = [item for item in reports if not item["masked_by_veto"]]
    winner = eligible[0] if eligible else None
    vetoed_dish_ids = [int(item["dish_id"]) for item in reports if item["masked_by_veto"]]
    return {
        "winner_dish_id": int(winner["dish_id"]) if winner else None,
        "winner_group_score": float(winner["group_score"]) if winner else 0.0,
        # has_consensus=False 时 winner 为 None，调用方必须给出"没谈拢"的明确结果，
        # 而不是把 0 分当成推荐结果发出去。
        "has_consensus": bool(eligible),
        "vetoed_dish_ids": vetoed_dish_ids,
        "omega_group": omega_group,
        "dishes": reports,
    }
