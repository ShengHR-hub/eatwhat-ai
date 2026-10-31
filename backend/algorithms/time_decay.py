"""算法 1：基于艾宾浩斯遗忘曲线的跨场景防腻时间衰减（MASTER_SPEC v2.1.1 第四章）。"""

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models import Dish, EatingLog, utcnow

LOOKBACK_DAYS = 14
SAME_DAY_WEIGHT = 0.05
# 日期分界必须按本地时区：数据库存的是 naive UTC（models.utcnow），
# 直接用 .date() 会把上海 07:30 的早餐算成"前一天"，当天重吃就不再强制 0.05。
# 与 admin_stats 的统计口径（ZoneInfo("Asia/Shanghai")）保持一致。
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def _ingredient_set(values: Optional[Iterable[str]]) -> set[str]:
    return {str(v).strip() for v in (values or []) if str(v).strip()}


def _local_date(value: datetime):
    """把时间转成本地（上海）日期；naive 值按 UTC 解释。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ).date()


def _days_since(eaten_at: datetime, now: datetime) -> int:
    return max(0, (_local_date(now) - _local_date(eaten_at)).days)


def _decay_formula(
    lambda_decay: float,
    dt_exact: Optional[int],
    dt_similar: Optional[int],
) -> float:
    if dt_exact == 0:
        return SAME_DAY_WEIGHT
    exact_factor = 1.0
    if dt_exact is not None:
        exact_factor = 1.0 - math.exp(-lambda_decay * dt_exact)
    similar_factor = 1.0
    if dt_similar is not None:
        similar_factor = 1.0 - 0.4 * math.exp(-lambda_decay * dt_similar)
    return max(0.0, min(1.0, exact_factor * similar_factor))


def compute_decay_weights(
    db: Session,
    user_id: int,
    dishes: Sequence[Dish],
    lambda_decay: float = 0.5,
    now: Optional[datetime] = None,
) -> Dict[int, float]:
    """返回候选菜品 dish_id -> W_decay；14 天内无任何相关记录时为 1.0。"""
    now = now or utcnow()
    since = now - timedelta(days=LOOKBACK_DAYS)
    logs = (
        db.query(EatingLog)
        .filter(EatingLog.user_id == user_id, EatingLog.eaten_at >= since)
        .all()
    )
    if not logs:
        return {dish.id: 1.0 for dish in dishes}

    logged_ids = {log.dish_id for log in logs}
    logged_dishes = {
        dish.id: dish
        for dish in db.query(Dish).filter(Dish.id.in_(logged_ids)).all()
    }

    weights: Dict[int, float] = {}
    for dish in dishes:
        dish_mains = _ingredient_set(dish.ingredients_main)
        dt_exact: Optional[int] = None
        dt_similar: Optional[int] = None
        for log in logs:
            delta = _days_since(log.eaten_at, now)
            if delta > LOOKBACK_DAYS:
                continue
            if log.dish_id == dish.id:
                dt_exact = delta if dt_exact is None else min(dt_exact, delta)
                continue
            logged_dish = logged_dishes.get(log.dish_id)
            if logged_dish is None:
                continue
            same_cuisine = bool(
                dish.cuisine_type
                and logged_dish.cuisine_type
                and dish.cuisine_type == logged_dish.cuisine_type
            )
            shared_main = bool(dish_mains & _ingredient_set(logged_dish.ingredients_main))
            if same_cuisine or shared_main:
                dt_similar = delta if dt_similar is None else min(dt_similar, delta)

        if dt_exact is None and dt_similar is None:
            weights[dish.id] = 1.0
        else:
            weights[dish.id] = round(
                _decay_formula(lambda_decay, dt_exact, dt_similar), 4
            )
    return weights
