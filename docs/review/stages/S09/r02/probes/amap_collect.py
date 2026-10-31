"""S09/r02 高德真实 POI 只读采集（不写数据库，不落 Key）。

- Key 只从环境变量 AMAP_API_KEY 读取；输出中 key 永远为 <redacted>。
- 地名搜索固定“西安思源学院”；3km；types=050000（餐饮服务）。
- 单组参数最多 200 条，因此用 800m 半径网格覆盖 3km，并对 count>200 的格子递归细分。
- 去重键：poi.id；最终按与中心的 haversine 距离 <=3000m 过滤。
- 输出：data/amap_geocode.json、data/amap_collection.json、data/amap_pois.jsonl、logs/04_amap_collect.log
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"
LOGS = PACK / "logs"
DEFAULT_ADDRESS = "西安思源学院"
RADIUS_M = 3000
CELL_RADIUS_M = 800
STEP_M = 1000
MAX_DEPTH = 3
MIN_RADIUS_M = 100
MAX_PAGES = 8
OFFSET = 25
QPS_SLEEP = 0.7


def haversine_m(lng1, lat1, lng2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def meters_to_deg(lat):
    dlat = STEP_M / 111320.0
    dlon = STEP_M / (111320.0 * math.cos(math.radians(lat)))
    return dlat, dlon


def call_place(key, lat, lng, radius, page):
    params = {
        "key": key,
        "location": f"{lng:.6f},{lat:.6f}",
        "radius": str(radius),
        "types": "050000",
        "offset": str(OFFSET),
        "page": str(page),
        "extensions": "all",
    }
    last_error = None
    for attempt in range(4):
        try:
            r = requests.get("https://restapi.amap.com/v3/place/around", params=params, timeout=25)
            body = r.json()
            if body.get("status") == "1" or body.get("info") != "CUQPS_HAS_EXCEEDED_THE_LIMIT":
                return r.status_code, body
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(1.5 * (attempt + 1))
    reason = str(last_error or "request failed").replace(key, "<redacted>")[:200]
    return 0, {"status": "0", "info": "REQUEST_ERROR", "reason": reason}


def fetch_cell(key, lat, lng, radius, depth, label, calls, errors):
    collected = []
    status, body = call_place(key, lat, lng, radius, 1)
    calls.append(
        {
            "cell": label,
            "depth": depth,
            "center": f"{lng:.6f},{lat:.6f}",
            "radius": radius,
            "page": 1,
            "http": status,
            "api_status": body.get("status"),
            "info": body.get("info"),
            "count": int(body.get("count") or 0),
            "returned": len(body.get("pois") or []),
        }
    )
    if body.get("status") != "1":
        errors.append({"cell": label, "page": 1, "status": status, "body": body})
        return collected, 0, False
    count = int(body.get("count") or 0)
    collected.extend(body.get("pois") or [])
    if count == 0:
        return collected, 0, True
    if count > 200:
        # 同参数最多 200 条，当前格子不完整
        if depth < MAX_DEPTH:
            return collected, count, False
        return collected, count, False
    pages = min(MAX_PAGES, math.ceil(count / OFFSET))
    for page in range(2, pages + 1):
        time.sleep(QPS_SLEEP)
        status, body = call_place(key, lat, lng, radius, page)
        returned = len(body.get("pois") or [])
        calls.append(
            {
                "cell": label,
                "depth": depth,
                "center": f"{lng:.6f},{lat:.6f}",
                "radius": radius,
                "page": page,
                "http": status,
                "api_status": body.get("status"),
                "info": body.get("info"),
                "count": int(body.get("count") or 0),
                "returned": returned,
            }
        )
        if body.get("status") != "1":
            errors.append({"cell": label, "page": page, "status": status, "body": body})
            break
        collected.extend(body.get("pois") or [])
        if returned < OFFSET:
            break
    return collected, count, True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default=DEFAULT_ADDRESS)
    parser.add_argument("--campus", default="SIYUAN")
    parser.add_argument("--prefix", default="amap")
    parser.add_argument("--require-text", default="")
    parser.add_argument("--forbid-text", default="")
    parser.add_argument("--city", default="西安")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
    key = os.getenv("AMAP_API_KEY", "").strip()
    collection_path = DATA / f"{args.prefix}_collection.json"
    geocode_path = DATA / f"{args.prefix}_geocode.json"
    result = {
        "checked_at": checked_at,
        "address": args.address,
        "campus": args.campus,
        "key_present": bool(key),
        "key": "<redacted>",
        "radius_m": RADIUS_M,
        "types": "050000",
        "status": "BLOCKED",
    }
    if not key:
        result["reason"] = "AMAP_API_KEY missing; no real geocode/POI call executed"
        collection_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    s = requests.Session()
    s.trust_env = True
    # 1) 地名搜索（异常不输出含 key 的 URL）
    try:
        geo_resp = s.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"key": key, "address": args.address, "city": args.city},
            timeout=25,
        )
        geo_body = geo_resp.json()
    except Exception as exc:  # noqa: BLE001
        result.update(
            {
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "reason": str(exc).replace(key, "<redacted>")[:300],
            }
        )
        geocode_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        collection_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    geos = geo_body.get("geocodes") or []
    geocode_result = {
        "checked_at": checked_at,
        "address": args.address,
        "city": args.city,
        "key_present": bool(key),
        "key": "<redacted>",
        "endpoint": "https://restapi.amap.com/v3/geocode/geo",
        "http_status": geo_resp.status_code,
        "api": {k: geo_body.get(k) for k in ("status", "info", "infocode", "count")},
        "request": {"address": args.address, "city": args.city, "key": "<redacted>"},
        "results": [
            {k: g.get(k) for k in ("formatted_address", "province", "city", "district", "location", "level", "adcode")}
            for g in geos[:5]
        ],
    }
    result["geocode"] = geocode_result
    if not geos or not geos[0].get("location"):
        result["status"] = "ERROR"
        result["reason"] = "geocode returned no location"
        geocode_path.write_text(json.dumps(geocode_result, ensure_ascii=False, indent=2), encoding="utf-8")
        collection_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    fmt = str(geos[0].get("formatted_address") or "")
    geocode_result.update({"status": "OK", "center_gcj02": geos[0]["location"], "center_source": "AMap geocode/geo 实际返回"})
    if args.forbid_text and (args.forbid_text in fmt or args.forbid_text in args.address):
        geocode_result["status"] = "NEED_USER_DECISION"
        geocode_result["reason"] = f"高德返回包含 {args.forbid_text}，按要求停止并询问用户"
    elif args.require_text and args.require_text not in fmt:
        geocode_result["status"] = "NEED_USER_DECISION"
        geocode_result["reason"] = f"高德返回地址未明确包含 {args.require_text}，停止并询问用户"
    geocode_path.write_text(json.dumps(geocode_result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["geocode"] = geocode_result
    if geocode_result["status"] != "OK":
        result["status"] = geocode_result["status"]
        result["reason"] = geocode_result.get("reason")
        collection_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    lng, lat = [float(x) for x in geos[0]["location"].split(",")]
    result["center_gcj02"] = {"lng": lng, "lat": lat, "location": geos[0]["location"]}

    # 1b) 直接 3km 查询的 count 与分页上限（同参数最多 200）
    direct_pages = []
    for page in (1, 8, 9):
        status, body = call_place(key, lat, lng, RADIUS_M, page)
        direct_pages.append({
            "page": page,
            "http": status,
            "api_status": body.get("status"),
            "info": body.get("info"),
            "count": int(body.get("count") or 0),
            "returned": len(body.get("pois") or []),
        })
        time.sleep(QPS_SLEEP)
    result["direct_3km_query"] = {
        "count": direct_pages[0]["count"],
        "pages": direct_pages,
        "note": "同参数翻页最多 200 条；page 9 起为空。count 可能被 API 截断，不能直接当 3km 总量。",
    }

    # 2) 网格覆盖
    dlat, dlon = meters_to_deg(lat)
    centers = []
    steps = int(RADIUS_M / STEP_M) + 1
    for iy in range(-steps, steps + 1):
        for ix in range(-steps, steps + 1):
            clat = lat + iy * dlat
            clng = lng + ix * dlon
            if haversine_m(lng, lat, clng, clat) <= RADIUS_M + CELL_RADIUS_M:
                centers.append((clat, clng, CELL_RADIUS_M, 0, f"g{iy}_{ix}"))
    calls, errors, pois = [], [], []
    incomplete = []
    queue = list(centers)
    processed = 0
    while queue:
        clat, clng, radius, depth, label = queue.pop(0)
        got, total, complete = fetch_cell(key, clat, clng, radius, depth, label, calls, errors)
        pois.extend(got)
        processed += 1
        if not complete:
            if total > 200 and depth < MAX_DEPTH and radius > MIN_RADIUS_M:
                sub_radius = max(MIN_RADIUS_M, radius // 2)
                sub_step_lat = (radius / 2) / 111320.0
                sub_step_lon = (radius / 2) / (111320.0 * math.cos(math.radians(clat)))
                for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                    queue.append(
                        (
                            clat + sy * sub_step_lat,
                            clng + sx * sub_step_lon,
                            sub_radius,
                            depth + 1,
                            f"{label}_{sx}_{sy}",
                        )
                    )
            else:
                incomplete.append({"cell": label, "count": total, "depth": depth})
        time.sleep(QPS_SLEEP)

    # 3) 去重 + 3km 过滤
    unique = {}
    for p in pois:
        pid = p.get("id")
        if not pid:
            continue
        unique[pid] = p
    filtered = []
    outside = 0
    for pid, p in unique.items():
        try:
            plng, plat = [float(x) for x in str(p.get("location", "")).split(",")]
        except Exception:
            continue
        dist = haversine_m(lng, lat, plng, plat)
        if dist <= RADIUS_M:
            p = dict(p)
            p["_distance_m"] = round(dist, 1)
            filtered.append(p)
        else:
            outside += 1
    filtered.sort(key=lambda x: (x.get("_distance_m", 1e9), x.get("id", "")))
    non_dining = [p for p in filtered if not str(p.get("typecode") or "").startswith("05")]
    dining = [p for p in filtered if str(p.get("typecode") or "").startswith("05")]

    # 4) 统计
    from collections import Counter
    def typecode(p):
        return str(p.get("typecode") or "")
    category = Counter(typecode(p)[:4] for p in dining)
    def _biz(p):
        b = p.get("biz_ext")
        return b if isinstance(b, dict) else {}
    rating_present = sum(1 for p in dining if _biz(p).get("rating") not in (None, "", []))
    cost_present = sum(1 for p in dining if _biz(p).get("cost") not in (None, "", []))
    tag_present = sum(1 for p in dining if p.get("tag") not in (None, "", []))
    missing_rating = len(dining) - rating_present
    missing_cost = len(dining) - cost_present
    tag_missing = len(dining) - tag_present
    result.update(
        {
            "status": "OK",
            "query_time": checked_at,
            "cells_planned": len(centers),
            "cells_processed": processed,
            "api_calls": len(calls),
            "errors": errors,
            "incomplete_cells": incomplete,
            "raw_pois": len(pois),
            "unique_pois": len(unique),
            "outside_3km": outside,
            "within_3km_before_typecode_filter": len(filtered),
            "non_dining_excluded": len(non_dining),
            "real_poi_count": len(dining),
            "campus": args.campus,
            "synthetic_canteen_count": 200,
            "synthetic_canteen_note": "每个校区单独 200 个合成食堂目标；S09 不导入，不计入 real_poi_count；S10 写入时 is_synthetic=1。",
            "total_restaurants_target_if_200_canteen": len(dining) + 200,
            "target_1500_met": len(dining) >= 1500,
            "target_shortfall": max(0, 1500 - len(dining)),
            "rating_present": rating_present,
            "rating_missing": missing_rating,
            "cost_present": cost_present,
            "cost_missing": missing_cost,
            "tag_present": tag_present,
            "tag_missing": tag_missing,
            "missing_rating": missing_rating,
            "missing_cost": missing_cost,
            "typecode_prefix_counts": dict(sorted(category.items())),
            "dedup_rule": "poi.id 唯一；最终按中心 haversine <=3000m 过滤；跨格子重复只保留一条",
            "sample": [
                {k: p.get(k) for k in ("id", "name", "type", "typecode", "address", "location", "distance", "tag", "biz_ext", "_distance_m")}
                for p in dining[:5]
            ],
        }
    )
    result["source_dataset"] = "amap_place_around_20261025"
    collection_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    raw_path = DATA / f"{args.prefix}_pois.raw.jsonl"
    with raw_path.open("w", encoding="utf-8") as handle:
        for p in dining:
            row = dict(p)
            row["campus"] = args.campus
            row["is_synthetic"] = 0
            row["source_dataset"] = "amap_place_around_20261025"
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
