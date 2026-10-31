"""生成 S03/r01 validation.json（机器可读验收摘要）。"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/EatWhat")
OUT = ROOT / "docs" / "review" / "stages" / "S03" / "r01"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

manifest = json.loads((OUT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
probe = json.loads((OUT / "data/live_api_probe.json").read_text(encoding="utf-8"))
protection = json.loads((OUT / "data/db_protection.json").read_text(encoding="utf-8"))
boundary = json.loads((OUT / "data/clock_boundary.json").read_text(encoding="utf-8"))

sha_by_path = {item["path"]: item["sha256"] for item in manifest["files"]}


def parse_log(name):
    text = (OUT / "logs" / name).read_text(encoding="utf-8", errors="ignore")
    tail = "\n".join(text.strip().splitlines()[-3:])
    found = {}
    for key in ("passed", "failed", "skipped", "errors"):
        match = re.search(rf"(\d+) {key}", text)
        if match:
            found[key] = int(match.group(1))
    return {"log": f"logs/{name}", "summary_line": tail, **found}


changed = [
    "backend/algorithms/fridge_clock.py",
    "backend/algorithms/single_recommender.py",
    "backend/algorithms/combo_optimizer.py",
    "backend/routers/fridge.py",
    "backend/tests/test_s03_fridge_lifecycle.py",
    "backend/tests/test_identity_bounds_and_stock.py",
    "backend/tests/test_query_budget.py",
    "MASTER_SPEC.md",
]

data = {
    "step": "S03",
    "round": "r01",
    "generated_at": NOW,
    "status": "SUBMITTED_FOR_REVIEW",
    "self_signed_pass": False,
    "prior_clearance": {
        "step": "S02",
        "round": "r02",
        "conclusion": "PASS",
        "report": "docs/review/clearance-codex-s02-r02/REPORT.md",
        "manifest_fingerprint": "2c8cc39df3a00c8f11c15ecf77d768da47e969447ba6a4fb5140885829c9556a",
    },
    "user_rulings": [
        {
            "id": "1A",
            "decision": (
                "UTC 绝对时间：expires_at = created_at + expire_days*24h；"
                "now >= expires_at 即过期；过期返回 0 天；未过期剩余秒数向上取整；"
                "临期 = 未过期且实际剩余 <=48h"
            ),
        },
        {
            "id": "2A",
            "decision": (
                "同名食材再次 ADD 视为重新入库：覆盖属性并把 created_at 重置为当前时间；"
                "历史重复行保留不合并；任一条有效匹配即视为已有"
            ),
        },
        {
            "id": "3B",
            "decision": "后端实现 + 证据包记录裁决 + 同步 MASTER_SPEC；不改前端",
        },
    ],
    "source_baseline": {
        "branch": "master",
        "head": None,
        "commit_count": 0,
        "manifest_file_count": len(manifest["files"]),
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "contract_version": manifest["contract_version"],
        "git_status": manifest["git"]["status"],
    },
    "environment": {
        "python": "3.13.9",
        "node": "v24.19.0",
        "npm": "11.17.0",
        "fastapi": "0.115.0",
        "sqlalchemy": "2.0.35",
        "pydantic": "2.13.3",
    },
    "changed_files": [
        {"path": path, "sha256": sha_by_path.get(path)} for path in changed
    ],
    "test_runs": {
        "red_baseline_targeted": parse_log("00_red_baseline.log"),
        "targeted_final": parse_log("12_backend_pytest_s03_final.log"),
        "backend_full": parse_log("10_backend_pytest_full.log"),
    },
    "acceptance_matrix": [
        {
            "item": "统一库存时钟与时区口径；UTC 绝对时间，DST 不影响",
            "result": "PASS",
            "evidence": "logs/12_backend_pytest_s03_final.log、data/clock_boundary.json",
        },
        {
            "item": "精确覆盖到期前 / 到期时 / 到期后；边界等价关系明确",
            "result": "PASS",
            "evidence": "test_clock_boundary_matrix、test_clock_invariants_hold_across_sweep、data/clock_boundary.json",
        },
        {
            "item": "列表 / 下厨推荐 / 采购清单 / 组合采购同一过期判定",
            "result": "PASS",
            "evidence": "test_expired_stock_consistent_across_all_consumers、live_api_probe.json",
        },
        {
            "item": "过期库存不计可用、不提升状态分、不抵扣清单",
            "result": "PASS",
            "evidence": "test_status_score_uses_exact_clock_and_double_weight、test_shopping_list_merges_dedupes_and_subtracts_valid_stock",
        },
        {
            "item": "临期提权严格符合 SSOT（未过期且 <=48h 双倍）",
            "result": "PASS",
            "evidence": "test_status_score_uses_exact_clock_and_double_weight（48h 整 / 48h+1s 两侧）",
        },
        {
            "item": "余料反推只使用有效库存",
            "result": "PASS",
            "evidence": "test_expired_stock_consistent_across_all_consumers、test_home_cooking_without_mains_or_stock_scores_zero",
        },
        {
            "item": "采购清单合并、去重、已有扣减、同名重复行",
            "result": "PASS",
            "evidence": "test_shopping_list_merges_dedupes_and_subtracts_valid_stock、test_shopping_list_duplicate_same_name_rows_one_valid_is_owned",
        },
        {
            "item": "库存增删改查、推荐、清单同一用户闭环一致",
            "result": "PASS",
            "evidence": "test_fridge_crud_loop_and_readd_resets_created_at、live_api_probe.json",
        },
        {
            "item": "跨用户读取 / 更新 / 删除 / 推荐 / 清单消费负向",
            "result": "PASS",
            "evidence": "test_cross_user_cannot_read_update_delete_or_consume_fridge、live_api_probe.json",
        },
        {
            "item": "外食推荐不读取冰箱",
            "result": "PASS",
            "evidence": "test_out_dining_does_not_read_fridge（结果不变 + SQL 不查 fridge_inventory）",
        },
        {
            "item": "测试使用内存库 / 新隔离副本，不写受保护库",
            "result": "PASS",
            "evidence": "data/db_protection.json、logs/21_live_probe.log",
        },
        {
            "item": "后端全量测试、无新增 500、受保护库指纹不变",
            "result": "PASS",
            "evidence": "logs/10_backend_pytest_full.log、data/db_protection.json",
        },
        {
            "item": "前端改动",
            "result": "N/A",
            "evidence": "本步未改 frontend/src；按任务要求纯后端改动不补浏览器验收",
        },
    ],
    "live_probe": {
        "base_url": probe["base_url"],
        "iso_db": probe["iso_db"],
        "steps": len(probe["steps"]),
        "status_codes": probe["status_codes"],
        "no_500": probe["no_500"],
        "protected_unchanged": probe["protected_unchanged"],
        "passed": probe["passed"],
    },
    "databases": protection,
    "boundary_evidence": {
        "fixed_now_utc": boundary["fixed_now_utc"],
        "boundary_cases": len(boundary["boundary_cases"]),
        "timezone_dst_cases": len(boundary["timezone_dst_cases"]),
        "file": "data/clock_boundary.json",
    },
    "design_notes": [
        "quantity_desc 按 SSOT 是自由文本描述，本步不做数量/单位算术；有有效库存即视为已有（test_shopping_list_quantity_desc_is_descriptive_not_deducted）。",
        "外食推荐不消费冰箱；S03 只确认并验证其不受库存影响，不给它增加库存逻辑。",
        "同名历史重复行保留展示；推荐与清单只认有效行，不叠加权重。",
    ],
    "residual_risks": [
        "pytest 全量保留 1 个既有 Windows 符号链接权限 skip；本步未新增 skip。",
        "测试日志中的 DeprecationWarning 来自既有 test_room / 旧测试的 datetime.utcnow()，生产时钟已改用 UTC-aware 实现；本步未扩大警告范围。",
        "真实 HTTP 探针使用真实系统时钟与相对时间样本；精确到秒的边界由固定时钟单测覆盖。",
    ],
    "out_of_scope": [
        "S04 四算法与决策红线",
        "S05/S06/S07/S08 及其它未开放专项",
        "/admin、S10–S20、APK",
        "前端改动与浏览器验收",
    ],
    "stop": {
        "action": "submitted_for_review_and_stopped",
        "next_step_allowed": False,
        "note": "开发方不签 PASS、不改 STAGE_STATUS.md、不创建 REVIEW.md、不开始 S04。",
    },
}

(OUT / "validation.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "status": data["status"],
            "manifest": data["source_baseline"]["manifest_fingerprint"],
            "tests": data["test_runs"],
            "live": data["live_probe"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
