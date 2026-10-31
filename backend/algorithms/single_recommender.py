"""算法 2：多维上下文单人效用推荐与红黑榜修正（MASTER_SPEC v2.3.2 第四章）。"""

import math
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from ..config import DEFAULT_ALGO_PARAMS, current_algo_params
from ..models import AlgoConfig, Dish, FridgeInventory, Restaurant, UserPreference
from . import fridge_clock
from .combo_optimizer import optimize_combo
from .time_decay import compute_decay_weights
from .veto_rules import hits as veto_hits
from .vector_spec import (
    build_explain_reason,
    light_healthy_hits,
    normalize_vector,
    resolve_bubble_effects,
    similarity_to_100,
    target_match_score,
    weather_match_score,
)

FAVORITE_BOOST = 1.15
PARAM_KEYS = (
    "lambda_decay",
    "omega_group",
    "alpha_taste",
    "beta_weather",
    "gamma_budget",
    "delta_status",
)
WEIGHT_KEYS = ("alpha_taste", "beta_weather", "gamma_budget", "delta_status")


def _normalize_weights(params: Dict[str, float]) -> Dict[str, float]:
    clipped = {key: max(0.0, float(params[key])) for key in WEIGHT_KEYS}
    total = sum(clipped.values())
    if total <= 0.0:
        clipped = {key: max(0.0, float(current_algo_params()[key])) for key in WEIGHT_KEYS}
        total = sum(clipped.values())
    if total <= 0.0:
        # 运行期缓存本身也被改成全 0（后台允许 0–1 任意值，包括 0）。
        # 此时再除就是 ZeroDivisionError，会让每一笔推荐 500。
        # 退化成等权保证接口可用；后台侧同时拒绝"四权重全 0"的提交。
        clipped = {key: 0.25 for key in WEIGHT_KEYS}
        total = 1.0
    for key in WEIGHT_KEYS:
        params[key] = clipped[key] / total
    return params


def _ingredient_set(values: Optional[Iterable[str]]) -> set[str]:
    return {str(v).strip() for v in (values or []) if str(v).strip()}


def _hit_veto(ingredients: set[str], veto_tags: Sequence[str]) -> bool:
    """F01 修复：忌口匹配统一走 `veto_rules`（类别词表 + 别名展开）。

    历史实现在这里做双向子串匹配，导致用户写「海鲜」、菜谱写「鲜虾/虾皮」时
    互相不包含而漏判。现在两处调用（单人推荐、群组初筛）共用同一套规则。
    """
    return veto_hits(ingredients, veto_tags)


def _appliance_set(value: object) -> set[str]:
    """appliance_tag 兼容 JSON 数组与历史单值字符串两种存储形态。"""
    if value is None:
        return set()
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    if isinstance(value, (list, tuple, set)):
        return {str(v).strip() for v in value if str(v).strip()}
    return set()


def _budget_score(price: float, budget: float) -> float:
    if budget <= 0:
        return 0.0
    if price <= budget:
        return round(85.0 + 15.0 * (1.0 - price / budget), 2)
    over_ratio = (price - budget) / budget
    return round(max(0.0, 85.0 * math.exp(-3.0 * over_ratio)), 2)


def _fridge_index(
    db: Session, user_id: int, now: Optional[datetime] = None
) -> List[tuple[str, float]]:
    """一次查出这台冰箱，返回 [(食材名, 权重)]。

    审查 R01：原实现每个候选菜都查一次 `fridge_inventory`，40 道下厨菜 = 40 次
    SELECT，加在一起一次推荐 45 次查询。批次 4 要压万人数据，这种 N+1 会把基准
    测糊。改成循环外查一次、循环内纯内存匹配。

    S03：过期跳过、临期双倍都统一走 `fridge_clock`；`now` 与衰减共用同一时点。
    """
    items = db.query(FridgeInventory).filter(FridgeInventory.user_id == user_id).all()
    current = now if now is not None else fridge_clock.now_utc()
    index: List[tuple[str, float]] = []
    for item in items:
        name = str(item.ingredient_name).strip()
        if not name:
            continue
        if fridge_clock.is_expired(item, current):
            continue
        index.append(
            (name, 2.0 if fridge_clock.is_expiring_soon(item, current) else 1.0)
        )
    return index


def _fridge_status_from_index(index: Sequence[tuple[str, float]], dish: Dish) -> float:
    """纯内存计算：用预取的冰箱索引给菜品打「用现有食材」分。"""
    mains = _ingredient_set(dish.ingredients_main)
    if not mains or not index:
        return 0.0
    total_weight = 0.0
    matched_weight = 0.0
    for main in mains:
        for name, item_weight in index:
            if name in main or main in name:
                matched_weight += item_weight
                break
        total_weight += 1.0
    if total_weight == 0:
        return 0.0
    return round(min(100.0, 100.0 * matched_weight / total_weight), 2)


def _fridge_status_score(
    db: Session, user_id: int, dish: Dish, now: Optional[datetime] = None
) -> float:
    """单菜查询入口（保留给外部/测试用；推荐主循环不复用它）。"""
    return _fridge_status_from_index(_fridge_index(db, user_id, now=now), dish)


def _load_params(db: Session, override: Optional[Dict[str, float]]) -> Dict[str, float]:
    """取当前生效的算法参数。

    唯一出口是 config.current_algo_params()：后台保存 → reload_algo_params 写入内存缓存。
    这里原本还会用 algo_configs 表里 config_name='default_production' 的固定行再覆盖一遍，
    结果后台调参（只写 system_settings）看起来成功、实际打分仍读旧值（独立审查 P2）。
    algo_configs 现在只服务于离线仿真脚本 simulate_personas，不参与在线打分。
    """
    params = current_algo_params()
    if override:
        for key, value in override.items():
            if key in PARAM_KEYS and value is not None:
                params[key] = float(value)
    return params


def recommend_single(
    db: Session,
    user_id: int,
    mode_type: str,
    budget: Optional[float] = None,
    bubbles: Optional[Sequence[str]] = None,
    combo_mode: bool = False,
    override_params: Optional[Dict[str, float]] = None,
    weather_temp: float = 20.0,
    weather_text: str = "",
    max_distance_meters: Optional[int] = None,
    campus: Optional[str] = None,
    limit: int = 10,
    exclude_dish_ids: Optional[Sequence[int]] = None,
    only_dish_ids: Optional[Sequence[int]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    # `now`：仿真实验（R02）要按历史时刻重放决策，衰减查询必须能用可控时钟。
    # 生产调用不传，等价于 datetime.utcnow()；这不是算法改动，只是把时点变成参数。

    # 审查 F13：客户端可以把「已经看过/已划过」的菜排掉，后端在打分前就过滤，
    # 这样「换一批」拿到的是真正的新候选，而不是同一批 Top N 再来一遍。
    excluded = {int(i) for i in (exclude_dish_ids or [])}

    prefs = (
        db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    )
    if prefs is None:
        raise ValueError(f"用户 {user_id} 缺少饮食基因配置")

    bubbles = list(bubbles or [])
    effects = resolve_bubble_effects(bubbles, mode_type)
    params = _load_params(db, override_params)
    params.update(effects["param_overrides"])
    _normalize_weights(params)

    budget = float(prefs.default_budget if budget is None else budget)
    base_vector = normalize_vector(prefs.base_vector)
    veto_tags = [str(t) for t in (prefs.veto_tags or [])]
    blacklist = {int(i) for i in (prefs.blacklist_dish_ids or [])}
    # 黑榜门店：外食模式下该门店全部菜品一并剔除（v2.3.1 第三章硬性红线）
    blacklist_restaurants = {
        int(i) for i in (getattr(prefs, "blacklist_restaurant_ids", None) or [])
    }
    favorites = {int(i) for i in (prefs.favorite_dish_ids or [])}
    target_vector = effects["target_vector"]

    # 分层菜单策略：推荐是菜品驱动的；没有菜品的真实 POI 自然不进入候选，
    # 不用共享 fixture 冒充真实门店菜单（docs/MENU_STRATEGY.md）。
    # 软删除必须在这里挡住：后台 DELETE 只写 deleted_at，
    # 少了这个过滤，下架的菜/店照样会被推荐（独立审查 2026-10-31 P2）。
    # only_dish_ids：房间快照只需要给「本局这 10 道候选」算个人匹配度，
    # 传了它就只取这些行。不传时行为不变（全量候选）。
    # 加这个参数是因为房间每次 join/GET/WS 重连都会跑一遍快照，
    # 下厨模式 6440 道全表打分实测 0.55s，8 人进房会把事件循环拖住。
    dish_query = db.query(Dish).filter(
        Dish.mode_type == mode_type, Dish.deleted_at.is_(None)
    )
    if only_dish_ids is not None:
        ids = [int(i) for i in only_dish_ids]
        if not ids:
            return {"recommendations": [], "params_used": params, "total_scored": 0}
        dish_query = dish_query.filter(Dish.id.in_(ids))
    dishes = dish_query.order_by(Dish.id).all()
    restaurant_map: Dict[int, Restaurant] = {}
    if mode_type == "OUT_DINING":
        restaurant_map = {
            r.id: r
            for r in db.query(Restaurant).filter(Restaurant.deleted_at.is_(None)).all()
        }

    candidates: List[Dish] = []
    for dish in dishes:
        if dish.id in blacklist:
            continue
        if dish.id in excluded:
            continue
        # D-S04-01（方案 A）：未打标菜品不进入候选。SSOT 允许 feature_vector=NULL
        # 表示未完成，且禁止用默认向量蒙混；这里不做 normalize_vector(None) 的 0.5 回退。
        # 候选因此为空时沿用现有空结果语义，不反向补回这些菜。
        if dish.feature_vector is None:
            continue
        if (
            mode_type == "OUT_DINING"
            and dish.restaurant_id is not None
            and int(dish.restaurant_id) in blacklist_restaurants
        ):
            continue
        ingredients = _ingredient_set(dish.ingredients_main) | _ingredient_set(
            dish.ingredients_aux
        )
        if _hit_veto(ingredients, veto_tags):
            continue
        # v2.3.4 §5.5.3：外食严格按门店校区过滤；NULL 门店不默认共享。
        # campus=None 只给历史/仿真内部调用保留，API 层外食必填（缺失 422）。
        if mode_type == "OUT_DINING" and campus is not None:
            store = restaurant_map.get(dish.restaurant_id)
            if store is None or store.campus is None or str(store.campus) != str(campus):
                continue
        if max_distance_meters is not None and mode_type == "OUT_DINING":
            restaurant = restaurant_map.get(dish.restaurant_id)
            if restaurant is not None and (restaurant.distance_meters or 0) > max_distance_meters:
                continue
        if effects["budget_filter"] and float(dish.price_or_cost or 0.0) > budget:
            continue
        vector = normalize_vector(dish.feature_vector)
        if effects["hot_soup_filter"]:
            if not (
                vector["soup_level"] >= 0.7 and vector["temp_fit"] <= 0.4
            ):
                continue
        if effects["lazy_filter"]:
            # v2.3.2 审核裁决：lazy_one_pot 语义是「厨具可用性（低动手）」，与出餐速度正交，
            # 已删除 prep_speed >= 0.7 门槛，只按 appliance_tag 数组筛选。
            allowed = set(effects.get("allowed_appliances") or ())
            if not (allowed & _appliance_set(dish.appliance_tag)):
                continue
        candidates.append(dish)

    decay_weights = compute_decay_weights(
        db, user_id, candidates, params["lambda_decay"], now=now
    )

    # R01：循环外查一次冰箱，循环内纯内存匹配（原先是每道菜一次查询）
    # S03：使用与衰减相同的 `now`，历史回放/固定时钟下库存时效也一致
    fridge_index: Sequence[tuple[str, float]] = (
        _fridge_index(db, user_id, now=now) if mode_type == "HOME_COOKING" else ()
    )

    scored: List[Dict[str, object]] = []
    for dish in candidates:
        vector = normalize_vector(dish.feature_vector)
        taste = similarity_to_100(base_vector, vector)
        weather = weather_match_score(vector, weather_temp, weather_text)
        price = float(dish.price_or_cost or 0.0)
        budget_score = _budget_score(price, budget)
        decay = decay_weights.get(dish.id, 1.0)
        freshness = round(decay * 100.0, 2)
        if mode_type == "HOME_COOKING":
            status = _fridge_status_from_index(fridge_index, dish)
        elif target_vector:
            status = target_match_score(vector, target_vector)
        else:
            status = 60.0

        total = decay * (
            params["alpha_taste"] * taste
            + params["beta_weather"] * weather
            + params["gamma_budget"] * budget_score
            + params["delta_status"] * status
        )
        if effects["light_penalty"] and light_healthy_hits(vector):
            total *= float(effects.get("penalty_multiplier", 0.2))
        is_favorite = dish.id in favorites
        if is_favorite:
            total *= FAVORITE_BOOST
        raw_score = round(total, 4)
        total = round(min(100.0, raw_score), 1)

        restaurant = restaurant_map.get(dish.restaurant_id)
        scored.append(
            {
                "dish_id": dish.id,
                "name": dish.name,
                "mode_type": dish.mode_type,
                "cuisine_type": dish.cuisine_type or "",
                "dish_role": dish.dish_role,
                "price": price,
                "restaurant_id": dish.restaurant_id,
                "restaurant_name": restaurant.name if restaurant else None,
                "total_score": total,
                "raw_score": raw_score,
                "radar_5d": {
                    "taste": taste,
                    "weather": weather,
                    "budget": budget_score,
                    "freshness": freshness,
                    "status": status,
                },
                "decay_weight": decay,
                "explain_reason": build_explain_reason(
                    taste,
                    weather,
                    budget_score,
                    freshness,
                    status,
                    decay,
                    is_favorite,
                    list(effects["labels"]),
                ),
                "feature_vector": vector,
                # 前端要把八维翻译成人话，主料与时长是「怎么做的」那句的原料
                "ingredients_main": dish.ingredients_main or [],
                "cook_minutes": dish.cook_minutes,
                "is_favorite": is_favorite,
                # 图片缺失时为 None，前端渲染无图占位；不借用其它菜的图。
                "image_url": (dish.image_url or None),
            }
        )

    scored.sort(key=lambda item: (-float(item["raw_score"]), int(item["dish_id"])))
    combo = None
    if combo_mode:
        combo_candidates = [
            {
                "dish_id": item["dish_id"],
                "name": item["name"],
                "dish_role": item["dish_role"],
                "price": item["price"],
                "score": item["raw_score"],
                "oily_level": item["feature_vector"]["oily_level"],
            }
            for item in scored[:20]
        ]
        combo = optimize_combo(combo_candidates, budget)

    return {
        "mode_type": mode_type,
        "recommendations": scored[: max(1, limit)],
        "combo": combo,
        "params_used": {key: round(params[key], 4) for key in PARAM_KEYS},
        "bubble_effects": {
            "applied": effects["labels"],
            "ignored": effects["ignored"],
        },
    }
