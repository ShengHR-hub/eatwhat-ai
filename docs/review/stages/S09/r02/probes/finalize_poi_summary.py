"""把 3km 直接查询 count 与网格去重结果合并；只读证据，不写数据库。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    summary = json.loads((DATA / "amap_collection.json").read_text(encoding="utf-8"))
    probe = json.loads((DATA / "amap_pagination_probe.json").read_text(encoding="utf-8"))
    pages = {item["page"]: item for item in probe["pages"]}
    direct = pages.get(1, {}).get("count")
    direct_int = int(direct) if direct not in (None, "") else None
    summary["direct_3km_query"] = {
        "count": direct_int,
        "pages_probed": probe["pages"],
        "page_1_returned": pages.get(1, {}).get("returned"),
        "page_8_returned": pages.get(8, {}).get("returned"),
        "page_9_returned": pages.get(9, {}).get("returned"),
        "note": "同参数翻页最多 200 条；page 9 起为空。直接 count 是 API 自身计数。",
    }
    if direct_int is not None:
        summary["collected_vs_direct_difference"] = summary["real_poi_count"] - direct_int
    summary["count_note"] = (
        "直接查询 count 与网格去重后的 haversine<=3000m 结果分别报告；"
        "前者是 AMap 计数，后者是实际落盘/去重结果。两者不等时不得用其中一个冒充另一个。"
    )
    summary["target_shortfall"] = max(0, 1500 - summary["real_poi_count"])
    summary["target_note"] = (
        "D03 已于 2026-10-25 裁决：接受实际 real_poi_count 为样本 A；"
        "目标差额仅作历史记录，不再作为 S10 阻塞；禁止合成补足、跨校区挪用或混算。"
    )
    summary["d03_decision"] = "ACCEPT_ACTUAL_AS_SAMPLE_A"
    (DATA / "amap_collection.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: summary.get(k) for k in (
        "checked_at", "center_gcj02", "direct_3km_query", "raw_pois", "unique_pois",
        "within_3km_before_typecode_filter", "non_dining_excluded", "real_poi_count",
        "synthetic_canteen_count", "total_restaurants_target_if_200_canteen",
        "target_1500_met", "target_shortfall", "errors", "incomplete_cells",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
