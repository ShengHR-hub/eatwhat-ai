"""生成 S02/r02 validation.json（机器可读摘要，不代表 PASS）。"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path("docs/review/stages/S02/r02")
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
    entry["field"] for entry in boundary["entries"] if entry["status"] == "CODE_DERIVED_PENDING"
]
gaps = [
    {"field": entry["field"], "owner": entry.get("owner"), "note": entry.get("note")}
    for entry in boundary["entries"]
    if entry["status"] == "OUT_OF_SCOPE_GAP"
]

validation = {
    "step": "S02",
    "round": "r02",
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
    "prior_review": {
        "step": "S02",
        "round": "r01",
        "conclusion": "FAIL",
        "report": "docs/review/clearance-codex-s02-r01/REPORT.md",
        "manifest_fingerprint": "eb17fe30bea0b2c3e530da3465006504944af480f88d65ba4724ce0e17f9b03f",
        "findings": [
            "S02-R01-01：历史非法向量可通过非向量偏好更新继续持久化",
            "S02-R01-02：历史未知键在向量更新中被静默丢弃",
        ],
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
            "summary": last_summary(OUT / "logs/12_backend_pytest_s02_final.log"),
            "log": "logs/12_backend_pytest_s02_final.log",
        },
        "full_baseline_before_change": {
            "command": "python -m pytest -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": "210 passed, 1 skipped (S01/r01 受审基线)",
            "log": "docs/review/stages/S01/r01/logs/20_backend_pytest.log",
        },
        "full_final": {
            "command": "python -m pytest -q -p no:cacheprovider",
            "cwd": "D:/EatWhat/backend",
            "exit_code": 0,
            "summary": last_summary(OUT / "logs/10_backend_pytest_full.log"),
            "log": "logs/10_backend_pytest_full.log",
        },
        "live_http_probe": {
            "command": "DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s02_r02_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8014",
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
            "requirement": "所有偏好更新路径先校验历史向量（复审 S02-R01-01）",
            "tests": [
                "test_invalid_history_blocks_every_update_path[budget_only-*]",
                "test_invalid_history_blocks_every_update_path[veto_only-*]",
                "test_invalid_history_blocks_every_update_path[cuisine_only-*]",
                "test_invalid_history_blocks_every_update_path[vector_only-*]",
                "history_out_of_range_blocks_budget_only（live）",
            ],
            "result": "pass",
        },
        {
            "requirement": "历史未知键不得被静默丢弃（复审 S02-R01-02）",
            "tests": [
                "test_invalid_history_blocks_every_update_path[*-unknown_key]",
                "test_full_vector_cannot_bypass_invalid_history[unknown_key]",
                "history_unknown_key_blocks_vector_update（live）",
            ],
            "result": "pass",
        },
        {
            "requirement": "非法历史向量下预算/忌口/菜系均不提交，数据库完全不变",
            "tests": [
                "test_invalid_history_blocks_every_update_path（9 状态 × 4 路径）",
                "test_invalid_history_blocks_combined_update",
                "live history_* 用例",
            ],
            "result": "pass",
            "detail": "409；base_vector/default_budget/veto_tags/preferred_cuisines/红黑榜快照前后一致",
        },
        {
            "requirement": "合法但缺键的历史向量按 0.5 补齐（任何更新路径）",
            "tests": [
                "test_valid_but_incomplete_history_is_completed_on_every_update_path",
                "history_incomplete_valid_filled_on_budget_update（live）",
            ],
            "result": "pass",
        },
        {
            "requirement": "历史合法完整时，预算/忌口/菜系更新不改变向量",
            "tests": ["test_valid_complete_history_keeps_vector_on_non_vector_updates"],
            "result": "pass",
        },
        {
            "requirement": "原有 r01 验收项保持通过",
            "tests": ["r01 保留的 45 条", "live 其余 40 步"],
            "result": "pass",
        },
    ],
    "pending_adjudications": pending,
    "out_of_scope_gaps": gaps,
    "stop_reason": "S02/r02 证据包已提交；等待 Codex 独立复审。未修改 STAGE_STATUS、未自签 PASS、未开始 S03、未触碰 /admin 或 S10。",
}

(OUT / "validation.json").write_text(
    json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "status": validation["status"],
            "red": validation["checks"]["red_baseline"]["summary"],
            "targeted": validation["checks"]["targeted_final"]["summary"],
            "full": validation["checks"]["full_final"]["summary"],
            "live_steps": validation["checks"]["live_http_probe"]["steps"],
            "live_statuses": validation["checks"]["live_http_probe"]["statuses"],
            "pending": len(pending),
            "gaps": len(gaps),
        },
        ensure_ascii=False,
        indent=2,
    )
)
