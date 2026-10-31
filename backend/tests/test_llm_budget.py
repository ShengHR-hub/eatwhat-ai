"""S11 付费调用硬预算回归。"""

from __future__ import annotations

import pytest

from backend.algorithms.vector_spec import FEATURE_KEYS
from backend.scripts.llm_batch_tagger import BudgetTracker, collect_dishes, validate_batch


def test_budget_tracker_uses_actual_usage_rates():
    tracker = BudgetTracker(1.0, input_usd_per_m=2.0, output_usd_per_m=10.0)

    cost = tracker.add_usage(
        {"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000}}
    )

    assert cost == pytest.approx(7.0)
    assert tracker.input_tokens == 1_000_000
    assert tracker.output_tokens == 500_000
    assert tracker.calls == 1
    assert tracker.spent_usd == pytest.approx(7.0)
    assert tracker.exhausted is True


def test_budget_tracker_does_not_exhaust_before_limit():
    tracker = BudgetTracker(0.9, input_usd_per_m=0.06, output_usd_per_m=0.3)

    tracker.add_usage({"usage": {"prompt_tokens": 1_700, "completion_tokens": 1_800}})

    assert tracker.spent_usd < 0.9
    assert tracker.exhausted is False


def test_budget_tracker_accepts_alternative_usage_keys():
    tracker = BudgetTracker(1.0, input_usd_per_m=1.0, output_usd_per_m=2.0)

    cost = tracker.add_usage({"usage": {"input_tokens": 1000, "output_tokens": 500}})

    assert cost == pytest.approx(0.002)


def test_budget_tracker_rejects_non_positive_budget():
    with pytest.raises(ValueError, match="budget_usd_must_be_positive"):
        BudgetTracker(0, input_usd_per_m=1.0, output_usd_per_m=2.0)


def _batch_item():
    return {
        "dish_id": 1,
        "name": "番茄炒蛋",
        "cuisine_type": "家常菜",
        "ingredients_main": ["番茄", "鸡蛋"],
        "ingredients_aux": [],
    }


def test_validate_batch_uses_dish_name_contract():
    import json

    response = [{
        "dish_name": "番茄炒蛋",
        "dish_role": "ONE_MEAL",
        "feature_vector": {key: 0.5 for key in FEATURE_KEYS},
        "allergen_tags": ["鸡蛋"],
    }]

    validated, reason = validate_batch(json.dumps(response), [_batch_item()])

    assert reason == ""
    assert validated[0]["dish_id"] == 1
    assert validated[0]["dish_role"] == "ONE_MEAL"


def test_validate_batch_missing_dish_name_is_clean_failure():
    import json

    response = [{"dish_role": "ONE_MEAL"}]

    validated, reason = validate_batch(json.dumps(response), [_batch_item()])

    assert validated is None
    assert reason == "missing_dish:番茄炒蛋"


def test_collect_dishes_shards_are_disjoint_and_complete(session_factory):
    with session_factory() as session:
        all_ids = {row["dish_id"] for row in collect_dishes(session, False, 0)}
        shard_zero = {row["dish_id"] for row in collect_dishes(session, False, 0, 0, 2)}
        shard_one = {row["dish_id"] for row in collect_dishes(session, False, 0, 1, 2)}

    assert shard_zero.isdisjoint(shard_one)
    assert shard_zero | shard_one == all_ids
