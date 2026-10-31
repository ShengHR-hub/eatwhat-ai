"""S10 导入共用口径：校区注册表、距离、隔离库、拒绝日志与指纹。

所有写库入口都经过 `ensure_import_db()`，演示库 `backend/eatwhat.db` 一律拒绝。
"""

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DEMO_DB = (ROOT / "backend" / "eatwhat.db").resolve()
DEFAULT_DB = ROOT / "backend" / "eatwhat_batch4.db"

SCRIPT_VERSION = "s10_import_v1"
AMAP_DATASET = "amap_place_around_20261025"
AMAP_DATA_VERSION = "amap_place_around_20261025_v1"
CANTEEN_DATASET = "synthetic_canteen_v1"
CANTEEN_DATA_VERSION = "synthetic_canteen_v1"
RECIPE_DATASET = "synthetic_recipe_v1"
RECIPE_DATA_VERSION = "synthetic_recipe_v1"

# GCJ-02 校区中心（S09/r02 高德地名搜索实测值）
CAMPUS_CENTERS = {
    "SIYUAN": (109.078487, 34.234818),
    "JIANDA_YANTA": (108.967153, 34.236991),
}
CAMPUS_NAMES = {
    "SIYUAN": "西安思源学院主校区",
    "JIANDA_YANTA": "西安建筑科技大学雁塔校区",
}
CAMPUS_INPUTS = {
    "SIYUAN": ROOT / "docs/review/stages/S09/r02/data/amap_pois.jsonl",
    "JIANDA_YANTA": ROOT / "docs/review/stages/S09/r02/data/amap_jianda_pois.jsonl",
}
CAOTANG = "JIANDA_CAOTANG"

# 合成食堂锚点：4 个食堂建筑 × (5 层 × 10 窗口)。
# 每个锚点距该校区任意真实 POI 均 >100m（S10 验证脚本复算），
# 坐标为确定性合成 GCJ-02 点，仅用于演示地图，不冒充真实店铺位置。
CANTEEN_ANCHORS = {
    "SIYUAN": [
        (109.075414, 34.237359),
        (109.074141, 34.234818),
        (109.075414, 34.232277),
        (109.078487, 34.238411),
    ],
    "JIANDA_YANTA": [
        (108.969326, 34.236991),
        (108.969458, 34.238897),
        (108.962807, 34.236991),
        (108.967153, 34.234296),
    ],
}
CANTEEN_BASE_NAMES = {
    "SIYUAN": ["一食堂", "二食堂", "三食堂", "清真食堂"],
    "JIANDA_YANTA": ["建大·第一餐厅", "建大·第二餐厅", "建大·第三餐厅", "建大·清真餐厅"],
}


def ensure_import_db(db_path: Path) -> Path:
    path = Path(db_path).resolve()
    if path == DEMO_DB:
        raise SystemExit("拒绝写演示库 backend/eatwhat.db；请使用独立批次 4 导入库")
    return path


def make_session(db_path: Path):
    path = ensure_import_db(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path.as_posix()}", future=True)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def haversine_m(a, b) -> float:
    radius = 6371008.8
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(h))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_reject(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError as exc:
                yield line_no, {"__parse_error__": str(exc), "__raw__": line.strip()}
