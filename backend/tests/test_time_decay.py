import pytest

from backend.algorithms.time_decay import (
    SAME_DAY_WEIGHT,
    _decay_formula,
    compute_decay_weights,
)
from backend.models import Dish, utcnow


def _dish(db, name: str, mode: str = "OUT_DINING") -> Dish:
    dish = (
        db.query(Dish)
        .filter(Dish.name == name, Dish.mode_type == mode)
        .first()
    )
    assert dish is not None, f"缺少种子菜品 {name}"
    return dish


def test_same_day_forces_min_weight(db):
    dish = _dish(db, "麻辣香锅")
    weights = compute_decay_weights(db, 1, [dish], lambda_decay=0.5, now=utcnow())
    assert weights[dish.id] == SAME_DAY_WEIGHT


def test_exact_and_similar_share_formula(db):
    dish = _dish(db, "水煮鱼")
    weights = compute_decay_weights(db, 1, [dish], lambda_decay=0.5, now=utcnow())
    expected = _decay_formula(0.5, 3, 0)
    assert weights[dish.id] == pytest.approx(expected, rel=1e-4)


def test_similar_only_penalises_without_exact_hit(db):
    dish = _dish(db, "辣子鸡")
    weights = compute_decay_weights(db, 1, [dish], lambda_decay=0.5, now=utcnow())
    assert weights[dish.id] == pytest.approx(0.6, rel=1e-4)


def test_unrelated_dish_stays_fresh(db):
    dish = _dish(db, "白切鸡饭")
    weights = compute_decay_weights(db, 1, [dish], lambda_decay=0.5, now=utcnow())
    assert weights[dish.id] == 1.0


def test_user_without_logs_gets_full_weight(db):
    dish = _dish(db, "麻辣香锅")
    weights = compute_decay_weights(db, 999, [dish], lambda_decay=0.5, now=utcnow())
    assert weights[dish.id] == 1.0


def test_formula_boundaries():
    assert _decay_formula(0.5, None, None) == 1.0
    assert _decay_formula(0.5, 0, 0) == SAME_DAY_WEIGHT
    assert _decay_formula(0.5, 14, None) > 0.99
