"""人工指定图片：按 Commons 文件标题精确取件，覆盖自动挑选的结果。

用法：python scripts/apply_picks.py            # 执行 PICKS 里的全部条目
      python scripts/apply_picks.py --drop     # 只执行 DROP 里的删除（并记入缺失清单）

PICKS 的键是菜名，值是要用的 Commons 文件标题（必须带 "File:" 前缀）。
DROP 里是"自动命中的图明显不对、Commons 又没有合适替代"的菜：删文件并记缺失，
不拿别的菜顶（口径见 docs/DISH_IMAGES_PLAN.md）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")
import fetch_dish_images as f  # noqa: E402
from PIL import Image  # noqa: E402

PICKS = {
    "宫保鸡丁": "File:Kung Pao Chicken With Rice.jpg",
    "麻婆豆腐": "File:Mapo Tofu (麻婆豆腐).jpg",
    "烧鹅拼饭": "File:Roast Goose with Rice and Choy Sum.JPG",
    "藜麦鸡胸沙拉": "File:Quinoa salad (29307761548).jpg",
    "番茄炒蛋": "File:Hunan cuisine, stir-fried tomato with eggs.jpg",
    "西红柿炒蛋": "File:Hunan cuisine, stir-fried tomato with eggs.jpg",
    "蒜蓉西兰花": "File:Black pan with stir-fried vegetables (broccoli, onion, red pepper).jpg",
}

# 删掉并记入缺失清单的（菜名 → 剔除原因）
DROP = {
    # 自动检索/二次恢复都没能命中"这道菜"的：宁可缺图，也不拿别的菜顶
    "酸辣土豆丝": "自动命中为米饭拼盘，Commons 无合格成品图",
    "凉拌折耳根": "只检索到生鲜植株图，无凉拌成品图",
    "青椒土豆丝": "只检索到牛肉/生土豆丝，无成品图",
    "韭菜炒鸡蛋": "命中的是热狗图，非本菜",
    "洋葱炒蛋": "命中的是得州 Migas，非中式洋葱炒蛋",
    "酸辣白菜": "命中的是腌菜罐照片，非成品菜",
    "玉米排骨汤": "命中的是尼日利亚玉米糊汤，非本菜",
    "腊肠煲仔饭": "与「电饭煲焖饭」同图且无腊肠，避免误导",
    "凉拌木耳": "命中的是木耳生长照，非凉拌成品",
    "一锅出番茄牛腩": "只有清汤排骨图，不是番茄牛腩，退回缺失",
    "一锅出土豆炖鸡": "命中的是肉末碟，不是炖鸡，退回缺失",
    "番茄麻辣烫": "与「麻辣烫套餐」同图，避免重复，等确认是否复用",
    "骨汤麻辣烫": "与「麻辣烫套餐」同图，避免重复，等确认是否复用",
}

LEDGER = Path("docs/_data/image_ledger.json")
MISSING = Path("docs/_data/image_missing.json")
PLAN = Path("docs/DISH_IMAGES_PLAN.md")


def rows_by_name() -> dict[str, dict]:
    return {r["name"]: r for r in f.parse_plan()}


def info_for_title(s, title: str) -> dict:
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": "1600",
    }
    for attempt in range(4):
        f.throttle()
        r = s.get(f.API, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(8 * (attempt + 1))
            continue
        r.raise_for_status()
        pages = (r.json().get("query") or {}).get("pages") or {}
        for p in pages.values():
            if p.get("imageinfo"):
                return p
        raise SystemExit(f"取不到 {title} 的 imageinfo")
    raise SystemExit(f"429 太频繁，放弃 {title}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true")
    ap.add_argument("--skip-picks", action="store_true")
    args = ap.parse_args()

    rows = rows_by_name()
    ledger = {e["file"]: e for e in json.loads(LEDGER.read_text(encoding="utf-8"))} if LEDGER.exists() else {}
    missing = {m["file"]: m for m in json.loads(MISSING.read_text(encoding="utf-8"))} if MISSING.exists() else {}
    s = f.session()

    for name, title in ({} if args.skip_picks else PICKS).items():
        row = rows.get(name)
        if not row:
            print(f"?? 清单里没有 {name}")
            continue
        dest = f.OUT_DIR / row["file"]
        print(f"[pick] {name} <- {title}")
        page = info_for_title(s, title)
        info = page["imageinfo"][0]
        raw = f.download(s, info.get("thumburl") or info["url"])
        if not raw:
            print("   ✗ 下载失败")
            continue
        size = f.process(raw, dest)
        meta = info.get("extmetadata") or {}
        ledger[row["file"]] = {
            "name": name,
            "cuisine": row["cuisine"],
            "dish_ids": row["ids"],
            "file": row["file"],
            "source_page": info.get("descriptionurl"),
            "original": info.get("url"),
            "license": (meta.get("LicenseShortName") or {}).get("value"),
            "license_url": (meta.get("LicenseUrl") or {}).get("value"),
            "author": re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value") or "").strip(),
            "src_size": list(size),
            "out_size": list(Image.open(dest).size),
            "bytes": dest.stat().st_size,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()[:16],
            "title": page.get("title"),
            "picked_by": "manual",
        }
        missing.pop(row["file"], None)
        print(f"   ✓ {dest.name} ({dest.stat().st_size // 1024} KB)")

    if args.drop or True:
        for name, reason in DROP.items():
            row = rows.get(name)
            if not row:
                continue
            dest = f.OUT_DIR / row["file"]
            if dest.exists():
                dest.unlink()
                print(f"[drop] {name} ({row['file']}) — {reason}")
            ledger.pop(row["file"], None)
            missing[row["file"]] = {
                "name": name,
                "cuisine": row["cuisine"],
                "file": row["file"],
                "query": row["query"],
                "tried": [f"Commons 自动检索（{row['query']}）无合格成品图", reason],
                "candidates": 0,
            }

    LEDGER.write_text(json.dumps(sorted(ledger.values(), key=lambda e: e["file"]), ensure_ascii=False, indent=2), encoding="utf-8")
    MISSING.write_text(json.dumps(sorted(missing.values(), key=lambda e: e["file"]), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nledger {len(ledger)} / missing {len(missing)}")


if __name__ == "__main__":
    main()
