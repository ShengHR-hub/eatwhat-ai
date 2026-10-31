"""小样导入映射核对：源记录 → 入库字段（POI 40 条、菜谱 60 条）。"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DB = ROOT / "backend" / "eatwhat_g2_s10_smoke.db"
INPUTS = {
    "SIYUAN": ROOT / "docs/review/stages/S09/r02/data/amap_pois.jsonl",
    "JIANDA_YANTA": ROOT / "docs/review/stages/S09/r02/data/amap_jianda_pois.jsonl",
}
OUT = Path(__file__).resolve().parent / "smoke_mapping.json"
CENTERS = {"SIYUAN": (109.078487, 34.234818), "JIANDA_YANTA": (108.967153, 34.236991)}


def haversine(lon1, lat1, lon2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse(value):
    if value in (None, "", []) or value == []:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    poi_rows = []
    for campus, path in INPUTS.items():
        source_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()][:20]
        for source in source_rows:
            db_row = connection.execute(
                "SELECT * FROM restaurants WHERE campus=? AND source_record_id=?",
                (campus, source["id"]),
            ).fetchone()
            lon, lat = map(float, source["location"].split(","))
            distance = haversine(lon, lat, *CENTERS[campus])
            checks = {
                "row_present": db_row is not None,
            }
            if db_row:
                checks.update(
                    {
                        "name": db_row["name"] == source["name"],
                        "longitude": abs(db_row["longitude"] - lon) < 1e-6,
                        "latitude": abs(db_row["latitude"] - lat) < 1e-6,
                        "gcj02_unchanged": abs(db_row["longitude"] - lon) < 1e-6
                        and abs(db_row["latitude"] - lat) < 1e-6,
                        "distance_within_1m": abs(db_row["distance_meters"] - distance) <= 1.0,
                        "campus": db_row["campus"] == campus,
                        "source_type": db_row["source_type"] == "AMAP_POI",
                        "is_synthetic_false": db_row["is_synthetic"] == 0,
                        "dataset": db_row["source_dataset"] == "amap_place_around_20261025",
                        "rating_matches_source": (
                            (parse(source.get("rating")) is None and db_row["rating"] is None)
                            or (
                                parse(source.get("rating")) is not None
                                and abs(db_row["rating"] - parse(source.get("rating"))) < 1e-6
                            )
                        ),
                        "cost_matches_source": (
                            (parse(source.get("cost")) is None and db_row["avg_price"] is None)
                            or (
                                parse(source.get("cost")) is not None
                                and abs(db_row["avg_price"] - parse(source.get("cost"))) < 1e-6
                            )
                        ),
                    }
                )
            poi_rows.append(
                {
                    "campus": campus,
                    "source_record_id": source["id"],
                    "source": {
                        "name": source["name"],
                        "location": source["location"],
                        "rating": source.get("rating"),
                        "cost": source.get("cost"),
                        "tag": source.get("tag"),
                    },
                    "db": dict(db_row) if db_row else None,
                    "checks": checks,
                    "ok": all(checks.values()),
                }
            )

    recipe_rows = []
    for row in connection.execute(
        "SELECT * FROM dishes_and_recipes ORDER BY source_record_id LIMIT 60"
    ).fetchall():
        checks = {
            "mode_home": row["mode_type"] == "HOME_COOKING",
            "restaurant_null": row["restaurant_id"] is None,
            "role": row["dish_role"] in {"MEAT", "VEG", "SOUP", "ONE_MEAL"},
            "appliance": all(
                item in {"炒锅", "电饭煲", "空气炸锅", "免开火凉拌", "一锅出"}
                for item in json.loads(row["appliance_tag"])
            ),
            "mains": bool(json.loads(row["ingredients_main"])),
            "steps": bool((row["recipe_steps"] or "").strip()),
            "minutes": 5 <= int(row["cook_minutes"]) <= 120,
            "synthetic": row["is_synthetic"] == 1,
            "dataset": row["source_dataset"] == "synthetic_recipe_v1",
            "tagging_pending": row["tagging_status"] == "PENDING",
            "feature_null": row["feature_vector"] is None,
            "allergen_null": row["allergen_tags"] is None,
        }
        recipe_rows.append(
            {
                "source_record_id": row["source_record_id"],
                "name": row["name"],
                "cook_minutes": row["cook_minutes"],
                "dish_role": row["dish_role"],
                "appliance": json.loads(row["appliance_tag"]),
                "mains": json.loads(row["ingredients_main"]),
                "aux": json.loads(row["ingredients_aux"]),
                "checks": checks,
                "ok": all(checks.values()),
            }
        )
    connection.close()

    payload = {
        "db": str(DB),
        "poi_sampled": len(poi_rows),
        "poi_ok": sum(1 for row in poi_rows if row["ok"]),
        "recipe_sampled": len(recipe_rows),
        "recipe_ok": sum(1 for row in recipe_rows if row["ok"]),
        "poi_rows": poi_rows,
        "recipe_rows": recipe_rows,
        "ok": len(poi_rows) >= 30
        and len(recipe_rows) >= 30
        and all(row["ok"] for row in poi_rows)
        and all(row["ok"] for row in recipe_rows),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("poi_sampled", "poi_ok", "recipe_sampled", "recipe_ok", "ok")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
