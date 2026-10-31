"""S11 预检：不产生任何付费调用的批次计划、覆盖现状与阻塞判定。"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DB = ROOT / "backend" / "eatwhat_g2_s10_full.db"
DATA = Path(__file__).resolve().parent
OUT = DATA / "s11_preflight.json"
COVERAGE = DATA / "coverage.json"
FEATURE_KEYS = [
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
]


def run_dry_run() -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    command = [
        sys.executable,
        "-m",
        "backend.scripts.llm_batch_tagger",
        "--db",
        str(DB),
        "--dry-run",
        "--summary-out",
        str(DATA / "s11_dryrun_full.json"),
    ]
    result = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr[-1000:])
    return json.loads((DATA / "s11_dryrun_full.json").read_text(encoding="utf-8"))


def main() -> None:
    dry = run_dry_run()
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        status_counts = {
            row["tagging_status"] or "NULL": row["count"]
            for row in connection.execute(
                "SELECT tagging_status, COUNT(*) AS count FROM dishes_and_recipes "
                "WHERE mode_type='HOME_COOKING' GROUP BY tagging_status"
            )
        }
        total_home = connection.execute(
            "SELECT COUNT(*) FROM dishes_and_recipes WHERE mode_type='HOME_COOKING'"
        ).fetchone()[0]
        with_vector = connection.execute(
            "SELECT COUNT(*) FROM dishes_and_recipes WHERE mode_type='HOME_COOKING' AND feature_vector IS NOT NULL"
        ).fetchone()[0]
        with_tags = connection.execute(
            "SELECT COUNT(*) FROM dishes_and_recipes WHERE mode_type='HOME_COOKING' AND allergen_tags IS NOT NULL"
        ).fetchone()[0]
        vectors = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT feature_vector FROM dishes_and_recipes WHERE mode_type='HOME_COOKING' AND feature_vector IS NOT NULL"
            ).fetchall()
        ]
        anomalies = []
        for vector in vectors:
            if not isinstance(vector, dict) or set(vector.keys()) != set(FEATURE_KEYS):
                anomalies.append("keys_or_type")
                continue
            for key in FEATURE_KEYS:
                value = vector[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
                    anomalies.append(key)
        cuisine_counts = Counter(
            row["cuisine_type"] or "NULL"
            for row in connection.execute(
                "SELECT cuisine_type FROM dishes_and_recipes WHERE mode_type='HOME_COOKING'"
            )
        )
        recipe_rows = connection.execute(
            "SELECT id, name, cuisine_type, dish_role, cook_minutes FROM dishes_and_recipes "
            "WHERE mode_type='HOME_COOKING' ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    sample_size = 50
    step = max(1, len(recipe_rows) // sample_size)
    samples = [
        {
            "dish_id": row["id"],
            "name": row["name"],
            "cuisine_type": row["cuisine_type"],
            "dish_role": row["dish_role"],
            "cook_minutes": row["cook_minutes"],
        }
        for row in recipe_rows[::step][:sample_size]
    ]

    credentials = {
        "api_key_present": bool(os.getenv("LLM_API_KEY")),
        "base_url_present": bool(os.getenv("LLM_BASE_URL")),
        "model_env_present": bool(os.getenv("LLM_MODEL")),
        "model_arg_confirmed": False,
        "budget_confirmed": False,
        "prompt_version": dry["prompt_version"],
        "batch_size": dry["batch_size"],
        "max_calls_with_retries": dry["max_calls_with_retries"],
        "retry_limit": 3,
    }
    blocked = not (
        credentials["api_key_present"]
        and credentials["base_url_present"]
        and credentials["model_arg_confirmed"]
        and credentials["budget_confirmed"]
    )

    coverage = {
        "db": str(DB),
        "mode": "HOME_COOKING",
        "total_dishes": total_home,
        "tagging_status": status_counts,
        "with_feature_vector": with_vector,
        "with_allergen_tags": with_tags,
        "success_coverage": round(with_vector / total_home, 6) if total_home else 0.0,
        "feature_values_success_x8": with_vector * 8,
        "vector_anomalies": len(anomalies),
        "vector_anomaly_examples": anomalies[:10],
        "cuisine_distribution": dict(cuisine_counts),
        "sample_50": samples,
    }
    COVERAGE.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "db": str(DB),
        "status": "BLOCKED" if blocked else "READY",
        "blocked_reason": (
            "未确认 LLM Key / 模型版本 / 预算上限，按 G2 要求不发起付费全量调用"
            if blocked
            else ""
        ),
        "credentials": credentials,
        "dry_run": {
            "model": dry["model"],
            "prompt_version": dry["prompt_version"],
            "batch_size": dry["batch_size"],
            "dish_count": dry["dish_count"],
            "batch_count": dry["batch_count"],
            "max_calls_with_retries": dry["max_calls_with_retries"],
            "estimated_input_tokens": dry["estimated_input_tokens"],
            "estimated_output_tokens": dry["estimated_output_tokens"],
            "budget_usd": dry["budget_usd"],
        },
        "coverage_file": str(COVERAGE),
        "coverage": {key: coverage[key] for key in (
            "total_dishes",
            "tagging_status",
            "with_feature_vector",
            "success_coverage",
            "vector_anomalies",
        )},
        "network_calls": 0,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "blocked_reason", "dry_run", "coverage", "network_calls")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
