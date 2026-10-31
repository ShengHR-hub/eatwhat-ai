"""S11 查询预算：不同候选规模下的 SQL 条数与结果等价性（扩容库上复测）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DB = ROOT / "backend" / "eatwhat_g2_bridge_iso.db"
OUT = Path(__file__).resolve().parent / "query_budget.json"
PYTHON = sys.executable


def measure(mode: str, limit: int, legacy: bool = False) -> dict:
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
    env["PYTHONIOENCODING"] = "utf-8"
    command = [PYTHON, "-m", "backend.scripts.measure_recommend_sql", "--mode", mode, "--limit", str(limit)]
    if legacy:
        command.append("--legacy")
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-800:])
    return json.loads(result.stdout)


def main() -> None:
    sizes = [5, 10, 24]
    rows = []
    for mode in ("OUT_DINING", "HOME_COOKING"):
        for limit in sizes:
            rows.append({"mode": mode, "limit": limit, **measure(mode, limit)})
    legacy = {
        "OUT_DINING": measure("OUT_DINING", 10, legacy=True),
        "HOME_COOKING": measure("HOME_COOKING", 10, legacy=True),
    }
    optimised = {row["mode"]: row for row in rows if row["limit"] == 10}

    fridge_counts = {f"{row['mode']}:{row['limit']}": row["fridge_inventory_statements"] for row in rows}
    totals = {f"{row['mode']}:{row['limit']}": row["total_statements"] for row in rows}
    same_results = {
        mode: legacy[mode]["top3"] == optimised[mode]["top3"] for mode in legacy
    }
    payload = {
        "db": str(DB),
        "measurements": rows,
        "legacy": legacy,
        "constant_fridge_queries": all(
            fridge_counts[f"HOME_COOKING:{limit}"] == 1
            and fridge_counts[f"OUT_DINING:{limit}"] == 0
            for limit in sizes
        ),
        "fridge_counts": fridge_counts,
        "total_statements": totals,
        "no_per_dish_growth": len(set(totals.values())) <= 1,
        "legacy_fridge_queries": {
            mode: legacy[mode]["fridge_inventory_statements"] for mode in legacy
        },
        "same_top3_as_legacy": same_results,
        "ok": all(
            fridge_counts[f"HOME_COOKING:{limit}"] == 1
            and fridge_counts[f"OUT_DINING:{limit}"] == 0
            for limit in sizes
        )
        and all(same_results.values()),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "constant_fridge_queries", "total_statements", "legacy_fridge_queries", "same_top3_as_legacy", "ok"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
