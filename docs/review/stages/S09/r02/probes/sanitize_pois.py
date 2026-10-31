"""把高德原始 POI 压缩为契约所需字段，去除电话/邮箱/图片/评论等非必要信息。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=str(DATA / "amap_pois.jsonl"))
    parser.add_argument("--dst", default=str(DATA / "amap_pois.jsonl"))
    parser.add_argument("--campus", default="SIYUAN")
    parser.add_argument("--source-dataset", default="amap_place_around_20261025")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    src_path = Path(args.src)
    dst_path = Path(args.dst)
    tmp_path = dst_path.with_suffix(dst_path.suffix + ".tmp")
    rows = 0
    with src_path.open(encoding="utf-8") as src, tmp_path.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            p = json.loads(line)
            biz = p.get("biz_ext") if isinstance(p.get("biz_ext"), dict) else None
            rating = biz.get("rating") if biz else p.get("rating")
            cost = biz.get("cost") if biz else p.get("cost")

            def clean(value):
                return None if value in (None, "", []) else value

            out = {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("type"),
                "typecode": p.get("typecode"),
                "address": p.get("address"),
                "location": p.get("location"),
                "distance": p.get("distance"),
                "tag": clean(p.get("tag")),
                "rating": clean(rating),
                "cost": clean(cost),
                "pname": p.get("pname"),
                "cityname": p.get("cityname"),
                "adname": p.get("adname"),
                "business_area": clean(p.get("business_area")),
                "_distance_m": p.get("_distance_m"),
                "campus": args.campus,
                "is_synthetic": 0,
                "source_dataset": args.source_dataset,
            }
            dst.write(json.dumps(out, ensure_ascii=False) + "\n")
            rows += 1
    tmp_path.replace(dst_path)
    print(json.dumps({"rows": rows, "path": str(dst_path), "campus": args.campus}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
