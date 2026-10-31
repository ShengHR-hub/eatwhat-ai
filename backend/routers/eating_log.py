from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..algorithms.time_decay import compute_decay_weights
from ..config import current_algo_params
from ..database import get_db
from ..deps import ensure_self, require_user, resolve_user_id
from ..models import DishFeedback, AlgoConfig, Dish, EatingLog, Restaurant, User, utcnow
from ..schemas import (
    CheckinRequest,
    CheckinResponse,
    CoolingDish,
    CuisinePieItem,
    LogStatsResponse,
    TimelineItem,
    TimelineResponse,
)

router = APIRouter(tags=["饮食足迹"])


def _lambda_decay(db: Session) -> float:
    """衰减系数只认运行期缓存，与 single_recommender 保持同一出口。

    以前这里优先读 algo_configs 的固定行，导致后台把 λ 改到 0.9 后，
    足迹页的冷却权重仍按 0.5 计算。
    """
    return float(current_algo_params()["lambda_decay"])


def _require_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return user


def _cooling_status(weight: float) -> str:
    if weight < 0.3:
        return "COOLING"
    if weight < 0.8:
        return "WARMING"
    return "READY"


@router.post("/logs/checkin", response_model=CheckinResponse)
def checkin(
    payload: CheckinRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> CheckinResponse:
    user_id = resolve_user_id(header_user_id, payload.user_id)
    _require_user(db, user_id)
    dish = db.query(Dish).filter(Dish.id == payload.dish_id).first()
    if dish is None:
        raise HTTPException(status_code=404, detail=f"菜品 {payload.dish_id} 不存在")
    if dish.mode_type != payload.mode_type:
        raise HTTPException(
            status_code=400,
            detail=f"菜品模式 {dish.mode_type} 与请求模式 {payload.mode_type} 不一致",
        )

    now = utcnow()
    log = EatingLog(
        user_id=user_id,
        dish_id=dish.id,
        mode_type=payload.mode_type,
        cost_amount=(
            float(payload.cost_amount)
            if payload.cost_amount is not None
            else float(dish.price_or_cost or 0.0)
        ),
        weather_snapshot=payload.weather_snapshot,
        status_bubbles=list(payload.bubbles),
        eaten_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    weights = compute_decay_weights(
        db, user_id, [dish], lambda_decay=_lambda_decay(db), now=now
    )
    return CheckinResponse(
        log_id=log.id, new_decay_weight=round(weights.get(dish.id, 1.0), 4)
    )


@router.get("/logs/timeline/{user_id}", response_model=TimelineResponse)
def log_timeline(
    user_id: int,
    limit: int = 50,
    before: datetime | None = None,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> TimelineResponse:
    """按时间倒序返回真实饮食记录，供足迹时间线使用。"""
    ensure_self(user_id, header_user_id)
    _require_user(db, user_id)
    query = (
        db.query(EatingLog, Dish, Restaurant)
        .outerjoin(Dish, Dish.id == EatingLog.dish_id)
        .outerjoin(Restaurant, Restaurant.id == Dish.restaurant_id)
        .filter(EatingLog.user_id == user_id)
    )
    if before is not None:
        query = query.filter(EatingLog.eaten_at < before)
    rows = query.order_by(EatingLog.eaten_at.desc(), EatingLog.id.desc()).limit(max(1, min(int(limit), 100))).all()
    # 一次查出这批流水的评价，避免逐条再查（N+1）
    log_ids = [log.id for log, _, _ in rows]
    ratings = dict(
        db.query(DishFeedback.log_id, DishFeedback.rating)
        .filter(DishFeedback.log_id.in_(log_ids))
        .all()
    ) if log_ids else {}
    items = [
        TimelineItem(
            log_id=log.id,
            dish_id=log.dish_id,
            rating=int(ratings.get(log.id, 0)),
            dish_name=dish.name if dish else "已删除菜品",
            restaurant_name=(restaurant.name if restaurant else ""),
            mode_type=log.mode_type,
            cost_amount=float(log.cost_amount or 0.0),
            weather_snapshot=log.weather_snapshot or "",
            status_bubbles=list(log.status_bubbles or []),
            eaten_at=log.eaten_at,
        )
        for log, dish, restaurant in rows
    ]
    return TimelineResponse(items=items)


@router.get("/logs/stats/{user_id}", response_model=LogStatsResponse)
def log_stats(
    user_id: int,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> LogStatsResponse:
    ensure_self(user_id, header_user_id)
    _require_user(db, user_id)
    now = utcnow()

    recent_logs = (
        db.query(EatingLog)
        .filter(
            EatingLog.user_id == user_id,
            EatingLog.eaten_at >= now - timedelta(days=14),
        )
        .order_by(EatingLog.eaten_at.desc())
        .all()
    )
    dish_ids = {log.dish_id for log in recent_logs}
    dishes = (
        db.query(Dish).filter(Dish.id.in_(list(dish_ids))).all() if dish_ids else []
    )
    decay_weights = compute_decay_weights(
        db, user_id, dishes, lambda_decay=_lambda_decay(db), now=now
    )
    last_eaten: Dict[int, datetime] = {}
    for log in recent_logs:
        if log.dish_id not in last_eaten:
            last_eaten[log.dish_id] = log.eaten_at

    cooling: List[CoolingDish] = []
    for dish in dishes:
        weight = round(decay_weights.get(dish.id, 1.0), 4)
        eaten_at = last_eaten[dish.id]
        cooling.append(
            CoolingDish(
                dish_id=dish.id,
                name=dish.name,
                last_eaten_at=eaten_at,
                days_since=max(0, (now.date() - eaten_at.date()).days),
                decay_weight=weight,
                cooling_percent=round((1.0 - weight) * 100.0, 1),
                status=_cooling_status(weight),
            )
        )
    cooling.sort(
        key=lambda item: (item.decay_weight, -item.last_eaten_at.timestamp())
    )

    weekly_logs = [
        log for log in recent_logs if log.eaten_at >= now - timedelta(days=7)
    ]
    weekly_expense = sum(float(log.cost_amount or 0.0) for log in weekly_logs)
    dish_map = {dish.id: dish for dish in db.query(Dish).all()}
    cuisine_counts: Dict[str, int] = {}
    for log in weekly_logs:
        dish = dish_map.get(log.dish_id)
        if dish is None:
            continue
        name = dish.cuisine_type or "其他"
        cuisine_counts[name] = cuisine_counts.get(name, 0) + 1
    cuisine_pie = [
        CuisinePieItem(name=name, value=count)
        for name, count in sorted(
            cuisine_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]

    return LogStatsResponse(
        cooling_dishes=cooling,
        weekly_expense=round(weekly_expense, 2),
        meals_this_week=len(weekly_logs),
        cuisine_pie_data=cuisine_pie,
    )


@router.post("/logs/{log_id}/feedback")
def submit_feedback(
    log_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    header_user_id: int = Depends(require_user),
):
    """吃完之后的满意度：3=好吃 2=一般 1=踩雷。

    同一条流水重复提交按更新处理（用户可能改主意），不堆多条。
    """
    rating = payload.get("rating")
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise HTTPException(422, "rating 必须是 1–3 的整数")
    if rating not in (1, 2, 3):
        raise HTTPException(422, "rating 只能是 1（踩雷）、2（一般）、3（好吃）")

    log = db.get(EatingLog, log_id)
    if log is None:
        raise HTTPException(404, "饮食记录不存在")
    if log.user_id != header_user_id:
        raise HTTPException(403, "只能评价自己的记录")

    existing = db.query(DishFeedback).filter(DishFeedback.log_id == log_id).first()
    if existing:
        existing.rating = rating
    else:
        db.add(DishFeedback(user_id=log.user_id, dish_id=log.dish_id, log_id=log_id, rating=rating))
    db.commit()
    return {"log_id": log_id, "rating": rating}
