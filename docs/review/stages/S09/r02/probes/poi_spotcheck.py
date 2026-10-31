"""对已脱敏 POI 做抽查：前 20 条、类型/距离分布、同店多 ID、3km 越界检查。"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"

TYPE_LABELS = {
    "0500": "餐饮服务",
    "0501": "中餐厅",
    "0502": "外国餐厅",
    "0503": "快餐厅",
    "0504": "休闲餐饮场所",
    "0505": "咖啡厅",
    "0506": "茶艺馆",
    "0507": "冷饮店",
    "0508": "糕饼店",
    "0509": "甜品店",
}
BANDS = [
    (0, 100),
    (100, 300),
    (300, 500),
    (500, 1000),
    (1000, 1500),
    (1500, 2000),
    (2000, 2500),
    (2500, 3000.001),
]


def haversine_m(lng1, lat1, lng2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def norm(value):
    return "".join(str(value or "").split()).replace("（", "(").replace("）", ")")


def base_name(name):
    text = norm(name)
    return text.split("(")[0] or text


def pair_distance(a, b):
    alng, alat = [float(x) for x in str(a.get("location")).split(",")]
    blng, blat = [float(x) for x in str(b.get("location")).split(",")]
    return haversine_m(alng, alat, blng, blat)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=str(DATA / "amap_jianda_pois.jsonl"))
    parser.add_argument("--center", default="108.967153,34.236991")
    parser.add_argument("--out", default=str(DATA / "jianda_poi_spotcheck.json"))
    parser.add_argument("--label", default="JIANDA_YANTA")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    clng, clat = [float(x) for x in args.center.split(",")]
    rows = []
    invalid = 0
    for line in Path(args.file).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            lng, lat = [float(x) for x in str(row.get("location")).split(",")]
        except Exception:
            invalid += 1
            continue
        row["_calc_distance_m"] = round(haversine_m(clng, clat, lng, lat), 1)
        rows.append(row)

    distances = sorted(r["_calc_distance_m"] for r in rows)
    bands = {}
    for low, high in BANDS:
        values = [d for d in distances if low <= d < high]
        bands[f"{int(low)}-{int(min(high, 3000))}m"] = len(values)
    outside = [r for r in rows if r["_calc_distance_m"] > 3000.5]
    max_distance = distances[-1] if distances else None
    median_distance = statistics.median(distances) if distances else None

    type_counts = Counter()
    full_type_counts = Counter()
    for row in rows:
        code = str(row.get("typecode") or "")[:4]
        type_counts[code] += 1
        full_type_counts[str(row.get("type") or "")] += 1
    type_distribution = [
        {"typecode_prefix": code, "label": TYPE_LABELS.get(code, "未映射"), "count": count}
        for code, count in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    top_full_types = [
        {"type": name, "count": count}
        for name, count in full_type_counts.most_common(10)
    ]

    by_name = defaultdict(list)
    by_name_addr = defaultdict(list)
    by_location = defaultdict(list)
    by_base = defaultdict(list)
    for row in rows:
        name = norm(row.get("name"))
        by_name[name].append(row)
        by_name_addr[(name, norm(row.get("address")))].append(row)
        by_location[str(row.get("location"))].append(row)
        by_base[base_name(row.get("name"))].append(row)

    exact_name_groups = [
        {
            "name": group[0].get("name"),
            "count": len(group),
            "ids": [r.get("id") for r in group],
            "distances_m": [r["_calc_distance_m"] for r in group],
        }
        for group in by_name.values()
        if len(group) > 1
    ]
    exact_name_addr_groups = [
        {
            "name": group[0].get("name"),
            "address": group[0].get("address"),
            "count": len(group),
            "ids": [r.get("id") for r in group],
            "distances_m": [r["_calc_distance_m"] for r in group],
        }
        for group in by_name_addr.values()
        if len(group) > 1
    ]
    same_location_groups = [
        {
            "location": group[0].get("location"),
            "count": len(group),
            "ids": [r.get("id") for r in group],
            "names": [r.get("name") for r in group],
        }
        for group in by_location.values()
        if len(group) > 1
    ]
    close_same_name = []
    exact_name_pairs = []
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                d = pair_distance(a, b)
                pair = {
                    "name": a.get("name"),
                    "ids": [a.get("id"), b.get("id")],
                    "distance_between_m": round(d, 1),
                }
                exact_name_pairs.append(pair)
                if d <= 50:
                    close_same_name.append(pair)
    exact_name_pair_thresholds = {
        f"<={limit}m": sum(1 for p in exact_name_pairs if p["distance_between_m"] <= limit)
        for limit in (10, 50, 100, 200)
    }
    exact_name_pairs_within_100m = [
        p for p in exact_name_pairs if p["distance_between_m"] <= 100
    ]
    close_base_name = []
    for base, group in by_base.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                d = pair_distance(a, b)
                if d <= 200 and norm(a.get("name")) != norm(b.get("name")):
                    close_base_name.append(
                        {
                            "base_name": base,
                            "names": [a.get("name"), b.get("name")],
                            "ids": [a.get("id"), b.get("id")],
                            "distance_between_m": round(d, 1),
                        }
                    )

    first20 = []
    for row in sorted(rows, key=lambda r: r["_calc_distance_m"])[:20]:
        first20.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "type": row.get("type"),
                "typecode": row.get("typecode"),
                "distance_m": row["_calc_distance_m"],
                "rating": row.get("rating"),
                "cost": row.get("cost"),
                "address": row.get("address"),
            }
        )

    result = {
        "label": args.label,
        "source_file": str(args.file),
        "center_gcj02": args.center,
        "row_count": len(rows),
        "invalid_location_rows": invalid,
        "unique_ids": len({r.get("id") for r in rows}),
        "distance_summary": {
            "min_m": distances[0] if distances else None,
            "median_m": median_distance,
            "max_m": max_distance,
        },
        "outside_3km": {
            "count": len(outside),
            "examples": [
                {"id": r.get("id"), "name": r.get("name"), "distance_m": r["_calc_distance_m"]}
                for r in sorted(outside, key=lambda x: -x["_calc_distance_m"])[:5]
            ],
        },
        "distance_bands": bands,
        "typecode_distribution": type_distribution,
        "top_full_types": top_full_types,
        "duplicate_checks": {
            "exact_name_groups": exact_name_groups,
            "exact_name_and_address_groups": exact_name_addr_groups,
            "same_location_groups": same_location_groups,
            "same_exact_name_pair_thresholds": exact_name_pair_thresholds,
            "same_exact_name_within_50m": close_same_name,
            "same_exact_name_within_100m": exact_name_pairs_within_100m,
            "same_base_name_within_200m": close_base_name,
        },
        "first_20_by_distance": first20,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "label": args.label,
        "row_count": result["row_count"],
        "unique_ids": result["unique_ids"],
        "invalid_location_rows": invalid,
        "distance_summary": result["distance_summary"],
        "outside_3km": len(outside),
        "distance_bands": bands,
        "exact_name_duplicate_groups": len(exact_name_groups),
        "exact_name_addr_duplicate_groups": len(exact_name_addr_groups),
        "same_location_groups": len(same_location_groups),
        "same_exact_name_within_50m": len(close_same_name),
        "same_base_name_within_200m": len(close_base_name),
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
