from backend.algorithms.combo_optimizer import build_shopping_list, optimize_combo


def _item(dish_id, role, price, score, oily):
    return {
        "dish_id": dish_id,
        "name": f"dish-{dish_id}",
        "dish_role": role,
        "price": price,
        "score": score,
        "oily_level": oily,
    }


def test_branch_and_bound_picks_feasible_best():
    candidates = [
        _item(1, "MEAT", 10, 50, 0.2),
        _item(2, "MEAT", 30, 90, 0.2),
        _item(3, "VEG", 5, 60, 0.2),
        _item(4, "SOUP", 5, 40, 0.2),
    ]
    tight = optimize_combo(candidates, budget=35)
    assert [dish["dish_id"] for dish in tight["dishes"]] == [1, 3, 4]
    looser = optimize_combo(candidates, budget=45)
    assert [dish["dish_id"] for dish in looser["dishes"]] == [2, 3, 4]


def test_oily_constraint_is_enforced():
    candidates = [
        _item(1, "MEAT", 10, 100, 0.9),
        _item(2, "MEAT", 10, 50, 0.2),
        _item(3, "VEG", 10, 90, 0.9),
        _item(4, "VEG", 10, 60, 0.2),
        _item(5, "SOUP", 10, 40, 0.2),
    ]
    result = optimize_combo(candidates, budget=100)
    roles = {dish["dish_role"]: dish["dish_id"] for dish in result["dishes"]}
    assert roles["VEG"] == 4
    assert result["avg_oily_level"] <= 0.65


def test_infeasible_or_missing_role_returns_none():
    candidates = [
        _item(1, "MEAT", 10, 50, 0.2),
        _item(3, "VEG", 5, 60, 0.2),
        _item(4, "SOUP", 5, 40, 0.2),
    ]
    assert optimize_combo(candidates, budget=1) is None
    assert optimize_combo(candidates[:2], budget=100) is None


def test_shopping_list_subtracts_fridge(db):
    from backend.models import Dish

    names = ["番茄炒蛋", "凉拌黄瓜", "紫菜蛋花汤"]
    ids = [
        db.query(Dish)
        .filter(Dish.name == name, Dish.mode_type == "HOME_COOKING")
        .first()
        .id
        for name in names
    ]
    result = build_shopping_list(db, 2, ids)
    assert "番茄" in result["owned_ingredients"]
    assert "鸡蛋" in result["owned_ingredients"]
    assert "紫菜" in result["to_buy_ingredients"]
    assert not set(result["owned_ingredients"]) & set(result["to_buy_ingredients"])
