"""S11 完成后只读核验：覆盖率、八维向量、模型一致性、账本和分层抽样。"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

FEATURE_KEYS = {
    "spicy_level", "oily_level", "soup_level", "temp_fit",
    "satiety_level", "prep_speed", "social_fit", "comfort_level",
}
VALID_ROLES = {"MEAT", "VEG", "SOUP", "ONE_MEAL"}


def as_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gemini-3.7-flash")
    args = parser.parse_args()

    connection = sqlite3.connect(f"file:{args.db.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT id, name, cuisine_type, dish_role, feature_vector, allergen_tags, "
        "tagging_status, tagging_error, llm_meta FROM dishes_and_recipes "
        "WHERE mode_type='HOME_COOKING' ORDER BY id"
    ).fetchall()

    status = Counter()
    models = Counter()
    anomalies = []
    valid_success = []
    by_cuisine = defaultdict(list)
    for row in rows:
        status[row["tagging_status"] or "NULL"] += 1
        if row["tagging_status"] != "SUCCESS":
            continue
        try:
            vector = as_json(row["feature_vector"], {})
            tags = as_json(row["allergen_tags"], [])
            meta = as_json(row["llm_meta"], {})
        except (TypeError, json.JSONDecodeError) as exc:
            anomalies.append({"dish_id": row["id"], "reason": f"json:{type(exc).__name__}"})
            continue
        models[meta.get("model", "MISSING")] += 1
        reason = ""
        if set(vector) != FEATURE_KEYS:
            reason = "vector_keys"
        elif any(
            isinstance(vector[key], bool)
            or not isinstance(vector[key], (int, float))
            or not math.isfinite(float(vector[key]))
            or not 0 <= float(vector[key]) <= 1
            for key in FEATURE_KEYS
        ):
            reason = "vector_value"
        elif row["dish_role"] not in VALID_ROLES:
            reason = "dish_role"
        elif not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            reason = "allergen_tags"
        if reason:
            anomalies.append({"dish_id": row["id"], "reason": reason})
            continue
        item = {
            "dish_id": row["id"],
            "name": row["name"],
            "cuisine_type": row["cuisine_type"],
            "dish_role": row["dish_role"],
            "feature_vector": vector,
            "allergen_tags": tags,
        }
        valid_success.append(item)
        by_cuisine[row["cuisine_type"] or "UNKNOWN"].append(item)
    connection.close()

    ledger_rows = []
    for ledger_path in args.ledger:
        if ledger_path.exists():
            ledger_rows.extend(
                json.loads(line)
                for line in ledger_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    valid_ledger_ids = {
        dish_id
        for row in ledger_rows
        if row.get("valid")
        for dish_id in row.get("dish_ids", [])
    }
    ledger_cost = sum(float(row.get("estimated_cost_usd", 0)) for row in ledger_rows)
    vector_fingerprints = {
        tuple(float(item["feature_vector"][key]) for key in sorted(FEATURE_KEYS))
        for item in valid_success
    }
    all_half = sum(
        all(float(item["feature_vector"][key]) == 0.5 for key in FEATURE_KEYS)
        for item in valid_success
    )

    # 各菜系按 ID 排序后轮流取样，保证覆盖不同菜系且恰好 50 条。
    sample = []
    depth = 0
    cuisines = sorted(by_cuisine)
    while len(sample) < 50 and cuisines:
        added = False
        for cuisine in cuisines:
            group = by_cuisine[cuisine]
            if depth < len(group) and len(sample) < 50:
                sample.append(group[depth])
                added = True
        if not added:
            break
        depth += 1
    sample.sort(key=lambda item: item["dish_id"])

    checks = {
        "total_6400": len(rows) == 6400,
        "success_6400": status.get("SUCCESS", 0) == 6400,
        "no_vector_anomalies": not anomalies,
        "single_model": set(models) == {args.model},
        "valid_ledger_ids_6400": len(valid_ledger_ids) == 6400,
        "no_all_half_vectors": all_half == 0,
        "vectors_have_variation": len(vector_fingerprints) > 1,
        "sample_50": len(sample) == 50,
    }
    payload = {
        "db": str(args.db.resolve()),
        "total_dishes": len(rows),
        "tagging_status": dict(status),
        "models": dict(models),
        "valid_success": len(valid_success),
        "vector_anomalies": anomalies,
        "unique_vector_count": len(vector_fingerprints),
        "all_half_vector_count": all_half,
        "ledger": {
            "files": [str(path.resolve()) for path in args.ledger],
            "response_rows": len(ledger_rows),
            "valid_response_rows": sum(bool(row.get("valid")) for row in ledger_rows),
            "valid_dish_ids": len(valid_ledger_ids),
            "estimated_cost_usd": round(ledger_cost, 8),
            "input_tokens": sum((row.get("usage") or {}).get("prompt_tokens", 0) for row in ledger_rows),
            "output_tokens": sum((row.get("usage") or {}).get("completion_tokens", 0) for row in ledger_rows),
        },
        "checks": checks,
        "overall_ok": all(checks.values()),
        "sample": sample,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "total_dishes", "tagging_status", "models", "valid_success",
        "unique_vector_count", "all_half_vector_count", "checks", "overall_ok",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
