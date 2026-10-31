"""生成 S01/r01 的身份矩阵与 validation.json。"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path("docs/review/stages/S01/r01")
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

live = json.loads((BASE / "data/live_identity_probe.json").read_text(encoding="utf-8"))
browser = json.loads((BASE / "browser/browser_evidence.json").read_text(encoding="utf-8"))
dbp = json.loads((BASE / "data/db_protection.json").read_text(encoding="utf-8"))
man = json.loads((BASE / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
http_statuses = [row["status"] for row in live["http"]]

matrix = {
    "step": "S01",
    "round": "r01",
    "contract": "MASTER_SPEC v2.3.5 §5.0",
    "status_codes": {
        "missing_header": "422",
        "empty_header": "422",
        "non_integer_header": "422",
        "zero_or_negative_header": "422",
        "beyond_int64_header": "422",
        "unknown_user": "404",
        "path_header_mismatch": "403 (existing semantics; SSOT does not explicitly rule path conflicts)",
        "body_or_query_mismatch": "200 as header identity + identity_conflict log",
        "room_non_member": "403",
        "ws_invalid_or_non_member": "HTTP 403 handshake rejection",
        "public_demo_list": "200 without identity",
    },
    "public_entries": [
        {"path": "GET /api/v1/users/demo-list", "identity": "none", "note": "global demo persona list; not bound to current user"},
        {"path": "GET /api/v1/context/weather", "identity": "none", "note": "context endpoint"},
        {"path": "GET /api/v1/catalog/dishes", "identity": "none", "note": "read-only catalog"},
        {"path": "GET /api/v1/catalog/restaurants", "identity": "none", "note": "read-only catalog"},
        {"path": "GET /health", "identity": "none", "note": "health"},
    ],
    "private_entries": [
        {"path": "GET /api/v1/users/{user_id}/profile", "identity_source": "path+header", "conflict": "path mismatch 403", "missing": "422", "unknown": "404"},
        {"path": "PUT /api/v1/users/{user_id}/preferences", "identity_source": "path+header", "conflict": "path mismatch 403", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/users/{user_id}/red-black-list", "identity_source": "path+header", "conflict": "path mismatch 403", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/recommend/single", "identity_source": "header; body user_id is non-authoritative", "conflict": "header wins + log", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/logs/checkin", "identity_source": "header; body user_id is non-authoritative", "conflict": "header wins + log", "missing": "422", "unknown": "404"},
        {"path": "GET /api/v1/logs/stats/{user_id}", "identity_source": "path+header", "conflict": "path mismatch 403", "missing": "422", "unknown": "404"},
        {"path": "GET /api/v1/fridge/{user_id}", "identity_source": "path+header", "conflict": "path mismatch 403", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/fridge/{user_id}", "identity_source": "path+header", "conflict": "path mismatch 403", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/fridge/shopping-list", "identity_source": "header; body user_id is non-authoritative", "conflict": "header wins + log", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/rooms/create", "identity_source": "header; body host_user_id is non-authoritative", "conflict": "header wins + log", "missing": "422", "unknown": "404"},
        {"path": "POST /api/v1/rooms/{code}/join", "identity_source": "header; body user_id is non-authoritative", "conflict": "header wins + log; repeat join idempotent", "missing": "422", "unknown": "404"},
        {"path": "GET /api/v1/rooms/{code}", "identity_source": "header; membership required", "conflict": "non-member 403", "missing": "422", "unknown": "404"},
        {"path": "WS /ws/room/{room_code}/{user_id}", "identity_source": "path; optional X-User-Id must match", "conflict": "path/header mismatch 403; non-member 403; unknown user 403", "missing": "path required by contract", "unknown": "403 handshake"},
        {"path": "WS START_SWIPING", "identity_source": "path member + host check", "conflict": "non-host gets ERROR detail", "missing": "n/a", "unknown": "n/a"},
    ],
    "design_gap": {
        "id": "S01-GAP-01",
        "topic": "path user_id vs X-User-Id conflict status code",
        "ssot": "MASTER_SPEC says body/query user_id must match X-User-Id and header wins with a log; path conflicts are not explicitly ruled.",
        "existing_code_before_S01": "ensure_self returned 403 for path mismatch, and allowed missing header.",
        "this_round": "keeps 403 for path mismatch; missing/invalid header is now 422 instead of silent allow/fallback.",
        "action_required": "User/Codex must confirm whether path conflicts stay 403 or are resolved as header-scoped reads before changing product semantics.",
    },
}
(BASE / "data/identity_matrix.json").write_text(
    json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

validation = {
    "step": "S01",
    "round": "r01",
    "generated_at": NOW,
    "status": "SUBMITTED_FOR_REVIEW",
    "self_signed_pass": False,
    "prior_clearance": {
        "step": "S00",
        "round": "r01",
        "conclusion": "PASS",
        "report": "docs/review/clearance-codex-s00-r01/REPORT.md",
        "manifest_fingerprint": "16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0",
    },
    "environment": {
        "python": "3.13.9",
        "node": "v24.19.0",
        "npm": "11.17.0",
        "pkgs": {
            "fastapi": "0.115.0",
            "sqlalchemy": "2.0.35",
            "pydantic": "2.13.3",
            "websockets": "16.0",
        },
    },
    "source_baseline": {
        "branch": "master",
        "head": None,
        "commit_count": 0,
        "manifest_file_count": len(man["files"]),
        "manifest_fingerprint": man["manifest_fingerprint"],
        "contract_version": "MASTER_SPEC v2.3.5",
        "git_status": man["git"]["status"],
    },
    "databases": dbp["databases"],
    "checks": [
        {
            "id": "red-baseline",
            "cwd": "D:/EatWhat/backend",
            "command": "python -m pytest -q -p no:cacheprovider tests/test_identity_s01.py",
            "started_at": "not captured; log completed 2026-10-26T00:14:33+08:00",
            "finished_at": "2026-10-26T00:14:33+08:00",
            "exit_code": 1,
            "result": "24 failed, 11 passed",
            "log": "logs/00_red_baseline.log",
        },
        {
            "id": "s01-special",
            "cwd": "D:/EatWhat/backend",
            "command": "python -m pytest -q -p no:cacheprovider tests/test_identity_s01.py",
            "started_at": "not captured (standalone run before the final full run)",
            "finished_at": "not captured (standalone run before the final full run)",
            "exit_code": 0,
            "result": "35 passed",
            "log": "logs/20_backend_pytest.log (included in full run)",
        },
        {
            "id": "backend-full",
            "cwd": "D:/EatWhat/backend",
            "command": "python -m pytest -q -p no:cacheprovider",
            "started_at": "2026-10-26T00:23:08+08:00",
            "finished_at": "2026-10-26T00:23:25+08:00",
            "exit_code": 0,
            "result": "210 passed, 1 skipped",
            "log": "logs/20_backend_pytest.log",
        },
        {
            "id": "frontend-build",
            "cwd": "D:/EatWhat/frontend",
            "command": "npm run build",
            "started_at": "2026-10-26T00:23:28+08:00",
            "finished_at": "2026-10-26T00:23:37+08:00",
            "exit_code": 0,
            "result": "775 modules transformed",
            "log": "logs/19_frontend_build_final.log",
        },
        {
            "id": "home-fit",
            "cwd": "D:/EatWhat",
            "command": "node scripts/home-fit.mjs",
            "started_at": "2026-10-26T00:19:34+08:00",
            "finished_at": "2026-10-26T00:19:55+08:00",
            "exit_code": 0,
            "result": "PASS 390x844 (card 422px, 50%) / 390x667 (card 261px, 39%); overlap 0",
            "log": "logs/13_home_fit.log",
        },
        {
            "id": "refill-fresh",
            "cwd": "D:/EatWhat",
            "command": "node scripts/refill-fresh.mjs",
            "started_at": "2026-10-26T00:19:58+08:00",
            "finished_at": "2026-10-26T00:20:17+08:00",
            "exit_code": 0,
            "result": "refill excluded 24, returned 24 new candidates",
            "log": "logs/15_refill-fresh.log",
        },
        {
            "id": "sandbox-sync",
            "cwd": "D:/EatWhat",
            "command": "node scripts/sandbox-sync.mjs",
            "started_at": "2026-10-26T00:20:17+08:00",
            "finished_at": "2026-10-26T00:20:20+08:00",
            "exit_code": 0,
            "result": "requests 1 -> 2; card and sandbox share the same request",
            "log": "logs/15_sandbox-sync.log",
        },
        {
            "id": "check-colors",
            "cwd": "D:/EatWhat",
            "command": "node scripts/check-colors.mjs",
            "started_at": "2026-10-26T00:20:20+08:00",
            "finished_at": "2026-10-26T00:20:20+08:00",
            "exit_code": 0,
            "result": "38 files, no bare hex/rgb/hsl",
            "log": "logs/16_check_colors.log",
        },
        {
            "id": "browser-role-switch",
            "cwd": "D:/EatWhat",
            "command": "node docs/review/stages/S01/r01/browser/run_role_switch.mjs",
            "started_at": "2026-10-26T00:30:41+08:00",
            "finished_at": "2026-10-26T00:31:03+08:00",
            "exit_code": 0,
            "result": (
                f"{browser['summary']['clicks']} real clicks; "
                f"before-switch wrong identity {browser['summary']['before_switch_wrong_identity']}; "
                f"{browser['summary']['after_switch_api_requests']} post-switch API requests; "
                f"{browser['summary']['after_switch_wrong_identity']} wrong identity; "
                "0 non-favicon console/exception errors; only /favicon.ico 404"
            ),
            "log": "logs/17_browser_role_switch.log",
        },
        {
            "id": "live-http-ws-probe",
            "cwd": "D:/EatWhat",
            "command": "python docs/review/stages/S01/r01/data/live_identity_probe.py",
            "started_at": "2026-10-26T00:31:11+08:00",
            "finished_at": "2026-10-26T00:31:12+08:00",
            "exit_code": 0,
            "result": f"{len(live['http'])} HTTP cases {http_statuses}; WS rejected/accepted as expected; demo-list identical",
            "log": "logs/18_live_identity_probe.log",
        },
        {
            "id": "manifest",
            "cwd": "D:/EatWhat",
            "command": "python docs/review/stages/S01/r01/data/build_manifest.py",
            "started_at": "not captured",
            "finished_at": "2026-10-26T00:25:32+08:00",
            "exit_code": 0,
            "result": f"{len(man['files'])} files; fingerprint {man['manifest_fingerprint']}",
            "log": "data/build_manifest.stdout.txt",
        },
    ],
    "tests": {
        "s01_special_file": "35 passed",
        "backend_full": "210 passed, 1 skipped",
        "red_baseline": "24 failed, 11 passed",
        "new_tests_added": 35,
        "historical_skip": "1 (Windows symlink permission, unchanged)",
    },
    "stop_reason": "evidence package complete; waiting for independent Codex review",
    "notes": [
        "No PASS is self-signed; STAGE_STATUS.md was not modified.",
        "The isolated run database is backend/eatwhat_s01_r01_iso.db copied from eatwhat_dev_pre00_r02.db; demo and S10 databases were not written.",
        "Path conflict status code remains 403 pending a user/Codex decision (S01-GAP-01).",
        "S07 multiplayer swiping remains DEFERRED; only REST/WS identity entries were exercised.",
        "Browser run used a fresh Chrome profile: pre-switch requests were all user 1, post-switch all user 2; the only failed resource was the pre-existing /favicon.ico 404.",
    ],
}
(BASE / "validation.json").write_text(
    json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"manifest": man["manifest_fingerprint"], "http_statuses": http_statuses, "browser": browser["summary"]}, ensure_ascii=False, indent=2))
