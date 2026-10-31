"""S10 共享合成菜谱导入（D 类合成来源，不采集任何第三方菜谱文本）。

- 全部行 `is_synthetic=1`、`source_dataset=synthetic_recipe_v1`；
- 6,400 行由确定性模板生成，菜名唯一，不用重复行凑规模；
- `feature_vector`/`allergen_tags` 留给 S11 打标，当前为 NULL、`tagging_status=PENDING`；
- 只写下厨模式 `HOME_COOKING`，不绑定门店，不与真实菜单混称。
"""

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from backend.models import Dish
from backend.scripts.s10_common import (
    DEFAULT_DB,
    RECIPE_DATASET,
    RECIPE_DATA_VERSION,
    SCRIPT_VERSION,
    ensure_import_db,
    make_session,
    sha256_file,
    utc_now_iso,
    write_json,
    write_reject,
)

GENERATOR_SEED = 20261025
DEFAULT_COUNT = 6400

PROTEINS = [
    ("鸡胸肉", "meat", 12.0),
    ("鸡腿肉", "meat", 14.0),
    ("鸡翅", "meat", 15.0),
    ("牛腩", "meat", 22.0),
    ("牛里脊", "meat", 26.0),
    ("猪肉末", "meat", 12.0),
    ("猪里脊", "meat", 16.0),
    ("五花肉", "meat", 18.0),
    ("排骨", "meat", 24.0),
    ("羊肉", "meat", 24.0),
    ("鸭肉", "meat", 20.0),
    ("腊肠", "meat", 16.0),
    ("火腿", "meat", 12.0),
    ("培根", "meat", 18.0),
    ("鲈鱼", "seafood", 22.0),
    ("草鱼", "seafood", 18.0),
    ("虾仁", "seafood", 28.0),
    ("鱿鱼", "seafood", 20.0),
    ("蛤蜊", "seafood", 18.0),
    ("三文鱼", "seafood", 32.0),
    ("鸡蛋", "plant", 6.0),
    ("鹌鹑蛋", "plant", 8.0),
    ("豆腐", "plant", 5.0),
    ("豆干", "plant", 6.0),
    ("腐竹", "plant", 8.0),
    ("香菇", "plant", 7.0),
    ("杏鲍菇", "plant", 8.0),
    ("金针菇", "plant", 6.0),
    ("木耳", "plant", 6.0),
    ("土豆", "plant", 4.0),
    ("茄子", "plant", 5.0),
    ("西红柿", "plant", 4.0),
    ("黄瓜", "plant", 3.0),
    ("西兰花", "plant", 6.0),
    ("菜花", "plant", 5.0),
    ("菠菜", "plant", 4.0),
    ("生菜", "plant", 4.0),
    ("白菜", "plant", 3.0),
    ("豆角", "plant", 5.0),
    ("莲藕", "plant", 7.0),
]

VEGETABLES = [
    "土豆",
    "青椒",
    "茄子",
    "西红柿",
    "黄瓜",
    "西兰花",
    "菜花",
    "菠菜",
    "生菜",
    "白菜",
    "豆角",
    "莲藕",
    "山药",
    "南瓜",
    "玉米",
    "胡萝卜",
    "洋葱",
    "芹菜",
    "韭菜",
    "蒜薹",
    "莴笋",
    "冬瓜",
    "丝瓜",
    "苦瓜",
    "蘑菇",
    "香菇",
    "木耳",
    "豆腐",
    "豆芽",
    "荷兰豆",
]

STYLE_META = {
    "清炒": ("家常菜", ["炒锅"], 10, "大火快炒", ["蒜"]),
    "蒜蓉": ("家常菜", ["炒锅"], 12, "蒜末爆香后快炒", ["蒜"]),
    "红烧": ("江浙菜", ["炒锅"], 35, "煸香后加酱油与糖小火收汁", ["生抽", "冰糖", "葱姜蒜"]),
    "清蒸": ("粤菜", ["炒锅"], 25, "水开后上锅蒸制", ["葱姜蒜", "蒸鱼豉油"]),
    "水煮": ("川湘菜", ["炒锅"], 25, "豆瓣酱炒香后加水煮制", ["豆瓣酱", "辣椒", "花椒"]),
    "酸辣": ("川湘菜", ["炒锅"], 15, "爆香辣椒后快炒并调醋", ["干辣椒", "醋", "蒜"]),
    "麻辣": ("川湘菜", ["炒锅"], 20, "花椒辣椒炒香后翻炒", ["辣椒", "花椒", "葱姜蒜"]),
    "糖醋": ("鲁菜", ["炒锅"], 20, "煎制后裹糖醋汁", ["醋", "白糖", "番茄酱"]),
    "酱香": ("鲁菜", ["炒锅"], 25, "甜面酱炒香后焖制", ["甜面酱", "生抽", "葱姜蒜"]),
    "孜然": ("西北菜", ["炒锅"], 15, "孜然辣椒面快炒", ["孜然", "辣椒面"]),
    "黑椒": ("粤菜", ["空气炸锅"], 20, "黑椒腌制后烤制", ["黑胡椒", "橄榄油"]),
    "咖喱": ("家常菜", ["炒锅"], 30, "咖喱块加水煮稠", ["咖喱块", "洋葱"]),
    "番茄": ("家常菜", ["炒锅"], 15, "番茄炒出汁后同煮", ["番茄酱", "葱"]),
    "蚝油": ("粤菜", ["炒锅"], 12, "蚝油调味后快炒", ["蚝油", "蒜"]),
    "凉拌": ("家常菜", ["免开火凉拌"], 8, "焯水过凉后拌匀", ["香菜", "蒜", "醋"]),
    "干煸": ("川湘菜", ["炒锅"], 18, "煸至表皮微皱后调味", ["干辣椒", "花椒"]),
    "炖煮": ("家常菜", ["炒锅"], 45, "加水小火炖煮", ["葱姜蒜", "生抽"]),
    "煲汤": ("粤菜", ["炒锅"], 60, "加水慢煲", ["姜片", "盐"]),
    "焖饭": ("家常菜", ["电饭煲"], 40, "与米同入电饭煲焖熟", ["生抽", "葱"]),
    "一锅出": ("家常菜", ["电饭煲", "一锅出"], 35, "食材同锅焖煮", ["生抽", "葱姜蒜"]),
}

SOUP_STYLES = {"炖煮", "煲汤"}
ONE_MEAL_STYLES = {"焖饭", "一锅出"}
VALID_ROLES = {"MEAT", "VEG", "SOUP", "ONE_MEAL"}
VALID_APPLIANCES = {"炒锅", "电饭煲", "空气炸锅", "免开火凉拌", "一锅出"}
MAX_COMBINATIONS = len(STYLE_META) * (
    len(PROTEINS) * len(VEGETABLES)
    - sum(1 for protein in PROTEINS for vegetable in VEGETABLES if protein[0] == vegetable)
)


def generate_recipes(count: int = DEFAULT_COUNT):
    combinations = [
        (style, protein, vegetable)
        for style in STYLE_META
        for protein in PROTEINS
        for vegetable in VEGETABLES
        if protein[0] != vegetable
    ]
    rng = random.Random(GENERATOR_SEED)
    rng.shuffle(combinations)
    selected = combinations[:count]
    rows = []
    for index, (style, protein, vegetable) in enumerate(selected, start=1):
        protein_name, protein_group, protein_cost = protein
        cuisine, appliances, base_minutes, method, style_aux = STYLE_META[style]
        if style in SOUP_STYLES:
            role = "SOUP"
        elif style in ONE_MEAL_STYLES:
            role = "ONE_MEAL"
        elif protein_group == "plant":
            role = "VEG"
        else:
            role = "MEAT"

        mains = [protein_name, vegetable]
        if style in ONE_MEAL_STYLES:
            mains.append("大米")
        aux = ["盐", "食用油", *style_aux]
        minutes = max(5, min(120, base_minutes + (index % 7) - 3))
        cost = round(protein_cost + 2.0 + (1.5 if style in SOUP_STYLES else 0.0), 1)
        rows.append(
            {
                "name": f"{style}{protein_name}{vegetable}",
                "mode_type": "HOME_COOKING",
                "restaurant_id": None,
                "cuisine_type": cuisine,
                "dish_role": role,
                "price_or_cost": cost,
                "cook_minutes": minutes,
                "appliance_tag": list(appliances),
                "ingredients_main": mains,
                "ingredients_aux": aux,
                "recipe_steps": (
                    f"1. 将{protein_name}与{vegetable}洗净切配，辅料备好。"
                    f"2. {method}，注意火候与翻动。"
                    f"3. 加盐调味，确认熟透后出锅。"
                ),
                "feature_vector": None,
                "image_url": "",
                "allergen_tags": None,
                "tagging_status": "PENDING",
                "tagging_error": None,
                "llm_meta": None,
                "source_dataset": RECIPE_DATASET,
                "source_record_id": f"recipe-{index:06d}",
                "source_url": None,
                "data_version": RECIPE_DATA_VERSION,
                "is_synthetic": 1,
                "deleted_at": None,
            }
        )
    return rows


def validate_generated(rows) -> dict:
    names = [row["name"] for row in rows]
    keys = [
        (row["name"], tuple(sorted(row["ingredients_main"]))) for row in rows
    ]
    errors = []
    for row in rows:
        if row["dish_role"] not in VALID_ROLES:
            errors.append(f"{row['source_record_id']}:bad_role")
        if not set(row["appliance_tag"]) <= VALID_APPLIANCES:
            errors.append(f"{row['source_record_id']}:bad_appliance")
        if row["mode_type"] != "HOME_COOKING" or row["restaurant_id"] is not None:
            errors.append(f"{row['source_record_id']}:bad_mode_or_restaurant")
        if not row["ingredients_main"] or not row["ingredients_aux"]:
            errors.append(f"{row['source_record_id']}:missing_ingredients")
        if not row["recipe_steps"].strip():
            errors.append(f"{row['source_record_id']}:missing_steps")
        if row["feature_vector"] is not None:
            errors.append(f"{row['source_record_id']}:unexpected_feature_vector")
        if row["tagging_status"] != "PENDING":
            errors.append(f"{row['source_record_id']}:bad_tagging_status")
        if row["is_synthetic"] != 1:
            errors.append(f"{row['source_record_id']}:not_synthetic")
    return {
        "rows": len(rows),
        "unique_names": len(set(names)),
        "unique_name_ingredient_pairs": len(set(keys)),
        "duplicate_names": len(names) - len(set(names)),
        "duplicate_row_keys": len(keys) - len(set(keys)),
        "errors": errors,
        "ok": not errors and len(names) == len(set(names)) == len(set(keys)),
    }


def import_recipes(
    db,
    batch_id: str,
    count: int = DEFAULT_COUNT,
    reject_path: Path = None,
) -> dict:
    rows = generate_recipes(count)
    validation = validate_generated(rows)
    summary = {
        "kind": "SYNTHETIC_RECIPE",
        "batch_id": batch_id,
        "dataset": RECIPE_DATASET,
        "data_version": RECIPE_DATA_VERSION,
        "script_version": SCRIPT_VERSION,
        "generator_seed": GENERATOR_SEED,
        "generated": len(rows),
        "unique_names": validation["unique_names"],
        "unique_name_ingredient_pairs": validation["unique_name_ingredient_pairs"],
        "inserted": 0,
        "existing": 0,
        "rejected": 0,
        "failures": 0,
        "by_mode_type": {},
        "by_dish_role": {},
        "null_feature_vector_inserted": 0,
        "started_at": utc_now_iso(),
        "generation_validation": validation,
    }
    for payload in rows:
        source_id = payload["source_record_id"]
        existing = db.execute(
            select(Dish.id).where(
                Dish.source_dataset == RECIPE_DATASET,
                Dish.source_record_id == source_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            summary["existing"] += 1
            continue
        if payload["dish_role"] not in VALID_ROLES:
            summary["rejected"] += 1
            if reject_path is not None:
                write_reject(
                    reject_path,
                    {
                        "batch_id": batch_id,
                        "kind": "SYNTHETIC_RECIPE",
                        "reason": "bad_role",
                        "retryable": False,
                        "raw": payload,
                    },
                )
            continue
        try:
            dish = Dish(**payload)
            with db.begin_nested():
                db.add(dish)
                db.flush()
            summary["inserted"] += 1
            summary["by_mode_type"]["HOME_COOKING"] = (
                summary["by_mode_type"].get("HOME_COOKING", 0) + 1
            )
            role = payload["dish_role"]
            summary["by_dish_role"][role] = summary["by_dish_role"].get(role, 0) + 1
            if payload["feature_vector"] is None:
                summary["null_feature_vector_inserted"] += 1
        except Exception as exc:  # noqa: BLE001
            summary["failures"] += 1
            if reject_path is not None:
                write_reject(
                    reject_path,
                    {
                        "batch_id": batch_id,
                        "kind": "SYNTHETIC_RECIPE",
                        "reason": f"db_error:{type(exc).__name__}",
                        "retryable": True,
                        "raw": payload,
                    },
                )
    db.commit()
    summary["finished_at"] = utc_now_iso()
    summary["ok"] = (
        summary["rejected"] == 0
        and summary["failures"] == 0
        and validation["ok"]
        and summary["inserted"] + summary["existing"] == len(rows)
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="S10 合成菜谱导入")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--summary-out", type=Path, default=None)
    parser.add_argument("--reject-out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.count <= MAX_COMBINATIONS:
        raise SystemExit(f"--count 必须在 1..{MAX_COMBINATIONS}")
    batch_id = args.batch_id or f"s10-recipe-{datetime.now().strftime('%Y%m%dT%H%M%S')}"

    if args.dry_run:
        rows = generate_recipes(args.count)
        summary = {
            "kind": "SYNTHETIC_RECIPE_DRY_RUN",
            "batch_id": batch_id,
            "generated": len(rows),
            **validate_generated(rows),
        }
    else:
        db_path = ensure_import_db(args.db)
        db_sha_before = sha256_file(db_path) if db_path.exists() else None
        engine, Session = make_session(db_path)
        db = Session()
        try:
            summary = import_recipes(
                db, batch_id, count=args.count, reject_path=args.reject_out
            )
        finally:
            db.close()
            engine.dispose()
        summary["db"] = str(db_path)
        summary["db_sha256_before"] = db_sha_before
        summary["db_sha256_after"] = sha256_file(db_path)

    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.summary_out:
        write_json(args.summary_out, summary)
    print(text)
    if not summary.get("ok", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
