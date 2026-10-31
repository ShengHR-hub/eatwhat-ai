"""模块 4：多人「干饭房间」（批次 3 后半）。

REST（对齐 `MASTER_SPEC.md` 第 197-207、315-317 行）：
    POST /api/v1/rooms/create          {mode_type, budget?, host_user_id?} → 6 位数字码 + 候选
    POST /api/v1/rooms/{code}/join     {user_id?}     → 加入（幂等，最多 8 人，仅 WAITING）
    GET  /api/v1/rooms/{code}                         → 房间快照（含候选/我的票/截止/赢家/报告）

WebSocket（`MASTER_SPEC.md` 第 344-352 行）：
    ws://{host}/ws/room/{room_code}/{user_id}
    * 建连前必须已经 join 过，否则**握手直接 403**（不再 accept 后 1008）
    * 客户端 → 服务端：{"type":"START_SWIPING"}（仅房主）、
      {"type":"SUBMIT_VOTE","dish_id":..,"vote_type":"LIKE"}
    * 服务端 → 客户端：MEMBER_SYNC / START_SWIPING / PROGRESS_UPDATE / CONSENSUS_REVEAL

状态机（规格只允许这三个值）：
    WAITING --房主 START_SWIPING--> SWIPING --全员划完或 15 秒到--> FINISHED

审查报告整改（F03/F04/F05/F11）：
    F03 截止时间落库（`group_rooms.deadline_at`），结算幂等（`settled_at`）。
        最后一个人断线**不再取消定时器**；进程重启/无定时器时由 GET 或建连时惰性结算。
    F04 只有 SWIPING 且未过期时接受投票，FINISHED 后一律拒绝。
    F05 快照带候选、本人已投票、服务端截止与赢家详情，刷新/断线重进都能恢复现场。
    F11 契约对齐：`/rooms/create` + budget、6 位数字码、`FINISHED`、握手 403。

分工说明：候选池来自 `shortlist_candidates`（算法 3 阶段一），
结算走 `compute_group_consensus`（阶段二，含最小痛苦项与 VETO 一票否决），
本模块只负责「房间状态 + 协议 + 广播」，不重复实现博弈逻辑。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import random
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from starlette.concurrency import run_in_threadpool

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import current_algo_params
from ..database import SessionLocal, get_db
from ..deps import ensure_member, require_user, resolve_user_id
from ..models import (
    AlgoConfig,
    AuthToken,
    Dish,
    GroupRoom,
    Restaurant,
    RoomVote,
    User,
    utcnow,
)
from ..schemas import (
    RoomCandidate,
    RoomCreateRequest,
    RoomJoinRequest,
    RoomMemberBrief,
    RoomSnapshot,
)
from ..algorithms.single_recommender import recommend_single
from ..algorithms.group_recommender import (
    compute_group_consensus,
    shortlist_candidates,
)
from ..algorithms.vector_spec import VOTE_SCORES

router = APIRouter(tags=["多人干饭房间"])
# WebSocket 挂在根路径（ws://host/ws/room/...），REST 挂在 /api/v1 下，所以用两个 router
ws_router = APIRouter()
identity_logger = logging.getLogger("eatwhat.identity")

MAX_MEMBERS = 8
CANDIDATE_COUNT = 10
SWIPE_SECONDS = 15
# v2.3.6：客户端只允许 SSOT 四个枚举；TIMEOUT 仅作为结算内部缺席分。
VALID_VOTE_TYPES = set(VOTE_SCORES.keys())
# 进程重启/定时器丢失后的兜底扫描周期（秒）。
SETTLE_SWEEP_SECONDS = 5
STATUS_WAITING = "WAITING"
STATUS_SWIPING = "SWIPING"
STATUS_FINISHED = "FINISHED"

room_logger = logging.getLogger("eatwhat.room")
# uvicorn 只给自身的 logger 配置 handler，应用 logger 的 INFO 默认会被丢弃。
# 房间审计日志（create/join/start/sweep_settled）单独输出，失败路径仍用
# warning/exception；propagate=False 避免重复。
if not room_logger.handlers:
    _room_handler = logging.StreamHandler()
    _room_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    room_logger.addHandler(_room_handler)
room_logger.setLevel(logging.INFO)
room_logger.propagate = False

# v2.3.6：同一房间的 join / START / 投票 / 结算串行化。
# 单进程内用 per-room RLock；跨进程重复票由 room_votes 唯一索引兜底。
_room_locks: Dict[str, threading.RLock] = {}
_room_locks_guard = threading.Lock()


def _room_lock(code: str) -> threading.RLock:
    with _room_locks_guard:
        lock = _room_locks.get(code)
        if lock is None:
            lock = threading.RLock()
            _room_locks[code] = lock
        return lock


def utcnow() -> datetime:
    """和 models 里的 created_at 保持同一口径（naive UTC）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# —————————————————————— 房间读写 ——————————————————————


def _room_or_404(db: Session, code: str) -> GroupRoom:
    room = (
        db.query(GroupRoom)
        .filter(GroupRoom.room_code == str(code).strip())
        .first()
    )
    if room is None:
        raise HTTPException(status_code=404, detail=f"房间 {code} 不存在")
    return room


def _unique_code(db: Session) -> str:
    """规格第 198 行：6 位**数字**字符串，如 886421。"""
    for _ in range(50):
        code = str(random.randint(100000, 999999))
        if db.query(GroupRoom).filter(GroupRoom.room_code == code).first() is None:
            return code
    raise HTTPException(status_code=500, detail="房间码生成失败，请重试")


def _remaining_ms(room: GroupRoom) -> int:
    if room.deadline_at is None:
        return 0
    delta = (room.deadline_at - utcnow()).total_seconds() * 1000
    return max(0, int(delta))


def _progress_map(
    db: Session, code: str, member_ids: List[int], total: int
) -> Dict[int, int]:
    """每个成员「划了几张」= 该成员投过的不同菜品数（封顶 total）。"""
    if not member_ids or total <= 0:
        return {}
    rows = (
        db.query(RoomVote)
        .filter(
            RoomVote.room_code == code,
            RoomVote.user_id.in_(member_ids),
        )
        .all()
    )
    seen: Dict[int, set] = {}
    for row in rows:
        seen.setdefault(int(row.user_id), set()).add(int(row.dish_id))
    return {
        uid: min(len(seen.get(uid, set())), total) for uid in member_ids
    }


def _member_briefs(db: Session, room: GroupRoom) -> List[RoomMemberBrief]:
    ids = [int(i) for i in (room.member_user_ids or [])]
    if not ids:
        return []
    users = {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()}
    progress = _progress_map(db, room.room_code, ids, len(room.candidate_dish_ids or []))
    out: List[RoomMemberBrief] = []
    for uid in ids:
        user = users.get(uid)
        out.append(
            RoomMemberBrief(
                user_id=uid,
                nickname=getattr(user, "nickname", f"用户{uid}"),
                avatar=getattr(user, "avatar", "🍚") or "🍚",
                is_host=uid == room.host_user_id,
                progress=progress.get(uid, 0),
            )
        )
    return out


def _candidate_payload(db: Session, dish_ids: List[int]) -> List[RoomCandidate]:
    if not dish_ids:
        return []
    dishes = {d.id: d for d in db.query(Dish).filter(Dish.id.in_(dish_ids)).all()}
    restaurant_ids = {d.restaurant_id for d in dishes.values() if d.restaurant_id}
    restaurants = (
        {r.id: r for r in db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()}
        if restaurant_ids
        else {}
    )
    out: List[RoomCandidate] = []
    for did in dish_ids:
        dish = dishes.get(int(did))
        if dish is None:
            continue
        store = restaurants.get(dish.restaurant_id)
        out.append(
            RoomCandidate(
                dish_id=dish.id,
                name=dish.name,
                price=float(dish.price_or_cost or 0),
                cuisine_type=dish.cuisine_type or "",
                restaurant_name=getattr(store, "name", "") or "",
                image_url=dish.image_url or None,
                feature_vector=dish.feature_vector,
            )
        )
    return out


def _snapshot(
    db: Session, room: GroupRoom, viewer_id: Optional[int] = None
) -> RoomSnapshot:
    dish_ids = [int(i) for i in (room.candidate_dish_ids or [])]
    candidates = _candidate_payload(db, dish_ids)
    if viewer_id:
        try:
            personal = recommend_single(
                db,
                int(viewer_id),
                room.mode_type,
                budget=room.budget,
                campus=room.campus,
                weather_temp=20.0,
                weather_text="",
                limit=100,
                bubbles=[],
                # 只给本局这 10 道候选算匹配度，不再全表扫一遍
                only_dish_ids=dish_ids,
            )
            scores = {
                int(item["dish_id"]): item.get("radar_5d")
                for item in personal.get("recommendations", [])
            }
            for candidate in candidates:
                match = scores.get(candidate.dish_id)
                if match:
                    candidate.my_match = match
        except Exception:
            # 匹配度算不出来不该让整个快照挂掉，但也不能像以前那样静默：
            # 卡面上的「你的匹配」整块消失时，日志里至少要能查到原因。
            room_logger.exception(
                "room_snapshot_match_failed room_code=%s viewer=%s",
                room.room_code,
                viewer_id,
            )
    report = room.consensus_report or None
    winner_payload = None
    if room.winner_dish_id:
        found = _candidate_payload(db, [int(room.winner_dish_id)])
        winner_payload = found[0] if found else None

    my_votes: Dict[int, str] = {}
    if viewer_id:
        rows = (
            db.query(RoomVote)
            .filter(
                RoomVote.room_code == room.room_code,
                RoomVote.user_id == int(viewer_id),
            )
            .all()
        )
        my_votes = {int(r.dish_id): str(r.vote_type) for r in rows}

    return RoomSnapshot(
        room_code=room.room_code,
        host_user_id=int(room.host_user_id),
        mode_type=room.mode_type,
        campus=room.campus,
        omega_group=_omega_group(db, room),
        status=room.status,
        members=_member_briefs(db, room),
        candidates=candidates,
        candidate_count=len(candidates),
        winner_dish_id=int(room.winner_dish_id) if room.winner_dish_id else None,
        winner_dish=winner_payload,
        consensus_report=report,
        has_consensus=bool((report or {}).get("has_consensus")),
        deadline_at=room.deadline_at.isoformat() if room.deadline_at else None,
        remaining_ms=_remaining_ms(room),
        my_votes=my_votes,
        budget=room.budget,
        swipe_seconds=SWIPE_SECONDS,
    )


# —————————————————————— 结算（幂等）——————————————————————


def _algo_override(room: GroupRoom) -> Dict[str, float]:
    """建房时写下的算法参数快照（v2.3.6 起只写 omega_group）。"""
    params = getattr(room, "algo_params", None)
    if not isinstance(params, dict):
        return {}
    out: Dict[str, float] = {}
    for key, value in params.items():
        if value is None:
            continue
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _clamp_omega(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _configured_omega(db: Session) -> Tuple[float, str]:
    """生产配置里的 ω；非法值回退默认并记日志。"""
    config = (
        db.query(AlgoConfig)
        .filter(AlgoConfig.config_name == "default_production")
        .first()
    )
    if config is not None and config.omega_group is not None:
        raw = float(config.omega_group)
        if math.isfinite(raw):
            return _clamp_omega(raw), "algo_configs"
        room_logger.warning("room_omega_invalid source=algo_configs value=%r", raw)
    return float(current_algo_params()["omega_group"]), "default"


def _effective_omega(
    db: Session, override_params: Optional[Dict[str, float]]
) -> Tuple[float, str]:
    """建房屋确定本房有效 ω：请求 override → 生产配置 → 默认 0.5。"""
    if override_params and override_params.get("omega_group") is not None:
        return _clamp_omega(float(override_params["omega_group"])), "request"
    return _configured_omega(db)


def _omega_group(db: Session, room: GroupRoom) -> float:
    """群组折中系数 ω 的唯一出口（F10 收口 / v2.3.6 建房冻结）。

    新房间在 create 时把有效值写进 `algo_params`，之后 join/START/投票/结算
    都只读快照，不再读 DB。只有历史房间缺快照时才回退 DB → 默认，并告警。
    """
    override = _algo_override(room).get("omega_group")
    if override is not None:
        return _clamp_omega(override)
    value, source = _configured_omega(db)
    room_logger.warning(
        "room_omega_legacy_fallback room_code=%s source=%s value=%s",
        room.room_code,
        source,
        value,
    )
    return value


def _settle(db: Session, room: GroupRoom) -> Optional[dict]:
    """把 SWIPING 结算成 FINISHED。幂等 + 原子 claim（v2.3.6）。

    结算顺序：
    1. 在房间锁内刷新状态，只允许 SWIPING 且未结算；
    2. 先只读计算报告（失败不写任何状态，房间保持 SWIPING 可重试）；
    3. 用 `status='SWIPING' AND settled_at IS NULL` 的条件更新一次性写入
       status / winner / report / settled_at；`rowcount=0` 表示别的入口已结算，
       本入口不得写第二份结果。

    GET、WS 重连、定时器、全员完成早结算、启动/周期扫描都走这里。
    """
    code = room.room_code
    with _room_lock(code):
        db.refresh(room)
        if room.status != STATUS_SWIPING or room.settled_at is not None:
            return None

        members = [int(i) for i in (room.member_user_ids or [])]
        dish_ids = [int(i) for i in (room.candidate_dish_ids or [])]
        votes = db.query(RoomVote).filter(RoomVote.room_code == code).all()
        report = compute_group_consensus(
            db, members, dish_ids, votes, omega_group=_omega_group(db, room)
        )
        winner_id = report.get("winner_dish_id")
        settled_at = utcnow()

        try:
            claimed = (
                db.query(GroupRoom)
                .filter(
                    GroupRoom.room_code == code,
                    GroupRoom.status == STATUS_SWIPING,
                    GroupRoom.settled_at.is_(None),
                )
                .update(
                    {
                        GroupRoom.status: STATUS_FINISHED,
                        GroupRoom.winner_dish_id: (
                            int(winner_id) if winner_id is not None else None
                        ),
                        GroupRoom.consensus_report: report,
                        GroupRoom.settled_at: settled_at,
                    },
                    synchronize_session=False,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        if claimed != 1:
            db.expire_all()
            room_logger.info(
                "room_settle_lost_race room_code=%s claimed=%s", code, claimed
            )
            return None

    winner_payload = None
    if winner_id is not None:
        found = _candidate_payload(db, [int(winner_id)])
        winner_payload = found[0].model_dump() if found else None
    return {
        "type": "CONSENSUS_REVEAL",
        "room_code": code,
        "winner_dish_id": int(winner_id) if winner_id is not None else None,
        "winner": winner_payload,
        # F02：全票否决 / 候选全被否决时 winner 为 None，前端必须显示"没谈拢"，
        # 不能把 0 分当成推荐结果。
        "has_consensus": bool(report.get("has_consensus")),
        "message": (
            "大家已经选出这一顿"
            if winner_payload is not None
            else "所有候选都被否决了，这局没有共识"
        ),
        "report": report,
        "settled_at": settled_at.isoformat(),
    }


def _settle_if_due(db: Session, room: GroupRoom) -> Optional[dict]:
    """惰性结算：SWIPING 且已过截止时间就立刻结算。返回要广播的载荷。"""
    if room.status != STATUS_SWIPING:
        return None
    if room.deadline_at is None or _remaining_ms(room) > 0:
        return None
    return _settle(db, room)


# —————————————————————— REST ——————————————————————


def _rebuild_candidates(
    db: Session, room: GroupRoom, member_ids: List[int]
) -> List[int]:
    """v2.3.6：用当前全体成员 + 预算 + 校区重算 Top-10（如实返回实际数量）。"""
    pool = shortlist_candidates(
        db,
        [int(uid) for uid in member_ids],
        room.mode_type,
        top_n=CANDIDATE_COUNT,
        budget=room.budget,
        campus=room.campus,
    )
    room.candidate_dish_ids = [
        int(item["dish_id"]) for item in pool
    ][:CANDIDATE_COUNT]
    return [int(i) for i in room.candidate_dish_ids]


@router.post("/rooms/create", response_model=RoomSnapshot)
def create_room(
    payload: RoomCreateRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> RoomSnapshot:
    host_id = resolve_user_id(
        header_user_id, payload.host_user_id, field="host_user_id"
    )
    if db.query(User).filter(User.id == host_id).first() is None:
        raise HTTPException(status_code=404, detail=f"用户 {host_id} 不存在")

    # v2.3.6：建房时确定并冻结本房有效 ω；只保存 omega_group。
    effective_omega, omega_source = _effective_omega(db, payload.override_params)

    # 规格第 315 行：候选在建房时按房主 + 校区算好；成员加入后按全员重算。
    pool = shortlist_candidates(
        db,
        [host_id],
        payload.mode_type,
        top_n=CANDIDATE_COUNT,
        budget=payload.budget,
        campus=payload.campus,
    )
    dish_ids = [int(item["dish_id"]) for item in pool][:CANDIDATE_COUNT]

    room = GroupRoom(
        algo_params={"omega_group": effective_omega},
        room_code=_unique_code(db),
        host_user_id=host_id,
        mode_type=payload.mode_type,
        status=STATUS_WAITING,
        member_user_ids=[host_id],
        candidate_dish_ids=dish_ids,
        budget=payload.budget,
        campus=payload.campus,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    room_logger.info(
        "room_create room_code=%s host_user_id=%s campus=%s omega=%s omega_source=%s "
        "candidate_count=%s",
        room.room_code,
        host_id,
        room.campus,
        effective_omega,
        omega_source,
        len(dish_ids),
    )
    return _snapshot(db, room, viewer_id=host_id)


@router.post("/rooms/{code}/join", response_model=RoomSnapshot)
async def join_room(
    code: str,
    payload: RoomJoinRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> RoomSnapshot:
    room = _room_or_404(db, code)
    user_id = resolve_user_id(header_user_id, payload.user_id)
    if db.query(User).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    joined_now = False
    # v2.3.6：join / START / 投票 / 结算按房间串行，避免成员与候选半更新。
    with _room_lock(room.room_code):
        db.refresh(room)
        members = [int(i) for i in (room.member_user_ids or [])]
        is_new = user_id not in members

        # v2.3.6：join 只允许 WAITING，既有成员也不例外。
        # SWIPING/FINISHED 的恢复读取走 GET / ROOM_STATE，不用 join。
        if room.status != STATUS_WAITING:
            raise HTTPException(
                status_code=400,
                detail="这一局已经开始了，等下局吧",
            )

        if room.campus is None:
            # 历史 NULL 房间：只允许 WAITING 的首个 join 绑定校区并同事务重算。
            if is_new and len(members) >= MAX_MEMBERS:
                raise HTTPException(
                    status_code=400, detail=f"房间已满（最多 {MAX_MEMBERS} 人）"
                )
            target_members = members + ([user_id] if is_new else [])
            room.campus = payload.campus
            new_ids = _rebuild_candidates(db, room, target_members)
            if not new_ids:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="该历史房间无法绑定校区：全员约束下没有候选",
                )
            if is_new:
                room.member_user_ids = target_members
            db.commit()
            db.refresh(room)
            joined_now = is_new
            room_logger.info(
                "room_campus_bound room_code=%s campus=%s member_count=%s "
                "candidate_count=%s",
                room.room_code,
                room.campus,
                len(room.member_user_ids or []),
                len(new_ids),
            )
        else:
            if payload.campus != room.campus:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"跨校区不能加入：房间校区 {room.campus}，"
                        f"请求校区 {payload.campus}"
                    ),
                )
            if is_new:
                if len(members) >= MAX_MEMBERS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"房间已满（最多 {MAX_MEMBERS} 人）",
                    )
                members.append(user_id)
                room.member_user_ids = members
                # v2.3.6：新成员入组后按全员硬约束重算；0 道允许加入，START 会拒绝。
                _rebuild_candidates(db, room, members)
                db.commit()
                db.refresh(room)
                joined_now = True
                room_logger.info(
                    "room_join room_code=%s user_id=%s member_count=%s "
                    "candidate_count=%s",
                    room.room_code,
                    user_id,
                    len(members),
                    len(room.candidate_dish_ids or []),
                )

    snapshot = _snapshot(db, room, viewer_id=user_id)
    if joined_now:
        # 协议第 347 行：join 落库后广播 MEMBER_SYNC（v2.3.6 带最新候选）
        await hub.broadcast(code, _sync_payload(db, room))
    return snapshot


@router.get("/rooms/{code}", response_model=RoomSnapshot)
async def get_room(
    code: str,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> RoomSnapshot:
    room = _room_or_404(db, code)
    # S01/F07：房间快照包含成员与候选，只对已 join 的成员开放
    ensure_member(room.member_user_ids, header_user_id, room_code=room.room_code)
    # F03/F05：过期就顺手结算，刷新页面也能看到结果。
    # 结算与快照都是重活（_snapshot 内部会跑一遍单人推荐），放进线程池，
    # 避免阻塞事件循环把其他房间的 WS 一起卡住。
    payload = await run_in_threadpool(_settle_if_due, db, room)
    db.refresh(room)
    # 原实现把 _settle_if_due 的返回值直接丢弃：一旦结算由 GET 触发
    # （进程重启后定时器丢失、或 15 秒前后来不及挂 task），
    # 其他成员的 WS 收不到 CONSENSUS_REVEAL，会停在划卡界面。
    if payload is not None:
        await hub.broadcast(code, payload)
    return await run_in_threadpool(_snapshot, db, room, header_user_id)


# —————————————————————— WebSocket ——————————————————————


class RoomHub:
    """房间码 → 在线连接。进程内内存态，单机演示足够。

    注意：定时器丢了不会让房间卡死（结算只依赖数据库里的 deadline_at），
    这里只是"到点立刻广播"的加速器。
    """

    def __init__(self) -> None:
        self.rooms: Dict[str, Dict[int, WebSocket]] = {}
        self.timers: Dict[str, asyncio.Task] = {}

    def add(self, code: str, user_id: int, ws: WebSocket) -> None:
        self.rooms.setdefault(code, {})[user_id] = ws

    def remove(self, code: str, user_id: int) -> None:
        bucket = self.rooms.get(code)
        if not bucket:
            return
        bucket.pop(user_id, None)
        if not bucket:
            self.rooms.pop(code, None)

    async def broadcast(self, code: str, message: dict) -> None:
        dead: List[int] = []
        for uid, ws in list(self.rooms.get(code, {}).items()):
            try:
                await ws.send_json(message)
            except Exception:  # 客户端已断开
                dead.append(uid)
        for uid in dead:
            self.remove(code, uid)

    def schedule_settle(self, code: str, delay: float) -> None:
        """给到点结算挂一个定时器（已有就替换）。"""
        task = self.timers.pop(code, None)
        if task and not task.done():
            task.cancel()
        self.timers[code] = asyncio.create_task(_settle_after(code, delay))

    def forget_timer(self, code: str) -> None:
        task = self.timers.pop(code, None)
        if task and not task.done():
            task.cancel()


hub = RoomHub()


def _sync_payload(db: Session, room: GroupRoom) -> dict:
    """MEMBER_SYNC 要带最新成员、进度与候选，所以每次现查数据库。"""
    return {
        "type": "MEMBER_SYNC",
        "room_code": room.room_code,
        "status": room.status,
        "host_user_id": int(room.host_user_id),
        "mode_type": room.mode_type,
        "campus": room.campus,
        "omega_group": _omega_group(db, room),
        "members": [m.model_dump() for m in _member_briefs(db, room)],
        "candidate_count": len(room.candidate_dish_ids or []),
        "candidates": [
            c.model_dump()
            for c in _candidate_payload(
                db, [int(i) for i in (room.candidate_dish_ids or [])]
            )
        ],
    }


def _start_payload(db: Session, room: GroupRoom) -> dict:
    return {
        "type": "START_SWIPING",
        "room_code": room.room_code,
        "mode_type": room.mode_type,
        "campus": room.campus,
        "omega_group": _omega_group(db, room),
        "swipe_seconds": SWIPE_SECONDS,
        "deadline_at": room.deadline_at.isoformat() if room.deadline_at else None,
        "remaining_ms": _remaining_ms(room),
        "candidates": [
            c.model_dump()
            for c in _candidate_payload(
                db, [int(i) for i in (room.candidate_dish_ids or [])]
            )
        ],
    }


def _start_swiping(code: str) -> Tuple[Optional[dict], Optional[str]]:
    """WAITING -> SWIPING；成功返回 (payload, None)，失败返回 (None, 原因)。"""
    with _room_lock(code):
        db = SessionLocal()
        try:
            room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
            if room is None:
                return None, "房间不存在"
            if room.campus is None:
                return None, "房间未绑定校区，先让成员加入完成绑定"
            if room.status != STATUS_WAITING:
                return None, "这一局已经开始了"
            if not room.candidate_dish_ids:
                return None, "没有满足全员硬约束的候选，无法开局"
            room.status = STATUS_SWIPING
            room.deadline_at = utcnow() + timedelta(seconds=SWIPE_SECONDS)
            room.settled_at = None
            db.commit()
            db.refresh(room)
            room_logger.info(
                "room_start room_code=%s campus=%s member_count=%s candidate_count=%s "
                "deadline_at=%s",
                code,
                room.campus,
                len(room.member_user_ids or []),
                len(room.candidate_dish_ids or []),
                room.deadline_at.isoformat(),
            )
            return _start_payload(db, room), None
        finally:
            db.close()


async def _settle_after(code: str, delay: float) -> None:
    """15 秒到点结算。全员划完会提前结算，这个任务只是兜底。"""
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return
    db = SessionLocal()
    try:
        room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        if room is None:
            return
        try:
            payload = _settle_if_due(db, room)
        except Exception:
            room_logger.exception("room_timer_settle_failed room_code=%s", code)
            db.rollback()
            return
    finally:
        db.close()
    if payload is not None:
        await hub.broadcast(code, payload)


async def _maybe_settle_early(code: str) -> bool:
    """全员都划完时立刻结算。"""
    db = SessionLocal()
    try:
        room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        if room is None or room.status != STATUS_SWIPING:
            return False
        members = [int(i) for i in (room.member_user_ids or [])]
        total = len(room.candidate_dish_ids or [])
        progress = _progress_map(db, code, members, total)
        if total == 0 or any(progress.get(uid, 0) < total for uid in members):
            return False
        try:
            payload = _settle(db, room)
        except Exception:
            room_logger.exception("room_early_settle_failed room_code=%s", code)
            db.rollback()
            return False
    finally:
        db.close()

    if payload is None:
        return False
    hub.forget_timer(code)
    await hub.broadcast(code, payload)
    return True


def settle_overdue_rooms() -> List[Tuple[str, dict]]:
    """扫描并结算所有已过截止、尚未结算的 SWIPING 房间（v2.3.6）。

    启动扫描与 5 秒周期兜底共用；无客户端连接也能落库。返回要广播的
    `(room_code, payload)`，由调用方决定是否广播。单个房间失败只记日志，
    不影响其它房间。
    """
    db = SessionLocal()
    settled: List[Tuple[str, dict]] = []
    try:
        rooms = (
            db.query(GroupRoom)
            .filter(
                GroupRoom.status == STATUS_SWIPING,
                GroupRoom.settled_at.is_(None),
                GroupRoom.deadline_at.isnot(None),
                GroupRoom.deadline_at <= utcnow(),
            )
            .all()
        )
        for room in rooms:
            code = str(room.room_code)
            try:
                payload = _settle_if_due(db, room)
            except Exception:
                room_logger.exception("room_sweep_settle_failed room_code=%s", code)
                db.rollback()
                continue
            if payload is not None:
                settled.append((code, payload))
    finally:
        db.close()
    return settled


async def room_sweeper(interval: Optional[float] = None) -> None:
    """周期兜底：重启后即使无人 GET/WS，也把过期房间结算掉。

    v2.3.6/r02：单次扫描级异常（数据库暂时不可用、扫描查询失败等）只记录
    并进入下一周期，**不得退出循环**；取消信号仍向上传播。单个房间的失败由
    `settle_overdue_rooms()` 内部隔离，不影响同轮其它房间。
    """
    delay = SETTLE_SWEEP_SECONDS if interval is None else max(0.0, float(interval))
    while True:
        try:
            await asyncio.sleep(delay)
            settled = settle_overdue_rooms()
            if settled:
                room_logger.info(
                    "room_sweep_settled count=%s room_codes=%s",
                    len(settled),
                    [code for code, _ in settled],
                )
            for code, payload in settled:
                await hub.broadcast(code, payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            # 瞬态故障：记录后继续下一周期，不能永久关闭无人连接时的兜底。
            room_logger.exception("room_sweeper_failed")
            continue


def _is_member(db: Session, code: str, user_id: int) -> bool:
    room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
    return room is not None and int(user_id) in [
        int(i) for i in (room.member_user_ids or [])
    ]


def _apply_vote(
    code: str, user_id: int, dish_id: int, vote_type: str
) -> Tuple[Optional[str], Optional[Dict[int, int]]]:
    """在房间锁内完成「校验 + 写票」，返回 (错误文案, 最新进度)。

    v2.3.6：
    * 写前重新读取 status/deadline，避免检查后跨过截止时刻；
    * 同成员同菜品先 update，无行再 insert；唯一索引冲突时回滚后重试 update；
    * TIMEOUT 不在 `VALID_VOTE_TYPES`，不会进入本函数。
    """
    with _room_lock(code):
        db = SessionLocal()
        try:
            room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
            if room is None:
                return "房间不存在", None
            if room.status == STATUS_FINISHED:
                return "这一局已经结束了，不能再改票", None
            if room.status != STATUS_SWIPING:
                return "还没开始划卡，别急着投票", None
            if _remaining_ms(room) <= 0:
                return "15 秒已经到点了，这局正在结算", None
            if int(dish_id) not in [
                int(i) for i in (room.candidate_dish_ids or [])
            ]:
                return "这道菜不在本局候选里", None

            members = [int(i) for i in (room.member_user_ids or [])]
            total = len(room.candidate_dish_ids or [])
            row = (
                db.query(RoomVote)
                .filter(
                    RoomVote.room_code == code,
                    RoomVote.user_id == int(user_id),
                    RoomVote.dish_id == int(dish_id),
                )
                .first()
            )
            if row is None:
                db.add(
                    RoomVote(
                        room_code=code,
                        user_id=int(user_id),
                        dish_id=int(dish_id),
                        vote_type=vote_type,
                        voted_at=utcnow(),
                    )
                )
                try:
                    db.commit()
                except IntegrityError:
                    # 跨进程/并发插入撞唯一索引：回滚后按“已存在”更新。
                    db.rollback()
                    row = (
                        db.query(RoomVote)
                        .filter(
                            RoomVote.room_code == code,
                            RoomVote.user_id == int(user_id),
                            RoomVote.dish_id == int(dish_id),
                        )
                        .first()
                    )
                    if row is None:
                        return "投票写入冲突，请重试", None
                    row.vote_type = vote_type
                    row.voted_at = utcnow()
                    db.commit()
            else:
                row.vote_type = vote_type
                row.voted_at = utcnow()
                db.commit()

            progress = _progress_map(db, code, members, total)
            return None, progress
        finally:
            db.close()


@ws_router.websocket("/ws/room/{room_code}/{user_id}")
async def room_socket(websocket: WebSocket, room_code: str, user_id: int) -> None:
    code = str(room_code).strip()

    # 令牌优先。浏览器 WebSocket 不能设自定义头，因此同时支持 ?token=。
    # 只认路径 user_id 的话，任何知道 6 位房间码的人都能冒充成员投票/否决，
    # 与 v2.3.7「登录后身份锁定」冲突（独立审查 2026-10-31 P2）。
    auth_header = websocket.headers.get("authorization")
    token = ""
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = (websocket.query_params.get("token") or "").strip()

    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db = SessionLocal()
        try:
            row = (
                db.query(AuthToken)
                .filter(
                    AuthToken.token_hash == token_hash,
                    AuthToken.expires_at > utcnow(),
                )
                .first()
            )
        finally:
            db.close()
        if row is None:
            identity_logger.warning(
                "identity_rejected reason=invalid_ws_token room_code=%s status=403",
                code,
            )
            raise WebSocketException(code=403, reason="登录已过期，请重新登录")
        if int(row.user_id) != int(user_id):
            identity_logger.warning(
                "identity_rejected reason=ws_token_path_mismatch room_code=%s "
                "token_user_id=%s path_user_id=%s status=403",
                code,
                int(row.user_id),
                user_id,
            )
            raise WebSocketException(code=403, reason="令牌身份与路径 user_id 不一致")

    # 无令牌时才走演示口径：路径 user_id + 可选头必须一致。
    header_raw = websocket.headers.get("x-user-id")
    if header_raw is not None:
        try:
            header_id = int(str(header_raw).strip())
        except (TypeError, ValueError):
            identity_logger.warning(
                "identity_rejected reason=invalid_ws_header room_code=%s "
                "path_user_id=%s value=%r status=403",
                code,
                user_id,
                header_raw,
            )
            raise WebSocketException(
                code=403, reason="X-User-Id 与路径 user_id 必须一致"
            )
        if header_id != int(user_id):
            identity_logger.warning(
                "identity_rejected reason=ws_path_header_mismatch room_code=%s "
                "header_user_id=%s path_user_id=%s status=403",
                code,
                header_id,
                user_id,
            )
            raise WebSocketException(
                code=403, reason="X-User-Id 与路径 user_id 必须一致"
            )

    db = SessionLocal()
    try:
        user_exists = (
            db.query(User.id).filter(User.id == int(user_id)).first() is not None
        )
        member = _is_member(db, code, user_id)
    finally:
        db.close()

    if not user_exists:
        identity_logger.warning(
            "identity_rejected reason=unknown_ws_user room_code=%s user_id=%s "
            "status=403",
            code,
            user_id,
        )
        raise WebSocketException(code=403, reason=f"用户 {user_id} 不存在")

    if not member:
        # 协议第 346 行：未落库的连接直接 HTTP 403（不再 accept 后 1008）
        identity_logger.warning(
            "identity_rejected reason=not_room_member room_code=%s user_id=%s "
            "status=403 channel=ws",
            code,
            user_id,
        )
        raise WebSocketException(
            code=403, reason="还没加入这个房间，先 POST /rooms/{code}/join"
        )

    await websocket.accept()
    hub.add(code, int(user_id), websocket)

    # 断线重进 / 刷新：先把过期该结算的结算掉，再把现场推给这个连接
    db = SessionLocal()
    try:
        room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
        try:
            pending = _settle_if_due(db, room) if room is not None else None
        except Exception:
            room_logger.exception("room_connect_settle_failed room_code=%s", code)
            db.rollback()
            pending = None
        sync = _sync_payload(db, room) if room is not None else None
        snapshot = _snapshot(db, room, viewer_id=int(user_id)) if room is not None else None
        start = (
            _start_payload(db, room)
            if room is not None and room.status == STATUS_SWIPING
            else None
        )
    finally:
        db.close()

    if pending is not None:
        await hub.broadcast(code, pending)
    if sync is not None:
        await hub.broadcast(code, sync)
    if snapshot is not None:
        # F05：把完整现场（含我的票、截止时间）单独发给刚进来的这个人
        await websocket.send_json(
            {"type": "ROOM_STATE", "snapshot": snapshot.model_dump()}
        )
    if start is not None:
        await websocket.send_json(start)
        # 定时器可能已经丢了（进程重启），按剩余时间重新挂上
        remaining = max(0.0, (start.get("remaining_ms") or 0) / 1000.0)
        hub.schedule_settle(code, remaining)

    try:
        while True:
            message = await websocket.receive_json()
            kind = str(message.get("type") or "").upper()

            if kind == "START_SWIPING":
                db = SessionLocal()
                try:
                    room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
                    is_host = room is not None and int(room.host_user_id) == int(user_id)
                finally:
                    db.close()
                if not is_host:
                    await websocket.send_json(
                        {"type": "ERROR", "detail": "只有房主能开团"}
                    )
                    continue
                payload, start_error = _start_swiping(code)
                if start_error is not None:
                    await websocket.send_json(
                        {"type": "ERROR", "detail": start_error}
                    )
                    continue
                await hub.broadcast(code, payload)
                hub.schedule_settle(code, SWIPE_SECONDS)

            elif kind == "SUBMIT_VOTE":
                dish_id = message.get("dish_id")
                vote_type = str(message.get("vote_type") or "").upper()
                if not isinstance(dish_id, int) or vote_type not in VALID_VOTE_TYPES:
                    await websocket.send_json(
                        {
                            "type": "ERROR",
                            "detail": "投票格式不对：要 dish_id 整数 + 合法 vote_type",
                        }
                    )
                    continue
                vote_error, progress = _apply_vote(
                    code, int(user_id), int(dish_id), vote_type
                )
                if vote_error is not None:
                    # 带上 dish_id：前端在 onVote 里先做了乐观更新（卡片飞走、
                    # votes +1），没有这个字段就无法把那一票回滚回去。
                    await websocket.send_json(
                        {
                            "type": "ERROR",
                            "detail": vote_error,
                            "dish_id": int(dish_id),
                            "vote_type": vote_type,
                            "rejected": True,
                        }
                    )
                    continue

                await hub.broadcast(
                    code,
                    {
                        "type": "PROGRESS_UPDATE",
                        "room_code": code,
                        "user_id": int(user_id),
                        "progress": progress,
                    },
                )
                await _maybe_settle_early(code)

            else:
                await websocket.send_json(
                    {"type": "ERROR", "detail": f"未知指令 {kind}"}
                )
    except WebSocketDisconnect:
        room_logger.info("room_ws_closed room_code=%s user_id=%s", code, user_id)
    except Exception:
        # 不能把整个连接池带崩，但也不能像以前那样静默吞掉：
        # 任何 KeyError/OperationalError 都会退化成"莫名断线"，现场无法定位。
        room_logger.exception(
            "room_ws_loop_failed room_code=%s user_id=%s", code, user_id
        )
        try:
            await websocket.send_json(
                {"type": "ERROR", "detail": "服务端处理这条指令时出错，请重试"}
            )
        except Exception:
            pass
    finally:
        hub.remove(code, int(user_id))
        # F03：最后一个人断开**不取消**定时器，改成这一局的结算兜底
        db = SessionLocal()
        try:
            room = db.query(GroupRoom).filter(GroupRoom.room_code == code).first()
            if room is not None and room.status == STATUS_SWIPING:
                remaining = max(0.0, _remaining_ms(room) / 1000.0)
                if remaining > 0:
                    hub.schedule_settle(code, remaining)
                else:
                    try:
                        payload = _settle_if_due(db, room)
                    except Exception:
                        room_logger.exception(
                            "room_disconnect_settle_failed room_code=%s", code
                        )
                        db.rollback()
                        payload = None
                    if payload is not None:
                        await hub.broadcast(code, payload)
        finally:
            db.close()
