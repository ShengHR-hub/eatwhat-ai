"""生成 S02/r01 validation.json（机器可读摘要，不代表 PASS）。"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path("docs/review/stages/S02/r01")
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def last_summary(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    matches = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"\b\d+ (?:passed|failed)\b", line)
    ]
    return matches[-1] if matches else None


manifest = json.loads((OUT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
db = json.loads((OUT / "data/db_protection.json").read_text(encoding="utf-8"))
probe = json.loads((OUT / "data/live_api_probe.json").read_text(encoding="utf-8"))
boundary = json.loads((OUT / "data/boundary_table.json").read_text(encoding="utf-8"))

pending = [
    entry["field"]
    for entry in boundary["entries"]
    if entry["status"] == "CODE_DERIVED_PENDING"
]
gaps = [
    {"field": entry["field"], "owner": entry.get("owner"), "note": entry.get("note")}
    for entry in boundary["entries"]
    if entry["status"] == "OUT_OF_SCOPE_GAP"
]

validation = {
    "step": "S02",
    "round": "r01",
    "generated_at": NOW,
    "status": "SUBMITTED_FOR_REVIEW",
    "self_signed_pass": False,
    "prior_clearance": {
        "step": "S01",
        "round": "r01",
        "conclusion": "PASS",
        "report": "docs/review/clearance-codex-s01-r01/REPORT.md",
        "manifest_fingerprint": "3caa7db07f0516db1ecbda9e58a7cee35c3832ad235dc74f0f4f9c1002c4ad29",
    },
    "environment": {
        "python": "3.13.9",
        "node": "v24.19.0",
        "npm": "11.17.0",
        "pkgs": {
            "fastapi": "0.115.0",
            "sqlalchemy": "2.0.35",
            "pydantic": "2.13.3",
        },
    },
    "source_baseline": {
        "branch": manifest["git"]["branch"],
        "head": manifest["git"]["head"],
        "commit_count": manifest["git"]["commit_count"],
        "manifest_file_count": len(manifest["files"]),
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "contract_version": manifest["contract_version"],
        "git_status": manifest["git"]["status"],
    },
    "databases": db,
    "checks": {
        "red_baseline": {
            "command": "python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 1,
            "summary": last_summary(OUT / "logs/00_red_baseline.log"),
            "log": "logs/00_red_baseline.log",
        },
        "targeted_final": {
            "command": "python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": last_summary(OUT / "logs/14_backend_pytest_s02_final2.log"),
            "log": "logs/14_backend_pytest_s02_final2.log",
        },
        "full_baseline_before_change": {
            "command": "python -m pytest -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": "210 passed, 1 skipped (与 S01/r01 受审基线一致)",
            "log": "docs/review/stages/S01/r01/logs/20_backend_pytest.log",
        },
        "full_intermediate_after_first_fix": {
            "command": "python -m pytest -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": last_summary(OUT / "logs/10_backend_pytest_full.log"),
            "log": "logs/10_backend_pytest_full.log",
        },
        "full_after_legacy_guard": {
            "command": "python -m pytest -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": last_summary(OUT / "logs/11_backend_pytest_full_after_final.log"),
            "log": "logs/11_backend_pytest_full_after_final.log",
        },
        "full_final": {
            "command": "python -m pytest -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": last_summary(OUT / "logs/15_backend_pytest_full_final2.log"),
            "log": "logs/15_backend_pytest_full_final2.log",
        },
        "live_http_probe": {
            "command": "DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s02_r01_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8013",
            "cwd": "D:/EatWhat",
            "exit_code": 0,
            "steps": len(probe["steps"]),
            "statuses": sorted({step["status"] for step in probe["steps"]}),
            "protected_unchanged": probe["protected_unchanged"],
            "result": "data/live_api_probe.json",
            "server_log": "logs/20_live_server.log",
        },
    },
    "acceptance": [
        {
            "requirement": "合法边界 API 接受",
            "tests": [
                "test_vector_accepts_both_bounds",
                "test_preferences_budget_and_veto_bounds",
                "test_recommend_accepts_legal_boundaries_with_finite_scores",
                "test_weather_accepts_legal_boundaries",
                "test_recommend_override_bounds",
            ],
            "result": "pass",
        },
        {
            "requirement": "缺键/部分覆盖后仍八键完整",
            "tests": [
                "test_partial_vector_merges_and_keeps_eight_keys",
                "test_legacy_incomplete_vector_is_completed_on_write",
            ],
            "result": "pass",
        },
        {
            "requirement": "空对象/多键/布尔/字符串/NaN/Infinity/越界拒绝且不脏写",
            "tests": [
                "test_empty_vector_is_rejected_and_db_unchanged",
                "test_extra_vector_key_is_rejected_and_db_unchanged",
                "test_boolean_is_not_a_vector_number",
                "test_string_is_not_a_vector_number",
                "test_non_finite_vector_is_rejected",
                "test_non_finite_body_returns_422_not_500",
                "test_vector_out_of_range_is_rejected",
            ],
            "result": "pass",
        },
        {
            "requirement": "无效枚举/超长标签/负金额/不存在引用 4xx 且库不变",
            "tests": [
                "test_invalid_enums_are_422",
                "test_preferences_budget_and_veto_bounds",
                "test_checkin_rejects_negative_cost_and_keeps_log_count",
                "test_checkin_missing_dish_is_404_and_db_unchanged",
                "test_checkin_mode_mismatch_is_400_and_db_unchanged",
                "test_shopping_list_rejects_partially_unknown_dish_ids",
                "test_red_black_unknown_target_is_404_and_db_unchanged",
            ],
            "result": "pass",
        },
        {
            "requirement": "推荐分数有限且符合 SSOT 展示范围",
            "tests": ["test_recommend_accepts_legal_boundaries_with_finite_scores"],
            "result": "pass",
            "detail": "radar 0–100；total_score 0–100；decay 0–1；四权重和≈1",
        },
        {
            "requirement": "数据库前后状态断言",
            "tests": [
                "全部 *_db_unchanged / *_keeps_* 用例 + data/live_api_probe.json",
            ],
            "result": "pass",
        },
        {
            "requirement": "写入只落隔离库",
            "tests": ["conftest 内存库 + live probe 前后受保护库哈希"],
            "result": "pass",
            "detail": "demo / S10 / dev_source 三库 SHA-256 前后一致",
        },
    ],
    "pending_adjudications": pending,
    "out_of_scope_gaps": gaps,
    "stop_reason": "S02/r01 证据包已提交；等待 Codex 独立复审。未修改 STAGE_STATUS、未自签 PASS、未开始 S03、未触碰 /admin 或 S10。",
}

(OUT / "validation.json").write_text(
    json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "status": validation["status"],
            "targeted": validation["checks"]["targeted_final"]["summary"],
            "full": validation["checks"]["full_final"]["summary"],
            "live_steps": validation["checks"]["live_http_probe"]["steps"],
            "pending": len(pending),
            "gaps": len(gaps),
        },
        ensure_ascii=False,
        indent=2,
    )
)
