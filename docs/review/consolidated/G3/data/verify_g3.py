"""从 G3 原始 JSONL/SQLite 独立复算规模与曲线，不调用汇总器的合并逻辑。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "docs/review/consolidated/G3/data"
DETAIL = BASE / "parallel_full"
BENCHMARK = json.loads((BASE / "parallel_benchmark_full.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def curve_from_details(arm: str) -> tuple[list[float], dict]:
    per_day = defaultdict(lambda: [0, 0])
    rows_total = 0
    for shard in range(8):
        path = DETAIL / f"detail_seed20261029_shard{shard:02d}_{arm}.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows_total += len(rows)
        for row in rows:
            bucket = per_day[int(row["day"])]
            bucket[1] += 1
            bucket[0] += int(bool(row["duplicated"]))
    curve = []
    duplicate = 0
    total = 0
    for day in range(1, 15):
        duplicate += per_day[day][0]
        total += per_day[day][1]
        curve.append(round(duplicate / total, 4) if total else 0.0)
    return curve, {"rows": rows_total, "duplicates_first_14d": duplicate, "meals_first_14d": total}


ours, ours_counts = curve_from_details("ours")
baseline, baseline_counts = curve_from_details("baseline")
expected = BENCHMARK["duplication_rate_curve"]
group_db = DETAIL / "sim_seed20261029_groups.db"
connection = sqlite3.connect(f"file:{group_db.as_posix()}?mode=ro", uri=True)
rooms = connection.execute("SELECT COUNT(*) FROM group_rooms").fetchone()[0]
votes = connection.execute("SELECT COUNT(*) FROM room_votes").fetchone()[0]
room_sizes = dict(connection.execute("SELECT cnt, COUNT(*) FROM (SELECT room_code, COUNT(*) cnt FROM room_votes GROUP BY room_code) GROUP BY cnt").fetchall())
connection.close()
bridge = json.loads((BASE / "bridge_provenance.json").read_text(encoding="utf-8"))
source_db = ROOT / "backend/eatwhat_g3_bridge_iso.db"
source_unchanged = sha256(source_db) == bridge["target_sha256"]
checks = {
    "ours_24000_rows": ours_counts["rows"] == 24000,
    "baseline_24000_rows": baseline_counts["rows"] == 24000,
    "ours_curve_recomputed": ours == expected["ours_lambda_0.5"],
    "baseline_curve_recomputed": baseline == expected["baseline_no_decay"],
    "rooms_1000": rooms == 1000,
    "votes_40000": votes == 40000,
    "every_room_40_votes": room_sizes == {40: 1000},
    "source_db_unchanged": source_unchanged,
    "no_reported_errors": BENCHMARK["params"]["errors"] == [],
}
payload = {
    "checks": checks,
    "overall_ok": all(checks.values()),
    "ours_recomputed": ours,
    "baseline_recomputed": baseline,
    "detail_counts": {"ours": ours_counts, "baseline": baseline_counts},
    "group": {"rooms": rooms, "votes": votes, "room_vote_sizes": room_sizes},
    "source_sha256": sha256(source_db),
    "source_unchanged_since_bridge": source_unchanged,
}
(BASE / "g3_verification.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
