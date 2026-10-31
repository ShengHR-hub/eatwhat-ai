"""从脱敏 POI 文件统计 rating/cost/tag 的有值数与缺失数，并回填 collection JSON。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"
TARGETS = (
    ("SIYUAN", "amap_pois.jsonl", "amap_collection.json"),
    ("JIANDA_YANTA", "amap_jianda_pois.jsonl", "amap_jianda_collection.json"),
)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    summary = {}
    for campus, poi_name, collection_name in TARGETS:
        poi_path = DATA / poi_name
        rows = [json.loads(line) for line in poi_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        total = len(rows)
        stats = {"total": total}
        for field in ("rating", "cost", "tag"):
            present = sum(1 for row in rows if row.get(field) not in (None, "", []))
            stats[f"{field}_present"] = present
            stats[f"{field}_missing"] = total - present
        stats["c10_poi_only_not_plotted_no_rating"] = stats["rating_missing"]
        summary[campus] = stats

        collection_path = DATA / collection_name
        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        collection.update(
            {
                "rating_present": stats["rating_present"],
                "rating_missing": stats["rating_missing"],
                "cost_present": stats["cost_present"],
                "cost_missing": stats["cost_missing"],
                "tag_present": stats["tag_present"],
                "tag_missing": stats["tag_missing"],
                "field_stats_source": poi_name,
                "field_stats_note": "有值=非 null/空字符串/空数组；缺失保持 NULL，不填默认值；C10 只绘 rating 非空点。",
            }
        )
        collection_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")

    out = DATA / "poi_field_stats.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "out": str(out)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
