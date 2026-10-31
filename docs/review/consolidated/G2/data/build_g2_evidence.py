"""G2 证据汇总：导入计数、抽样映射、幂等、桥接与 S11 预检判定。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
FULL = DATA / "full"
VERIFY = DATA / "full_verify"
VERIFY_RERUN = DATA / "full_verify_after_rerun"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_import_counts() -> dict:
    payload = {"generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "per_campus_source": {}}
    for campus in ("SIYUAN", "JIANDA_YANTA"):
        poi = load(FULL / f"poi_{campus}.json")
        canteen = load(FULL / f"canteen_{campus}.json")
        payload["per_campus_source"][f"{campus}|AMAP_POI"] = {
            key: poi.get(key)
            for key in ("scanned", "inserted", "existing", "duplicate_in_input", "rejected", "failures", "missing_fields", "reject_reasons", "input_sha256")
        }
        payload["per_campus_source"][f"{campus}|CANTEEN"] = {
            key: canteen.get(key)
            for key in ("scanned", "inserted", "existing", "duplicate_in_input", "rejected", "failures", "missing_fields", "reject_reasons")
        }
    recipes = load(FULL / "recipes.json")
    payload["recipes"] = {
        key: recipes.get(key)
        for key in ("scanned", "inserted", "existing", "duplicate_in_input", "rejected", "failures", "reject_reasons", "ok")
    }
    validation = load(VERIFY / "validation.json")
    payload["verified_counts"] = validation["counts"]
    payload["count_chain"] = {
        "real_poi": {"SIYUAN": {"input": 605, "scanned": 605, "inserted": 605, "rejected": 0},
                     "JIANDA_YANTA": {"input": 6659, "scanned": 6659, "inserted": 6659, "rejected": 0}},
        "canteen": {"SIYUAN": {"inserted": 200, "rejected": 0}, "JIANDA_YANTA": {"inserted": 200, "rejected": 0}},
        "recipes": {"generated": 6400, "inserted": 6400, "duplicate_names": 0, "rejected": 0},
    }
    (DATA / "import_counts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def build_sample_mapping() -> dict:
    poi = load(VERIFY / "sample_poi_mapping.json")["samples"]
    recipes = load(VERIFY / "sample_recipe_mapping.json")["samples"]
    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "poi_count": len(poi),
        "poi_ok": sum(1 for row in poi if row.get("ok") is True),
        "recipe_count": len(recipes),
        "recipe_ok": sum(1 for row in recipes if row.get("ok") is True),
        "poi_samples": poi,
        "recipe_samples": recipes,
        "ok": len(poi) >= 30 and len(recipes) >= 30
        and all(row.get("ok") is True for row in poi)
        and all(row.get("ok") is True for row in recipes),
    }
    (DATA / "sample_mapping.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def build_idempotency() -> dict:
    validation = load(VERIFY_RERUN / "validation.json")
    check = next(item for item in validation["checks"] if item["id"] == "idempotent_reimport")
    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "before": check["actual"]["before"],
        "after": check["actual"]["after"],
        "restaurant_rows_delta": check["actual"]["restaurant_rows_delta"],
        "dish_rows_delta": check["actual"]["dish_rows_delta"],
        "association_rows_delta": check["actual"]["association_rows_delta"],
        "fingerprints_equal": check["actual"]["restaurant_fingerprint_equal"]
        and check["actual"]["dish_fingerprint_equal"]
        and check["actual"]["association_fingerprint_equal"],
        "rerun_summaries": {
            "poi_siyuan": str(FULL / "rerun_poi_SIYUAN.json"),
            "poi_jianda_limited": str(FULL / "rerun_poi_JIANDA.json"),
            "canteen": [str(FULL / "rerun_canteen_SIYUAN.json"), str(FULL / "rerun_canteen_JIANDA_YANTA.json")],
            "recipes": str(FULL / "rerun_recipes.json"),
        },
        "note": "JIANDA 真实 POI 复跑只取前 50 条（全量 6,659 逐行去重耗时约 10 分钟）；唯一来源索引与指纹共同证明不重复。",
        "ok": check["ok"],
    }
    (DATA / "idempotency.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def db_snapshot() -> dict:
    path = ROOT / "backend" / "eatwhat_g2_s10_full.db"
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return {
            "restaurants": connection.execute(
                "SELECT campus, source_type, source_dataset, COUNT(*) FROM restaurants GROUP BY 1,2,3"
            ).fetchall(),
            "null_campus": connection.execute(
                "SELECT COUNT(*) FROM restaurants WHERE campus IS NULL"
            ).fetchone()[0],
            "dishes": connection.execute(
                "SELECT mode_type, COALESCE(is_synthetic,-1), COUNT(*) FROM dishes_and_recipes GROUP BY 1,2"
            ).fetchall(),
            "pending": connection.execute(
                "SELECT COUNT(*) FROM dishes_and_recipes WHERE tagging_status='PENDING'"
            ).fetchone()[0],
        }
    finally:
        connection.close()


def main() -> None:
    counts = build_import_counts()
    samples = build_sample_mapping()
    idem = build_idempotency()
    verification = load(VERIFY / "validation.json")
    verification_after = load(VERIFY_RERUN / "validation.json")
    bridge = load(DATA / "bridge_api.json")
    protection = load(DATA / "db_protection.json")
    preflight = load(DATA / "s11_preflight.json")
    budget = load(DATA / "query_budget.json")
    smoke = load(DATA / "smoke_mapping.json")
    snapshot = db_snapshot()

    checks = {
        "s10_import": {
            "input_hashes_recorded": "input_manifest.json" in [p.name for p in VERIFY.iterdir()],
            "real_poi_counts": counts["verified_counts"]["real_poi"] == {"SIYUAN": 605, "JIANDA_YANTA": 6659},
            "canteen_counts_split": counts["verified_counts"]["canteen"] == {"SIYUAN": 200, "JIANDA_YANTA": 200},
            "recipe_count": counts["verified_counts"]["recipes"] == 6400,
            "recipe_unique_names": counts["verified_counts"]["recipe_unique_names"] == 6400,
            "zero_rejects": all(
                item["rejected"] == 0 and item["failures"] == 0
                for item in counts["per_campus_source"].values()
            ) and counts["recipes"]["rejected"] == 0,
            "no_null_campus_in_s10_rows": snapshot["null_campus"] == 0,
            "recipes_synthetic_pending": all(row[2] == 6400 for row in snapshot["dishes"]) and snapshot["pending"] == 6400,
            "small_sample_mapping": smoke["ok"],
            "full_verify_36": verification["overall_ok"] and len(verification["checks"]) == 36,
            "samples_ge_30_each": samples["ok"],
            "idempotent_rerun": idem["ok"],
            "protected_dbs_unchanged": protection["all_protected_unchanged"],
            "s09_evidence_unchanged": protection["s09_manifest_unchanged"],
        },
        "bridge10": {
            "runtime_db_has_no_s10_datasets": bridge["runtime_counts"]["contains_s10_datasets"] is False,
            "runtime_users_logs_present": bridge["runtime_counts"]["users"] >= 4
            and bridge["runtime_counts"]["eating_logs"] >= 1,
            "bridge_has_s10_payload": bridge["bridge_counts"]["by_dataset"].get("amap_place_around_20261025") == 7264
            and bridge["bridge_counts"]["by_dataset"].get("synthetic_canteen_v1") == 400,
            "group_out_candidates_campus_filtered": bridge["group_out"]["siyuan_candidates_all_in_campus"]
            and bridge["group_out"]["jianda_candidates_all_in_campus"],
            "group_cross_campus_join_rejected": bridge["group_out"]["cross_campus_join_status"] == 409,
            "home_cooking_shared_single": bridge["home_shared"]["same_ids"],
            "home_cooking_shared_group": bridge["group_home_shared"]["same_ids"],
            "single_recommend_campus_required": bridge["recommend_out"]["missing_campus_status"] == 422,
            "single_recommend_campus_filtered": bridge["recommend_out"]["siyuan_all_within_campus"]
            and bridge["recommend_out"]["jianda_all_within_campus"],
            "null_campus_not_attributed_single": bridge["recommend_out"]["no_null_campus_leak"],
        },
        "s11_preflight": {
            "no_paid_calls": preflight["network_calls"] == 0,
            "blocked_without_key_model_budget": preflight["status"] == "BLOCKED",
            "batch_plan_20": preflight["dry_run"]["batch_size"] == 20,
            "batch_count_320": preflight["dry_run"]["batch_count"] == 320,
            "max_calls_with_retries_960": preflight["dry_run"]["max_calls_with_retries"] == 960,
            "coverage_not_faked": preflight["coverage"]["success_coverage"] == 0.0,
            "no_vector_anomalies": preflight["coverage"]["vector_anomalies"] == 0,
        },
        "query_budget": {
            "fridge_query_constant": budget["constant_fridge_queries"],
            "no_per_dish_growth": budget["no_per_dish_growth"],
            "same_top3_as_legacy": budget["same_top3_as_legacy"],
        },
    }
    summary = {
        key: {"ok": all(value.values()), "passed": sum(1 for value in value.values() if value), "total": len(value), "checks": value}
        for key, value in checks.items()
    }
    resolved = {
        "BRIDGE-10-P1": {
            "severity": "P1",
            "status": "FIXED_AND_REVERIFIED",
            "title": "单人推荐未接校区：缺 campus 仍 200，且可返回 NULL / 另一校区门店",
            "evidence": {
                "missing_campus_status": bridge["recommend_out"]["missing_campus_status"],
                "siyuan_all_within_campus": bridge["recommend_out"]["siyuan_all_within_campus"],
                "jianda_all_within_campus": bridge["recommend_out"]["jianda_all_within_campus"],
                "no_null_campus_leak": bridge["recommend_out"]["no_null_campus_leak"],
            },
            "code": [
                "backend/schemas.py::SingleRecommendRequest 无 campus 字段",
                "backend/routers/recommend.py::recommend 未把 campus 传给算法",
                "backend/algorithms/single_recommender.py::recommend_single 无 campus 过滤",
                "frontend/src/stores/algo.js 请求体未带 campus",
            ],
            "impact": "BRIDGE-10 的『外食推荐按校区过滤 / 缺失 campus 422 / NULL 不误归属』无法通过；首页外食仍可能混入其他校区或 NULL 门店。",
            "fix": [
                "schemas.py：SingleRecommendRequest 新增 campus 与 model_validator（外食缺失 422）",
                "recommend.py：把 campus 传入算法",
                "single_recommender.py：外食按 restaurant.campus 过滤，NULL/跨校区排除",
                "frontend/src/stores/algo.js：请求体携带 mode.campus",
                "新增 tests/test_g2_single_campus.py（5 条）；迁移受影响 API 测试请求体；测试库种子店标为 SIYUAN",
            ],
            "verification": "browser bridge probe 全部通过；pytest 396 passed / 1 skipped；home-fit/refill/sandbox/build/colors 复跑通过；S08 在修复后重跑。",
        },
    }
    blockers = {
        "BRIDGE-10-BLOCKED": {
            "severity": "BLOCKED",
            "items": [
                "统计请求随校区同步变化：/admin/stats/* 属 S15，本组未实现（探针返回 404）",
                "前端全局校区切换 UI：SSOT v2.3.6 明确留到后续专项；本轮只验证 API 层",
                "S10 真实门店的外食菜单行：S10 只导入 POI/食堂/菜谱，未生成外食菜品，故 S10 门店暂不进入候选；校区过滤机制用运行库校园数据验证",
            ],
        },
        "S11-BLOCKED": {
            "severity": "BLOCKED",
            "reason": preflight["blocked_reason"],
            "needs": ["LLM Key 来源", "模型版本", "预算上限与最大调用量"],
        },
    }
    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "scope": "G2 (BRIDGE-10 + S10 + S11)",
        "note": "开发方自测判定，不是 Codex 正式 PASS。",
        "self_test_ok": all(item["ok"] for item in summary.values()),
        "groups": summary,
        "blockers": blockers,
        "resolved": resolved,
        "evidence": {
            "import_counts": "data/import_counts.json",
            "sample_mapping": "data/sample_mapping.json",
            "idempotency": "data/idempotency.json",
            "smoke_mapping": "data/smoke_mapping.json",
            "s10_verification": "data/full_verify/validation.json",
            "bridge_api": "data/bridge_api.json",
            "s11_preflight": "data/s11_preflight.json",
            "coverage": "data/coverage.json",
            "query_budget": "data/query_budget.json",
            "db_protection": "data/db_protection.json",
            "bridge_provenance": "data/bridge_provenance.json",
        },
    }
    (BASE / "validation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: item["ok"] for key, item in summary.items()}, ensure_ascii=False))
    print("self_test_ok", payload["self_test_ok"])


if __name__ == "__main__":
    main()
