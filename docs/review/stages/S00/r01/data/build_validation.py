"""生成 S00/r01 validation.json。"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path("docs/review/stages/S00/r01")
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

manifest = json.loads((OUT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
baseline = json.loads((OUT / "data/baseline.json").read_text(encoding="utf-8"))
protection = json.loads((OUT / "data/db_protection.json").read_text(encoding="utf-8"))
state = json.loads((OUT / "data/current_state.json").read_text(encoding="utf-8"))
defects = json.loads((OUT / "data/defects.json").read_text(encoding="utf-8"))["items"]
matrix = json.loads((OUT / "data/verification_matrix.json").read_text(encoding="utf-8"))["steps"]

by_step = {}
for item in defects:
    by_step.setdefault(item["step"], []).append(item["id"])

def db_entry(name):
    return {
        "path": name,
        "sha256": protection["after"][name]["sha256"],
        "size": protection["after"][name]["size"],
        "schema_fingerprint": baseline["databases"][name]["schema_fingerprint"],
        "rows": protection["after"][name]["rows"],
        "unchanged_after_readonly_probe": protection["after"][name]["unchanged"],
    }

validation = {
    "step": "S00",
    "round": "r01",
    "generated_at": NOW,
    "status": "SUBMITTED_FOR_REVIEW",
    "self_signed_pass": False,
    "prior_clearance": {
        "step": "PRE-00",
        "round": "r02",
        "conclusion": "PASS",
        "report": "docs/review/clearance-codex-pre00-r02/REPORT.md",
    },
    "environment": baseline["environment"],
    "source_baseline": {
        "branch": manifest["git"]["branch"],
        "head": manifest["git"]["head"],
        "commit_count": manifest["git"]["commit_count"],
        "staged_diff_sha256": manifest["git"]["staged_diff_sha256"],
        "git_status_counts": manifest["git"]["status"],
        "manifest_file_count": len(manifest["files"]),
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "contract_version": manifest["contract_version"],
    },
    "databases": {
        "demo": db_entry("backend/eatwhat.db"),
        "s10_import": db_entry("backend/eatwhat_batch4.db"),
        "dev_runtime": db_entry("backend/eatwhat_dev_pre00_r02.db"),
        "sidecars_after": protection["sidecars_after"],
        "originals_unchanged": protection["originals_unchanged"],
        "dev_unchanged": protection["dev_unchanged"],
        "writes_performed": False,
    },
    "current_state": {
        "server": state["server"],
        "frontend": state["frontend"],
        "entries": state["entries"],
        "interfaces": state["interfaces"],
        "interpretation": state["interpretation"],
        "internal_server_error_observed": False,
        "browser_clicked": False,
    },
    "baseline_checks": {
        "backend_pytest": {
            "exit_code": 0,
            "result": "175 passed, 1 skipped, 505 warnings in 10.38s",
            "isolation": "DATABASE_URL=sqlite:///D:/EatWhat/backend/_pytest_s00.db；测试库未生成",
            "log": "logs/02_pytest_full_isolated.log",
        },
        "frontend_build": {
            "exit_code": 0,
            "result": "✓ built in 18.79s",
            "log": "logs/03_frontend_build.log",
        },
        "check_colors": {
            "exit_code": 0,
            "result": "38 个文件无裸 hex / rgb / hsl",
            "log": "logs/04_check_colors.log",
        },
        "browser_gates": {
            "executed": False,
            "reason": "S00 不做真实点击；S05/S08 必做",
            "commands": baseline["commands"]["browser_gates"],
        },
    },
    "defects": {
        "count": len(defects),
        "ids": [item["id"] for item in defects],
        "by_step": by_step,
        "new_findings": ["N02", "N03", "N04", "N05"],
        "deferred": ["S07"],
        "residual_open": [item["id"] for item in defects if item["status"] in ("RESIDUAL_OPEN", "PARTIAL_OPEN", "OPEN_NEW", "BASELINE_RISK")],
        "evidence_path": "FINDINGS.md; data/defects.json",
    },
    "verification_matrix": {
        "steps": list(matrix.keys()),
        "s07_status": matrix["S07"]["status"],
        "s07_not_executed": matrix["S07"]["not_executed"],
        "evidence_path": "VERIFICATION_MATRIX.md; data/verification_matrix.json",
    },
    "old_evidence_policy": {
        "old_reports_are_not_current_pass": True,
        "statement": "旧审查、旧截图、旧账本、开发方自测只作线索；每条缺陷在 FINDINGS 中标注旧证据为何不能直接视为当前 PASS",
    },
    "limitations": [
        "S00 未做真实浏览器点击、写库复现或多人 WS；这些留给 S05/S06/S08。",
        "演示库仍是旧 schema；只能通过 dev_pre00_r02 或临时副本运行。",
        "S10 双校区/软删除/NULL 向量尚未接线；N02–N04 为潜在缺口。",
        "仓库无 commit，版本由逐文件 SHA + staged diff SHA 固定。",
        "本包不签 PASS、未改台账、未开始下一步。",
    ],
    "exit_codes": {
        "git_status": 0,
        "baseline_capture": 0,
        "pytest_full_isolated": 0,
        "frontend_build": 0,
        "check_colors": 0,
        "db_before_server": 0,
        "http_probes": 0,
        "db_after_server": 0,
        "latent_db_conditions": 0,
        "fridge_boundary_probe": 0,
        "f01_f13_readonly_probe": 0,
        "compose_state": 0,
        "build_defects_matrix": 0,
        "build_manifest": 0,
        "final_checks": 0,
        "no_source_changes": 0,
        "expected_failure_wrong_path_404": 404,
        "unexecuted_browser_gates": None,
    },
}

(OUT / "validation.json").write_text(
    json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
fp = hashlib.sha256(
    json.dumps(validation, ensure_ascii=False, sort_keys=True).encode()
).hexdigest()
print(json.dumps({"status": validation["status"], "defects": len(defects), "manifest_fingerprint": manifest["manifest_fingerprint"], "validation_sha256": fp}, ensure_ascii=False, indent=2))
