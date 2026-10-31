"""最简账号密码注册/登录。

不接手机号和微信：用户名 + 密码 + Bearer token。
密码用 stdlib PBKDF2-SHA256 存储，token 只存 SHA-256 哈希。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_user
from ..models import AuthCredential, AuthToken, User, UserPreference, utcnow
from ..schemas import AuthLoginRequest, AuthRegisterRequest, AuthResponse, AuthUser

router = APIRouter(prefix="/auth", tags=["账号"])

TOKEN_DAYS = 7
DEFAULT_VECTOR = {
    "spicy_level": 0.5,
    "oily_level": 0.5,
    "soup_level": 0.5,
    "temp_fit": 0.5,
    "satiety_level": 0.5,
    "prep_speed": 0.5,
    "social_fit": 0.5,
    "comfort_level": 0.5,
}


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


# ── 登录限流 ──────────────────────────────────────────────────────
# 单进程内存实现，本机演示够用；多副本部署要换成 Redis。
# 加这个是因为管理员入口是后台唯一入口，而之前没有任何失败计数/退避，
# 弱口令可以被脚本直接在线撞开。
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_MAX_FAILURES = 5
_login_failures: dict[tuple[str, str], list[float]] = {}
_login_lock = threading.Lock()

# 用户不存在时也跑一次同代价的哈希，避免用响应时间枚举用户名。
_DUMMY_HASH = ""


def _client_ip(request: Optional[Request]) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_login_rate(key: tuple[str, str]) -> None:
    now = time.monotonic()
    with _login_lock:
        hits = [t for t in _login_failures.get(key, []) if now - t < _LOGIN_WINDOW_SECONDS]
        _login_failures[key] = hits
        if len(hits) >= _LOGIN_MAX_FAILURES:
            retry = int(_LOGIN_WINDOW_SECONDS - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"登录失败次数过多，请 {max(1, retry)} 秒后再试",
            )


def _record_login_failure(key: tuple[str, str]) -> None:
    with _login_lock:
        _login_failures.setdefault(key, []).append(time.monotonic())


def _clear_login_failures(key: tuple[str, str]) -> None:
    with _login_lock:
        _login_failures.pop(key, None)


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            user_id=user_id,
            token_hash=_token_hash(token),
            expires_at=utcnow() + timedelta(days=TOKEN_DAYS),
        )
    )
    db.commit()
    return token


def _auth_user(user: User) -> AuthUser:
    return AuthUser(
        user_id=int(user.id),
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar or "",
        role=(user.role or "USER"),
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    username = payload.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=username,
        nickname=(payload.nickname.strip() or username),
        avatar=(payload.nickname.strip() or username)[:1],
        persona_title="新食客",
        is_demo_persona=False,
    )
    db.add(user)
    db.flush()
    db.add(AuthCredential(user_id=user.id, password_hash=_hash_password(payload.password)))
    db.add(
        UserPreference(
            user_id=user.id,
            base_vector=dict(DEFAULT_VECTOR),
            default_budget=25.0,
            veto_tags=[],
            preferred_cuisines=[],
            favorite_dish_ids=[],
            blacklist_dish_ids=[],
            blacklist_restaurant_ids=[],
        )
    )
    db.commit()
    db.refresh(user)
    return AuthResponse(token=_issue_token(db, user.id), user=_auth_user(user))


@router.post("/login", response_model=AuthResponse)
def login(
    payload: AuthLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    username = payload.username.strip()
    key = (username.lower(), _client_ip(request))
    _check_login_rate(key)

    user = db.query(User).filter(User.username == username).first()
    credential = (
        db.query(AuthCredential).filter(AuthCredential.user_id == user.id).first()
        if user is not None
        else None
    )
    # 无论用户是否存在都跑一次 PBKDF2，否则"不存在"会明显更快，可用于枚举用户名。
    stored = credential.password_hash if credential is not None else _DUMMY_HASH
    verified = _verify_password(payload.password, stored)
    if credential is None or not verified:
        _record_login_failure(key)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    _clear_login_failures(key)
    return AuthResponse(token=_issue_token(db, user.id), user=_auth_user(user))


@router.get("/me", response_model=AuthUser)
def me(user_id: int = Depends(require_user), db: Session = Depends(get_db)) -> AuthUser:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _auth_user(user)


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        db.query(AuthToken).filter(AuthToken.token_hash == _token_hash(token)).delete()
        db.commit()
    return {"ok": True}


# 启动即算一次假哈希（约 50ms），用于登录时序对齐。
_DUMMY_HASH = _hash_password("not-a-real-password")
