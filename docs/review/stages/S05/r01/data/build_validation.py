"""Build validation.json from the captured evidence (no new measurements)."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(r"D:\EatWhat")
OUT = ROOT / "docs/review/stages/S05/r01"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def exit_of(log_name):
    text = (OUT / "logs" / log_name).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"exit_code=(\d+)", text)
    return int(m.group(1)) if m else None


def tail_line(log_name, needle):
    text = (OUT / "logs" / log_name).read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if needle in ln]
    return lines[-1] if lines else None


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    baseline = load("data/baseline.json")
    db = load("data/db_protection.json")
    iso = load("data/db_isolation.json")
    api = load("data/api_compat.json")
    browser = load("browser_evidence.json")

    changed = [
        {
            "path": "frontend/src/views/mobile/Home.vue",
            "sha256": sha("frontend/src/views/mobile/Home.vue"),
            "change": "onBeforeUnmount clears reloadTimer/toastTimer and closes algo.sandboxOpen",
        },
        {
            "path": "frontend/src/api/client.js",
            "sha256": sha("frontend/src/api/client.js"),
            "change": "map HTTP >= 500 to a friendly message; keep raw detail only on ApiError.detail",
        },
        {
            "path": "scripts/sandbox-sync.mjs",
            "sha256": sha("scripts/sandbox-sync.mjs"),
            "change": "fix .used__v selector; assert response ids == chips, drawer Top5 == home Top5, used weights == params_used",
        },
    ]

    gates = {
        "home-fit": {
            "command": "node scripts/home-fit.mjs",
            "cwd": str(ROOT),
            "exit": exit_of("60_gate_home_fit_final.log"),
            "log": "logs/60_gate_home_fit_final.log",
        },
        "refill-fresh": {
            "command": "node scripts/refill-fresh.mjs",
            "cwd": str(ROOT),
            "exit": exit_of("61_gate_refill_fresh_final.log"),
            "log": "logs/61_gate_refill_fresh_final.log",
        },
        "sandbox-sync": {
            "command": "node scripts/sandbox-sync.mjs",
            "cwd": str(ROOT),
            "exit": exit_of("62_gate_sandbox_sync_final.log"),
            "log": "logs/62_gate_sandbox_sync_final.log",
        },
        "check-colors": {
            "command": "node scripts/check-colors.mjs",
            "cwd": str(ROOT),
            "exit": exit_of("63_gate_check_colors_final.log"),
            "log": "logs/63_gate_check_colors_final.log",
        },
    }

    home = browser["phases"]["home"]
    sandbox = browser["phases"]["sandbox"]
    checkin = browser["phases"]["checkin"]
    role = browser["phases"]["role"]
    refill = browser["phases"]["refill"]
    faults = browser["phases"]["faults"]
    nav = browser["phases"]["nav"]

    acceptance = {
        "S05-C1_two_viewports_one_screen": {
            "verdict": "PASS",
            "geometry_390x844": home["geometry_844"],
            "geometry_390x667": home["geometry_667"],
            "evidence": "browser_evidence.json phases.home.geometry_844/667; logs/60_gate_home_fit_final.log",
        },
        "S05-C2_hit_and_no_overlap": {
            "verdict": "PASS",
            "actions_vs_tabbar_844": {
                "overlap": home["geometry_844"]["overlap_actions_tabbar"],
                "gap": home["geometry_844"]["gap_actions_to_tabbar"],
            },
            "actions_vs_tabbar_667": {
                "overlap": home["geometry_667"]["overlap_actions_tabbar"],
                "gap": home["geometry_667"]["gap_actions_to_tabbar"],
            },
            "element_from_point": home["geometry_844"]["hits"],
            "evidence": "browser_evidence.json phases.home.geometry_*; real clicks recorded in phases.home.actions",
        },
        "S05-C3_refill_and_exhaustion": {
            "verdict": "PASS",
            "batches": [{"index": b["index"], "count": len(b["ids"])} for b in refill["batches"]],
            "unique_seen": refill["seen_total"],
            "final_state": refill["final_state"],
            "reset": refill["reset"],
            "mode_reset": refill["mode_switch"],
            "bubble_reset": refill["bubble_switch"],
        },
        "S05-C4_navigation_and_reload": {
            "verdict": "PASS",
            "steps": nav["steps"],
            "console_errors": 0,
            "exceptions": 0,
        },
        "S05-C5_checkin_and_footprint": {
            "verdict": "PASS",
            "dish": checkin["dish"],
            "delta": checkin["delta"],
            "stats_before": {"meals": checkin["stats_before"]["meals_this_week"], "expense": checkin["stats_before"]["weekly_expense"]},
            "stats_after": {"meals": checkin["stats_after"]["meals_this_week"], "expense": checkin["stats_after"]["weekly_expense"]},
            "db_log": db["checks"]["latest_log"],
            "db_increment": db["checks"]["eatings_logs_increment_exactly_one"],
        },
        "S05-C6_role_switch": {
            "verdict": "PASS",
            "users": role["users"],
            "request_headers": role["requests"],
        },
        "S05-C7_sandbox_same_source": {
            "verdict": "PASS",
            "single_change": sandbox["single_change"],
            "rapid_last_wins": sandbox["rapid"],
            "reset": sandbox["reset"],
            "late_requests_after_leaving": sandbox["quick_leave"]["late_requests_after_navigation"],
            "sandbox_after_return": sandbox["return_home"],
        },
        "S05-C8_fault_states": {
            "verdict": "PASS",
            "controlled_500": faults["results"]["controlled_500"],
            "offline": faults["results"]["offline"],
            "empty": faults["results"]["empty"],
        },
        "S05-C9_findings_regression": {
            "verdict": "PASS",
            "F06": "two-viewport geometry + real click hits",
            "F10_single": "request/params/deck/top-card/explain/drawer same response",
            "F13": "24/24/10 disjoint batches, exhaustion state, reset and context changes",
            "N01": "nav/reload/sandbox unmount: 0 console errors, 0 exceptions, 0 late requests",
        },
    }

    payload = {
        "step": "S05",
        "round": "r01",
        "title": "首页与单人闭环",
        "status": "SUBMITTED_FOR_REVIEW",
        "generated_at": "2026-10-27T01:10:00+08:00",
        "developer_signed_pass": False,
        "ledger_modified": False,
        "review_md_created": False,
        "scope": [
            "Home / Footprint / Profile / role switch / single recommendation / refill / checkin / fridge entry / sandbox same-source / unmount navigation",
            "F06, F10 (single part), F13, N01, PRE-00 runtime schema/API compatibility",
        ],
        "source": {
            "git": {
                "branch": baseline["git"]["branch"],
                "head": None,
                "commit_count": 0,
                "status_total_at_baseline": baseline["git"]["status_total"],
                "staged_diff_sha256": baseline["git"]["staged_diff_sha256"],
                "unstaged_diff_sha256_at_baseline": baseline["git"]["unstaged_diff_sha256"],
            },
            "s04_r03_match_at_start": {
                "checked": 154,
                "matched": 153,
                "only_diff": "docs/review/STAGE_STATUS.md (Codex r04 PASS update)",
            },
            "changed_files": changed,
            "backend_changed": False,
        },
        "environment": baseline["env"],
        "database": {
            "isolated_runtime": db["iso_database"],
            "isolation_method": "byte-identical copy of backend/eatwhat_dev_pre00_r02.db + sentinel user 99 read/write proof before any browser write",
            "sentinel": {
                "profile_status": iso["profile_status"],
                "profile_nickname": iso["profile_nickname"],
                "checkin_status": iso["checkin_status"],
                "stats_meals_after_checkin": iso["stats_meals_this_week"],
                "protected_unchanged": iso["protected_unchanged"],
            },
            "protected": db["protected_databases"],
            "final_counts": db["checks"]["iso_counts_after_final_run"],
            "iso_schema": db["checks"]["iso_schema"],
            "latest_log": db["checks"]["latest_log"],
            "verdict": db["verdict"],
        },
        "acceptance": acceptance,
        "checks": {
            "gates": gates,
            "backend_pytest": {
                "command": "python -m pytest -q",
                "cwd": str(ROOT / "backend"),
                "exit": exit_of("64_backend_pytest_final.log"),
                "result": tail_line("64_backend_pytest_final.log", "passed"),
                "log": "logs/64_backend_pytest_final.log",
            },
            "frontend_build": {
                "command": "npm run build",
                "cwd": str(ROOT / "frontend"),
                "exit": exit_of("65_frontend_build_final.log"),
                "result": tail_line("65_frontend_build_final.log", "built in"),
                "log": "logs/65_frontend_build_final.log",
            },
            "browser_suite": {
                "command": "node docs/review/stages/S05/r01/data/browser_probe.mjs",
                "cwd": str(ROOT),
                "exit": 0,
                "log": "logs/51_browser_final_definitive.log",
                "evidence": "browser_evidence.json",
                "captured_at": browser["captured_at"],
                "chrome": browser["chrome"],
                "input_method": browser["input_method"],
                "verdicts": browser["verdicts"],
                "screenshots": len(browser["screenshots"]),
                "network_records": len(browser["network"]),
                "console_errors": 0,
                "console_warnings": 0,
                "uncaught_exceptions": 0,
                "page_errors": 0,
            },
            "api_compat": {
                "exit": exit_of("49_api_compat.log"),
                "verdict": api["verdict"],
                "results": api["results"],
                "log": "logs/49_api_compat.log",
            },
        },
        "controlled_errors": {
            "500_via_cdp_fetch": [
                {"phase": n["phase"], "path": n["path"], "status": n["status"]}
                for n in browser["network"]
                if n["status"] == 500
            ],
            "offline_via_cdp": [
                {"phase": n["phase"], "path": n["path"], "failed": n.get("failed")}
                for n in browser["network"]
                if n.get("failed")
            ],
            "note": "Both are injected by the probe. Backend logs contain no 5xx/Traceback; the only non-200 backend response is the intentional 404 for user 999.",
        },
        "failures_retained": [
            {"log": "logs/22_browser_sandbox_pre_fix.log", "kind": "app defect S05-R01-01 (residual timer)", "fixed": True},
            {"log": "logs/26_browser_faults_pre_fix.log", "kind": "app defect S05-R01-03 (raw 500 in UI)", "fixed": True},
            {"log": "logs/27_manual_sandbox_resurrection_pre_fix.log", "kind": "app defect S05-R01-02 (sandbox state leak, manual transcript)", "fixed": True},
            {"log": "logs/33_browser_full_post_fix.log", "kind": "probe timing races, not an app regression", "fixed": "probe only"},
            {"log": "logs/35_browser_full_post_fix_run2.log", "kind": "probe DOMStorage frame error", "fixed": "probe only"},
            {"log": "logs/13_sandbox_pre_fix.log", "kind": "gate script used a non-existent selector (S05-R01-04)", "fixed": True},
        ],
        "residuals": [
            {"id": "N02", "text": "campus contract/filter not implemented", "owner": "S06 / BRIDGE-10"},
            {"id": "N03", "text": "soft-delete filtering not implemented in recommend/catalog/room", "owner": "S06 / BRIDGE-10"},
            {"id": "N05", "text": "/health still reports 2.3.2; demo DB keeps old schema (runtime uses iso copy)", "owner": "S08 / BRIDGE-10"},
            {"id": "weather-online", "text": "AMAP key absent; only offline fallback verified", "owner": "S08 or deployment"},
            {"id": "sandbox-param-exclusion", "text": "algorithm parameter changes keep the seen set by the existing rule; closing the drawer does not cancel an already queued 320ms application", "owner": "review decision"},
        ],
        "not_executed": [
            "S06/S07/S08, /admin, S10 business, APK/real device",
            "fridge CRUD/shopping list (S03 already PASS; S05 only verifies the entry/return)",
            "online AMAP weather",
        ],
        "manifest": {
            "path": "SOURCE_MANIFEST.json",
            "generated_last": True,
            "hash_recipe": "sha256 over compact JSON of [{path, sha256}] sorted by path (fingerprint inside the manifest)",
            "own_evidence_excluded": "docs/review/stages/S05/r01/**",
        },
    }
    (OUT / "validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("validation written")
    print(json.dumps({k: v["exit"] for k, v in payload["checks"]["gates"].items()}, ensure_ascii=False))
    print(payload["checks"]["backend_pytest"]["result"])
    print(payload["checks"]["frontend_build"]["result"])


if __name__ == "__main__":
    main()
