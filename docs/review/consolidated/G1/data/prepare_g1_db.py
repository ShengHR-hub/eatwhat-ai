"""G1 隔离运行库准备：复制受保护开发源库 → 明确命名的 G1 副本，
再补 S06 唯一索引与 `g1_fixture_v1` 校区 fixture。

只写 `backend/eatwhat_g1_s07_iso.db`；演示库、S10 导入库、PRE-00 源库、
S05/S06 历史隔离库全部只读。fixture 是明确标注的合成数据，不冒充真实采集。
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE = ROOT / "backend" / "eatwhat_dev_pre00_r02.db"
TARGET = ROOT / "backend" / "eatwhat_g1_s07_iso.db"
OUT = Path(__file__).resolve().parent / "db_provenance.json"
DATASET = "g1_fixture_v1"

CAMPUSES = {
    "SIYUAN": (109.078487, 34.234818, "G1思源fixture菜", "G1思源fixture餐厅"),
    "JIANDA_YANTA": (108.967153, 34.236991, "G1建大fixture菜", "G1建大fixture餐厅"),
}
ROLES = ("MEAT", "VEG", "SOUP", "ONE_MEAL")
CUISINES = ("川湘菜", "粤菜", "家常菜", "轻食", "面食")
# 0.0–1.0 的 8 维向量；按 index 轮换，保证有辣/清、油/淡、快/慢的对照
VECTORS = (
    (0.95, 0.85, 0.30, 0.50, 0.75, 0.60, 0.70, 0.80),
    (0.05, 0.15, 0.85, 0.45, 0.50, 0.55, 0.50, 0.60),
    (0.20, 0.10, 0.30, 0.50, 0.30, 0.85, 0.30, 0.35),
    (0.50, 0.45, 0.50, 0.50, 0.90, 0.70, 0.45, 0.55),
    (0.35, 0.30, 0.65, 0.55, 0.60, 0.65, 0.55, 0.65),
    (0.70, 0.35, 0.20, 0.50, 0.55, 0.75, 0.60, 0.50),
)
# 过敏原/忌口样本：与演示角色 1–4 的 veto_tags 对应
SPECIAL_INGREDIENTS = {
    3: "虾仁",  # 海鲜：角色 2 / 3 忌口
    7: "香菜",  # 香菜：角色 2 忌口
    11: "折耳根",  # 折耳根：角色 1 忌口
    17: "花生米",  # 花生：角色 4 忌口
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_state(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "counts": {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "users",
                    "restaurants",
                    "dishes_and_recipes",
                    "eating_logs",
                    "group_rooms",
                    "room_votes",
                    "fridge_inventory",
                    "algo_configs",
                )
                if table in tables
            },
            "columns": {
                table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                for table in ("restaurants", "dishes_and_recipes", "group_rooms", "room_votes")
                if table in tables
            },
            "indexes": {
                table: [row[1] for row in connection.execute(f"PRAGMA index_list({table})")]
                for table in ("room_votes",)
                if table in tables
            },
        }
    finally:
        connection.close()


def build_fixture(target: Path) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.algorithms.vector_spec import FEATURE_KEYS
    from backend.models import Dish, Restaurant

    engine = create_engine(f"sqlite:///{target.as_posix()}")
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    try:
        existing = (
            session.query(Restaurant).filter(Restaurant.source_dataset == DATASET).count()
        )
        if existing:
            counts = {
                campus: {
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
                for campus in CAMPUSES
            }
            return {"already_present": True, "counts": counts}

        records = []
        for campus, (lon, lat, dish_prefix, store_prefix) in CAMPUSES.items():
            for store_index in range(1, 11):
                store = Restaurant(
                    name=f"{store_prefix}{store_index:02d}",
                    source_type="CANTEEN",
                    category="G1 fixture",
                    avg_price=12.0 + store_index,
                    rating=4.0 + (store_index % 5) * 0.1,
                    longitude=lon + store_index * 0.00012,
                    latitude=lat + store_index * 0.00012,
                    distance_meters=120 + store_index * 10,
                    address="G1 校区 fixture（合成数据，非真实采集）",
                    source_dataset=DATASET,
                    source_record_id=f"g1-rest-{campus.lower()}-{store_index:02d}",
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
                for dish_index in range(1, 4):
                    global_index = (store_index - 1) * 3 + dish_index
                    vector = VECTORS[(global_index - 1) % len(VECTORS)]
                    main = [f"fixture主料{global_index:02d}"]
                    special = SPECIAL_INGREDIENTS.get(global_index)
                    if special:
                        main.append(special)
                    # 价格阶梯：一半菜低于 12 元，一半高于 30 元，用于预算冲突
                    price = 9.5 + (global_index % 6) * 7.0
                    dish = Dish(
                        name=f"{dish_prefix}{global_index:02d}",
                        mode_type="OUT_DINING",
                        restaurant_id=store.id,
                        cuisine_type=CUISINES[(global_index - 1) % len(CUISINES)],
                        dish_role=ROLES[(global_index - 1) % len(ROLES)],
                        price_or_cost=round(price, 1),
                        cook_minutes=10 + (global_index % 5) * 5,
                        appliance_tag=["炒锅"],
                        ingredients_main=main,
                        ingredients_aux=["盐", "食用油"],
                        recipe_steps="G1 fixture（合成条目，非真实菜谱）",
                        feature_vector={
                            key: value for key, value in zip(FEATURE_KEYS, vector)
                        },
                        image_url="",
                        allergen_tags=[],
                        tagging_status="SUCCESS",
                        source_dataset=DATASET,
                        source_record_id=f"g1-dish-{campus.lower()}-{global_index:02d}",
                        data_version=DATASET,
                        is_synthetic=True,
                    )
                    session.add(dish)
        session.commit()

        counts = {
            campus: {
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
            for campus in CAMPUSES
        }
        special = {
            "海鲜": session.query(Dish)
            .filter(Dish.source_dataset == DATASET, Dish.name.like("%菜03"))
            .count(),
            "香菜": session.query(Dish)
            .filter(Dish.source_dataset == DATASET, Dish.name.like("%菜07"))
            .count(),
            "折耳根": session.query(Dish)
            .filter(Dish.source_dataset == DATASET, Dish.name.like("%菜11"))
            .count(),
            "花生": session.query(Dish)
            .filter(Dish.source_dataset == DATASET, Dish.name.like("%菜17"))
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
        return {
            "already_present": False,
            "is_synthetic": True,
            "counts": counts,
            "special_dishes": special,
            "seed_null_restaurants": seed_null,
            "records": records,
        }
    finally:
        session.close()
        engine.dispose()


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"源库不存在：{SOURCE}")
    if TARGET.exists():
        raise SystemExit(f"目标已存在，拒绝覆盖：{TARGET}")

    before = {
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "source_state": table_state(SOURCE),
        "protected": {
            path.name: sha256(path)
            for path in (
                ROOT / "backend" / "eatwhat.db",
                ROOT / "backend" / "eatwhat_batch4.db",
                ROOT / "backend" / "eatwhat_s05_r01_iso.db",
                ROOT / "backend" / "eatwhat_s06_r01_iso.db",
                ROOT / "backend" / "eatwhat_s06_r02_iso.db",
            )
            if path.exists()
        },
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
    }

    shutil.copy2(SOURCE, TARGET)
    copied_sha = sha256(TARGET)
    if copied_sha != before["source_sha256"]:
        raise SystemExit("复制后 SHA 与源库不一致，停止")

    # S06 唯一索引迁移（幂等，脚本自带保护名单，目标不是受保护库）
    from backend.scripts import migrate_s06_room_contract as migration

    migration_result = migration.migrate(TARGET) if hasattr(migration, "migrate") else None
    if migration_result is None:
        # 脚本没有暴露函数时退回 CLI 语义：直接建索引
        connection = sqlite3.connect(str(TARGET))
        try:
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_room_votes_room_user_dish "
                "ON room_votes (room_code, user_id, dish_id)"
            )
            connection.commit()
        finally:
            connection.close()

    fixture = build_fixture(TARGET)

    target_state = table_state(TARGET)
    after_protected = {
        path.name: sha256(path)
        for path in (
            ROOT / "backend" / "eatwhat.db",
            ROOT / "backend" / "eatwhat_batch4.db",
            ROOT / "backend" / "eatwhat_s05_r01_iso.db",
            ROOT / "backend" / "eatwhat_s06_r01_iso.db",
            ROOT / "backend" / "eatwhat_s06_r02_iso.db",
        )
        if path.exists()
    }
    payload = {
        **before,
        "target": str(TARGET),
        "target_sha256": target_state["sha256"],
        "target_state": target_state,
        "fixture": fixture,
        "migration": migration_result,
        "protected_after": after_protected,
        "protected_unchanged": after_protected == before["protected"],
        "rollback": (
            "删除 backend/eatwhat_g1_s07_iso.db 即可；源库与受保护库未被写入，"
            "回滚不需要恢复任何文件。"
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "source", "source_sha256", "target", "target_sha256",
        "protected_unchanged", "created_at",
    )}, ensure_ascii=False, indent=2))
    print(json.dumps(fixture["counts"] if "counts" in fixture else fixture, ensure_ascii=False))


if __name__ == "__main__":
    main()
