"""S14：管理后台 CRUD 与真实 LLM 打标入口。

只复用 S11 已验收的提示词、调用与校验函数，不修改其脚本，也不提供演示打标回退。
"""

from __future__ import annotations

import json
import os
import urllib.error
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from ..admin_schemas import (
    DishCreate,
    DishUpdate,
    LlmTagRequest,
    RestaurantCreate,
    RestaurantUpdate,
)
from ..audit import record_audit
from ..database import get_db
from ..deps import require_admin
from ..models import AdminAuditLog, Dish, Restaurant, User, utcnow
from ..scripts.llm_batch_tagger import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
    call_model,
    validate_batch,
)

router = APIRouter(
    prefix="/admin",
    tags=["管理后台"],
    # 整个管理路由统一挂鉴权：改菜、删店、批量打标都属于高风险写操作，
    # 逐个函数加依赖容易漏，挂在 router 上不会漏。
    dependencies=[Depends(require_admin)],
)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def restaurant_dict(row: Restaurant) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "source_type": row.source_type,
        "category": row.category or "",
        "avg_price": row.avg_price,
        "rating": row.rating,
        "longitude": row.longitude,
        "latitude": row.latitude,
        "distance_meters": row.distance_meters,
        "address": row.address or "",
        "campus": row.campus,
        "source_dataset": row.source_dataset,
        "source_record_id": row.source_record_id,
        "source_url": row.source_url,
        "data_version": row.data_version,
        "is_synthetic": row.is_synthetic,
        "deleted_at": _iso(row.deleted_at),
    }


def dish_dict(row: Dish, restaurant: Optional[Restaurant] = None) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "mode_type": row.mode_type,
        "restaurant_id": row.restaurant_id,
        "restaurant_name": restaurant.name if restaurant else None,
        "campus": restaurant.campus if restaurant else "SHARED",
        "cuisine_type": row.cuisine_type or "",
        "dish_role": row.dish_role,
        "price_or_cost": row.price_or_cost,
        "cook_minutes": row.cook_minutes,
        "appliance_tag": row.appliance_tag or [],
        "ingredients_main": row.ingredients_main or [],
        "ingredients_aux": row.ingredients_aux or [],
        "recipe_steps": row.recipe_steps or "",
        "feature_vector": row.feature_vector,
        "image_url": row.image_url or "",
        "allergen_tags": row.allergen_tags,
        "tagging_status": row.tagging_status or "PENDING",
        "tagging_error": row.tagging_error,
        "llm_meta": row.llm_meta,
        "source_dataset": row.source_dataset,
        "source_record_id": row.source_record_id,
        "source_url": row.source_url,
        "data_version": row.data_version,
        "is_synthetic": row.is_synthetic,
        "deleted_at": _iso(row.deleted_at),
    }


def _dish_restaurant(db: Session, row: Dish) -> Optional[Restaurant]:
    return db.get(Restaurant, row.restaurant_id) if row.restaurant_id is not None else None


def _dish_rows_dict(db: Session, rows: list[Dish]) -> list[dict]:
    restaurant_ids = {row.restaurant_id for row in rows if row.restaurant_id is not None}
    restaurants = {
        row.id: row
        for row in db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()
    } if restaurant_ids else {}
    return [dish_dict(row, restaurants.get(row.restaurant_id)) for row in rows]


def _get_restaurant(db: Session, restaurant_id: int, *, include_deleted: bool = True) -> Restaurant:
    row = db.get(Restaurant, restaurant_id)
    if row is None or (row.deleted_at is not None and not include_deleted):
        raise HTTPException(404, "门店不存在或已下架")
    return row


def _get_dish(db: Session, dish_id: int, *, include_deleted: bool = True) -> Dish:
    row = db.get(Dish, dish_id)
    if row is None or (row.deleted_at is not None and not include_deleted):
        raise HTTPException(404, "菜品不存在或已删除")
    return row


@router.get("/restaurants")
def list_restaurants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = Query(None, max_length=32),
    category: Optional[str] = Query(None, max_length=64),
    campus: Optional[str] = Query(None, max_length=32),
    keyword: Optional[str] = Query(None, max_length=128),
    restaurant_id: Optional[int] = Query(None, ge=1),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Restaurant)
    if not include_deleted:
        query = query.filter(Restaurant.deleted_at.is_(None))
    if source_type:
        query = query.filter(Restaurant.source_type == source_type)
    if category:
        query = query.filter(Restaurant.category == category)
    if campus and campus != "ALL":
        query = query.filter(Restaurant.campus == campus)
    if keyword:
        query = query.filter(Restaurant.name.contains(keyword.strip()))
    if restaurant_id:
        query = query.filter(Restaurant.id == restaurant_id)
    total = query.count()
    rows = (
        query.order_by(Restaurant.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [restaurant_dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    return restaurant_dict(_get_restaurant(db, restaurant_id))


@router.post("/restaurants", status_code=201)
def create_restaurant(
    payload: RestaurantCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    row = Restaurant(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    record_audit(
        db,
        user_id=admin_id,
        action="restaurant.create",
        resource_type="restaurant",
        resource_id=row.id,
        summary=f"新建门店 {row.name}",
        detail=payload.model_dump(),
        request=request,
    )
    return restaurant_dict(row)


@router.put("/restaurants/{restaurant_id}")
def update_restaurant(
    restaurant_id: int,
    payload: RestaurantUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    row = _get_restaurant(db, restaurant_id, include_deleted=False)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    record_audit(
        db,
        user_id=admin_id,
        action="restaurant.update",
        resource_type="restaurant",
        resource_id=row.id,
        summary=f"修改门店 {row.name}（{len(changes)} 个字段）",
        detail=changes,
        request=request,
    )
    return restaurant_dict(row)


@router.delete("/restaurants/{restaurant_id}")
def delete_restaurant(
    restaurant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    row = _get_restaurant(db, restaurant_id, include_deleted=False)
    name = row.name
    deleted_at = utcnow()
    row.deleted_at = deleted_at
    affected = (
        db.query(Dish)
        .filter(Dish.restaurant_id == restaurant_id, Dish.deleted_at.is_(None))
        .update({Dish.deleted_at: deleted_at}, synchronize_session=False)
    )
    db.commit()
    record_audit(
        db,
        user_id=admin_id,
        action="restaurant.delete",
        resource_type="restaurant",
        resource_id=restaurant_id,
        summary=f"删除门店 {name}，连带下线 {affected} 道菜",
        detail={"restaurant_name": name, "dishes_offlined": int(affected)},
        request=request,
    )
    return {"ok": True, "id": restaurant_id, "deleted_at": _iso(deleted_at), "dishes_offlined": affected}


@router.get("/dishes")
def list_dishes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mode_type: Optional[str] = Query(None, max_length=16),
    cuisine_type: Optional[str] = Query(None, max_length=64),
    dish_role: Optional[str] = Query(None, max_length=16),
    campus: Optional[str] = Query(None, max_length=32),
    keyword: Optional[str] = Query(None, max_length=128),
    dish_id: Optional[int] = Query(None, ge=1),
    restaurant_id: Optional[int] = Query(None, ge=1),
    tagging_status: Optional[str] = Query(None, max_length=16),
    needs_tag: bool = Query(False, description="只看缺 allergen_tags 的菜品"),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Dish).outerjoin(Restaurant, Dish.restaurant_id == Restaurant.id)
    if not include_deleted:
        query = query.filter(Dish.deleted_at.is_(None))
    if mode_type:
        query = query.filter(Dish.mode_type == mode_type)
    if cuisine_type:
        query = query.filter(Dish.cuisine_type == cuisine_type)
    if dish_role:
        query = query.filter(Dish.dish_role == dish_role)
    if campus and campus not in {"ALL", "SHARED"}:
        query = query.filter(Restaurant.campus == campus)
    elif campus == "SHARED":
        query = query.filter(Dish.mode_type == "HOME_COOKING")
    if keyword:
        query = query.filter(Dish.name.contains(keyword.strip()))
    if dish_id:
        query = query.filter(Dish.id == dish_id)
    if restaurant_id:
        query = query.filter(Dish.restaurant_id == restaurant_id)
    if tagging_status:
        query = query.filter(Dish.tagging_status == tagging_status)
    if needs_tag:
        # 打标已全部完成，但过敏原标签仍有缺口；这是独立于 tagging_status 的维度。
        # 缺口有两种存法：NULL 与空数组 []，只判 NULL 会漏掉三分之二。
        # PG 的 json 类型没有 = 运算符（jsonb 才有），统一转文本比较，SQLite 同样适用
        query = query.filter(
            or_(
                Dish.allergen_tags.is_(None),
                cast(Dish.allergen_tags, String) == "[]",
            )
        )
    total = query.count()
    rows = (
        query.order_by(Dish.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": _dish_rows_dict(db, rows), "total": total, "page": page, "page_size": page_size}


@router.get("/dishes/{dish_id}")
def get_dish(dish_id: int, db: Session = Depends(get_db)):
    row = _get_dish(db, dish_id)
    return dish_dict(row, _dish_restaurant(db, row))


@router.post("/dishes", status_code=201)
def create_dish(
    payload: DishCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    if payload.restaurant_id is not None:
        _get_restaurant(db, payload.restaurant_id, include_deleted=False)
    values = payload.model_dump()
    values["tagging_status"] = "SUCCESS" if payload.feature_vector is not None else "PENDING"
    row = Dish(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    record_audit(
        db,
        user_id=admin_id,
        action="dish.create",
        resource_type="dish",
        resource_id=row.id,
        summary=f"新建菜品 {row.name}",
        detail={"name": row.name, "mode_type": row.mode_type, "restaurant_id": row.restaurant_id},
        request=request,
    )
    return dish_dict(row, _dish_restaurant(db, row))


@router.put("/dishes/{dish_id}")
def update_dish(
    dish_id: int,
    payload: DishUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    row = _get_dish(db, dish_id, include_deleted=False)
    values = payload.model_dump(exclude_unset=True)
    new_mode = values.get("mode_type", row.mode_type)
    new_restaurant = values.get("restaurant_id", row.restaurant_id)
    if new_mode == "OUT_DINING" and new_restaurant is None:
        raise HTTPException(422, "外食菜品必须绑定有效门店")
    if new_mode == "HOME_COOKING" and new_restaurant is not None:
        raise HTTPException(422, "下厨菜谱不能绑定门店")
    if new_restaurant is not None:
        _get_restaurant(db, new_restaurant, include_deleted=False)
    if "feature_vector" in values:
        values["tagging_status"] = "SUCCESS" if values["feature_vector"] is not None else "PENDING"
        values["tagging_error"] = None
    for key, value in values.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    record_audit(
        db,
        user_id=admin_id,
        action="dish.update",
        resource_type="dish",
        resource_id=row.id,
        summary=f"修改菜品 {row.name}（{len(values)} 个字段）",
        detail=values,
        request=request,
    )
    return dish_dict(row, _dish_restaurant(db, row))


@router.delete("/dishes/{dish_id}")
def delete_dish(
    dish_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    row = _get_dish(db, dish_id, include_deleted=False)
    name = row.name
    row.deleted_at = utcnow()
    db.commit()
    record_audit(
        db,
        user_id=admin_id,
        action="dish.delete",
        resource_type="dish",
        resource_id=dish_id,
        summary=f"删除菜品 {name}",
        detail={"name": name},
        request=request,
    )
    return {"ok": True, "id": dish_id, "deleted_at": _iso(row.deleted_at)}


@router.post("/llm-tag")
def llm_tag(
    payload: LlmTagRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    rows = db.query(Dish).filter(Dish.id.in_(payload.dish_ids)).all()
    by_id = {row.id: row for row in rows}
    missing = sorted(set(payload.dish_ids) - set(by_id))
    if missing:
        raise HTTPException(404, f"菜品不存在：{missing}")
    if any(by_id[item].deleted_at is not None for item in payload.dish_ids):
        raise HTTPException(409, "已删除菜品不能打标")

    base_url = os.getenv("LLM_BASE_URL", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    if not (base_url and api_key and model):
        raise HTTPException(503, "LLM 未配置：需要 LLM_BASE_URL、LLM_API_KEY、LLM_MODEL；未发起调用")

    skipped = [item for item in payload.dish_ids if by_id[item].tagging_status == "SUCCESS"]
    pending = [by_id[item] for item in payload.dish_ids if by_id[item].tagging_status != "SUCCESS"]
    if not pending:
        return {"items": [], "success_count": 0, "failed_count": 0, "skipped": skipped}

    items = [
        {
            "dish_id": row.id,
            "name": row.name,
            "cuisine_type": row.cuisine_type or "",
            "ingredients_main": row.ingredients_main or [],
            "ingredients_aux": row.ingredients_aux or [],
        }
        for row in pending
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(items)},
    ]
    error = ""
    validated = None
    meta = {}
    try:
        content, meta = call_model(base_url, api_key, model, messages)
        validated, error = validate_batch(content, items)
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
        error = f"transport_error:{type(exc).__name__}"

    if validated is None:
        failed = []
        for row in pending:
            row.tagging_status = "FAILED"
            row.tagging_error = (error or "unknown_model_error")[:400]
            row.llm_meta = {"model": model, "prompt_version": PROMPT_VERSION, "request_id": meta.get("id")}
            failed.append({"dish_id": row.id, "status": "FAILED", "error": row.tagging_error})
        db.commit()
        return {"items": failed, "success_count": 0, "failed_count": len(failed), "skipped": skipped}

    results = {item["dish_id"]: item for item in validated}
    response_items = []
    for row in pending:
        result = results[row.id]
        row.dish_role = result["dish_role"]
        row.feature_vector = result["feature_vector"]
        row.allergen_tags = result["allergen_tags"]
        row.tagging_status = "SUCCESS"
        row.tagging_error = None
        row.llm_meta = {
            "model": meta.get("model") or model,
            "prompt_version": PROMPT_VERSION,
            "request_id": meta.get("id"),
        }
        response_items.append({"dish_id": row.id, "status": "SUCCESS", **result})
    db.commit()
    record_audit(
        db,
        user_id=admin_id,
        action="dish.llm_tag",
        resource_type="dish",
        resource_id=None,
        summary=f"批量打标成功 {len(response_items)} 道",
        detail={"dish_ids": payload.dish_ids, "success": len(response_items), "skipped": skipped},
        request=request,
    )
    return {
        "items": response_items,
        "success_count": len(response_items),
        "failed_count": 0,
        "skipped": skipped,
    }


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None, max_length=32),
    resource_type: Optional[str] = Query(default=None, max_length=32),
    user_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """审计日志查询。只读，按时间倒序。

    故意只给管理员看：日志里带着谁删了哪家店、改了哪个价格，
    普通用户拿到等于拿到后台的操作档案。
    """
    query = db.query(AdminAuditLog)
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if resource_type:
        query = query.filter(AdminAuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AdminAuditLog.user_id == user_id)

    total = query.count()
    rows = (
        query.order_by(AdminAuditLog.id.desc()).offset(offset).limit(limit).all()
    )
    operator_ids = {row.user_id for row in rows}
    names = {
        user.id: (user.nickname or user.username)
        for user in db.query(User).filter(User.id.in_(operator_ids)).all()
    } if operator_ids else {}

    return {
        "total": total,
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "operator": names.get(row.user_id, f"用户{row.user_id}"),
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "summary": row.summary,
                "detail": row.detail,
                "ip": row.ip,
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ],
    }
