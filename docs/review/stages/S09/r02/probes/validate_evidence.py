"""S09/r02 证据自校验：JSON、AMap 数量、SSOT 口径、台账、DB 保护、Key 不泄漏。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def haversine_m(lng1, lat1, lng2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def check_poi_file(path: Path, cx: float, cy: float, expected: int, campus: str) -> dict:
    ids = set()
    lines = 0
    outside = 0
    missing_flags = 0
    forbidden = {"tel", "email", "photos", "website", "shopinfo", "reviews"}
    forbidden_hits = set()
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                lines += 1
                row = json.loads(line)
                ids.add(row.get("id"))
                forbidden_hits.update(forbidden & set(row))
                if row.get("is_synthetic") != 0 or not row.get("source_dataset") or row.get("campus") != campus:
                    missing_flags += 1
                try:
                    lng, lat = [float(v) for v in str(row.get("location")).split(",")]
                except Exception:
                    outside += 1
                    continue
                if haversine_m(cx, cy, lng, lat) > 3000.5:
                    outside += 1
    return {
        "ok": lines == expected and len(ids) == expected and outside == 0 and missing_flags == 0 and not forbidden_hits,
        "lines": lines,
        "expected": expected,
        "unique_ids": len(ids),
        "outside_3km": outside,
        "missing_synthetic_source_or_campus": missing_flags,
        "forbidden_fields": sorted(forbidden_hits),
        "campus": campus,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    checks = {}

    # 1) JSON 可解析
    bad = []
    for p in sorted(DATA.glob("*.json")):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            bad.append({"path": p.name, "error": repr(exc)})
    checks["json_parse"] = {"ok": not bad, "bad": bad}

    # 2) Key 不落盘：读环境变量后搜索 r02 全包；不输出 Key
    key = os.getenv("AMAP_API_KEY", "").strip()
    leaked = []
    if key:
        for p in PACK.rglob("*"):
            if p.is_file():
                try:
                    if key in p.read_text(encoding="utf-8", errors="ignore"):
                        leaked.append(str(p.relative_to(PACK)).replace("\\", "/"))
                except Exception:
                    pass
    checks["key_not_in_evidence"] = {"ok": not leaked, "key_present_in_env": bool(key), "leaked_files": leaked}

    # 3) 高德结果
    geo = json.loads((DATA / "amap_geocode.json").read_text(encoding="utf-8"))
    coll = json.loads((DATA / "amap_collection.json").read_text(encoding="utf-8"))
    pag = json.loads((DATA / "amap_pagination_probe.json").read_text(encoding="utf-8"))
    center_raw = geo.get("center_gcj02")
    center = center_raw if isinstance(center_raw, dict) else {"location": center_raw}
    pages = {x["page"]: x for x in pag["pages"]}
    checks["amap_geocode"] = {
        "ok": bool(center.get("location")) and center.get("location") == "109.078487,34.234818" and pages.get(1, {}).get("count") == "600",
        "center": center,
        "page1_count": pages.get(1, {}).get("count"),
        "page9_returned": pages.get(9, {}).get("returned"),
    }
    checks["amap_counts"] = {
        "ok": coll.get("real_poi_count") == 605
        and coll.get("synthetic_canteen_count") == 200
        and coll.get("total_restaurants_target_if_200_canteen") == 805
        and coll.get("cells_planned") == 45
        and coll.get("cells_processed") == 61
        and coll.get("api_calls") == 133
        and coll.get("errors") == []
        and coll.get("incomplete_cells") == [],
        "real_poi_count": coll.get("real_poi_count"),
        "synthetic_canteen_count": coll.get("synthetic_canteen_count"),
        "combined": coll.get("total_restaurants_target_if_200_canteen"),
        "direct_count": coll.get("direct_3km_query", {}).get("count"),
        "cells_planned": coll.get("cells_planned"),
        "cells_processed": coll.get("cells_processed"),
        "api_calls": coll.get("api_calls"),
        "target_1500_met": coll.get("target_1500_met"),
        "target_shortfall": coll.get("target_shortfall"),
        "d03_decision": coll.get("d03_decision"),
    }

    # 4) POI 文件行数/唯一/3km
    checks["poi_file"] = check_poi_file(
        DATA / "amap_pois.jsonl", 109.078487, 34.234818, 605, "SIYUAN"
    )

    # 4b) 建大雁塔试抓证据
    jg = DATA / "amap_jianda_geocode.json"
    jc = DATA / "amap_jianda_collection.json"
    jp = DATA / "amap_jianda_pois.jsonl"
    checks["jianda"] = {"ok": False, "reason": "missing Jianda evidence files"}
    if jg.exists() and jc.exists():
        geo_j = json.loads(jg.read_text(encoding="utf-8"))
        coll_j = json.loads(jc.read_text(encoding="utf-8"))
        center_j = (coll_j.get("center_gcj02") or {}).get("location")
        jianda_poi = check_poi_file(jp, 108.967153, 34.236991, 6659, "JIANDA_YANTA")
        checks["jianda"] = {
            "ok": geo_j.get("status") == "OK"
            and center_j == "108.967153,34.236991"
            and coll_j.get("status") == "OK"
            and coll_j.get("campus") == "JIANDA_YANTA"
            and coll_j.get("real_poi_count") == 6659
            and coll_j.get("synthetic_canteen_count") == 200
            and coll_j.get("total_restaurants_target_if_200_canteen") == 6859
            and coll_j.get("errors") == []
            and coll_j.get("incomplete_cells") == []
            and jianda_poi.get("ok"),
            "geocode": geo_j.get("status"),
            "center_gcj02": center_j,
            "http": geo_j.get("http_status"),
            "address": [x.get("formatted_address") for x in (geo_j.get("results") or [])[:1]],
            "real_poi_count": coll_j.get("real_poi_count"),
            "synthetic_canteen_count": coll_j.get("synthetic_canteen_count"),
            "combined": coll_j.get("total_restaurants_target_if_200_canteen"),
            "api_calls": coll_j.get("api_calls"),
            "incomplete_cells": coll_j.get("incomplete_cells"),
            "target_1500_met": coll_j.get("target_1500_met"),
            "poi_file": jianda_poi,
        }

    # 4c) 字段有值/缺失数与 C10 未绘制数
    fs = json.loads((DATA / "poi_field_stats.json").read_text(encoding="utf-8"))
    field_ok = True
    field_detail = {}
    for campus, poi_name, collection_name in (
        ("SIYUAN", "amap_pois.jsonl", "amap_collection.json"),
        ("JIANDA_YANTA", "amap_jianda_pois.jsonl", "amap_jianda_collection.json"),
    ):
        rows = [
            json.loads(line)
            for line in (DATA / poi_name).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        stats = fs.get(campus, {})
        coll_file = json.loads((DATA / collection_name).read_text(encoding="utf-8"))
        expected = {"total": len(rows)}
        for field in ("rating", "cost", "tag"):
            present = sum(1 for row in rows if row.get(field) not in (None, "", []))
            expected[f"{field}_present"] = present
            expected[f"{field}_missing"] = len(rows) - present
        for key, value in expected.items():
            if stats.get(key) != value:
                field_ok = False
            if key in ("rating_present", "rating_missing", "cost_present", "cost_missing", "tag_present", "tag_missing") and coll_file.get(key) != value:
                field_ok = False
        if stats.get("c10_poi_only_not_plotted_no_rating") != expected["rating_missing"]:
            field_ok = False
        field_detail[campus] = {"expected": expected, "reported": stats, "collection": {k: coll_file.get(k) for k in ("rating_present", "rating_missing", "cost_present", "cost_missing", "tag_present", "tag_missing")}}
    checks["poi_field_stats"] = {"ok": field_ok, "detail": field_detail}

    # 4d) 建大 POI 抽查：前 20、分段、同店/越界
    sc = json.loads((DATA / "jianda_poi_spotcheck.json").read_text(encoding="utf-8"))
    dup = sc.get("duplicate_checks", {})
    band_total = sum((sc.get("distance_bands") or {}).values())
    spot_ok = (
        sc.get("row_count") == 6659
        and sc.get("unique_ids") == 6659
        and sc.get("invalid_location_rows") == 0
        and (sc.get("outside_3km") or {}).get("count") == 0
        and (sc.get("distance_summary") or {}).get("max_m", 99999) <= 3000.5
        and len(sc.get("first_20_by_distance") or []) == 20
        and band_total == 6659
        and not dup.get("exact_name_and_address_groups")
        and (dup.get("same_exact_name_pair_thresholds") or {}).get("<=50m") == 4
        and (dup.get("same_exact_name_pair_thresholds") or {}).get("<=100m") == 5
    )
    checks["jianda_spotcheck"] = {
        "ok": spot_ok,
        "row_count": sc.get("row_count"),
        "unique_ids": sc.get("unique_ids"),
        "invalid_location_rows": sc.get("invalid_location_rows"),
        "outside_3km": (sc.get("outside_3km") or {}).get("count"),
        "max_m": (sc.get("distance_summary") or {}).get("max_m"),
        "first_20_count": len(sc.get("first_20_by_distance") or []),
        "band_total": band_total,
        "same_name_50m": (dup.get("same_exact_name_pair_thresholds") or {}).get("<=50m"),
        "same_name_100m": (dup.get("same_exact_name_pair_thresholds") or {}).get("<=100m"),
        "exact_name_addr_duplicate_groups": len(dup.get("exact_name_and_address_groups") or []),
    }

    # 5) 合成食堂计划
    canteen = json.loads((DATA / "canteen_plan.json").read_text(encoding="utf-8"))
    checks["canteen_plan"] = {
        "ok": canteen.get("target_count") == 200 and canteen.get("is_synthetic") == 1 and canteen.get("status") == "PLAN_ONLY_NOT_IMPORTED",
        "target_count": canteen.get("target_count"),
        "is_synthetic": canteen.get("is_synthetic"),
    }

    # 6) SSOT/台账口径
    spec = (ROOT / "MASTER_SPEC.md").read_text(encoding="utf-8")
    ledger = (ROOT / "docs/review/STAGE_STATUS.md").read_text(encoding="utf-8")
    checks["ssot"] = {
        "ok": "v2.3.5" in spec
        and "13 个" in spec
        and "12 个" not in spec
        and all(x in spec for x in ("allergen_tags", "deleted_at", "tagging_status", "source_dataset", "is_synthetic", "独立统计库"))
        and "applicable:false" in spec
        and "R=30" in spec
        and "109.078487,34.234818" in spec
        and "605" in spec
        and "独立统计库" in spec
        and "全部可空" in spec
        and "JIANDA_YANTA" in spec
        and "campus" in spec
        and "not_plotted_no_rating" in spec
        and "1700" in spec
        and "108.967153,34.236991" in spec
        and "6,659" in spec
        and "D03 已" in spec
        and "不返回 `applicable=false`" in spec,
        "has_v235": "v2.3.5" in spec,
        "has_v234_history": "v2.3.4" in spec,
        "has_v233_history": "v2.3.3" in spec,
        "has_13": "13 个" in spec,
        "has_12": "12 个" in spec,
        "has_schema_fields": all(x in spec for x in ("allergen_tags", "deleted_at", "tagging_status", "source_dataset", "is_synthetic")),
        "has_independent_stats_db": "独立统计库" in spec,
        "has_nullable_rule": "全部可空" in spec,
        "has_campus": "JIANDA_YANTA" in spec and "campus" in spec,
        "has_c10_clarification": "not_plotted_no_rating" in spec and "整数" in spec,
        "has_jianda": "108.967153,34.236991" in spec and "6,659" in spec,
        "has_d03": "D03 已" in spec,
        "has_c10_null_not_inapplicable": "不返回 `applicable=false`" in spec,
    }
    s09_line = next((line for line in ledger.splitlines() if line.startswith("| S09 |")), "")
    s10_line = next((line for line in ledger.splitlines() if line.startswith("| S10 |")), "")
    checks["ledger_s09"] = {
        "ok": "BLOCKED" in s09_line and "LOCKED" in s10_line,
        "s09_status_line": s09_line[:260],
        "s09_blocked": "BLOCKED" in s09_line,
        "s10_locked": "LOCKED" in s10_line,
    }
    checks["review_md_present"] = {"present": (PACK / "REVIEW.md").exists(), "note": "Codex-created review; doc-sync did not create/modify it."}

    decisions = (PACK / "DECISIONS.md").read_text(encoding="utf-8")
    checks["d03_decision"] = {
        "ok": "D03" in decisions
        and "样本 A" in decisions
        and "样本 B" in decisions
        and "不得跨校区混算" in decisions
        and "D03 已" in spec
        and "不返回 `applicable=false`" in spec
        and "not_plotted_no_rating" in spec,
        "has_sample_a": "样本 A" in decisions,
        "has_sample_b": "样本 B" in decisions,
        "has_no_cross_campus_mix": "不得跨校区混算" in decisions,
        "ledger_still_blocked": "BLOCKED" in s09_line and "LOCKED" in s10_line,
    }

    # 7) DB 保护
    base = json.loads((DATA / "db_baseline.json").read_text(encoding="utf-8"))
    db_path = ROOT / "backend" / "eatwhat.db"
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        rooms = con.execute("select count(*) from group_rooms").fetchone()[0]
        votes = con.execute("select count(*) from room_votes").fetchone()[0]
        logs = con.execute("select count(*) from eating_logs").fetchone()[0]
    finally:
        con.close()
    checks["demo_db_unchanged"] = {
        "ok": sha256(db_path) == base["file_sha256"] and rooms == 0 and votes == 0,
        "sha256_before": base["file_sha256"],
        "sha256_now": sha256(db_path),
        "group_rooms": rooms,
        "room_votes": votes,
        "eating_logs": logs,
    }

    # 8) 基线文件：代码/DB 不得变；文档可在本轮 doc-sync 中更新
    base_files = json.loads((DATA / "file_hashes.json").read_text(encoding="utf-8"))
    doc_prefixes = ("AGENTS.md", "MASTER_SPEC.md", "BATCH4_PLAN.md", "DASHBOARD_EXPANSION.md", "docs/")
    changed = [r["path"] for r in base_files["files"] if not (ROOT / r["path"]).exists() or sha256(ROOT / r["path"]) != r["sha256"]]
    code_changed = [path for path in changed if not path.startswith(doc_prefixes)]
    docs_changed = [path for path in changed if path.startswith(doc_prefixes)]
    checks["baseline_files_unchanged"] = {
        "ok": not code_changed,
        "code_changed": code_changed,
        "docs_changed": docs_changed,
        "note": "docs may change in the requested doc-sync; business code/DB files must not",
    }

    ok = all(v.get("ok", True) for v in checks.values() if isinstance(v, dict))
    payload = {"ok": ok, "checks": checks}
    (PACK / "validation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for p in sorted(PACK.rglob("*")):
        if p.is_file():
            rows.append({"path": str(p.relative_to(PACK)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": sha256(p)})
    (DATA / "evidence_index.json").write_text(json.dumps({"files": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
