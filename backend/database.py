from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import AUTO_CREATE_SCHEMA, DATABASE_URL

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# SQLite：单文件、多线程访问要放开 check_same_thread。
# PostgreSQL：连接池要带 pre_ping，避免长连接被中间层掐断后报 stale connection。
if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}, future=True
    )
else:
    engine = create_engine(
        DATABASE_URL,
        # connect_timeout：数据库不可达时 5 秒内报错，而不是无限等待。
        # 之前 PG 容器一挂，后端会卡在 startup 阶段不返回，健康检查全部超时。
        connect_args={"connect_timeout": 5},
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        future=True,
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表。

    生产库结构由 Alembic 管（`alembic upgrade head`），这里只做兜底：
    - SQLite 演示/本地默认仍然 create_all，图省事；
    - PostgreSQL 默认不建表，避免「模型一改，重启就把生产库结构带跑偏」。
    需要临时放开时设 AUTO_CREATE_SCHEMA=1。
    """
    if not AUTO_CREATE_SCHEMA:
        return
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
