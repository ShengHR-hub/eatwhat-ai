"""管理后台审计。

原则：
1. **业务优先**——调用方先提交业务，再写审计。审计写失败只记日志、不把请求判成失败，
   否则会出现"返回 500 但数据已经改了"，用户重试还会产生重复记录。
   （旧注释写的是"审计写失败必须让请求失败"，与实现正好相反，已改正。）
2. **只记写操作**——查询不改变数据，记了只会把表撑大。
3. **detail 存原始 payload**，不存渲染后的文案，方便以后追溯到底改了什么。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from .models import AdminAuditLog

audit_logger = logging.getLogger("eatwhat.audit")


def client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    # 反向代理后面要看 X-Forwarded-For 的第一跳
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else None) or None


def record_audit(
    db: Session,
    *,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    summary: str = "",
    detail: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    strict: bool = False,
) -> Optional[AdminAuditLog]:
    """写一条审计。调用方在业务提交之后调用，保证"改成功才有记录"。

    审计失败默认不抛异常：业务已经落库，此时把请求判成 500 会让用户以为没成功、
    重试产生重复数据，反而更糟。失败会打 exception 日志留痕。
    strict=True 时才会向上抛（给"必须留痕"的场景用）。
    """
    row = AdminAuditLog(
        user_id=int(user_id),
        action=action[:32],
        resource_type=resource_type[:32],
        resource_id=resource_id,
        summary=summary[:255],
        detail=detail,
        ip=client_ip(request),
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        audit_logger.exception(
            "audit_failed action=%s resource=%s/%s user_id=%s",
            action,
            resource_type,
            resource_id,
            user_id,
        )
        if strict:
            raise
        return None
