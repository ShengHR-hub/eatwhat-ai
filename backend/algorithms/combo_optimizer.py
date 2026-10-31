"""算法 4：一荤一素一汤套餐——Top-20 角色分组枚举 + 约束筛选（MASTER_SPEC v2.3.5 第四章）。"""

from datetime import datetime
from typing import Dict, List, Mapping, Optional, Sequence

from sqlalchemy.orm import Session

from . import fridge_clock
from ..models import Dish, FridgeInventory

ROLES = ("MEAT", "VEG", "SOUP")
MAX_AVG_OILY = 0.65
TOP_N = 20
EPS = 1e-9


def optimize_combo(
    candidates: Sequence[Mapping[str, object]],
    budget: float,
    max_avg_oily: float = MAX_AVG_OILY,
    top_n: int = TOP_N,
) -> Optional[Dict[str, object]]:
    """在 Top-20 内按 MEAT/VEG/SOUP 角色分组枚举，筛选目标得分最大的合法套餐。

    约束：各角色一道、总价 <= budget、三道平均 oily_level <= max_avg_oily。
    实现用「上界得分 + 下界价格」剪枝加速，行为等价于三元组枚举；论文与答辩
    口径按 SSOT 称「角色分组枚举 + 约束筛选」。
    """
    if budget <= 0:
        return None
    ranked = sorted(
        candidates, key=lambda item: -float(item.get("score", 0.0))
    )[:top_n]
    by_role: Dict[str, List[Mapping[str, object]]] = {
        role: [item for item in ranked if item.get("dish_role") == role]
        for role in ROLES
    }
    if any(not by_role[role] for role in ROLES):
        return None

    suffix_max_score = [0.0, 0.0, 0.0, 0.0]
    suffix_min_price = [0.0, 0.0, 0.0, 0.0]
    for index in range(len(ROLES) - 1, -1, -1):
        role_items = by_role[ROLES[index]]
        suffix_max_score[index] = suffix_max_score[index + 1] + max(
            float(item.get("score", 0.0)) for item in role_items
        )
        suffix_min_price[index] = suffix_min_price[index + 1] + min(
            float(item.get("price", 0.0)) for item in role_items
        )

    best_score = float("-inf")
    best_choice: List[Mapping[str, object]] = []

    def search(
        role_index: int,
        chosen: List[Mapping[str, object]],
        price_sum: float,
        oily_sum: float,
        score_sum: float,
    ) -> None:
        nonlocal best_score, best_choice
        if price_sum > budget + EPS:
            return
        if oily_sum > max_avg_oily * len(ROLES) + EPS:
            return
        if role_index == len(ROLES):
            if score_sum > best_score:
                best_score = score_sum
                best_choice = list(chosen)
            return
        if score_sum + suffix_max_score[role_index] <= best_score + EPS:
            return
        if price_sum + suffix_min_price[role_index] > budget + EPS:
            return

        for item in by_role[ROLES[role_index]]:
            item_price = float(item.get("price", 0.0))
            item_oily = float(item.get("oily_level", 0.0))
            if price_sum + item_price > budget + EPS:
                continue
            if oily_sum + item_oily > max_avg_oily * len(ROLES) + EPS:
                continue
            chosen.append(item)
            search(
                role_index + 1,
                chosen,
                price_sum + item_price,
                oily_sum + item_oily,
                score_sum + float(item.get("score", 0.0)),
            )
            chosen.pop()

    search(0, [], 0.0, 0.0, 0.0)
    if not best_choice:
        return None

    total_price = sum(float(item.get("price", 0.0)) for item in best_choice)
    avg_oily = sum(float(item.get("oily_level", 0.0)) for item in best_choice) / len(
        ROLES
    )
    return {
        "dish_ids": [int(item["dish_id"]) for item in best_choice],
        "dishes": [
            {
                "dish_id": int(item["dish_id"]),
                "name": str(item["name"]),
                "dish_role": str(item["dish_role"]),
                "price": round(float(item.get("price", 0.0)), 2),
                "score": round(float(item.get("score", 0.0)), 2),
            }
            for item in best_choice
        ],
        "total_price": round(total_price, 2),
        "avg_oily_level": round(avg_oily, 3),
        "total_score": round(best_score, 2),
    }


def build_shopping_list(
    db: Session,
    user_id: int,
    dish_ids: Sequence[int],
    now: Optional[datetime] = None,
) -> Dict[str, List[str]]:
    """菜谱主辅料并集 - 冰箱现有食材，去重合并同类项后返回差额清单。

    S03：与冰箱列表 / 推荐共用 `fridge_clock`，过期库存不抵扣采购。
    """
    dishes = db.query(Dish).filter(Dish.id.in_(list(dish_ids))).all()
    required: List[str] = []
    seen: set[str] = set()
    for dish in dishes:
        for raw in list(dish.ingredients_main or []) + list(dish.ingredients_aux or []):
            name = str(raw).strip()
            if name and name not in seen:
                seen.add(name)
                required.append(name)

    current = now if now is not None else fridge_clock.now_utc()
    fridge_names = [
        str(item.ingredient_name).strip()
        for item in db.query(FridgeInventory)
        .filter(FridgeInventory.user_id == user_id)
        .all()
        if str(item.ingredient_name).strip()
        and not fridge_clock.is_expired(item, current)
    ]

    owned: List[str] = []
    to_buy: List[str] = []
    for ingredient in required:
        if any(
            name in ingredient or ingredient in name for name in fridge_names
        ):
            owned.append(ingredient)
        else:
            to_buy.append(ingredient)
    return {"owned_ingredients": owned, "to_buy_ingredients": to_buy}
