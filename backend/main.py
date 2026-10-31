from pathlib import Path
import asyncio
import contextlib
import logging
import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import CORS_ORIGINS, runtime_summary
from .database import SessionLocal, init_db
from .routers import (
    admin,
    admin_ext,
    admin_experiments,
    admin_simulation,
    admin_stats,
    auth_local,
    auth_user,
    catalog,
    eating_log,
    fridge,
    group_room,
    recommend,
)

room_logger = logging.getLogger("eatwhat.room")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动横幅：把实际生效的 env / 库 / CORS 打出来。
    # 以前缺配置会静默落到本地 SQLite + CORS *，日志里一个字都没有。
    room_logger.info("startup_config %s", runtime_summary())
    init_db()
    # 后台保存过算法参数的话，启动时把它装进运行期缓存，否则重启就回落到默认值
    try:
        from .config import reload_algo_params
        from .database import SessionLocal

        _db = SessionLocal()
        try:
            reload_algo_params(_db)
        finally:
            _db.close()
    except Exception:
        room_logger.exception("algo_params_reload_failed")
    # v2.3.6：启动先结算一次过期房间；旧 schema/数据库异常不阻断启动。
    try:
        group_room.settle_overdue_rooms()
    except Exception:
        room_logger.exception("room_startup_sweep_failed")
    sweep_task = asyncio.create_task(group_room.room_sweeper())
    try:
        yield
    finally:
        sweep_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep_task


app = FastAPI(
    title="食刻 EatWhat AI API",
    version="2.3.2",
    description="基于多维上下文感知与群组偏好博弈的智能饮食决策系统",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # 前端只用 X-User-Id / Bearer，不依赖 Cookie，因此不开放 credentials。
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sanitize_non_finite(value):
    """S02：校验错误详情会回显原始输入；NaN/Infinity 无法被 JSON 序列化，
    不处理就会把本应 422 的请求变成 500。"""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _sanitize_non_finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_non_finite(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(_sanitize_non_finite(exc.errors()))},
    )

# 用户头像等上传文件：与 API 同源，前端直接用相对路径渲染
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth_user.router, prefix="/api/v1")
app.include_router(auth_local.router, prefix="/api/v1")
app.include_router(recommend.router, prefix="/api/v1")
app.include_router(eating_log.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(fridge.router, prefix="/api/v1")
app.include_router(group_room.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_ext.router, prefix="/api/v1")
app.include_router(admin_experiments.router, prefix="/api/v1")
app.include_router(admin_stats.router, prefix="/api/v1")
app.include_router(admin_simulation.router, prefix="/api/v1")
app.include_router(group_room.ws_router)


@app.get("/health", tags=["系统"])
def health():
    """存活 + 数据库可用性检查，供反向代理/容器探针使用。"""
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "version": "2.3.2", "db": "error"},
        )
    return {"status": "ok", "version": "2.3.2", "db": "ok"}
