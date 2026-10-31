"""模块 3：虚拟冰箱。

契约见 MASTER_SPEC.md 第五章「模块3：虚拟冰箱」：
* `GET  /fridge/{user_id}`        库存列表，临期（未过期且剩余 ≤48h）置顶并打
  `is_expiring_soon`；过期项返回 0 天、不带临期标记，但仍可见可删
* `POST /fridge/{user_id}`        录入 / 删除食材，返回更新后的整份库存
* `POST /fridge/shopping-list`    多道菜谱的主辅料并集 - 冰箱现有 → 待买清单

设计取舍：
* 录入按 `(user_id, ingredient_name)` 唯一，重复 ADD 是「重新入库」：覆盖属性并把
  `created_at` 重置为当前时间（S03 裁决 2A），否则改保质期会被旧入库时间拖成立即过期。
* 删除也只按名字定位，前端不用先取 id，省一轮请求。
* 买菜清单的「已有」判定用双向包含（「鸡蛋」↔「土鸡蛋」都算命中），
  比全等实用；命中与否都回带 `used_by`，前端的「这几道菜要用」才有得显示。
* 时效只走 `algorithms.fridge_clock`，展示 / 推荐 / 清单共用同一口径。
"""

import base64
import json
import re
from typing import Dict, List, Tuple

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import VISION_API_KEY, VISION_BASE_URL, VISION_MODEL
from ..database import get_db
from ..deps import ensure_self, require_user, resolve_user_id
from ..algorithms import fridge_clock
from ..models import Dish, FridgeInventory, User
from ..schemas import (
    FridgeItem,
    FridgeListResponse,
    FridgeUpsertRequest,
    ScanImportRequest,
    ScanItem,
    ScanResponse,
    ShoppingItem,
    ShoppingListRequest,
    ShoppingListResponse,
)

router = APIRouter(tags=["虚拟冰箱"])



def _require_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return user


def _to_item(row: FridgeInventory, now) -> FridgeItem:
    remaining = fridge_clock.remaining_days(row, now)
    return FridgeItem(
        id=row.id,
        ingredient_name=row.ingredient_name,
        category=row.category or "新鲜果蔬",
        quantity_desc=row.quantity_desc or "适量",
        expire_days=remaining,
        is_expiring_soon=fridge_clock.is_expiring_soon(row, now),
    )


def _sorted_items(rows: List[FridgeInventory], now) -> List[FridgeItem]:
    """临期置顶：先按是否临期，再按剩余天数升序，最后按名字稳定排序。

    过期项 `expire_days=0` 且不带临期标记，因此排在临期之后、新鲜项之前。
    """
    items = [_to_item(row, now) for row in rows]
    items.sort(key=lambda it: (not it.is_expiring_soon, it.expire_days, it.ingredient_name))
    return items


def _fridge_items(db: Session, user_id: int, now=None) -> List[FridgeItem]:
    current = now if now is not None else fridge_clock.now_utc()
    rows = (
        db.query(FridgeInventory)
        .filter(FridgeInventory.user_id == user_id)
        .all()
    )
    return _sorted_items(rows, current)


def _name_hit(needle: str, haystack: str) -> bool:
    a = (needle or "").strip()
    b = (haystack or "").strip()
    if not a or not b:
        return False
    return a in b or b in a


@router.get("/fridge/{user_id}", response_model=FridgeListResponse)
def get_fridge(
    user_id: int,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> FridgeListResponse:
    ensure_self(user_id, header_user_id)
    _require_user(db, user_id)
    now = fridge_clock.now_utc()
    return FridgeListResponse(user_id=user_id, items=_fridge_items(db, user_id, now))


@router.post("/fridge/shopping-list", response_model=ShoppingListResponse)
def shopping_list(
    payload: ShoppingListRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> ShoppingListResponse:
    """多菜谱主辅料并集，减去冰箱已有食材（下厨模式的「待采购买菜清单」）。"""
    user_id = resolve_user_id(header_user_id, payload.user_id)
    _require_user(db, user_id)
    if not payload.dish_ids:
        raise HTTPException(status_code=400, detail="dish_ids 不能为空")

    dishes = db.query(Dish).filter(Dish.id.in_(payload.dish_ids)).all()
    if not dishes:
        raise HTTPException(status_code=404, detail="这些菜谱都不存在")
    # S02：部分 ID 不存在不能被静默忽略，否则清单会少算这几道菜。
    missing = sorted({int(i) for i in payload.dish_ids} - {int(d.id) for d in dishes})
    if missing:
        raise HTTPException(
            status_code=404, detail=f"这些菜谱不存在：{missing}"
        )

    # 食材 -> (类别, 需要它的菜名)，同名食材合并同类项
    needed: Dict[str, Tuple[str, List[str]]] = {}
    for dish in dishes:
        for name in list(dish.ingredients_main or []) + list(dish.ingredients_aux or []):
            key = (name or "").strip()
            if not key:
                continue
            category, used_by = needed.get(key, ("", []))
            if dish.name not in used_by:
                used_by.append(dish.name)
            needed[key] = (category, used_by)

    fridge_rows = (
        db.query(FridgeInventory).filter(FridgeInventory.user_id == user_id).all()
    )
    now = fridge_clock.now_utc()
    owned: List[ShoppingItem] = []
    to_buy: List[ShoppingItem] = []
    for name, (_category, used_by) in needed.items():
        # F09：过期食材不能算「冰箱里有」，否则清单会让人少买一样
        hit = next(
            (
                row
                for row in fridge_rows
                if _name_hit(name, row.ingredient_name)
                and not fridge_clock.is_expired(row, now)
            ),
            None,
        )
        if hit is not None:
            owned.append(
                ShoppingItem(
                    ingredient=name,
                    category=hit.category or "",
                    used_by=used_by,
                    from_fridge=True,
                )
            )
        else:
            to_buy.append(ShoppingItem(ingredient=name, used_by=used_by))

    owned.sort(key=lambda it: it.ingredient)
    to_buy.sort(key=lambda it: (-len(it.used_by), it.ingredient))
    return ShoppingListResponse(owned_ingredients=owned, to_buy_ingredients=to_buy)


def _parse_vision_json(text: str) -> list[dict]:
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    data = json.loads(raw)
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict) and "items" in data[0]:
        data = data[0]
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("模型没有返回 items 数组")
    return items[:20]


@router.post("/fridge/scan", response_model=ScanResponse)
async def scan_fridge(
    file: UploadFile = File(...),
    header_user_id: int = Depends(require_user),
) -> ScanResponse:
    """拍照识别食材。需要配置 VISION_API_KEY；不自动写库。"""
    if not VISION_API_KEY:
        raise HTTPException(status_code=503, detail="未配置 VISION_API_KEY，暂时不能调用云端识别")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="图片为空")
    if len(raw) > 6 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片不能超过 6MB")
    mime = file.content_type or "image/jpeg"
    data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    prompt = (
        "你是冰箱食材识别器。识别图片里能看清的食材，只返回 JSON，不要解释。"
        '格式：{"items":[{"ingredient_name":"番茄","category":"新鲜果蔬","quantity_desc":"2 个","expire_days":3,"confidence":0.9}]}。'
        "category 只能是 肉禽蛋奶、新鲜果蔬、冷冻速食、豆制品与干货；不确定的食材不要编造。"
    )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{VISION_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {VISION_API_KEY}"},
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            items = _parse_vision_json(content)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"识别失败：{exc}") from exc

    cleaned: List[ScanItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            cleaned.append(ScanItem(**item))
        except Exception:
            continue
    return ScanResponse(items=cleaned, source="vision", model=VISION_MODEL)


@router.post("/fridge/{user_id}/scan-import", response_model=FridgeListResponse)
def scan_import(
    user_id: int,
    payload: ScanImportRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> FridgeListResponse:
    """批量写入已确认的识别结果；按名称 upsert，重复入库会刷新保质期。"""
    ensure_self(user_id, header_user_id)
    _require_user(db, user_id)
    now = fridge_clock.now_utc()
    for item in payload.items:
        name = item.ingredient_name.strip()
        if not name:
            continue
        row = (
            db.query(FridgeInventory)
            .filter(FridgeInventory.user_id == user_id, FridgeInventory.ingredient_name == name)
            .first()
        )
        if row is None:
            row = FridgeInventory(user_id=user_id, ingredient_name=name, created_at=now)
            db.add(row)
        row.category = item.category
        row.quantity_desc = item.quantity_desc
        row.expire_days = item.expire_days
        row.created_at = now
    db.commit()
    return FridgeListResponse(user_id=user_id, items=_fridge_items(db, user_id, now))


@router.post("/fridge/{user_id}", response_model=FridgeListResponse)
def upsert_fridge(
    user_id: int,
    payload: FridgeUpsertRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> FridgeListResponse:
    ensure_self(user_id, header_user_id)
    _require_user(db, user_id)
    name = payload.ingredient_name.strip()
    now = fridge_clock.now_utc()
    row = (
        db.query(FridgeInventory)
        .filter(
            FridgeInventory.user_id == user_id,
            FridgeInventory.ingredient_name == name,
        )
        .first()
    )

    if payload.action == "REMOVE":
        if row is None:
            raise HTTPException(status_code=404, detail=f"冰箱里没有「{name}」")
        db.delete(row)
        db.commit()
        return FridgeListResponse(user_id=user_id, items=_fridge_items(db, user_id, now))

    if row is None:
        row = FridgeInventory(
            user_id=user_id,
            ingredient_name=name,
            category=payload.category,
            quantity_desc=payload.quantity_desc,
            expire_days=payload.expire_days,
            created_at=now,
        )
        db.add(row)
    else:
        row.category = payload.category
        row.quantity_desc = payload.quantity_desc
        row.expire_days = payload.expire_days
        # S03 裁决 2A：同名再次 ADD = 重新入库，保质期从现在重新起算
        row.created_at = now
    db.commit()
    return FridgeListResponse(user_id=user_id, items=_fridge_items(db, user_id, now))
