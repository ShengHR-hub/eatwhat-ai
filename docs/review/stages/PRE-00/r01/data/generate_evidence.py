"""生成 PRE-00/r01 的 SOURCE_MANIFEST.json 与 validation.json（可复跑）。"""

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(".").resolve()
OUT = Path("docs/review/stages/PRE-00/r01")
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked(path):
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


files = []


def add(path, kind):
    p = Path(path)
    files.append(
        {
            "path": p.as_posix(),
            "sha256": sha(p),
            "size": p.stat().st_size,
            "kind": kind,
            "git_tracked": tracked(p.as_posix()),
        }
    )


for p in sorted(Path("backend").rglob("*.py")):
    if "__pycache__" in p.parts:
        continue
    kind = "test" if p.parts[1] == "tests" else ("script" if p.parts[1] == "scripts" else "source")
    add(p, kind)
add("backend/scripts/benchmark_snapshot.json", "data")
add("requirements.txt", "dependency_manifest")
add("pytest.ini", "config")
add("frontend/package.json", "dependency_lock")
add("frontend/package-lock.json", "dependency_lock")
for p in (
    "AGENTS.md",
    "MASTER_SPEC.md",
    "docs/AGENT_MEMORY.md",
    "docs/REVIEW_RULES.md",
    "docs/review/STAGE_STATUS.md",
    "docs/review/PRE_S10_REMEDIATION_PLAN.md",
):
    add(p, "contract")
for p in (
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00.db",
):
    add(p, "database_baseline")

status_lines = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True
).stdout.splitlines()
staged_diff = hashlib.sha256(
    subprocess.run(["git", "diff", "--cached", "--binary"], capture_output=True).stdout
).hexdigest()

manifest = {
    "step": "PRE-00",
    "round": "r01",
    "generated_at": NOW,
    "workspace": str(ROOT),
    "hash_algorithm": "sha256",
    "contract_version": "MASTER_SPEC v2.3.5",
    "git": {
        "branch": "master",
        "head": None,
        "commit_count": 0,
        "staged_diff_sha256": staged_diff,
        "status": {
            "staged": sum(1 for line in status_lines if len(line) > 1 and line[0] not in " ?"),
            "unstaged": sum(1 for line in status_lines if len(line) > 1 and line[1] not in " ?"),
            "untracked": sum(1 for line in status_lines if line.startswith("??")),
            "note": "仓库尚无 commit；新迁移脚本与测试为未跟踪文件，已按路径与 SHA 固定",
        },
    },
    "files": files,
    "excluded": [
        "docs/review/**（本轮证据文件，自身不参与受审源码清单）",
        "**/__pycache__/**",
        "frontend/src/**（PRE-00 未改前端业务代码；依赖仅锁 package.json/package-lock.json）",
    ],
}
manifest["manifest_fingerprint"] = hashlib.sha256(
    json.dumps(
        [(item["path"], item["sha256"]) for item in files],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
).hexdigest()
(OUT / "SOURCE_MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("SOURCE_MANIFEST.json files=", len(files), "fingerprint=", manifest["manifest_fingerprint"])

base = json.loads((OUT / "data/baseline.json").read_text(encoding="utf-8"))
run1 = json.loads((OUT / "data/migration_run1.json").read_text(encoding="utf-8"))
run2 = json.loads((OUT / "data/migration_run2.json").read_text(encoding="utf-8"))
post = json.loads((OUT / "logs/14_post_summary.json").read_text(encoding="utf-8"))
prot = json.loads((OUT / "data/final_protection.json").read_text(encoding="utf-8"))
fail = json.loads((OUT / "data/failure_rollback.json").read_text(encoding="utf-8"))
pre_schema = json.loads((OUT / "data/pre_schema.json").read_text(encoding="utf-8"))
post_schema = json.loads((OUT / "data/post_schema.json").read_text(encoding="utf-8"))

validation = {
    "step": "PRE-00",
    "round": "r01",
    "generated_at": NOW,
    "status": "SUBMITTED_FOR_REVIEW",
    "self_signed_pass": False,
    "environment": {
        "python": "3.13.9",
        "node": "v24.19.0",
        "npm": "11.17.0",
        "fastapi": "0.115.0",
        "sqlalchemy": "2.0.35",
        "pydantic": "2.13.3",
        "httpx": "0.28.1",
        "pytest": "9.0.3",
    },
    "source_baseline": {
        "head": None,
        "branch": "master",
        "commit_count": 0,
        "staged_diff_sha256": manifest["git"]["staged_diff_sha256"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
    },
    "databases": {
        "demo": {
            "path": "backend/eatwhat.db",
            "sha256": base["databases"]["backend/eatwhat.db"]["sha256"],
            "unchanged_after": prot["databases"]["backend/eatwhat.db"]["unchanged"],
            "rows": prot["databases"]["backend/eatwhat.db"]["rows"],
        },
        "s10_import": {
            "path": "backend/eatwhat_batch4.db",
            "sha256": base["databases"]["backend/eatwhat_batch4.db"]["sha256"],
            "unchanged_after": prot["databases"]["backend/eatwhat_batch4.db"]["unchanged"],
            "rows": prot["databases"]["backend/eatwhat_batch4.db"]["rows"],
        },
        "dev_runtime": {
            "path": "backend/eatwhat_dev_pre00.db",
            "created_from_demo_sha256": base["databases"]["backend/eatwhat.db"]["sha256"],
            "sha256_before_migration": run1["sha256_before"],
            "sha256_after_migration": run1["sha256_after"],
            "sha256_after_second_run": run2["sha256_after"],
            "rows_after": prot["databases"]["backend/eatwhat_dev_pre00.db"]["rows"],
        },
    },
    "reproduction_before_migration": {
        "server": {
            "url": "http://127.0.0.1:8031",
            "database_url": "sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00.db",
        },
        "health": {"status": 200, "body": {"status": "ok", "version": "2.3.2"}},
        "recommend_single": {
            "status": 500,
            "error": "sqlite3.OperationalError: no such column: dishes_and_recipes.allergen_tags",
            "log": "logs/02_server_pre_migration.log",
        },
        "logs_stats": {
            "status": 500,
            "error": "sqlite3.OperationalError: no such column: dishes_and_recipes.allergen_tags",
            "log": "logs/02_server_pre_migration.log",
        },
    },
    "migration": {
        "script": "backend/scripts/migrate_pre00_runtime_schema.py",
        "version": "pre00_runtime_v1",
        "target": "backend/eatwhat_dev_pre00.db",
        "run1": {
            "exit_code": 0,
            "added_columns": run1["added_columns"],
            "rebuilt_tables": run1["rebuilt_tables"],
            "feature_vector_nullable_before": run1["feature_vector_nullable_before"],
            "feature_vector_nullable_after": run1["feature_vector_nullable_after"],
            "schema_fingerprint_before": run1["schema_fingerprint_before"],
            "schema_fingerprint_after": run1["schema_fingerprint_after"],
            "row_counts": run1["row_counts"],
            "foreign_key_check": run1["foreign_key_check"],
            "sha256_before": run1["sha256_before"],
            "sha256_after": run1["sha256_after"],
        },
        "run2": {
            "exit_code": 0,
            "idempotent": run2["idempotent"],
            "added_columns": run2["added_columns"],
            "rebuilt_tables": run2["rebuilt_tables"],
            "schema_fingerprint_before": run2["schema_fingerprint_before"],
            "schema_fingerprint_after": run2["schema_fingerprint_after"],
            "sha256_before": run2["sha256_before"],
            "sha256_after": run2["sha256_after"],
        },
        "idempotent_byte_identical": run1["sha256_after"] == run2["sha256_after"] == run2["sha256_before"],
        "schema_tables_before": {table: value["rows"] for table, value in pre_schema.items()},
        "schema_tables_after": {table: value["rows"] for table, value in post_schema.items()},
        "orm_model_parity": {
            "ok": True,
            "missing": [],
            "nullability_mismatch": [],
            "log": "logs/18_model_schema_parity.log",
        },
    },
    "after_migration": {
        "server": {
            "url": "http://127.0.0.1:8032",
            "database_url": "sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00.db",
        },
        "health": {"status": post["health"]["status"], "body": post["health"]["body"]},
        "recommend_out_dining": {
            "status": post["recommend_out_dining"]["status"],
            "count": post["recommend_out_dining"]["count"],
            "top_dish_id": post["recommend_out_dining"]["top_dish_id"],
            "top_score": post["recommend_out_dining"]["top_score"],
            "contract_keys_ok": post["recommend_out_dining"]["has_contract_keys"],
            "scores_finite_in_range": post["recommend_out_dining"]["scores_finite_in_range"],
            "radar_keys_ok": post["recommend_out_dining"]["radar_keys_ok"],
        },
        "recommend_home_cooking": {
            "status": post["recommend_home_cooking"]["status"],
            "count": post["recommend_home_cooking"]["count"],
            "scores_finite_in_range": post["recommend_home_cooking"]["scores_finite_in_range"],
        },
        "logs_stats": {
            "status": post["logs_stats"]["status"],
            "keys": post["logs_stats"]["keys"],
            "cooling_count": post["logs_stats"]["cooling_count"],
            "weekly_expense": post["logs_stats"]["weekly_expense"],
            "meals_this_week": post["logs_stats"]["meals_this_week"],
        },
    },
    "failure_counterexamples": {
        "guard_demo": {
            "exit_code": 1,
            "log": "logs/15_guard_refusal.log",
            "demo_sha_unchanged": prot["databases"]["backend/eatwhat.db"]["unchanged"],
        },
        "guard_s10": {
            "exit_code": 1,
            "log": "logs/15_guard_refusal.log",
            "s10_sha_unchanged": prot["databases"]["backend/eatwhat_batch4.db"]["unchanged"],
        },
        "preflight_missing_table": {
            "exit_code": fail["preflight"]["exit_code"],
            "schema_unchanged": fail["preflight"]["schema_unchanged"],
            "file_sha_unchanged": fail["preflight"]["file_sha_unchanged"],
        },
        "mid_transaction_rollback": {
            "exit_code": fail["midtx"]["exit_code"],
            "schema_unchanged": fail["midtx"]["schema_unchanged"],
            "file_sha_unchanged": fail["midtx"]["file_sha_unchanged"],
            "restaurants_campus_present_after": fail["midtx"]["after"]["restaurants_campus_present"],
            "feature_vector_notnull_after": fail["midtx"]["after"]["feature_vector_notnull"],
        },
    },
    "no_s10_cross_wiring": {
        "assertion": "dev runtime uses backend/eatwhat_dev_pre00.db (4 users / 100 dishes); S10 import DB rows were never read by the demo flow",
        "dev_rows": prot["databases"]["backend/eatwhat_dev_pre00.db"]["rows"],
        "s10_rows": prot["databases"]["backend/eatwhat_batch4.db"]["rows"],
        "s10_sha_unchanged": prot["databases"]["backend/eatwhat_batch4.db"]["unchanged"],
    },
    "tests": {
        "pre00_regression": {
            "exit_code": 0,
            "result": "5 passed",
            "log": "logs/06_pytest_pre00.log",
        },
        "full_backend_isolated": {
            "exit_code": 0,
            "result": "173 passed",
            "log": "logs/17_pytest_full_isolated.log",
            "isolation": "DATABASE_URL=sqlite:///D:/EatWhat/backend/_pytest_pre00.db；测试库未生成",
        },
    },
    "exit_codes": {
        "baseline_capture": 0,
        "migration_run1": 0,
        "migration_run2": 0,
        "pytest_pre00": 0,
        "pytest_full_isolated": 0,
        "guard_demo_expected": 1,
        "guard_s10_expected": 1,
        "failure_preflight_expected": 1,
        "failure_midtx_expected": 1,
        "schema_parity": 0,
        "final_protection": 0,
    },
    "known_limits": [
        "未改前端，未跑 npm run build；PRE-00 范围仅后端运行库兼容层。",
        "未实现 v2.3.4 campus 推荐过滤；POST /recommend/single 当前不接受 campus，留待 S05/BRIDGE-10 对应步骤。",
        "开发运行库为演示库副本，不含 S10 导入数据；BRIDGE-10 才验证只读/导入边界。",
        "本包不签 PASS；结论仅为 SUBMITTED_FOR_REVIEW，等待 Codex 独立审查。",
    ],
}
(OUT / "validation.json").write_text(
    json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("validation.json written; status=", validation["status"])
