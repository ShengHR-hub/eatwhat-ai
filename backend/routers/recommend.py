import threading
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..algorithms.single_recommender import recommend_single
from ..algorithms.vector_spec import capsule_tip
from ..config import AMAP_API_KEY, AMAP_WEATHER_URL
from ..database import get_db
from ..deps import require_user, resolve_user_id
from ..schemas import (
    SingleRecommendRequest,
    SingleRecommendResponse,
    WeatherResponse,
)

router = APIRouter(tags=["单人决策"])

# 校区中心（思源）作为天气兜底坐标；有高德 Key 时仍优先按城市查高德。
DEFAULT_WEATHER_LAT = 34.234818
DEFAULT_WEATHER_LNG = 109.078487
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WMO_TEXT = {
    0: "晴", 1: "多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾",
    51: "小雨", 53: "小雨", 55: "中雨", 56: "冻雨", 57: "冻雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪",
    80: "阵雨", 81: "阵雨", 82: "强阵雨",
    85: "阵雪", 86: "阵雪",
    95: "雷雨", 96: "雷雨", 99: "雷雨",
}


def _open_meteo_weather(lat: float, lng: float) -> Optional[WeatherResponse]:
    """免 Key 的实时天气兜底，按坐标取当前温度与天气码。"""
    try:
        response = httpx.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lng,
                "current": "temperature_2m,weather_code",
                "timezone": "Asia/Shanghai",
            },
            timeout=3.0,
        )
        data = response.json()
        current = data.get("current") or {}
        temp = float(current.get("temperature_2m"))
        code = int(current.get("weather_code", 0))
        text = WMO_TEXT.get(code, "多云")
        return WeatherResponse(
            temp=round(temp, 1),
            weather_text=text,
            capsule_tip=capsule_tip(temp, text),
            source="open-meteo",
        )
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None


def _offline_weather(temp: float = 22.0, text: str = "晴") -> WeatherResponse:
    return WeatherResponse(
        temp=temp,
        weather_text=text,
        capsule_tip=capsule_tip(temp, text),
        source="offline",
    )


# 天气是首屏关键路径：上游 Open-Meteo 单次要 2 秒左右，不缓存的话
# 每次进首页都得干等。按坐标/城市做 10 分钟 TTL 缓存，命中即毫秒返回。
WEATHER_CACHE_TTL = 600.0
_weather_cache: dict[tuple, tuple[float, WeatherResponse]] = {}
_weather_cache_lock = threading.Lock()


def _weather_cache_get(key: tuple) -> Optional[WeatherResponse]:
    with _weather_cache_lock:
        hit = _weather_cache.get(key)
        if hit is None:
            return None
        stamped, value = hit
        if time.monotonic() - stamped > WEATHER_CACHE_TTL:
            _weather_cache.pop(key, None)
            return None
        return value


def _weather_cache_put(key: tuple, value: WeatherResponse) -> None:
    with _weather_cache_lock:
        _weather_cache[key] = (time.monotonic(), value)
        # 缓存键只有坐标/城市两种，量级很小；顺手清掉过期的
        if len(_weather_cache) > 64:
            now = time.monotonic()
            for k, (stamped, _) in list(_weather_cache.items()):
                if now - stamped > WEATHER_CACHE_TTL:
                    _weather_cache.pop(k, None)


def _amap_weather(city: str) -> Optional[WeatherResponse]:
    if not AMAP_API_KEY:
        return None
    try:
        response = httpx.get(
            AMAP_WEATHER_URL,
            params={"key": AMAP_API_KEY, "city": city, "extensions": "base"},
            timeout=3.0,
        )
        data = response.json()
        lives = data.get("lives") or []
        if data.get("status") != "1" or not lives:
            return None
        live = lives[0]
        temp = float(live.get("temperature", 22.0))
        text = str(live.get("weather", "晴"))
        return WeatherResponse(
            temp=temp,
            weather_text=text,
            capsule_tip=capsule_tip(temp, text),
            source="amap",
        )
    except (httpx.HTTPError, ValueError, TypeError):
        return None


@router.get("/context/weather", response_model=WeatherResponse)
def context_weather(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    # S02：与 recommend/single 的 weather_temp 同一边界；NaN/Inf 由 ge/le 拒绝。
    temp: Optional[float] = Query(default=None, ge=-30, le=50),
    weather: Optional[str] = Query(default=None, max_length=32),
) -> WeatherResponse:
    if temp is not None:
        return WeatherResponse(
            temp=float(temp),
            weather_text=weather or "晴",
            capsule_tip=capsule_tip(float(temp), weather or "晴"),
            source="override",
        )
    if city:
        cached = _weather_cache_get(("amap", city))
        if cached is not None:
            return cached
        live = _amap_weather(city)
        if live is not None:
            _weather_cache_put(("amap", city), live)
            return live

    lat_key = round(lat if lat is not None else DEFAULT_WEATHER_LAT, 3)
    lng_key = round(lng if lng is not None else DEFAULT_WEATHER_LNG, 3)
    cached = _weather_cache_get(("om", lat_key, lng_key))
    if cached is not None:
        return cached
    live = _open_meteo_weather(lat_key, lng_key)
    if live is not None:
        _weather_cache_put(("om", lat_key, lng_key), live)
        return live
    return _offline_weather(text=weather or "晴")


@router.post("/recommend/single", response_model=SingleRecommendResponse)
def recommend(
    payload: SingleRecommendRequest,
    header_user_id: int = Depends(require_user),
    db: Session = Depends(get_db),
) -> SingleRecommendResponse:
    user_id = resolve_user_id(header_user_id, payload.user_id)
    try:
        result = recommend_single(
            db=db,
            user_id=user_id,
            mode_type=payload.mode_type,
            budget=payload.budget,
            bubbles=payload.bubbles,
            combo_mode=payload.combo_mode,
            override_params=payload.override_params,
            weather_temp=payload.weather_temp if payload.weather_temp is not None else 20.0,
            weather_text=payload.weather_text or "晴",
            max_distance_meters=payload.max_distance_meters,
            campus=payload.campus,
            limit=payload.limit,
            exclude_dish_ids=payload.exclude_dish_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SingleRecommendResponse(**result)
