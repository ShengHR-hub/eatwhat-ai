"""S15：13 个大屏统计接口。

当前快照统计过滤软删除；历史流水与投票保留原关联。下厨数据始终按 SHARED
处理，校区筛选不会把共享菜谱复制到任一校区。
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date, timedelta, timezone
from itertools import combinations
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (
    Dish,
    EatingLog,
    GroupRoom,
    Restaurant,
    RoomVote,
    User,
    UserPreference,
)

router = APIRouter(
    prefix="/admin/stats",
    tags=["大屏统计"],
    # 大屏能导出全校进食流水，属于敏感数据，必须管理员才能看
    dependencies=[Depends(require_admin)],
)
Mode = Literal["OUT_DINING", "HOME_COOKING"]
Campus = Literal["SIYUAN", "JIANDA_YANTA", "JIANDA_CAOTANG", "ALL"]
SHANGHAI = ZoneInfo("Asia/Shanghai")
FEATURE_KEYS = {
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
}
STOP_INGREDIENTS = {"盐", "水", "油", "葱", "姜", "蒜", "食用油", "清水", "食盐", "生抽", "老抽"}


def _meta(scope="ALL", **extra):
    return {"scope": scope, **extra}


def _na(reason: str, scope="GLOBAL") -> dict:
    return {"applicable": False, "reason": reason, "items": [], "meta": _meta(scope)}


def _scope(campus: Optional[str]) -> str:
    return "ALL" if not campus or campus == "ALL" else campus


def _dish_query(db, mode_type, cuisine_type, campus, *, active=True, campus_out_only=False):
    query = db.query(Dish).outerjoin(Restaurant, Dish.restaurant_id == Restaurant.id)
    if active:
        query = query.filter(Dish.deleted_at.is_(None))
    if mode_type:
        query = query.filter(Dish.mode_type == mode_type)
    if cuisine_type:
        query = query.filter(Dish.cuisine_type == cuisine_type)
    if campus and campus != "ALL":
        if campus_out_only:
            query = query.filter(Dish.mode_type == "OUT_DINING", Restaurant.campus == campus)
        else:
            query = query.filter(or_(Dish.mode_type == "HOME_COOKING", Restaurant.campus == campus))
    return query


def _log_query(db, mode_type, cuisine_type, campus, *, campus_out_only=False):
    query = (
        db.query(EatingLog)
        .join(Dish, EatingLog.dish_id == Dish.id)
        .outerjoin(Restaurant, Dish.restaurant_id == Restaurant.id)
    )
    if mode_type:
        query = query.filter(EatingLog.mode_type == mode_type)
    if cuisine_type:
        query = query.filter(Dish.cuisine_type == cuisine_type)
    if campus and campus != "ALL":
        if campus_out_only:
            query = query.filter(EatingLog.mode_type == "OUT_DINING", Restaurant.campus == campus)
        else:
            query = query.filter(or_(EatingLog.mode_type == "HOME_COOKING", Restaurant.campus == campus))
    return query


def _vote_query(db, mode_type, cuisine_type, campus, *, campus_out_only=False, include_veto=True):
    query = (
        db.query(RoomVote)
        .join(Dish, RoomVote.dish_id == Dish.id)
        .join(GroupRoom, RoomVote.room_code == GroupRoom.room_code)
        .outerjoin(Restaurant, Dish.restaurant_id == Restaurant.id)
    )
    if not include_veto:
        query = query.filter(RoomVote.vote_type != "VETO")
    if mode_type:
        query = query.filter(GroupRoom.mode_type == mode_type)
    if cuisine_type:
        query = query.filter(Dish.cuisine_type == cuisine_type)
    if campus and campus != "ALL":
        if campus_out_only:
            query = query.filter(GroupRoom.mode_type == "OUT_DINING", GroupRoom.campus == campus)
        else:
            query = query.filter(or_(GroupRoom.mode_type == "HOME_COOKING", GroupRoom.campus == campus))
    return query


def _room_query(db, mode_type, campus, *, campus_out_only=False):
    query = db.query(GroupRoom)
    if mode_type:
        query = query.filter(GroupRoom.mode_type == mode_type)
    if campus and campus != "ALL":
        if campus_out_only:
            query = query.filter(GroupRoom.mode_type == "OUT_DINING", GroupRoom.campus == campus)
        else:
            query = query.filter(or_(GroupRoom.mode_type == "HOME_COOKING", GroupRoom.campus == campus))
    return query


def _local(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(SHANGHAI)


def _date_range(counts) -> list[str]:
    if not counts:
        return []
    first = date.fromisoformat(min(counts))
    last = date.fromisoformat(max(counts))
    return [
        (first + timedelta(days=offset)).isoformat()
        for offset in range((last - first).days + 1)
    ]


def _valid_vector(vector) -> bool:
    if not isinstance(vector, dict) or set(vector) != FEATURE_KEYS:
        return False
    return all(
        isinstance(vector.get(key), (int, float))
        and not isinstance(vector.get(key), bool)
        and math.isfinite(float(vector[key]))
        and 0 <= float(vector[key]) <= 1
        for key in FEATURE_KEYS
    )


def _quality(rows) -> dict:
    fields = (
        "name",
        "cuisine_type",
        "price_or_cost",
        "ingredients_main",
        "ingredients_aux",
        "feature_vector",
        "image_url",
        "allergen_tags",
    )
    missing = Counter()
    invalid = 0
    success_invalid = 0
    success = 0
    for row in rows:
        vector_valid = _valid_vector(row.feature_vector)
        if row.feature_vector is not None and not vector_valid:
            invalid += 1
        if row.tagging_status == "SUCCESS":
            if vector_valid:
                success += 1
            else:
                success_invalid += 1
        for field in fields:
            value = getattr(row, field)
            if value is None or value == "" or value == []:
                missing[field] += 1
    total = len(rows)
    coverage = success / total if total else 0.0
    return {
        "tagging_coverage": coverage,
        "tagged_dishes": success,
        "total_dishes": total,
        "missing_fields": [
            {"field": field, "count": count}
            for field, count in missing.most_common()
        ],
        "vector_anomalies": {
            "total": invalid,
            "invalid_vector": invalid,
            "success_without_valid_vector": success_invalid,
        },
    }


def _overview_block(db, mode_type, cuisine_type, campus, block):
    out_only = block not in {None, "SHARED"}
    selected_campus = None if block in {None, "SHARED"} else block
    if block == "UNASSIGNED":
        restaurant_query = db.query(Restaurant).filter(Restaurant.campus.is_(None))
    else:
        restaurant_query = db.query(Restaurant)
        if selected_campus:
            restaurant_query = restaurant_query.filter(Restaurant.campus == selected_campus)
    restaurant_query = restaurant_query.filter(Restaurant.deleted_at.is_(None))

    dish_query = _dish_query(db, mode_type, cuisine_type, selected_campus, campus_out_only=out_only)
    log_query = _log_query(db, mode_type, cuisine_type, selected_campus, campus_out_only=out_only)
    vote_query = _vote_query(db, mode_type, cuisine_type, selected_campus, campus_out_only=out_only)
    room_query = _room_query(db, mode_type, selected_campus, campus_out_only=out_only)
    if block == "SHARED":
        dish_query = dish_query.filter(Dish.mode_type == "HOME_COOKING")
        log_query = log_query.filter(EatingLog.mode_type == "HOME_COOKING")
        vote_query = vote_query.filter(GroupRoom.mode_type == "HOME_COOKING")
        room_query = room_query.filter(GroupRoom.mode_type == "HOME_COOKING")
        restaurant_query = restaurant_query.filter(Restaurant.id < 0)
    elif block == "UNASSIGNED":
        dish_query = _dish_query(db, mode_type, cuisine_type, None).filter(
            Dish.mode_type == "OUT_DINING", Restaurant.campus.is_(None)
        )
        log_query = _log_query(db, mode_type, cuisine_type, None).filter(
            EatingLog.mode_type == "OUT_DINING", Restaurant.campus.is_(None)
        )
        vote_query = _vote_query(db, mode_type, cuisine_type, None).filter(
            GroupRoom.mode_type == "OUT_DINING", Restaurant.campus.is_(None)
        )
        room_query = room_query.filter(GroupRoom.mode_type == "OUT_DINING", GroupRoom.campus.is_(None))
    if block in {"SIYUAN", "JIANDA_YANTA", "JIANDA_CAOTANG", "UNASSIGNED"}:
        restaurant_count = restaurant_query.count()
    else:
        restaurant_count = restaurant_query.count() if block is None else 0
    dishes = dish_query.all()
    quality = _quality(dishes)
    return {
        "restaurants": restaurant_count,
        "dishes": len(dishes),
        "feature_values": quality["tagged_dishes"] * 8,
        "logs": log_query.count(),
        "votes": vote_query.count(),
        "rooms": room_query.count(),
        "tagging_coverage": quality["tagging_coverage"],
    }


@router.get("/overview")
def overview(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    by_campus = {
        block: _overview_block(db, mode_type, cuisine_type, campus, block)
        for block in ("SIYUAN", "JIANDA_YANTA", "JIANDA_CAOTANG", "SHARED", "UNASSIGNED")
    }
    if campus and campus != "ALL":
        campus_block = _overview_block(db, mode_type, cuisine_type, campus, campus)
        shared_block = by_campus["SHARED"]
        total = {
            key: (campus_block[key] + shared_block[key] if key != "tagging_coverage" else 0.0)
            for key in campus_block
        }
        tagged = campus_block["feature_values"] // 8 + shared_block["feature_values"] // 8
        total["tagging_coverage"] = tagged / total["dishes"] if total["dishes"] else 0.0
    else:
        total = _overview_block(db, mode_type, cuisine_type, campus, None)
    return {
        "applicable": True,
        "by_campus": by_campus,
        "total": total,
        "restaurants_total": total["restaurants"],
        "dishes_total": total["dishes"],
        "feature_values_total": total["feature_values"],
        "logs_total": total["logs"],
        "votes_total": total["votes"],
        "rooms_total": total["rooms"],
        "tagging_coverage": total["tagging_coverage"],
        "meta": _meta(
            _scope(campus),
            mode_filter="dishes/logs/votes/rooms",
            cuisine_filter="dishes/logs/votes；restaurants/rooms 不按菜系隐含过滤",
            shared="HOME_COOKING 仅在 SHARED 单列；选择校区时 total=该校区外食+SHARED",
        ),
    }


@router.get("/geo")
def geo(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    limit: int = Query(3000, ge=200, le=10000, description="点位采样上限"),
    db: Session = Depends(get_db),
):
    if mode_type == "HOME_COOKING":
        return _na("共享下厨菜谱没有门店地理点位", "SHARED")
    heat = dict(
        _log_query(db, "OUT_DINING", cuisine_type, campus)
        .with_entities(Dish.restaurant_id, func.count(EatingLog.id))
        .group_by(Dish.restaurant_id)
        .all()
    )
    query = db.query(Restaurant).filter(Restaurant.deleted_at.is_(None))
    if campus and campus != "ALL":
        query = query.filter(Restaurant.campus == campus)
    if cuisine_type:
        restaurant_ids = (
            db.query(Dish.restaurant_id)
            .filter(
                Dish.deleted_at.is_(None),
                Dish.mode_type == "OUT_DINING",
                Dish.cuisine_type == cuisine_type,
            )
            .distinct()
        )
        query = query.filter(Restaurant.id.in_(restaurant_ids))

    # 全量 7,704 个点位实测 1.26MB。按 id 取模均匀采样后体积减半，
    # 地图上的空间分布不变（不是"取前 N 个"，那样会只剩某个片区）。
    total = query.count()
    sampled = total
    if total > limit:
        step = max(1, total // limit)
        query = query.filter(Restaurant.id % step == 0)
        sampled = limit

    points = [
        {
            "id": row.id,
            "name": row.name,
            "lng": row.longitude,
            "lat": row.latitude,
            "rating": row.rating,
            "cost": row.avg_price,
            "heat": int(heat.get(row.id, 0)),
            "campus": row.campus,
            "is_synthetic": row.is_synthetic,
        }
        for row in query.order_by(Restaurant.id).all()
        if row.longitude is not None and row.latitude is not None
    ]
    return {
        "applicable": True,
        "points": points,
        "meta": _meta(
            _scope(campus),
            coordinate="GCJ-02",
            sample_limit=limit,
            sampled=sampled,
            total=total,
        ),
    }


@router.get("/calendar")
def calendar(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    counts = Counter(
        _local(value).date().isoformat()
        for (value,) in _log_query(db, mode_type, cuisine_type, campus).with_entities(EatingLog.eaten_at).all()
    )
    return {
        "applicable": True,
        "daily": [{"date": key, "count": counts[key]} for key in _date_range(counts)],
        "meta": _meta(_scope(campus), timezone="Asia/Shanghai"),
    }


@router.get("/heatmap")
def heatmap(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    matrix = Counter()
    for (value,) in _log_query(db, mode_type, cuisine_type, campus).with_entities(EatingLog.eaten_at).all():
        local = _local(value)
        hour = local.hour
        slot = "早餐" if 5 <= hour < 10 else "午餐" if 10 <= hour < 15 else "晚餐" if 15 <= hour < 21 else "夜宵"
        matrix[(local.weekday(), slot)] += 1
    slots = ("早餐", "午餐", "晚餐", "夜宵")
    return {
        "applicable": True,
        "matrix": [
            {"weekday": weekday, "slot": slot, "count": matrix[(weekday, slot)]}
            for weekday in range(7)
            for slot in slots
        ],
        "meta": _meta(_scope(campus), timezone="Asia/Shanghai", slots="[05,10)/[10,15)/[15,21)/[21,05)"),
    }


@router.get("/cuisine")
def cuisine(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    rows = (
        _dish_query(db, mode_type, cuisine_type, campus)
        .with_entities(Dish.cuisine_type, func.count(Dish.id))
        .group_by(Dish.cuisine_type)
        .order_by(func.count(Dish.id).desc())
        .all()
    )
    total = sum(int(count) for _, count in rows)
    items = [
        {"cuisine_type": name or "未标注", "count": int(count), "share": int(count) / total if total else 0.0}
        for name, count in rows
    ]
    return {"applicable": True, "items": items, "meta": _meta(_scope(campus), unit="dishes_rows")}


@router.get("/cuisine-trend")
def cuisine_trend(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    rows = _log_query(db, mode_type, cuisine_type, campus).with_entities(
        EatingLog.eaten_at, Dish.cuisine_type
    ).all()
    counts = Counter()
    cuisines = Counter()
    for eaten_at, cuisine_name in rows:
        day = _local(eaten_at).date().isoformat()
        name = cuisine_name or "未标注"
        counts[(day, name)] += 1
        cuisines[name] += 1
    dates = _date_range({day for day, _ in counts})
    series = [
        {"cuisine_type": name, "data": [counts[(day, name)] for day in dates]}
        for name, _ in cuisines.most_common()
    ]
    return {"applicable": True, "dates": dates, "series": series, "meta": _meta(_scope(campus), unit="eating_logs")}


@router.get("/personas")
def personas(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    scope: str = Query("demo", pattern="^(demo|real|all)$"),
    db: Session = Depends(get_db),
):
    if (campus and campus != "ALL") or mode_type or cuisine_type:
        return _na("C09 为 GLOBAL 人设图，不支持校区、模式或菜系筛选")

    def _rows(is_demo: bool, limit: int, newest_first: bool = False):
        query = (
            db.query(User, UserPreference)
            .join(UserPreference, UserPreference.user_id == User.id)
            .filter(User.is_demo_persona.is_(is_demo))
        )
        if not is_demo:
            query = query.filter(User.role == "USER")
        order = User.id.desc() if newest_first else User.id
        return query.order_by(order).limit(limit).all()

    rows = []
    if scope in ("demo", "all"):
        rows.extend(_rows(True, 4))
    if scope in ("real", "all"):
        rows.extend(_rows(False, 6, newest_first=True))

    return {
        "applicable": True,
        "scope": scope,
        "personas": [
            {
                "user_id": user.id,
                "nickname": user.nickname,
                "persona_title": user.persona_title,
                "is_demo": bool(user.is_demo_persona),
                "base_vector": preference.base_vector,
            }
            for user, preference in rows
        ],
        "meta": _meta("GLOBAL"),
    }


@router.get("/scatter")
def scatter(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    limit: int = Query(1500, ge=100, le=5000, description="每类实体的采样上限"),
    db: Session = Depends(get_db),
):
    dish_heat = Counter()
    for dish_id, count in _log_query(db, mode_type, cuisine_type, campus).with_entities(
        EatingLog.dish_id, func.count(EatingLog.id)
    ).group_by(EatingLog.dish_id).all():
        dish_heat[dish_id] += int(count)
    for dish_id, count in _vote_query(db, mode_type, cuisine_type, campus, include_veto=False).with_entities(
        RoomVote.dish_id, func.count(RoomVote.id)
    ).group_by(RoomVote.dish_id).all():
        dish_heat[dish_id] += int(count)
    restaurant_heat = Counter()
    for restaurant_id, count in _log_query(db, "OUT_DINING", cuisine_type, campus).with_entities(
        Dish.restaurant_id, func.count(EatingLog.id)
    ).group_by(Dish.restaurant_id).all():
        restaurant_heat[restaurant_id] += int(count)
    for restaurant_id, count in _vote_query(db, "OUT_DINING", cuisine_type, campus, include_veto=False).with_entities(
        Dish.restaurant_id, func.count(RoomVote.id)
    ).group_by(Dish.restaurant_id).all():
        restaurant_heat[restaurant_id] += int(count)

    points = []
    if mode_type != "HOME_COOKING":
        restaurants = db.query(Restaurant).filter(Restaurant.deleted_at.is_(None))
        if campus and campus != "ALL":
            restaurants = restaurants.filter(Restaurant.campus == campus)
        if cuisine_type:
            ids = _dish_query(db, "OUT_DINING", cuisine_type, campus).with_entities(Dish.restaurant_id).distinct()
            restaurants = restaurants.filter(Restaurant.id.in_(ids))
        # 全量返回会让单次响应到 2.3MB（实测 7,704 店 + 6,560 菜）。
        # 按 id 取模均匀采样，保持空间/价格分布，不会像"取前 N 个"那样塌成一团。
        total_r = restaurants.count()
        sampled_r = total_r
        if total_r > limit:
            step_r = max(1, total_r // limit)
            restaurants = restaurants.filter(Restaurant.id % step_r == 0)
            sampled_r = limit
        for row in restaurants.all():
            points.append({
                "name": row.name,
                "price": row.avg_price,
                "rating": row.rating,
                "freq": restaurant_heat[row.id],
                "entity_id": row.id,
                "entity_type": "RESTAURANT",
                "mode_type": "OUT_DINING",
                "campus": row.campus,
            })
    dish_source = _dish_query(db, mode_type, cuisine_type, campus)
    total_d = dish_source.count()
    sampled_d = total_d
    if total_d > limit:
        step_d = max(1, total_d // limit)
        dish_source = dish_source.filter(Dish.id % step_d == 0)
        sampled_d = limit
    dishes = dish_source.all()
    restaurant_ids = {row.restaurant_id for row in dishes if row.restaurant_id is not None}
    restaurant_by_id = {
        row.id: row
        for row in db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()
    } if restaurant_ids else {}
    for row in dishes:
        restaurant = restaurant_by_id.get(row.restaurant_id)
        points.append({
            "name": row.name,
            "price": row.price_or_cost,
            "rating": restaurant.rating if row.mode_type == "OUT_DINING" and restaurant else None,
            "freq": dish_heat[row.id],
            "entity_id": row.id,
            "entity_type": "DISH",
            "mode_type": row.mode_type,
            "campus": restaurant.campus if restaurant else "SHARED",
        })
    no_rating = sum(point["rating"] is None for point in points)
    no_price = sum(point["price"] is None for point in points)
    return {
        "applicable": True,
        "points": points,
        "meta": _meta(
            _scope(campus),
            not_plotted_no_rating=no_rating,
            not_plotted_no_price=no_price,
            rating_source="restaurant.rating；HOME_COOKING 不伪造评分",
            sample_limit=limit,
            sampled={"restaurants": sampled_r, "dishes": sampled_d},
            totals={"restaurants": total_r, "dishes": total_d},
        ),
    }


@router.get("/flow")
def flow(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    if cuisine_type:
        return _na("桑基缺席分母需要完整房间候选，不能用菜系筛选后伪算缺席", _scope(campus))
    votes = _vote_query(db, mode_type, None, campus).with_entities(
        RoomVote.vote_type, RoomVote.dish_id, GroupRoom.winner_dish_id
    ).all()
    rooms = _room_query(db, mode_type, campus).with_entities(
        GroupRoom.member_user_ids, GroupRoom.candidate_dish_ids
    ).all()
    opportunities = sum(len(members or []) * len(candidates or []) for members, candidates in rooms)
    by_type = Counter(vote_type for vote_type, _, _ in votes)
    outcomes = Counter()
    for vote_type, dish_id, winner_id in votes:
        outcome = "否决" if vote_type == "VETO" else "赢家" if winner_id == dish_id else "其他候选"
        outcomes[(vote_type, outcome)] += 1
    absent = max(0, opportunities - len(votes))
    links = [
        {"source": "全部候选", "target": vote_type, "value": count}
        for vote_type, count in sorted(by_type.items())
    ]
    if absent:
        links.append({"source": "全部候选", "target": "缺席", "value": absent})
    links.extend(
        {"source": vote_type, "target": outcome, "value": count}
        for (vote_type, outcome), count in sorted(outcomes.items())
    )
    node_names = sorted({item for link in links for item in (link["source"], link["target"])})
    return {
        "applicable": True,
        "nodes": [{"name": name} for name in node_names],
        "links": links,
        "meta": _meta(
            _scope(campus),
            unit="票",
            total_opportunities=opportunities,
            actual_votes=len(votes),
            absent_votes=absent,
            room_results="赢家/其他候选/否决按房间 winner_dish_id 与票型归属",
        ),
    }


def _name_tokens(row) -> list[str]:
    name = re.sub(r"[（(].*?[）)]", "", row.name or "").strip()
    if not name:
        return []
    lexicon = sorted(
        {item for item in (row.ingredients_main or []) + (row.ingredients_aux or []) if len(item) >= 2},
        key=len,
        reverse=True,
    )
    tokens = [item for item in lexicon if item in name]
    if tokens:
        return list(dict.fromkeys(tokens))
    parts = [part for part in re.split(r"[\s·×xX、，,/\\_-]+", name) if len(part) >= 2]
    return parts[:4]


@router.get("/keywords")
def keywords(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    top_n: int = Query(80, ge=1, le=200),
    db: Session = Depends(get_db),
):
    counts = Counter()
    for row in _dish_query(db, mode_type, cuisine_type, campus).all():
        counts.update(tag for tag in (row.allergen_tags or []) if tag and tag not in STOP_INGREDIENTS)
        counts.update(token for token in _name_tokens(row) if token not in STOP_INGREDIENTS)
    return {
        "applicable": True,
        "words": [{"name": name, "value": value} for name, value in counts.most_common(top_n)],
        "meta": _meta(
            _scope(campus),
            source="allergen_tags + 菜名分词",
            tokenizer="主辅料词典最长匹配；无命中时按分隔符切分并保留完整词组",
        ),
    }


@router.get("/race")
def race(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    events = []
    for dish_id, name, eaten_at in _log_query(db, mode_type, cuisine_type, campus).with_entities(
        EatingLog.dish_id, Dish.name, EatingLog.eaten_at
    ).all():
        events.append((dish_id, name, eaten_at))
    for dish_id, name, voted_at in _vote_query(db, mode_type, cuisine_type, campus, include_veto=False).with_entities(
        RoomVote.dish_id, Dish.name, RoomVote.voted_at
    ).all():
        events.append((dish_id, name, voted_at))
    overall = Counter()
    weekly = Counter()
    names = {}
    for dish_id, name, occurred_at in events:
        local = _local(occurred_at)
        week = (local.date() - timedelta(days=local.weekday())).isoformat()
        overall[dish_id] += 1
        weekly[(week, dish_id)] += 1
        names[dish_id] = name
    weeks = sorted({week for week, _ in weekly})
    weekly_top = set()
    for week in weeks:
        weekly_top.update(
            dish_id
            for dish_id, _ in sorted(
                ((dish_id, weekly[(week, dish_id)]) for dish_id in names),
                key=lambda item: (-item[1], item[0]),
            )[:10]
        )
    latest_ids = [dish_id for dish_id, _ in sorted(overall.items(), key=lambda item: (-item[1], item[0]))[:10]]
    series_ids = list(dict.fromkeys(latest_ids + sorted(weekly_top)))
    series = [
        {
            "dish_id": dish_id,
            "dish_name": names[dish_id],
            "data": [weekly[(week, dish_id)] for week in weeks],
        }
        for dish_id in series_ids
    ]
    latest = [
        {"dish_id": dish_id, "dish_name": names[dish_id], "value": overall[dish_id], "count": overall[dish_id]}
        for dish_id in latest_ids
    ]
    return {
        "applicable": True,
        "weeks": weeks,
        "series": series,
        "latest_top10": latest,
        "meta": _meta(_scope(campus), heat="eating_logs + room_votes（VETO 不计）", week="Asia/Shanghai 周一起始"),
    }


@router.get("/cooccurrence")
def cooccurrence(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    top_n: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if mode_type == "OUT_DINING":
        return _na("食材共现只统计共享下厨菜谱", "SHARED")
    pairs = Counter()
    ingredient_rows = Counter()
    for row in _dish_query(db, "HOME_COOKING", cuisine_type, campus).all():
        ingredients = sorted(
            {
                item.strip()
                for item in (row.ingredients_main or []) + (row.ingredients_aux or [])
                if isinstance(item, str) and item.strip() and item.strip() not in STOP_INGREDIENTS
            }
        )
        ingredient_rows.update(ingredients)
        pairs.update(combinations(ingredients, 2))
    selected = sorted(
        ((pair, count) for pair, count in pairs.items() if count >= 3),
        key=lambda item: (-item[1], item[0]),
    )[:top_n]
    used = {item for pair, _ in selected for item in pair}
    nodes = [
        {"name": name, "value": ingredient_rows[name]}
        for name in sorted(used, key=lambda item: (-ingredient_rows[item], item))
    ]
    links = [
        {"source": pair[0], "target": pair[1], "value": count}
        for pair, count in selected
    ]
    return {
        "applicable": True,
        "nodes": nodes,
        "links": links,
        "meta": _meta("SHARED" if mode_type == "HOME_COOKING" else _scope(campus), min_count=3, top_n=top_n, unordered=True),
    }


@router.get("/quality")
def quality(
    mode_type: Optional[Mode] = None,
    cuisine_type: Optional[str] = Query(None, max_length=64),
    campus: Optional[Campus] = None,
    db: Session = Depends(get_db),
):
    result = _quality(_dish_query(db, mode_type, cuisine_type, campus).all())
    return {
        "applicable": True,
        **result,
        "meta": _meta(
            _scope(campus),
            numerator="tagging_status=SUCCESS 且完整 8 维有限且 0~1",
            denominator="当前筛选下 deleted_at IS NULL 的 dishes 行数",
        ),
    }
