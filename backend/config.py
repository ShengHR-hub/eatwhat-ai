import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
AMAP_PLACE_AROUND_URL = "https://restapi.amap.com/v3/place/around"

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

# 冰箱拍照识别：任意 OpenAI 兼容视觉模型端点
VISION_API_KEY = os.getenv("VISION_API_KEY", LLM_API_KEY)
VISION_BASE_URL = os.getenv("VISION_BASE_URL", LLM_BASE_URL or "https://api.openai.com/v1")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o-mini")

# 运行环境：dev（默认）/ prod。
# prod 下拒绝所有"隐式回退"，因为这类默认值出问题后极难定位：
# 容器重启数据"消失"、多副本各写各的本地文件、任意站点可跨域打接口。
APP_ENV = os.getenv("APP_ENV", "dev").strip().lower()
IS_PROD = APP_ENV in ("prod", "production")

_raw_database_url = os.getenv("DATABASE_URL", "").strip()
if not _raw_database_url:
    if IS_PROD:
        raise RuntimeError(
            "APP_ENV=prod 但未设置 DATABASE_URL：拒绝回退到本地 SQLite。"
            "请显式配置数据库连接串。"
        )
    _raw_database_url = f"sqlite:///{(BASE_DIR / 'eatwhat.db').as_posix()}"
DATABASE_URL = _raw_database_url

# 生产库结构交给 Alembic；SQLite 本地默认仍然 create_all，省去每次建库都要先 upgrade。
# 显式设置 AUTO_CREATE_SCHEMA=0/1 可覆盖默认值。
_default_auto_create = "1" if DATABASE_URL.startswith("sqlite") else "0"
AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", _default_auto_create).strip().lower() not in (
    "0",
    "false",
    "no",
)

# 部署时用逗号分隔的白名单；本地默认放开，方便 Vite / Capacitor 调试。
_raw_cors = os.getenv("CORS_ORIGINS", "").strip()
if not _raw_cors:
    if IS_PROD:
        raise RuntimeError(
            "APP_ENV=prod 但未设置 CORS_ORIGINS：拒绝默认放开 *。"
            "请显式配置允许的来源白名单。"
        )
    _raw_cors = "*"
CORS_ORIGINS = [item.strip() for item in _raw_cors.split(",") if item.strip()]


def runtime_summary() -> str:
    """启动横幅：把实际生效的库与 CORS 打出来，避免"以为连的是 PG"。"""
    scheme = DATABASE_URL.split("://", 1)[0] if "://" in DATABASE_URL else "unknown"
    host = DATABASE_URL.split("@", 1)[1].split("/", 1)[0] if "@" in DATABASE_URL else ""
    cors = "*(全开)" if CORS_ORIGINS == ["*"] else ",".join(CORS_ORIGINS)
    return f"env={APP_ENV} db={scheme}{('@' + host) if host else ''} cors={cors}"

DEFAULT_ALGO_PARAMS = {
    "lambda_decay": 0.5,
    "omega_group": 0.5,
    "alpha_taste": 0.35,
    "beta_weather": 0.25,
    "gamma_budget": 0.20,
    "delta_status": 0.20,
}

# 算法参数运行期缓存：后台改完参数立即生效，不用重启服务。
# 放在 config 而不是算法模块里，是因为 single/group/log 三处都要读同一份。
_ALGO_RUNTIME = dict(DEFAULT_ALGO_PARAMS)


def current_algo_params() -> dict:
    """当前生效的算法参数（默认值 + 后台覆盖）。"""
    return dict(_ALGO_RUNTIME)


def set_algo_params(values: dict) -> dict:
    """用后台提交的值覆盖运行期缓存，越界或未知键直接丢弃。"""
    merged = dict(_ALGO_RUNTIME)
    for key, value in values.items():
        if key in DEFAULT_ALGO_PARAMS:
            merged[key] = float(value)
    _ALGO_RUNTIME.clear()
    _ALGO_RUNTIME.update(merged)
    return dict(_ALGO_RUNTIME)


def reload_algo_params(db) -> dict:
    """从 system_settings 重新加载，服务启动与后台保存后各调一次。"""
    from .models import SystemSetting

    row = db.get(SystemSetting, "algo_params")
    if row and isinstance(row.value, dict):
        return set_algo_params(row.value)
    return current_algo_params()
