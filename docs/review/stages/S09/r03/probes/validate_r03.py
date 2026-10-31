"""S09/r03 解封送审包自校验：r02 证据、D03、C10、r04 PASS 原件、代码/DB/admin 保护。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
R02 = ROOT / "docs/review/stages/S09/r02"
R03 = ROOT / "docs/review/stages/S09/r03"
R04 = ROOT / "docs/review/clearance-codex-r04-2026-10-24/REPORT.md"
PC01 = ROOT / "docs/review/stages/PC01/r04/REVIEW.md"
PC02 = ROOT / "docs/review/stages/PC02/r02/REVIEW.md"
PC03 = ROOT / "docs/review/stages/PC03/r04/REVIEW.md"


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


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_poi(path: Path, center: str, expected: int, campus: str) -> dict:
    cx, cy = [float(v) for v in center.split(",")]
    forbidden = {"tel", "email", "photos", "website", "shopinfo", "reviews"}
    ids, lines, outside, bad_flags, forbidden_hits = set(), 0, 0, 0, set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        lines += 1
        row = json.loads(line)
        ids.add(row.get("id"))
        forbidden_hits.update(forbidden & set(row))
        if row.get("is_synthetic") != 0 or row.get("campus") != campus or not row.get("source_dataset"):
            bad_flags += 1
        try:
            lng, lat = [float(v) for v in str(row.get("location")).split(",")]
        except Exception:
            outside += 1
            continue
        if haversine_m(cx, cy, lng, lat) > 3000.5:
            outside += 1
    return {
        "ok": lines == expected and len(ids) == expected and outside == 0 and bad_flags == 0 and not forbidden_hits,
        "lines": lines,
        "unique_ids": len(ids),
        "outside_3km": outside,
        "bad_flags": bad_flags,
        "forbidden_fields": sorted(forbidden_hits),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    checks = {}

    # 1) r02 manifest 84 项逐项重算
    r02_manifest_path = R02 / "SOURCE_MANIFEST.json"
    r02_manifest = load(r02_manifest_path)
    bad = []
    for row in r02_manifest.get("files", []):
        path = ROOT / row["path"]
        if not row.get("exists") or not path.exists() or path.stat().st_size != row.get("bytes") or sha256(path) != row.get("sha256"):
            bad.append(row["path"])
    checks["r02_manifest_84"] = {
        "ok": len(r02_manifest.get("files", [])) == 84 and not bad,
        "entry_count": len(r02_manifest.get("files", [])),
        "bad": bad,
        "sha256": sha256(r02_manifest_path),
    }

    # 2) r02 自校验仍为 ok
    r02_validation = load(R02 / "validation.json")
    checks["r02_validation"] = {"ok": r02_validation.get("ok") is True, "keys": sorted(r02_validation.get("checks", {}))}

    # 3) 思源重跑证据
    s_coll = load(R02 / "data/amap_collection.json")
    s_poi = check_poi(R02 / "data/amap_pois.jsonl", "109.078487,34.234818", 605, "SIYUAN")
    checks["siyuan"] = {
        "ok": s_coll.get("real_poi_count") == 605
        and s_coll.get("cells_planned") == 45
        and s_coll.get("cells_processed") == 61
        and s_coll.get("api_calls") == 133
        and s_coll.get("errors") == []
        and s_coll.get("incomplete_cells") == []
        and s_coll.get("d03_decision") == "ACCEPT_ACTUAL_605_AS_SAMPLE_A"
        and s_poi.get("ok"),
        "real_poi_count": s_coll.get("real_poi_count"),
        "cells_planned": s_coll.get("cells_planned"),
        "cells_processed": s_coll.get("cells_processed"),
        "api_calls": s_coll.get("api_calls"),
        "poi_file": s_poi,
    }

    # 4) 建大试抓证据
    j_coll = load(R02 / "data/amap_jianda_collection.json")
    j_poi = check_poi(R02 / "data/amap_jianda_pois.jsonl", "108.967153,34.236991", 6659, "JIANDA_YANTA")
    checks["jianda"] = {
        "ok": j_coll.get("real_poi_count") == 6659
        and j_coll.get("synthetic_canteen_count") == 200
        and j_coll.get("total_restaurants_target_if_200_canteen") == 6859
        and j_coll.get("cells_planned") == 45
        and j_coll.get("cells_processed") == 425
        and j_coll.get("api_calls") == 1206
        and j_coll.get("errors") == []
        and j_coll.get("incomplete_cells") == []
        and j_coll.get("d03_decision") == "ACCEPT_ACTUAL_6659_AS_SAMPLE_B"
        and j_poi.get("ok"),
        "real_poi_count": j_coll.get("real_poi_count"),
        "synthetic_canteen_count": j_coll.get("synthetic_canteen_count"),
        "combined": j_coll.get("total_restaurants_target_if_200_canteen"),
        "cells_processed": j_coll.get("cells_processed"),
        "api_calls": j_coll.get("api_calls"),
        "poi_file": j_poi,
    }

    # 5) rating/cost/tag 有值/缺失
    fs = load(R02 / "data/poi_field_stats.json")
    expected_fields = {
        "SIYUAN": {"total": 605, "rating_present": 604, "rating_missing": 1, "cost_present": 427, "cost_missing": 178, "tag_present": 309, "tag_missing": 296},
        "JIANDA_YANTA": {"total": 6659, "rating_present": 6652, "rating_missing": 7, "cost_present": 5411, "cost_missing": 1248, "tag_present": 3871, "tag_missing": 2788},
    }
    field_bad = {}
    for campus, expected in expected_fields.items():
        got = fs.get(campus, {})
        diff = {key: {"expected": value, "got": got.get(key)} for key, value in expected.items() if got.get(key) != value}
        if diff:
            field_bad[campus] = diff
    checks["poi_field_stats"] = {"ok": not field_bad, "bad": field_bad}

    # 6) 建大抽查
    sc = load(R02 / "data/jianda_poi_spotcheck.json")
    dup = sc.get("duplicate_checks", {})
    checks["jianda_spotcheck"] = {
        "ok": sc.get("row_count") == 6659
        and sc.get("unique_ids") == 6659
        and sc.get("invalid_location_rows") == 0
        and (sc.get("outside_3km") or {}).get("count") == 0
        and (sc.get("distance_summary") or {}).get("max_m", 99999) <= 3000.5
        and len(sc.get("first_20_by_distance") or []) == 20
        and sum((sc.get("distance_bands") or {}).values()) == 6659
        and not dup.get("exact_name_and_address_groups")
        and (dup.get("same_exact_name_pair_thresholds") or {}).get("<=50m") == 4
        and (dup.get("same_exact_name_pair_thresholds") or {}).get("<=100m") == 5,
        "row_count": sc.get("row_count"),
        "outside_3km": (sc.get("outside_3km") or {}).get("count"),
        "max_m": (sc.get("distance_summary") or {}).get("max_m"),
        "first_20_count": len(sc.get("first_20_by_distance") or []),
        "same_name_50m": (dup.get("same_exact_name_pair_thresholds") or {}).get("<=50m"),
        "same_name_100m": (dup.get("same_exact_name_pair_thresholds") or {}).get("<=100m"),
        "exact_name_addr_duplicates": len(dup.get("exact_name_and_address_groups") or []),
    }

    # 7) D03 / C10 口径
    decisions = (R02 / "DECISIONS.md").read_text(encoding="utf-8")
    spec = (ROOT / "MASTER_SPEC.md").read_text(encoding="utf-8")
    matrix = (R02 / "CONTRACT_MATRIX.md").read_text(encoding="utf-8")
    checks["d03_c10"] = {
        "ok": "样本 A" in decisions
        and "样本 B" in decisions
        and "不得跨校区混算" in decisions
        and "不是 1700 合计" in decisions
        and "D03 已" in spec
        and "不返回 `applicable=false`" in spec
        and "not_plotted_no_rating" in spec
        and "整数" in spec
        and "not_plotted_no_rating" in matrix
        and "整数" in matrix,
        "sample_a": "样本 A" in decisions,
        "sample_b": "样本 B" in decisions,
        "no_cross_campus_mix": "不得跨校区混算" in decisions,
        "not_1700_total": "不是 1700 合计" in decisions,
        "c10_null_not_inapplicable": "不返回 `applicable=false`" in spec,
    }

    # 8) r04 PASS 原件（PC02 现行 PASS 是 r02，不是 r01）
    report = R04.read_text(encoding="utf-8")
    pc01 = PC01.read_text(encoding="utf-8")
    pc02 = PC02.read_text(encoding="utf-8")
    pc03 = PC03.read_text(encoding="utf-8")
    checks["r04_pass_reports"] = {
        "ok": R04.exists()
        and PC01.exists()
        and PC02.exists()
        and PC03.exists()
        and "PC01/R02：PASS" in report
        and "PC03/F12：PASS" in report
        and "PASS" in pc01
        and "PASS" in pc02
        and "PASS" in pc03,
        "r04_report": {"path": str(R04.relative_to(ROOT)), "sha256": sha256(R04)},
        "pc01": {"path": str(PC01.relative_to(ROOT)), "sha256": sha256(PC01)},
        "pc02": {"path": str(PC02.relative_to(ROOT)), "sha256": sha256(PC02), "note": "PC02 现行 PASS 原件；PC02/r01 为 FAIL 历史"},
        "pc03": {"path": str(PC03.relative_to(ROOT)), "sha256": sha256(PC03)},
    }

    # 9) 台账未改：S09 BLOCKED / S10 LOCKED，且 hash 与 r02 manifest 一致
    ledger_path = ROOT / "docs/review/STAGE_STATUS.md"
    ledger = ledger_path.read_text(encoding="utf-8")
    s09 = next((line for line in ledger.splitlines() if line.startswith("| S09 |")), "")
    s10 = next((line for line in ledger.splitlines() if line.startswith("| S10 |")), "")
    r02_ledger_hash = next((row["sha256"] for row in r02_manifest["files"] if row["path"] == "docs/review/STAGE_STATUS.md"), None)
    checks["ledger"] = {
        "ok": "BLOCKED" in s09 and "LOCKED" in s10 and r02_ledger_hash == sha256(ledger_path),
        "s09_status_line": s09[:260],
        "s10_locked": "LOCKED" in s10,
        "hash_matches_r02_manifest": r02_ledger_hash == sha256(ledger_path),
    }

    # 10) 代码/DB/admin 保护
    file_hashes = load(R02 / "data/file_hashes.json")
    code_changed = []
    for row in file_hashes["files"]:
        if not row["path"].startswith(("backend/", "frontend/", "scripts/")):
            continue
        path = ROOT / row["path"]
        if not path.exists() or sha256(path) != row["sha256"]:
            code_changed.append(row["path"])
    db_path = ROOT / "backend/eatwhat.db"
    db_base = load(R02 / "data/db_baseline.json")
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        rooms = con.execute("select count(*) from group_rooms").fetchone()[0]
        votes = con.execute("select count(*) from room_votes").fetchone()[0]
    finally:
        con.close()
    from backend.main import app
    admin = sorted({getattr(route, "path", "") for route in app.routes if "/admin" in getattr(route, "path", "")})
    checks["protection"] = {
        "ok": not code_changed and sha256(db_path) == db_base["file_sha256"] and rooms == 0 and votes == 0 and not admin,
        "code_changed": code_changed,
        "db_sha256_before": db_base["file_sha256"],
        "db_sha256_now": sha256(db_path),
        "group_rooms": rooms,
        "room_votes": votes,
        "admin_routes": admin,
    }

    # 11) Key 不落入 r03/r02 证据
    key = os.getenv("AMAP_API_KEY", "").strip()
    leaked = []
    if key:
        for base in (R03, R02):
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    if key in path.read_text(encoding="utf-8", errors="ignore"):
                        leaked.append(str(path.relative_to(ROOT)).replace("\\", "/"))
                except Exception:
                    pass
    checks["key_not_in_evidence"] = {"ok": not leaked, "key_present_in_env": bool(key), "leaked_files": leaked}

    # 12) 未创建 r03 REVIEW.md
    checks["review_md_not_created"] = {
        "ok": not (R03 / "REVIEW.md").exists(),
        "r03_review_exists": (R03 / "REVIEW.md").exists(),
        "r02_review_sha256": sha256(R02 / "REVIEW.md") if (R02 / "REVIEW.md").exists() else None,
    }

    ok = all(value.get("ok", True) for value in checks.values() if isinstance(value, dict))
    payload = {"ok": ok, "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "checks": checks}
    (R03 / "validation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    evidence = {
        "pack": "S09/r03",
        "generated_at": payload["generated_at"],
        "status": {"s09": "BLOCKED", "s10": "LOCKED", "ledger_modified": False},
        "blockers": {
            "B1_dual_campus": {"ok": checks["jianda"]["ok"] and checks["r02_manifest_84"]["ok"]},
            "B2_d03": {"ok": checks["d03_c10"]["ok"] and checks["siyuan"]["ok"]},
            "B3_manifest": {"ok": checks["r02_manifest_84"]["ok"]},
        },
        "counts": {
            "siyuan_real": checks["siyuan"]["real_poi_count"],
            "siyuan_combined": 805,
            "jianda_real": checks["jianda"]["real_poi_count"],
            "jianda_combined": checks["jianda"]["combined"],
            "r02_manifest_entries": checks["r02_manifest_84"]["entry_count"],
        },
        "protection": checks["protection"],
        "r04_reports": checks["r04_pass_reports"],
        "referenced_files": {
            "r02_manifest": {"path": "docs/review/stages/S09/r02/SOURCE_MANIFEST.json", "sha256": checks["r02_manifest_84"]["sha256"]},
            "r02_validation": {"path": "docs/review/stages/S09/r02/validation.json", "sha256": sha256(R02 / "validation.json")},
            "decisions": {"path": "docs/review/stages/S09/r02/DECISIONS.md", "sha256": sha256(R02 / "DECISIONS.md")},
            "field_stats": {"path": "docs/review/stages/S09/r02/data/poi_field_stats.json", "sha256": sha256(R02 / "data/poi_field_stats.json")},
            "jianda_spotcheck": {"path": "docs/review/stages/S09/r02/data/jianda_poi_spotcheck.json", "sha256": sha256(R02 / "data/jianda_poi_spotcheck.json")},
        },
        "checks_ok": ok,
    }
    (R03 / "data/r03_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": ok,
        "failed": [key for key, value in checks.items() if isinstance(value, dict) and not value.get("ok", True)],
        "r02_manifest": checks["r02_manifest_84"],
        "siyuan": checks["siyuan"],
        "jianda": checks["jianda"],
        "d03_c10": checks["d03_c10"],
        "ledger": checks["ledger"],
        "protection": checks["protection"],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
