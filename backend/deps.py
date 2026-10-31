"""演示级身份解析（S01/F07 的唯一口径）。

MASTER_SPEC v2.3.5 第五章 0：
* 所有需要用户上下文的请求必须携带 ``X-User-Id``；
* 请求头必须解析为 ``users`` 表里已存在的用户，查无此人 404；
* 缺失 / 空 / 非整数 / 非正整数 / 超出 SQLite INTEGER 范围一律 422，
  **不回退用户 1**；
* body / query 里的 ``user_id``、``host_user_id`` 只能作为缺省值记录，
  与请求头冲突时以请求头为准并写冲突日志；
* 路径 ``user_id`` 与请求头冲突沿用既有 403 语义。SSOT 只写了 body/query
  的「按头解析」，路径冲突尚无明确裁决，本步不擅自改产品语义，作为设计缺口
  记录在 S01/r01 证据包中。
"""

import hashlib
import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuthToken, User, utcnow

logger = logging.getLogger("eatwhat.identity")

# SQLite INTEGER 是 64 位有符号整数；再大就会在 SQL 绑定阶段抛 OverflowError。
MAX_USER_ID = 2**63 - 1


def raw_user_id(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> Optional[str]:
    """原样返回请求头字符串，用于区分「没带」与「带了空值」。"""
    return x_user_id


def parse_user_id(raw: Optional[str]) -> int:
    text = "" if raw is None else str(raw).strip()
    if not text:
        logger.warning("identity_rejected reason=missing_header status=422")
        raise HTTPException(
            status_code=422,
            detail="缺少 X-User-Id 请求头；演示身份必须显式指定当前用户",
        )
    try:
        value = int(text)
    except (TypeError, ValueError):
        logger.warning("identity_rejected reason=invalid_header value=%r status=422", raw)
        raise HTTPException(
            status_code=422,
            detail=f"X-User-Id 必须是整数，收到 {raw!r}",
        )
    if value <= 0:
        logger.warning("identity_rejected reason=invalid_header value=%r status=422", raw)
        raise HTTPException(
            status_code=422,
            detail=f"X-User-Id 必须是正整数，收到 {value}",
        )
    if value > MAX_USER_ID:
        logger.warning("identity_rejected reason=invalid_header value=%r status=422", raw)
        raise HTTPException(
            status_code=422,
            detail="X-User-Id 超出可支持范围",
        )
    return value


def require_user_id(
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> int:
    """Bearer token 优先；没有 token 时保留 X-User-Id 演示身份。"""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        row = (
            db.query(AuthToken)
            .filter(AuthToken.token_hash == token_hash, AuthToken.expires_at > utcnow())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
        return int(row.user_id)
    return parse_user_id(x_user_id)


def require_user(
    header_user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> int:
    """当前请求头身份必须真实存在；未知用户 404，不静默回退。"""
    exists = db.query(User.id).filter(User.id == header_user_id).first()
    if exists is None:
        logger.warning(
            "identity_rejected reason=unknown_user header_user_id=%s status=404",
            header_user_id,
        )
        raise HTTPException(status_code=404, detail=f"用户 {header_user_id} 不存在")
    return header_user_id


ADMIN_ROLE = "ADMIN"


def require_admin(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> int:
    """管理接口专用：必须是 ADMIN 角色，且必须用真实登录 token。

    这里**故意不接受 X-User-Id**。那个头没有任何秘密，谁都能填 1；
    如果管理接口认它，等于把「改菜、删店、跑实验」的能力挂在明文头上。
    所以没带 Bearer token 一律 401，带了但角色不对一律 403。
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        logger.warning("admin_rejected reason=missing_token status=401")
        raise HTTPException(status_code=401, detail="管理后台需要登录，请先使用管理员账号登录")

    token = authorization.split(" ", 1)[1].strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = (
        db.query(AuthToken)
        .filter(AuthToken.token_hash == token_hash, AuthToken.expires_at > utcnow())
        .first()
    )
    if row is None:
        logger.warning("admin_rejected reason=invalid_token status=401")
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        logger.warning("admin_rejected reason=unknown_user user_id=%s status=401", row.user_id)
        raise HTTPException(status_code=401, detail="账号不存在")

    role = (user.role or "USER").upper()
    if role != ADMIN_ROLE:
        logger.warning(
            "admin_rejected reason=not_admin user_id=%s role=%s status=403",
            user.id,
            role,
        )
        raise HTTPException(status_code=403, detail="当前账号没有管理权限")

    return int(user.id)


def resolve_user_id(
    header_user_id: int,
    body_user_id: Optional[int],
    *,
    field: str = "user_id",
) -> int:
    """请求头是唯一事实来源；body 身份只在冲突时留痕。"""
    header_id = int(header_user_id)
    if body_user_id is not None:
        try:
            body_id: Optional[int] = int(body_user_id)
        except (TypeError, ValueError):
            body_id = None
        if body_id != header_id:
            logger.warning(
                "identity_conflict field=%s header_user_id=%s body_user_id=%r "
                "resolution=header",
                field,
                header_id,
                body_user_id,
            )
    return header_id


def ensure_self(path_user_id: int, header_user_id: int) -> int:
    """路径里的 user_id 与请求头必须一致，否则 403。

    路径标识被操作的资源，请求头标识当前操作者。演示环境也不允许跨用户。
    没带请求头的情况已由 ``require_user`` 在更早的依赖里拒绝（422）。
    """
    path_id = int(path_user_id)
    header_id = int(header_user_id)
    if header_id != path_id:
        logger.warning(
            "identity_rejected reason=path_header_mismatch header_user_id=%s "
            "path_user_id=%s status=403",
            header_id,
            path_id,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                f"不能操作其他用户的资源（请求头 X-User-Id={header_id}，"
                f"路径 user_id={path_id}）"
            ),
        )
    return path_id


def ensure_member(member_user_ids, user_id: int, *, room_code: str) -> int:
    """房间资源只对已 join 的成员开放；非成员 403，不泄露候选/成员/报告。"""
    uid = int(user_id)
    members = [int(i) for i in (member_user_ids or [])]
    if uid not in members:
        logger.warning(
            "identity_rejected reason=not_room_member room_code=%s user_id=%s "
            "status=403",
            room_code,
            uid,
        )
        raise HTTPException(
            status_code=403,
            detail=f"你还没加入房间 {room_code}，先 POST /rooms/{room_code}/join",
        )
    return uid
