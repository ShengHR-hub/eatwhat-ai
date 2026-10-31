"""Alembic 运行环境。

连接串只有一个来源：`backend/config.py` 里的 `DATABASE_URL`（读 `backend/.env`）。
命令行想临时指向别的库（例如影子库做回滚验证），直接设环境变量：

    DATABASE_URL=postgresql+psycopg://... alembic upgrade head
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.config import DATABASE_URL
from backend.database import Base
from backend import models  # noqa: F401  仅为把全部表注册进 Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# SQLite 不支持大部分 ALTER，批处理模式会把改动包成「建新表→拷数据→改名」。
# PostgreSQL 下 render_as_batch 无副作用，保留可以两边共用同一套迁移脚本。
IS_SQLITE = DATABASE_URL.startswith("sqlite")


def _database_url() -> str:
    # 命令行 -x db_url=... 优先级最高，其次环境变量（config 已读），最后 .env
    override = context.get_x_argument(as_dictionary=True).get("db_url")
    return override or DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=IS_SQLITE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=IS_SQLITE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
