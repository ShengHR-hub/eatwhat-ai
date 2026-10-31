"""对缺失清单里的菜再试一轮更贴合的叫法；只在"标题像这道菜"时才采用。

规则比自动批更严：
  * 查询词需至少命中 1 个核心词（去停用词后）
  * 标题里出现 chart/receipt/rock/plant/diagram/sign/menu 等一律否掉
  * 尺寸 ≥500 宽
用了哪些查询、为什么仍是缺失，都会写回 docs/_data/image_missing.json。

用法：python scripts/recover_missing.py [--dry]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import fetch_dish_images as f  # noqa: E402
from PIL import Image  # noqa: E402

QUERIES = {
    "酸辣土豆丝": ["hot and sour potato", "shredded potato stir fry"],
    "青椒土豆丝": ["green pepper potato", "shredded potato"],
    "韭菜炒鸡蛋": ["chive scrambled egg", "chinese chives"],
    "洋葱炒蛋": ["onion scrambled egg", "onion omelette"],
    "酸辣白菜": ["pickled cabbage", "suancai", "sour cabbage"],
    "蒜蓉生菜": ["lettuce stir fry", "garlic lettuce"],
    "西芹百合": ["celery lily bulb", "stir fried celery"],
    "玉米排骨汤": ["corn soup", "sweetcorn soup"],
    "电饭煲焖饭": ["claypot rice", "rice cooker"],
    "腊肠煲仔饭": ["claypot rice", "chinese sausage rice"],
    "电饭煲青菜粥": ["congee", "rice porridge"],
    "空气炸锅薯条": ["french fries", "potato fries"],
    "凉拌木耳": ["wood ear mushroom", "black fungus salad"],
    "一锅出番茄牛腩": ["beef brisket", "braised beef"],
    "一锅出土豆炖鸡": ["chicken stew", "braised chicken"],
    "凉拌折耳根": ["houttuynia", "fish mint"],
}

BAD = re.compile(
    r"(chart|diagram|graph|receipt|sign|menu|poster|map|logo|rock|stone|plant|leaf|flower|butterfl|insect|bird|phase|ticket|bill)",
    re.I,
)
STOP = {"with", "and", "the", "of", "in", "on", "a", "an", "soup", "bowl", "dish", "rice", "stir", "fried"}


def core_tokens(q: str) -> list[str]:
    return [t for t in re.split(r"[^a-z]+", q.lower()) if len(t) > 2 and t not in STOP]


def ok_title(title: str, query: str) -> bool:
    if BAD.search(title):
        return False
    toks = core_tokens(query)
    if not toks:
        return False
    low = title.lower()
    return any(t in low for t in toks)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    rows = {r["name"]: r for r in f.parse_plan()}
    missing = {m["file"]: m for m in json.loads(f.MISSING.read_text(encoding="utf-8"))}
    ledger = {e["file"]: e for e in json.loads(f.LEDGER.read_text(encoding="utf-8"))}
    s = f.session()
    recovered = 0

    for key, m in list(missing.items()):
        name = m["name"]
        row = rows.get(name)
        if not row or key not in {r["file"] for r in rows.values()}:
            continue
        queries = QUERIES.get(name)
        if not queries:
            continue
        print(f"[retry] {name}")
        tried = list(m.get("tried") or [])
        page = None
        for q in queries:
            tried.append(f"Commons search: {q}")
            cands = f.search(s, q)
            good = [
                p
                for p in cands
                if (p["imageinfo"][0].get("width") or 0) >= f.MIN_SRC_WIDTH and ok_title(p.get("title", ""), q)
            ]
            if good:
                good.sort(key=lambda p: -f.score(p, q))
                page = good[0]
                print(f"   hit: {page['title']}")
                break
        if not page:
            m["tried"] = tried
            print("   ✗ 仍无合格图")
            continue
        if args.dry:
            print("   (dry) 不落盘")
            continue
        info = page["imageinfo"][0]
        raw = f.download(s, info.get("thumburl") or info["url"])
        if not raw:
            continue
        dest = f.OUT_DIR / row["file"]
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
            "picked_by": "recover",
        }
        del missing[key]
        recovered += 1
        print(f"   ✓ {dest.name} ({dest.stat().st_size // 1024} KB) {ledger[row['file']]['license']}")

    if not args.dry:
        f.LEDGER.write_text(json.dumps(sorted(ledger.values(), key=lambda e: e["file"]), ensure_ascii=False, indent=2), encoding="utf-8")
        f.MISSING.write_text(json.dumps(sorted(missing.values(), key=lambda e: e["file"]), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nrecovered {recovered}, still missing {len(missing)}")


if __name__ == "__main__":
    main()
