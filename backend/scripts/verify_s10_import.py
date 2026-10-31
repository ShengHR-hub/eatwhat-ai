"""S10 独立验证：直接读取封存输入与目标库重算，不采信导入脚本的汇总数字。

用法（在仓库根目录）：
  python -m backend.scripts.verify_s10_import --db backend/eatwhat_batch4.db \
      --out-dir docs/review/stages/S10/r01/data \
      --import-summary ... --reject-log ... --fingerprint-out ... \
      [--idempotency-before ...]

所有写操作只发生在 `--out-dir` 的证据文件；数据库以 SQLite 只读模式打开。
"""

import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from backend.scripts.import_open_recipes import (
    GENERATOR_SEED,
    VALID_APPLIANCES,
    VALID_ROLES,
    generate_recipes,
)
from backend.scripts.s10_common import (
    AMAP_DATASET,
    AMAP_DATA_VERSION,
    CAMPUS_CENTERS,
    CAMPUS_INPUTS,
    CAMPUS_NAMES,
    CANTEEN_ANCHORS,
    CANTEEN_DATASET,
    CANTEEN_DATA_VERSION,
    CAOTANG,
    DEMO_DB,
    RECIPE_DATASET,
    RECIPE_DATA_VERSION,
    ROOT,
    haversine_m,
    sha256_file,
    write_json,
)

EXPECTED_REAL = {"SIYUAN": 605, "JIANDA_YANTA": 6659}
EXPECTED_CANTEEN = {"SIYUAN": 200, "JIANDA_YANTA": 200}
EXPECTED_RECIPES = 6400
SAMPLE_SIZE = 30


def connect_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def rows_to_dicts(cursor, rows):
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in rows]


def canonical_sha(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def parse_float(value):
    if value is None or value == "":
        return None
    return float(value)


def load_inputs():
    payload = {}
    for campus, path in CAMPUS_INPUTS.items():
        rows = []
        with open(path, encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if line.strip():
                    row = json.loads(line)
                    row["__line_no"] = line_no
                    rows.append(row)
        ids = [row["id"] for row in rows]
        payload[campus] = {
            "path": path,
            "rows": rows,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "line_count": len(rows),
            "unique_ids": len(set(ids)),
            "duplicates": len(ids) - len(set(ids)),
            "campus_values": dict(Counter(row.get("campus") for row in rows)),
            "synthetic_values": dict(Counter(row.get("is_synthetic") for row in rows)),
            "datasets": dict(Counter(row.get("source_dataset") for row in rows)),
            "missing_rating": sum(row.get("rating") in (None, "") for row in rows),
            "missing_cost": sum(row.get("cost") in (None, "") for row in rows),
            "missing_tag": sum(row.get("tag") in (None, "") for row in rows),
            "max_distance": max(float(row["_distance_m"]) for row in rows),
        }
    return payload


def load_recipes():
    rows = generate_recipes(EXPECTED_RECIPES)
    canonical = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
    )
    return rows, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fingerprint(restaurants, dishes):
    restaurant_payload = [
        [
            row["source_type"],
            row["campus"],
            row["source_dataset"],
            row["source_record_id"],
            row["name"],
            row["longitude"],
            row["latitude"],
            row["distance_meters"],
            row["rating"],
            row["avg_price"],
            row["is_synthetic"],
            row["category"],
            row["address"],
            row["data_version"],
        ]
        for row in restaurants
    ]
    dish_payload = [
        [
            row["source_dataset"],
            row["source_record_id"],
            row["name"],
            row["mode_type"],
            row["restaurant_id"],
            row["cuisine_type"],
            row["dish_role"],
            row["price_or_cost"],
            row["cook_minutes"],
            row["ingredients_main"],
            row["ingredients_aux"],
            row["appliance_tag"],
            row["feature_vector"],
            row["tagging_status"],
            row["is_synthetic"],
        ]
        for row in dishes
    ]
    associations = [
        [row["source_record_id"], row["restaurant_id"]]
        for row in dishes
        if row["restaurant_id"] is not None
    ]
    return {
        "restaurant_rows": len(restaurants),
        "dish_rows": len(dishes),
        "association_rows": len(associations),
        "restaurant_fingerprint": canonical_sha(restaurant_payload),
        "dish_fingerprint": canonical_sha(dish_payload),
        "association_fingerprint": canonical_sha(associations),
    }


def evenly_spaced(items, count):
    if len(items) <= count:
        return list(items)
    indices = sorted({round(i * (len(items) - 1) / (count - 1)) for i in range(count)})
    return [items[index] for index in indices]


def compare_poi_sample(db_row, input_row, campus):
    lon, lat = map(float, input_row["location"].split(","))
    distance = haversine_m((lon, lat), CAMPUS_CENTERS[campus])
    input_rating = parse_float(input_row.get("rating"))
    input_cost = parse_float(input_row.get("cost"))
    checks = {
        "name": db_row["name"] == input_row["name"],
        "campus": db_row["campus"] == campus,
        "source_type": db_row["source_type"] == "AMAP_POI",
        "is_synthetic": db_row["is_synthetic"] == 0,
        "source_dataset": db_row["source_dataset"] == AMAP_DATASET,
        "source_record_id": db_row["source_record_id"] == input_row["id"],
        "data_version": db_row["data_version"] == AMAP_DATA_VERSION,
        "longitude": abs(db_row["longitude"] - lon) <= 1e-6,
        "latitude": abs(db_row["latitude"] - lat) <= 1e-6,
        "within_3km": distance <= 3000.5,
        "distance_meters": abs(db_row["distance_meters"] - distance) <= 1.0,
        "rating_null_policy": (
            (db_row["rating"] is None) if input_rating is None
            else abs(db_row["rating"] - input_rating) <= 1e-6
        ),
        "cost_null_policy": (
            (db_row["avg_price"] is None) if input_cost is None
            else abs(db_row["avg_price"] - input_cost) <= 1e-6
        ),
        "address": (db_row["address"] or "") == (input_row.get("address") or ""),
        "deleted_at": db_row["deleted_at"] is None,
        "category_non_empty": bool((db_row["category"] or "").strip()),
    }
    return {
        "campus": campus,
        "source_record_id": db_row["source_record_id"],
        "input_file": str(CAMPUS_INPUTS[campus]),
        "input_sha256": sha256_file(CAMPUS_INPUTS[campus]),
        "input_line_no": input_row["__line_no"],
        "db_id": db_row["id"],
        "db": {
            "name": db_row["name"],
            "longitude": db_row["longitude"],
            "latitude": db_row["latitude"],
            "distance_meters": db_row["distance_meters"],
            "rating": db_row["rating"],
            "avg_price": db_row["avg_price"],
            "campus": db_row["campus"],
            "source_dataset": db_row["source_dataset"],
            "source_record_id": db_row["source_record_id"],
            "data_version": db_row["data_version"],
            "is_synthetic": db_row["is_synthetic"],
        },
        "input": {
            "name": input_row["name"],
            "location": input_row["location"],
            "_distance_m": input_row["_distance_m"],
            "rating": input_row.get("rating"),
            "cost": input_row.get("cost"),
            "tag": input_row.get("tag"),
            "typecode": input_row.get("typecode"),
            "address": input_row.get("address"),
        },
        "checks": checks,
        "ok": all(checks.values()),
    }


def compare_recipe_sample(db_row, generated_row, index):
    generated_sha = canonical_sha(generated_row)
    checks = {
        "name": db_row["name"] == generated_row["name"],
        "mode_type": db_row["mode_type"] == "HOME_COOKING",
        "restaurant_id_null": db_row["restaurant_id"] is None,
        "cuisine_type": db_row["cuisine_type"] == generated_row["cuisine_type"],
        "dish_role": db_row["dish_role"] == generated_row["dish_role"],
        "price_or_cost": abs((db_row["price_or_cost"] or 0) - generated_row["price_or_cost"]) <= 1e-6,
        "cook_minutes": db_row["cook_minutes"] == generated_row["cook_minutes"],
        "appliance_tag": json.loads(db_row["appliance_tag"]) == generated_row["appliance_tag"],
        "ingredients_main": json.loads(db_row["ingredients_main"]) == generated_row["ingredients_main"],
        "ingredients_aux": json.loads(db_row["ingredients_aux"]) == generated_row["ingredients_aux"],
        "recipe_steps": db_row["recipe_steps"] == generated_row["recipe_steps"],
        "feature_vector_null": db_row["feature_vector"] is None,
        "allergen_tags_null": db_row["allergen_tags"] is None,
        "tagging_status": db_row["tagging_status"] == "PENDING",
        "source_dataset": db_row["source_dataset"] == RECIPE_DATASET,
        "source_record_id": db_row["source_record_id"] == generated_row["source_record_id"],
        "data_version": db_row["data_version"] == RECIPE_DATA_VERSION,
        "is_synthetic": db_row["is_synthetic"] == 1,
        "deleted_at": db_row["deleted_at"] is None,
    }
    return {
        "source_record_id": db_row["source_record_id"],
        "generator": "backend/scripts/import_open_recipes.py",
        "generator_seed": GENERATOR_SEED,
        "generated_index": index,
        "generated_record_sha256": generated_sha,
        "db_id": db_row["id"],
        "db": {
            "name": db_row["name"],
            "ingredients_main": json.loads(db_row["ingredients_main"]),
            "ingredients_aux": json.loads(db_row["ingredients_aux"]),
            "dish_role": db_row["dish_role"],
            "appliance_tag": json.loads(db_row["appliance_tag"]),
            "cook_minutes": db_row["cook_minutes"],
            "source_dataset": db_row["source_dataset"],
            "source_record_id": db_row["source_record_id"],
            "is_synthetic": db_row["is_synthetic"],
        },
        "checks": checks,
        "ok": all(checks.values()),
    }


def demo_baseline():
    if not DEMO_DB.exists():
        return {"exists": False}
    connection = connect_ro(DEMO_DB)
    try:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "users",
                "restaurants",
                "dishes_and_recipes",
                "eating_logs",
                "group_rooms",
                "room_votes",
            )
        }
    finally:
        connection.close()
    expected = None
    evidence_path = ROOT / "docs/review/stages/S09/r04/data/r04_evidence.json"
    if evidence_path.exists():
        expected = json.loads(evidence_path.read_text(encoding="utf-8"))["protection"][
            "db_sha256"
        ]
    return {
        "exists": True,
        "path": str(DEMO_DB),
        "sha256": sha256_file(DEMO_DB),
        "expected_sha256_from_s09_r04": expected,
        "sha_unchanged": expected is not None and sha256_file(DEMO_DB) == expected,
        "counts": counts,
        "group_rooms_zero": counts.get("group_rooms") == 0,
        "room_votes_zero": counts.get("room_votes") == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="S10 独立数据验证")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--import-summary", type=Path, action="append", default=[])
    parser.add_argument("--reject-log", type=Path, action="append", default=[])
    parser.add_argument("--fingerprint-out", type=Path, default=None)
    parser.add_argument("--idempotency-before", type=Path, default=None)
    args = parser.parse_args()

    db_path = args.db.resolve()
    if db_path == DEMO_DB:
        raise SystemExit("验证目标不能是演示库")
    if not db_path.exists():
        raise SystemExit(f"目标库不存在：{db_path}")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    inputs = load_inputs()
    generated, generated_sha = load_recipes()

    connection = connect_ro(db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    restaurant_rows = rows_to_dicts(
        cursor,
        cursor.execute("SELECT * FROM restaurants ORDER BY source_type, campus, source_record_id, id").fetchall(),
    )
    dish_rows = rows_to_dicts(
        cursor,
        cursor.execute("SELECT * FROM dishes_and_recipes ORDER BY source_dataset, source_record_id, id").fetchall(),
    )
    integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_key_errors = cursor.execute("PRAGMA foreign_key_check").fetchall()
    table_counts = {
        table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "users",
            "restaurants",
            "dishes_and_recipes",
            "eating_logs",
            "group_rooms",
            "room_votes",
            "fridge_inventory",
            "user_preferences",
            "algo_configs",
        )
    }
    indexes = {}
    for table in ("restaurants", "dishes_and_recipes", "group_rooms"):
        indexes[table] = [
            dict(zip(["seq", "name", "unique", "origin", "partial"], row))
            for row in connection.execute(f"PRAGMA index_list({table})").fetchall()
        ]
    columns = {}
    for table in ("restaurants", "dishes_and_recipes", "group_rooms"):
        columns[table] = [
            dict(zip(["cid", "name", "type", "notnull", "default", "pk"], row))
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        ]
    connection.close()

    real = [
        row
        for row in restaurant_rows
        if row["source_type"] == "AMAP_POI" and row["is_synthetic"] == 0
    ]
    canteens = [row for row in restaurant_rows if row["source_type"] == "CANTEEN"]
    real_by_campus = Counter(row["campus"] for row in real)
    canteen_by_campus = Counter(row["campus"] for row in canteens)
    synthetic_restaurants = [row for row in restaurant_rows if row["is_synthetic"] == 1]
    unknown_campus = [
        row for row in restaurant_rows if row["campus"] not in CAMPUS_CENTERS
    ]

    # —— 真实 POI 完整性 ——
    input_by_campus = {
        campus: {row["id"]: row for row in payload["rows"]}
        for campus, payload in inputs.items()
    }
    real_checks = []
    distance_errors = []
    coordinate_mismatch = []
    value_mismatch = []
    for row in real:
        campus = row["campus"]
        source = input_by_campus.get(campus, {}).get(row["source_record_id"])
        ok = source is not None
        real_checks.append(ok)
        if source is None:
            value_mismatch.append(
                {"source_record_id": row["source_record_id"], "reason": "not_in_input"}
            )
            continue
        lon, lat = map(float, source["location"].split(","))
        distance = haversine_m((lon, lat), CAMPUS_CENTERS[campus])
        if abs(row["longitude"] - lon) > 1e-6 or abs(row["latitude"] - lat) > 1e-6:
            coordinate_mismatch.append(row["source_record_id"])
        if distance > 3000.5:
            distance_errors.append(
                {"source_record_id": row["source_record_id"], "distance": distance}
            )
        if abs(row["distance_meters"] - distance) > 1.0:
            distance_errors.append(
                {
                    "source_record_id": row["source_record_id"],
                    "distance": distance,
                    "stored": row["distance_meters"],
                }
            )
        expected_rating = parse_float(source.get("rating"))
        expected_cost = parse_float(source.get("cost"))
        if expected_rating is None:
            if row["rating"] is not None:
                value_mismatch.append(
                    {"source_record_id": row["source_record_id"], "reason": "rating_should_be_null"}
                )
        elif row["rating"] is None or abs(row["rating"] - expected_rating) > 1e-6:
            value_mismatch.append(
                {"source_record_id": row["source_record_id"], "reason": "rating_mismatch"}
            )
        if expected_cost is None:
            if row["avg_price"] is not None:
                value_mismatch.append(
                    {"source_record_id": row["source_record_id"], "reason": "cost_should_be_null"}
                )
        elif row["avg_price"] is None or abs(row["avg_price"] - expected_cost) > 1e-6:
            value_mismatch.append(
                {"source_record_id": row["source_record_id"], "reason": "cost_mismatch"}
            )
        if row["name"] != source["name"]:
            value_mismatch.append(
                {"source_record_id": row["source_record_id"], "reason": "name_mismatch"}
            )
        if row["source_dataset"] != AMAP_DATASET or row["data_version"] != AMAP_DATA_VERSION:
            value_mismatch.append(
                {"source_record_id": row["source_record_id"], "reason": "source_version_mismatch"}
            )
        if row["is_synthetic"] != 0 or row["deleted_at"] is not None:
            value_mismatch.append(
                {"source_record_id": row["source_record_id"], "reason": "flag_or_delete_mismatch"}
            )

    # —— 合成食堂 ——
    canteen_checks = []
    anchor_min_distances = {}
    for campus, anchors in CANTEEN_ANCHORS.items():
        campus_real = [row for row in real if row["campus"] == campus]
        for anchor in anchors:
            anchor_min_distances[f"{campus}:{anchor[0]:.6f},{anchor[1]:.6f}"] = round(
                min(
                    haversine_m(anchor, (row["longitude"], row["latitude"]))
                    for row in campus_real
                ),
                3,
            )
    canteen_name_pattern_ok = True
    for row in canteens:
        checks = {
            "campus": row["campus"] in CAMPUS_CENTERS,
            "source_type": row["source_type"] == "CANTEEN",
            "is_synthetic": row["is_synthetic"] == 1,
            "rating_null": row["rating"] is None,
            "price_null": row["avg_price"] is None,
            "dataset": row["source_dataset"] == CANTEEN_DATASET,
            "data_version": row["data_version"] == CANTEEN_DATA_VERSION,
            "deleted_at": row["deleted_at"] is None,
            "coords": row["longitude"] is not None and row["latitude"] is not None,
            "within_3km": haversine_m(
                (row["longitude"], row["latitude"]), CAMPUS_CENTERS[row["campus"]]
            )
            <= 3000.5,
            "name_pattern": row["name"].startswith(
                tuple(
                    base + "·"
                    for base in ("一食堂", "二食堂", "三食堂", "清真食堂", "建大")
                )
            ),
            "address_label": "合成" in (row["address"] or ""),
        }
        if not checks["name_pattern"]:
            canteen_name_pattern_ok = False
        canteen_checks.append(checks)

    # —— 菜谱 ——
    generated_by_id = {row["source_record_id"]: row for row in generated}
    generated_index = {
        row["source_record_id"]: index for index, row in enumerate(generated)
    }
    recipe_name_counter = Counter(row["name"] for row in dish_rows)
    recipe_row_key_counter = Counter(
        (row["name"], tuple(sorted(json.loads(row["ingredients_main"])))) for row in dish_rows
    )
    recipe_checks = []
    for row in dish_rows:
        source = generated_by_id.get(row["source_record_id"])
        checks = {
            "source_id_known": source is not None,
            "mode": row["mode_type"] == "HOME_COOKING",
            "restaurant_null": row["restaurant_id"] is None,
            "role": row["dish_role"] in VALID_ROLES,
            "appliance": set(json.loads(row["appliance_tag"])) <= VALID_APPLIANCES,
            "mains": bool(json.loads(row["ingredients_main"])),
            "aux": bool(json.loads(row["ingredients_aux"])),
            "steps": bool((row["recipe_steps"] or "").strip()),
            "cook_minutes": isinstance(row["cook_minutes"], int) and 5 <= row["cook_minutes"] <= 120,
            "feature_null": row["feature_vector"] is None,
            "allergen_null": row["allergen_tags"] is None,
            "tagging_pending": row["tagging_status"] == "PENDING",
            "synthetic": row["is_synthetic"] == 1,
            "dataset": row["source_dataset"] == RECIPE_DATASET,
            "data_version": row["data_version"] == RECIPE_DATA_VERSION,
            "deleted_at": row["deleted_at"] is None,
            "name_matches_generator": source is not None and source["name"] == row["name"],
        }
        if source is not None:
            checks["ingredients_match_generator"] = (
                json.loads(row["ingredients_main"]) == source["ingredients_main"]
                and json.loads(row["ingredients_aux"]) == source["ingredients_aux"]
            )
        recipe_checks.append(checks)
    recipe_duplicate_names = [name for name, count in recipe_name_counter.items() if count > 1]
    recipe_duplicate_rows = [
        list(key) for key, count in recipe_row_key_counter.items() if count > 1
    ]
    recipe_role_counts = Counter(row["dish_role"] for row in dish_rows)
    recipe_cuisine_counts = Counter(row["cuisine_type"] for row in dish_rows)
    recipe_recipe_modes = Counter(row["mode_type"] for row in dish_rows)

    # —— 唯一性 / 外键 / 关联 ——
    rest_id_unique = len({row["id"] for row in restaurant_rows}) == len(restaurant_rows)
    rest_source_key_counter = Counter(
        (
            row["source_type"],
            row["campus"],
            row["source_dataset"],
            row["source_record_id"],
        )
        for row in restaurant_rows
    )
    rest_source_duplicates = [
        list(key) for key, count in rest_source_key_counter.items() if count > 1
    ]
    source_id_cross_campus = defaultdict(set)
    for row in real:
        source_id_cross_campus[
            (row["source_type"], row["source_dataset"], row["source_record_id"])
        ].add(row["campus"])
    cross_campus_duplicates = [
        list(key) for key, campuses in source_id_cross_campus.items() if len(campuses) > 1
    ]
    dish_id_unique = len({row["id"] for row in dish_rows}) == len(dish_rows)
    dish_source_key_counter = Counter(
        (row["source_dataset"], row["source_record_id"]) for row in dish_rows
    )
    dish_source_duplicates = [
        list(key) for key, count in dish_source_key_counter.items() if count > 1
    ]
    associations = [row for row in dish_rows if row["restaurant_id"] is not None]
    restaurant_ids = {row["id"] for row in restaurant_rows}
    dangling_associations = [
        row["id"] for row in associations if row["restaurant_id"] not in restaurant_ids
    ]

    # —— 抽样 30+30+30 ——
    poi_samples = []
    for campus, payload in inputs.items():
        rows = evenly_spaced(payload["rows"], SAMPLE_SIZE)
        for source in rows:
            matches = [row for row in real if row["source_record_id"] == source["id"] and row["campus"] == campus]
            if not matches:
                poi_samples.append(
                    {
                        "campus": campus,
                        "source_record_id": source["id"],
                        "ok": False,
                        "error": "db_row_missing",
                    }
                )
                continue
            poi_samples.append(compare_poi_sample(matches[0], source, campus))
    recipe_samples = []
    dish_by_source_id = {row["source_record_id"]: row for row in dish_rows}
    for source in evenly_spaced(generated, SAMPLE_SIZE):
        db_row = dish_by_source_id.get(source["source_record_id"])
        if db_row is None:
            recipe_samples.append(
                {
                    "source_record_id": source["source_record_id"],
                    "ok": False,
                    "error": "db_row_missing",
                }
            )
            continue
        recipe_samples.append(
            compare_recipe_sample(
                db_row,
                generated[generated_index[source["source_record_id"]]],
                generated_index[source["source_record_id"]],
            )
        )

    # —— 拒绝 / 失败记录 ——
    reject_records = []
    for path in args.reject_log:
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        reject_records.append(json.loads(line))
    reject_reasons = Counter(record.get("reason") for record in reject_records)

    # —— 指纹与幂等 ——
    current_fingerprint = fingerprint(restaurant_rows, dish_rows)
    if args.fingerprint_out:
        write_json(args.fingerprint_out, current_fingerprint)
    idempotency = None
    if args.idempotency_before and args.idempotency_before.exists():
        before = json.loads(args.idempotency_before.read_text(encoding="utf-8"))
        idempotency = {
            "before": before,
            "after": current_fingerprint,
            "restaurant_rows_delta": current_fingerprint["restaurant_rows"]
            - before["restaurant_rows"],
            "dish_rows_delta": current_fingerprint["dish_rows"] - before["dish_rows"],
            "association_rows_delta": current_fingerprint["association_rows"]
            - before["association_rows"],
            "restaurant_fingerprint_equal": before["restaurant_fingerprint"]
            == current_fingerprint["restaurant_fingerprint"],
            "dish_fingerprint_equal": before["dish_fingerprint"]
            == current_fingerprint["dish_fingerprint"],
            "association_fingerprint_equal": before["association_fingerprint"]
            == current_fingerprint["association_fingerprint"],
        }
        idempotency["ok"] = (
            idempotency["restaurant_rows_delta"] == 0
            and idempotency["dish_rows_delta"] == 0
            and idempotency["association_rows_delta"] == 0
            and idempotency["restaurant_fingerprint_equal"]
            and idempotency["dish_fingerprint_equal"]
            and idempotency["association_fingerprint_equal"]
        )

    demo = demo_baseline()

    # —— 逐项断言 ——
    checks = []

    def add(check_id, ok, expected=None, actual=None, detail=None):
        item = {"id": check_id, "ok": bool(ok)}
        if expected is not None:
            item["expected"] = expected
        if actual is not None:
            item["actual"] = actual
        if detail:
            item["detail"] = detail
        checks.append(item)

    add(
        "input_counts_match_s09",
        all(inputs[c]["line_count"] == EXPECTED_REAL[c] for c in EXPECTED_REAL),
        EXPECTED_REAL,
        {c: inputs[c]["line_count"] for c in inputs},
    )
    add("input_unique_ids", all(inputs[c]["duplicates"] == 0 for c in inputs), 0, {c: inputs[c]["duplicates"] for c in inputs})
    add("input_no_caotang", all(CAOTANG not in inputs[c]["campus_values"] for c in inputs), True, {c: CAOTANG in inputs[c]["campus_values"] for c in inputs})
    add("db_real_counts", real_by_campus == Counter(EXPECTED_REAL), EXPECTED_REAL, dict(real_by_campus))
    add("db_canteen_counts", canteen_by_campus == Counter(EXPECTED_CANTEEN), EXPECTED_CANTEEN, dict(canteen_by_campus))
    add(
        "canteen_separated_from_real",
        len(synthetic_restaurants) == sum(EXPECTED_CANTEEN.values())
        and all(row["source_type"] == "CANTEEN" for row in synthetic_restaurants),
        sum(EXPECTED_CANTEEN.values()),
        len(synthetic_restaurants),
    )
    add("no_unknown_campus", len(unknown_campus) == 0, 0, len(unknown_campus))
    add("restaurant_id_unique", rest_id_unique, True, rest_id_unique)
    add("restaurant_source_key_unique", not rest_source_duplicates, [], rest_source_duplicates[:10])
    add("no_cross_campus_source_id", not cross_campus_duplicates, [], cross_campus_duplicates[:10])
    add("real_poi_all_in_input", all(real_checks), True, sum(real_checks))
    add("real_poi_coords_equal_input", not coordinate_mismatch, [], coordinate_mismatch[:10])
    add("real_poi_within_3km", not distance_errors, [], distance_errors[:10])
    add("real_poi_values_match_input", not value_mismatch, [], value_mismatch[:10])
    add("canteen_all_valid", all(all(item.values()) for item in canteen_checks), True, sum(all(item.values()) for item in canteen_checks))
    add("canteen_name_pattern", canteen_name_pattern_ok, True, canteen_name_pattern_ok)
    add(
        "canteen_anchor_min_distance_ge_100m",
        all(value >= 100.0 for value in anchor_min_distances.values()),
        ">=100m",
        anchor_min_distances,
    )
    add("recipe_count", len(dish_rows) == EXPECTED_RECIPES, EXPECTED_RECIPES, len(dish_rows))
    add("recipe_unique_names", not recipe_duplicate_names, [], recipe_duplicate_names[:10])
    add("recipe_unique_rows", not recipe_duplicate_rows, [], recipe_duplicate_rows[:10])
    add("recipe_rows_all_valid", all(all(item.values()) for item in recipe_checks), True, sum(all(item.values()) for item in recipe_checks))
    add("dish_id_unique", dish_id_unique, True, dish_id_unique)
    add("dish_source_key_unique", not dish_source_duplicates, [], dish_source_duplicates[:10])
    add("home_dishes_have_no_restaurant", not associations, [], len(associations))
    add("no_dangling_associations", not dangling_associations, [], dangling_associations[:10])
    add("foreign_key_check", not foreign_key_errors, [], [list(row) for row in foreign_key_errors[:10]])
    add("sqlite_integrity_check", integrity == "ok", "ok", integrity)
    add("poi_samples_30_each", len([s for s in poi_samples if s.get("ok")]) >= 60, ">=60", len([s for s in poi_samples if s.get("ok")]))
    add("poi_samples_all_traceable", all(sample.get("ok") for sample in poi_samples), True, len(poi_samples))
    add("recipe_samples_30", len([s for s in recipe_samples if s.get("ok")]) >= 30, ">=30", len([s for s in recipe_samples if s.get("ok")]))
    add("recipe_samples_all_traceable", all(sample.get("ok") for sample in recipe_samples), True, len(recipe_samples))
    add("no_reject_or_failure_records", not reject_records, [], {"count": len(reject_records), "reasons": dict(reject_reasons)})
    add("target_db_isolated", db_path != DEMO_DB, True, str(db_path))
    add("demo_db_sha_unchanged", demo.get("sha_unchanged") is True, demo.get("expected_sha256_from_s09_r04"), demo.get("sha256"))
    add("demo_group_rooms_zero", demo.get("group_rooms_zero") is True, 0, demo.get("counts", {}).get("group_rooms"))
    add("demo_room_votes_zero", demo.get("room_votes_zero") is True, 0, demo.get("counts", {}).get("room_votes"))
    if idempotency is not None:
        add("idempotent_reimport", idempotency["ok"], True, idempotency)

    overall = all(item["ok"] for item in checks)

    # —— 写证据文件 ——
    input_manifest = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "s09_evidence": {
            "s09_r04_manifest": str(ROOT / "docs/review/stages/S09/r04/SOURCE_MANIFEST.json"),
            "s09_r04_manifest_sha256": sha256_file(ROOT / "docs/review/stages/S09/r04/SOURCE_MANIFEST.json"),
            "s09_b3_report": str(ROOT / "docs/review/clearance-codex-s09-r04/REPORT.md"),
        },
        "campus_inputs": {
            campus: {
                "path": str(payload["path"]),
                "sha256": payload["sha256"],
                "bytes": payload["bytes"],
                "line_count": payload["line_count"],
                "unique_ids": payload["unique_ids"],
                "campus_values": payload["campus_values"],
                "synthetic_values": {str(k): v for k, v in payload["synthetic_values"].items()},
                "datasets": payload["datasets"],
            }
            for campus, payload in inputs.items()
        },
        "synthetic_recipe_input": {
            "generator": "backend/scripts/import_open_recipes.py",
            "generator_sha256": sha256_file(ROOT / "backend/scripts/import_open_recipes.py"),
            "seed": GENERATOR_SEED,
            "count": len(generated),
            "canonical_jsonl_sha256": generated_sha,
            "dataset": RECIPE_DATASET,
            "data_version": RECIPE_DATA_VERSION,
        },
        "synthetic_canteen_rule": {
            "dataset": CANTEEN_DATASET,
            "data_version": CANTEEN_DATA_VERSION,
            "per_campus": 200,
            "anchors": {
                campus: [list(anchor) for anchor in anchors]
                for campus, anchors in CANTEEN_ANCHORS.items()
            },
        },
    }

    field_quality = {
        "real_poi": {
            campus: {
                "input_rows": payload["line_count"],
                "db_rows": real_by_campus.get(campus, 0),
                "rating_present_in_input": payload["line_count"] - payload["missing_rating"],
                "rating_missing_in_input": payload["missing_rating"],
                "cost_present_in_input": payload["line_count"] - payload["missing_cost"],
                "cost_missing_in_input": payload["missing_cost"],
                "tag_present_in_input": payload["line_count"] - payload["missing_tag"],
                "tag_missing_in_input": payload["missing_tag"],
                "rating_null_in_db": sum(
                    row["rating"] is None for row in real if row["campus"] == campus
                ),
                "cost_null_in_db": sum(
                    row["avg_price"] is None for row in real if row["campus"] == campus
                ),
                "tag_storage": "restaurants 无 tag 字段（SSOT §3）；原始 tag 保留在封存 JSONL，缺失计数按输入统计，不填默认值",
                "max_distance_m": round(
                    max(row["distance_meters"] for row in real if row["campus"] == campus),
                    1,
                ),
            }
            for campus, payload in inputs.items()
        },
        "synthetic_canteen": {
            "per_campus": dict(canteen_by_campus),
            "rating_null_all": all(row["rating"] is None for row in canteens),
            "price_null_all": all(row["avg_price"] is None for row in canteens),
            "coords_present_all": all(
                row["longitude"] is not None and row["latitude"] is not None
                for row in canteens
            ),
            "anchor_min_distance_to_real_poi_m": anchor_min_distances,
        },
        "synthetic_recipes": {
            "rows": len(dish_rows),
            "unique_names": len({row["name"] for row in dish_rows}),
            "unique_name_ingredient_pairs": len(recipe_row_key_counter),
            "feature_vector_null": sum(row["feature_vector"] is None for row in dish_rows),
            "tagging_status": dict(Counter(row["tagging_status"] for row in dish_rows)),
            "allergen_tags_null": sum(row["allergen_tags"] is None for row in dish_rows),
            "by_role": dict(recipe_role_counts),
            "by_cuisine": dict(recipe_cuisine_counts),
            "by_mode_type": dict(recipe_recipe_modes),
            "mode_types": list(recipe_recipe_modes),
        },
    }

    reject_counts = Counter(
        (record.get("kind"), record.get("campus")) for record in reject_records
    )
    dedup_report = {
        "real_poi": {
            campus: {
                "input_rows": payload["line_count"],
                "unique_source_ids": payload["unique_ids"],
                "duplicates_in_input": payload["duplicates"],
                "valid_rows": real_by_campus.get(campus, 0),
                "imported_rows": real_by_campus.get(campus, 0),
                "rejected_rows": reject_counts.get(("AMAP_POI", campus), 0),
                "db_source_key_duplicates": len(
                    [
                        key
                        for key in rest_source_duplicates
                        if key[1] == campus and key[0] == "AMAP_POI"
                    ]
                ),
            }
            for campus, payload in inputs.items()
        },
        "synthetic_canteen": {
            campus: {
                "planned": 200,
                "generated": 200,
                "imported_rows": canteen_by_campus.get(campus, 0),
                "rejected_rows": reject_counts.get(("CANTEEN", campus), 0),
                "duplicates": 0,
            }
            for campus in EXPECTED_CANTEEN
        },
        "synthetic_recipes": {
            "generated": len(generated),
            "unique_source_ids": len({row["source_record_id"] for row in generated}),
            "unique_names": len({row["name"] for row in generated}),
            "imported_rows": len(dish_rows),
            "duplicate_names": len(recipe_duplicate_names),
            "duplicate_row_keys": len(recipe_duplicate_rows),
            "rejected_rows": reject_counts.get(("SYNTHETIC_RECIPE", None), 0),
        },
        "reject_logs": {
            "records": len(reject_records),
            "reasons": dict(reject_reasons),
        },
    }

    db_inventory = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "target_db": {
            "path": str(db_path),
            "sha256": sha256_file(db_path),
            "bytes": db_path.stat().st_size,
            "isolated_from_demo": db_path != DEMO_DB,
            "sqlite_integrity": integrity,
            "foreign_key_violations": [list(row) for row in foreign_key_errors],
            "table_counts": table_counts,
            "columns": columns,
            "indexes": indexes,
        },
        "demo_db": demo,
        "logical_counts": {
            "real_poi_by_campus": dict(real_by_campus),
            "canteen_by_campus": dict(canteen_by_campus),
            "recipes": len(dish_rows),
            "recipe_unique_names": len(recipe_name_counter),
        },
    }

    validation = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "step": "S10",
        "script": "backend/scripts/verify_s10_import.py",
        "target_db": str(db_path),
        "target_db_sha256": sha256_file(db_path),
        "demo_db_sha256": demo.get("sha256"),
        "checks": checks,
        "overall_ok": overall,
        "counts": {
            "real_poi": dict(real_by_campus),
            "canteen": dict(canteen_by_campus),
            "recipes": len(dish_rows),
            "recipe_unique_names": len(recipe_name_counter),
        },
    }

    write_json(out / "input_manifest.json", input_manifest)
    write_json(out / "field_quality.json", field_quality)
    write_json(out / "dedup_report.json", dedup_report)
    write_json(out / "db_inventory.json", db_inventory)
    write_json(out / "validation.json", validation)
    write_json(out / "sample_poi_mapping.json", {"samples": poi_samples})
    write_json(out / "sample_recipe_mapping.json", {"samples": recipe_samples})
    if idempotency is not None:
        write_json(out / "idempotency_report.json", idempotency)

    if args.import_summary:
        runs = []
        for path in args.import_summary:
            if path.exists():
                runs.append({"path": str(path), "payload": json.loads(path.read_text(encoding="utf-8"))})
        write_json(
            out / "import_summary.json",
            {
                "note": "导入脚本运行记录；验收断言以 validation.json 的库内重算为准",
                "runs": runs,
            },
        )

    print(
        json.dumps(
            {
                "overall_ok": overall,
                "failed": [item["id"] for item in checks if not item["ok"]],
                "real_poi": dict(real_by_campus),
                "canteen": dict(canteen_by_campus),
                "recipes": len(dish_rows),
                "recipe_unique_names": len(recipe_name_counter),
                "demo_sha_unchanged": demo.get("sha_unchanged"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
