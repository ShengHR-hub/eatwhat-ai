import math
from typing import List

import time
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from ..algorithms.vector_spec import DEFAULT_FEATURE_VECTOR
from ..database import get_db
from ..deps import ensure_self, require_user
from ..models import Dish, EatingLog, GroupRoom, Restaurant, User, UserPreference
from ..schemas import (
    GENE_KEYS,
    DemoUser,
    PreferenceUpdate,
    ProfileResponse,
    RedBlackListRequest,
    RedBlackListResponse,
)

router = APIRouter(tags=["用户与主页"])


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return user


def _get_prefs(db: Session, user_id: int) -> UserPreference:
    prefs = (
        db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    )
    if prefs is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 缺少饮食基因配置")
    return prefs


def _build_profile(db: Session, user: User, prefs: UserPreference) -> ProfileResponse:
    logs = db.query(EatingLog).filter(EatingLog.user_id == user.id).all()
    total_spent = sum(float(log.cost_amount or 0.0) for log in logs)
    out_spent = sum(
        float(log.cost_amount or 0.0)
        for log in logs
        if log.mode_type == "OUT_DINING"
    )
    home_spent = sum(
        float(log.cost_amount or 0.0)
        for log in logs
        if log.mode_type == "HOME_COOKING"
    )
    rooms = sum(
        1
        for room in db.query(GroupRoom).all()
        if user.id in (room.member_user_ids or [])
    )
    return ProfileResponse(
        user_id=user.id,
        nickname=user.nickname,
        avatar=user.avatar or "",
        persona_title=user.persona_title or "",
        base_vector=prefs.base_vector or {},
        default_budget=float(prefs.default_budget or 25.0),
        veto_tags=list(prefs.veto_tags or []),
        preferred_cuisines=list(prefs.preferred_cuisines or []),
        favorite_dish_ids=[int(i) for i in (prefs.favorite_dish_ids or [])],
        blacklist_dish_ids=[int(i) for i in (prefs.blacklist_dish_ids or [])],
        blacklist_restaurant_ids=[int(i) for i in (prefs.blacklist_restaurant_ids or [])],
        achievements={
            "meals_logged": len(logs),
            "total_spent": round(total_spent, 2),
            "out_dining_spent": round(out_spent, 2),
            "home_cooking_spent": round(home_spent, 2),
            "group_rooms_joined": int(rooms),
        },
    )


@router.get("/users/demo-list", response_model=List[DemoUser])
def demo_list(db: Session = Depends(get_db)) -> List[DemoUser]:
    users = (
        db.query(User)
        .filter(User.is_demo_persona.is_(True))
        .order_by(User.id)
        .all()
    )
    result: List[DemoUser] = []
    for user in users:
        prefs = (
            db.query(UserPreference)
            .filter(UserPreference.user_id == user.id)
            .first()
        )
        if prefs is None:
            continue
        result.append(
            DemoUser(
                id=user.id,
                nickname=user.nickname,
                avatar=user.avatar or "",
                persona_title=user.persona_title or "",
                base_vector=prefs.base_vector or {},
                default_budget=float(prefs.default_budget or 25.0),
                veto_tags=list(prefs.veto_tags or []),
            )
        )
    return result


@router.get("/users/{user_id}/profile", response_model=ProfileResponse)
def profile(
    user_id: int,
    db: Session = Depends(get_db),
    header_user_id: int = Depends(require_user),
) -> ProfileResponse:
    # F07：路径里的 user_id 不能绕过请求头身份
    ensure_self(user_id, header_user_id)
    user = _get_user(db, user_id)
    prefs = _get_prefs(db, user_id)
    return _build_profile(db, user, prefs)


@router.put("/users/{user_id}/preferences", response_model=ProfileResponse)
def update_preferences(
    user_id: int,
    payload: PreferenceUpdate,
    db: Session = Depends(get_db),
    header_user_id: int = Depends(require_user),
) -> ProfileResponse:
    ensure_self(user_id, header_user_id)
    user = _get_user(db, user_id)
    prefs = _get_prefs(db, user_id)

    # S02/r02：历史向量守卫必须先于任何字段赋值。只改预算/忌口/菜系时同样执行，
    # 否则非法历史向量会被保留、新字段却已提交。
    stored = _validated_history_vector(prefs.base_vector)
    completed = {
        key: stored.get(key, DEFAULT_FEATURE_VECTOR[key]) for key in GENE_KEYS
    }
    if payload.base_vector is not None:
        completed.update(payload.base_vector)
    prefs.base_vector = completed

    if payload.default_budget is not None:
        prefs.default_budget = float(payload.default_budget)
    if payload.veto_tags is not None:
        prefs.veto_tags = list(dict.fromkeys(str(t) for t in payload.veto_tags))
    if payload.preferred_cuisines is not None:
        prefs.preferred_cuisines = list(dict.fromkeys(payload.preferred_cuisines))
    db.commit()
    db.refresh(prefs)
    return _build_profile(db, user, prefs)


def _valid_stored_value(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return 0 <= value <= 1
    return math.isfinite(value) and 0.0 <= value <= 1.0


def _validated_history_vector(raw):
    """历史向量统一守卫：未知键/非法值一律 409，且不写任何字段。

    只有“键都在八维内、值全部合法”的历史向量才允许进入补齐流程；
    缺键由调用方按方案 A 补 0.5，不允许静默丢弃未知键或覆盖坏值。
    """
    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=409,
            detail="库内历史口味向量不是对象；本次偏好更新未写入",
        )
    unknown = sorted(set(raw) - set(GENE_KEYS))
    invalid = sorted(
        key
        for key, value in raw.items()
        if key in GENE_KEYS and not _valid_stored_value(value)
    )
    if unknown or invalid:
        parts = []
        if unknown:
            parts.append(f"未知键 {unknown}")
        if invalid:
            parts.append(f"非法值 {invalid}")
        raise HTTPException(
            status_code=409,
            detail="库内历史口味向量存在" + "、".join(parts) + "；本次偏好更新未写入",
        )
    return raw


def _toggle(ids: List[int], target_id: int, action: str) -> List[int]:
    """红黑榜增删：ADD 去重追加，REMOVE 过滤掉目标 ID。"""
    current = [int(i) for i in (ids or [])]
    if action == "ADD":
        if target_id not in current:
            current.append(target_id)
    else:
        current = [i for i in current if i != target_id]
    return current


@router.post(
    "/users/{user_id}/red-black-list", response_model=RedBlackListResponse
)
def update_red_black_list(
    user_id: int,
    payload: RedBlackListRequest,
    db: Session = Depends(get_db),
    header_user_id: int = Depends(require_user),
) -> RedBlackListResponse:
    ensure_self(user_id, header_user_id)
    _get_user(db, user_id)
    prefs = _get_prefs(db, user_id)

    # 红榜只对菜品开放；门店只进黑榜（v2.3.1 第五章）
    if payload.list_type == "FAV" and payload.target_type != "DISH":
        raise HTTPException(
            status_code=400, detail="美食红榜仅支持菜品（target_type 必须为 DISH）"
        )

    if payload.target_type == "DISH":
        dish = db.query(Dish).filter(Dish.id == payload.target_id).first()
        if dish is None:
            raise HTTPException(
                status_code=404, detail=f"菜品 {payload.target_id} 不存在"
            )
        field = (
            "favorite_dish_ids"
            if payload.list_type == "FAV"
            else "blacklist_dish_ids"
        )
    else:
        restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == payload.target_id)
            .first()
        )
        if restaurant is None:
            raise HTTPException(
                status_code=404, detail=f"门店 {payload.target_id} 不存在"
            )
        field = "blacklist_restaurant_ids"

    setattr(
        prefs, field, _toggle(getattr(prefs, field), payload.target_id, payload.action)
    )
    db.commit()
    db.refresh(prefs)
    return RedBlackListResponse(
        favorite_dish_ids=[int(i) for i in (prefs.favorite_dish_ids or [])],
        blacklist_dish_ids=[int(i) for i in (prefs.blacklist_dish_ids or [])],
        blacklist_restaurant_ids=[
            int(i) for i in (prefs.blacklist_restaurant_ids or [])
        ],
    )


@router.patch("/users/{user_id}/profile", response_model=ProfileResponse)
def update_profile_basic(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    header_user_id: int = Depends(require_user),
) -> ProfileResponse:
    """改昵称与头像。

    与 preferences 分开：那支管算法用的偏好（预算/忌口/向量），
    这支只管展示信息，两者权限与校验口径不同，混在一起容易误改。
    """
    ensure_self(user_id, header_user_id)
    user = _get_user(db, user_id)
    prefs = _get_prefs(db, user_id)

    nickname = payload.get("nickname")
    if nickname is not None:
        nickname = str(nickname).strip()
        if not nickname:
            raise HTTPException(422, "昵称不能为空")
        if len(nickname) > 32:
            raise HTTPException(422, "昵称最多 32 个字符")
        user.nickname = nickname

    avatar = payload.get("avatar")
    if avatar is not None:
        avatar = str(avatar).strip()
        if len(avatar) > 4:
            raise HTTPException(422, "头像目前只支持 1–4 个字符（emoji 或首字）")
        user.avatar = avatar

    db.commit()
    db.refresh(user)
    return _build_profile(db, user, prefs)


@router.post("/users/{user_id}/avatar")
async def upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    header_user_id: int = Depends(require_user),
):
    """上传头像。

    存文件而不是 base64：头像会被列表页反复渲染，base64 塞进用户表会让每次查询都拖着几十 KB。
    统一裁成 256×256 JPEG，既省空间也避免前端拿到各种尺寸的原图。
    """
    ensure_self(user_id, header_user_id)
    user = _get_user(db, user_id)

    content = await file.read()
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 3MB")
    try:
        image = Image.open(BytesIO(content)).convert("RGB")
    except Exception:
        raise HTTPException(422, "无法识别的图片格式，请上传 JPG / PNG / WebP")

    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((256, 256), Image.LANCZOS)

    out_dir = Path(__file__).resolve().parents[1] / "uploads" / "avatars"
    out_dir.mkdir(parents=True, exist_ok=True)
    # 文件名带时间戳：同名覆盖会被浏览器缓存，换了头像看不到变化
    name = f"{user_id}_{int(time.time())}.jpg"
    image.save(out_dir / name, "JPEG", quality=86)

    user.avatar = f"/uploads/avatars/{name}"
    db.commit()
    return {"avatar": user.avatar}
