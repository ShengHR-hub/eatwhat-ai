from backend.algorithms.group_recommender import (
    compute_group_consensus,
    shortlist_candidates,
)
from backend.models import Dish

VETO_UNION = {"折耳根", "海鲜", "香菜", "花生"}


def _dish(db, name: str) -> Dish:
    dish = (
        db.query(Dish)
        .filter(Dish.name == name, Dish.mode_type == "OUT_DINING")
        .first()
    )
    assert dish is not None
    return dish


def _dish_hits_veto(dish: Dish) -> bool:
    ingredients = list(dish.ingredients_main or []) + list(dish.ingredients_aux or [])
    return any(
        tag in ingredient or ingredient in tag
        for tag in VETO_UNION
        for ingredient in ingredients
    )


def test_shortlist_uses_union_veto_and_blacklist(db):
    shortlist = shortlist_candidates(db, [1, 2, 3, 4], "OUT_DINING", top_n=10)
    assert len(shortlist) == 10
    for item in shortlist:
        dish = db.query(Dish).filter(Dish.id == item["dish_id"]).first()
        assert not _dish_hits_veto(dish)
    ids = {item["dish_id"] for item in shortlist}
    assert _dish(db, "麻辣香锅").id not in ids  # 用户 2 黑榜
    assert _dish(db, "白切鸡饭").id not in ids  # 用户 1 黑榜
    assert _dish(db, "凉拌折耳根").id not in ids  # 用户 1 忌口


def test_veto_masks_dish_and_winner_is_consensus(db):
    winner = _dish(db, "兰州牛肉拉面")
    vetoed = _dish(db, "老火靓汤")
    votes = [
        {"user_id": 1, "dish_id": winner.id, "vote_type": "LIKE"},
        {"user_id": 2, "dish_id": winner.id, "vote_type": "LIKE"},
        {"user_id": 3, "dish_id": winner.id, "vote_type": "SUPER_LIKE"},
        {"user_id": 4, "dish_id": winner.id, "vote_type": "PASS"},
        {"user_id": 1, "dish_id": vetoed.id, "vote_type": "SUPER_LIKE"},
        {"user_id": 2, "dish_id": vetoed.id, "vote_type": "VETO"},
        {"user_id": 3, "dish_id": vetoed.id, "vote_type": "LIKE"},
        {"user_id": 4, "dish_id": vetoed.id, "vote_type": "LIKE"},
    ]
    report = compute_group_consensus(
        db, [1, 2, 3, 4], [winner.id, vetoed.id], votes, omega_group=0.5
    )
    assert report["winner_dish_id"] == winner.id
    vetoed_report = next(
        item for item in report["dishes"] if item["dish_id"] == vetoed.id
    )
    assert vetoed_report["masked_by_veto"] is True
    assert vetoed_report["group_score"] == 0.0
    veto_member = next(
        member for member in vetoed_report["members"] if member["user_id"] == 2
    )
    assert veto_member["vote_type"] == "VETO"


def test_omega_interpolates_mean_and_least_misery(db):
    dish = _dish(db, "兰州牛肉拉面")
    votes = [
        {"user_id": 1, "dish_id": dish.id, "vote_type": "SUPER_LIKE"},
        {"user_id": 2, "dish_id": dish.id, "vote_type": "LIKE"},
        {"user_id": 3, "dish_id": dish.id, "vote_type": "PASS"},
        {"user_id": 4, "dish_id": dish.id, "vote_type": "LIKE"},
    ]
    mean_report = compute_group_consensus(
        db, [1, 2, 3, 4], [dish.id], votes, omega_group=1.0
    )["dishes"][0]
    misery_report = compute_group_consensus(
        db, [1, 2, 3, 4], [dish.id], votes, omega_group=0.0
    )["dishes"][0]
    assert mean_report["group_score"] == mean_report["mean_satisfaction"]
    assert misery_report["group_score"] == misery_report["least_misery"]
    assert mean_report["least_misery"] <= mean_report["mean_satisfaction"]


def test_missing_vote_defaults_to_timeout_score(db):
    dish = _dish(db, "兰州牛肉拉面")
    votes = [
        {"user_id": 1, "dish_id": dish.id, "vote_type": "LIKE"},
        {"user_id": 2, "dish_id": dish.id, "vote_type": "LIKE"},
        {"user_id": 3, "dish_id": dish.id, "vote_type": "LIKE"},
    ]
    report = compute_group_consensus(
        db, [1, 2, 3, 4], [dish.id], votes, omega_group=0.5
    )
    member = next(
        item for item in report["dishes"][0]["members"] if item["user_id"] == 4
    )
    assert member["vote_type"] == "TIMEOUT"
    assert member["satisfaction"] > 0
