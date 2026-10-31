"""向 S06 隔离库写入明确标注的校区 fixture（s06_fixture_v1）。

只允许写 `backend/eatwhat_s06_r01_iso.db`；绝不写演示库、S10 库、开发源库或
种子脚本。fixture 用于证明严格校区过滤与 10 候选流程，不作为真实采集数据。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGET = (ROOT / "backend" / "eatwhat_s06_r01_iso.db").resolve()
OUT = Path(__file__).resolve().parent / "fixture.json"
DATASET = "s06_fixture_v1"

CAMPUSES = {
    "SIYUAN": (109.078487, 34.234818, "S06思源固定菜", "S06思源fixture餐厅"),
    "JIANDA_YANTA": (108.967153, 34.236991, "S06建大固定菜", "S06建大fixture餐厅"),
}
ROLES = ("MEAT", "VEG", "SOUP", "ONE_MEAL")
VECTORS = (
    (0.90, 0.80, 0.10, 0.40, 0.80, 0.60, 0.60, 0.80),
    (0.10, 0.20, 0.90, 0.30, 0.60, 0.70, 0.40, 0.60),
    (0.50, 0.50, 0.30, 0.50, 0.60, 0.70, 0.50, 0.55),
    (0.00, 0.10, 0.20, 0.50, 0.30, 0.80, 0.30, 0.40),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.models import Dish, Restaurant
    from backend.algorithms.vector_spec import FEATURE_KEYS

    if not TARGET.exists():
        raise SystemExit(f"目标不存在：{TARGET}")
    engine = create_engine(f"sqlite:///{TARGET.as_posix()}")
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    try:
        existing = (
            session.query(Restaurant)
            .filter(Restaurant.source_dataset == DATASET)
            .count()
        )
        if existing:
            payload = {
                "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                "target": str(TARGET),
                "dataset": DATASET,
                "already_present": True,
                "restaurant_count": existing,
                "dish_count": session.query(Dish)
                .filter(Dish.source_dataset == DATASET)
                .count(),
                "sha256": sha256(TARGET),
            }
            OUT.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        records = []
        for campus, (lon, lat, dish_prefix, store_prefix) in CAMPUSES.items():
            for store_index in range(1, 7):
                store = Restaurant(
                    name=f"{store_prefix}{store_index:02d}",
                    source_type="CANTEEN",
                    category="S06 fixture",
                    avg_price=15.0,
                    rating=4.5,
                    longitude=lon + store_index * 0.0001,
                    latitude=lat + store_index * 0.0001,
                    distance_meters=100 + store_index,
                    address="S06 校区 fixture（非真实采集）",
                    source_dataset=DATASET,
                    source_record_id=f"s06-rest-{campus.lower()}-{store_index:02d}",
                    data_version=DATASET,
                    is_synthetic=True,
                    campus=campus,
                )
                session.add(store)
                session.flush()
                records.append(
                    {
                        "campus": campus,
                        "restaurant_id": store.id,
                        "restaurant_name": store.name,
                    }
                )
                for dish_index in range(1, 3):
                    global_index = (store_index - 1) * 2 + dish_index
                    vector = VECTORS[(global_index - 1) % len(VECTORS)]
                    dish = Dish(
                        name=f"{dish_prefix}{global_index:02d}",
                        mode_type="OUT_DINING",
                        restaurant_id=store.id,
                        cuisine_type="S06Fixture",
                        dish_role=ROLES[(global_index - 1) % len(ROLES)],
                        price_or_cost=float(10 + global_index),
                        cook_minutes=10,
                        appliance_tag=["炒锅"],
                        ingredients_main=[f"fixture主料{global_index:02d}"],
                        ingredients_aux=[],
                        recipe_steps="S06 fixture（非真实菜谱）",
                        feature_vector={
                            key: value for key, value in zip(FEATURE_KEYS, vector)
                        },
                        image_url="",
                        allergen_tags=[],
                        tagging_status="SUCCESS",
                        source_dataset=DATASET,
                        source_record_id=(
                            f"s06-dish-{campus.lower()}-{global_index:02d}"
                        ),
                        data_version=DATASET,
                        is_synthetic=True,
                    )
                    session.add(dish)
        session.commit()

        counts = {}
        for campus in CAMPUSES:
            counts[campus] = {
                "restaurants": session.query(Restaurant)
                .filter(
                    Restaurant.source_dataset == DATASET,
                    Restaurant.campus == campus,
                )
                .count(),
                "dishes": session.query(Dish)
                .join(Restaurant, Dish.restaurant_id == Restaurant.id)
                .filter(
                    Dish.source_dataset == DATASET,
                    Restaurant.campus == campus,
                )
                .count(),
            }
        seed_null = (
            session.query(Restaurant)
            .filter(
                Restaurant.source_dataset.is_(None),
                Restaurant.campus.is_(None),
            )
            .count()
        )
        payload = {
            "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "target": str(TARGET),
            "dataset": DATASET,
            "already_present": False,
            "is_synthetic": True,
            "counts": counts,
            "records": records,
            "seed_null_restaurants": seed_null,
            "sha256": sha256(TARGET),
        }
        OUT.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
