"""只读目录查询：给「红黑榜 / 忌口台」把 id 翻译成人类可读的名字。

前端拿到的 profile 只有 id 数组（favorite_dish_ids / blacklist_dish_ids /
blacklist_restaurant_ids），没有名字。与其在前端硬编码字典，不如给两个
只读接口：

    GET /api/v1/catalog/dishes?ids=1,2,3
    GET /api/v1/catalog/restaurants?ids=1,2,3

不传 ids 时返回全部（当前数据量小，够用）。只读、不改库、不加新表。
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Dish, Restaurant
from ..schemas import DishBrief, RestaurantBrief

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _parse_ids(ids: Optional[str]) -> Optional[List[int]]:
    """解析 ?ids=1,2,3。

    返回 None 表示"没传这个参数"（不过滤）；传了但一个合法 id 都没有时
    直接 422。以前这种情况会退化成 None，于是返回全量目录——
    调用方以为筛选生效，实际拿到 6560 道菜。
    """
    if not ids:
        return None
    out: List[int] = []
    for chunk in ids.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            out.append(int(chunk))
    if not out:
        raise HTTPException(422, "ids 必须是以逗号分隔的正整数")
    return out


@router.get("/dishes", response_model=List[DishBrief])
def list_dishes(
    ids: Optional[str] = Query(default=None, description="逗号分隔的菜品 id，不传则返回全部"),
    mode_type: Optional[str] = Query(default=None, description="OUT_DINING / HOME_COOKING"),
    db: Session = Depends(get_db),
):
    # 后台删除是软删除；不过滤的话，红黑榜仍会显示已下架菜品的名字。
    query = db.query(Dish).filter(Dish.deleted_at.is_(None))
    id_list = _parse_ids(ids)
    if id_list:
        query = query.filter(Dish.id.in_(id_list))
    if mode_type:
        query = query.filter(Dish.mode_type == mode_type)
    rows = query.order_by(Dish.id.asc()).all()
    return [
        DishBrief(
            dish_id=row.id,
            name=row.name,
            mode_type=row.mode_type,
            cuisine_type=row.cuisine_type,
            dish_role=row.dish_role,
            price=float(row.price_or_cost or 0),
            appliance_tag=row.appliance_tag or [],
            image_url=row.image_url or None,
        )
        for row in rows
    ]


@router.get("/restaurants", response_model=List[RestaurantBrief])
def list_restaurants(
    ids: Optional[str] = Query(default=None, description="逗号分隔的门店 id，不传则返回全部"),
    db: Session = Depends(get_db),
):
    query = db.query(Restaurant).filter(Restaurant.deleted_at.is_(None))
    id_list = _parse_ids(ids)
    if id_list:
        query = query.filter(Restaurant.id.in_(id_list))
    rows = query.order_by(Restaurant.id.asc()).all()
    return [
        RestaurantBrief(
            restaurant_id=row.id,
            name=row.name,
            category=row.category,
            avg_price=float(row.avg_price or 0),
        )
        for row in rows
    ]
