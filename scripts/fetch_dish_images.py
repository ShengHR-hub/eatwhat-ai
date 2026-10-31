"""从 Wikimedia Commons 取菜品示意图，处理成 800x450 / JPEG 并落 frontend/public/dishes/。

用法：
    python scripts/fetch_dish_images.py            # 全部（跳过已存在的文件）
    python scripts/fetch_dish_images.py --limit 20 # 只跑前 20 张
    python scripts/fetch_dish_images.py --redo     # 已存在也重下

产物：
    frontend/public/dishes/<id>-<slug>.jpg
    docs/_data/image_ledger.json   （逐张：菜名/文件/来源页/授权/作者/尺寸/sha256）
    docs/_data/image_missing.json  （取不到：菜名/菜系/试过的查询）

设计口径（docs/DISH_IMAGES_PLAN.md）：
    * 只从 Commons 取（授权明确、可脚本取件）；取不到就记缺失，不拿别的菜顶。
    * 每张图先按文件名/标题与查询词的重合度排序，再核对尺寸，避免"词不达意"的图。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
UA = "EatWhatThesis/1.0 (graduation project; contact: local)"
OUT_DIR = Path("frontend/public/dishes")
LEDGER = Path("docs/_data/image_ledger.json")
MISSING = Path("docs/_data/image_missing.json")
PLAN = Path("docs/DISH_IMAGES_PLAN.md")

W, H, QUALITY = 800, 450, 82
MIN_SRC_WIDTH = 500

# Commons 的文件名多是拼音/意译混写，单一英文查询召回很差。
# 这里给英文查不到的菜补拼音或更常用的叫法（按实际命中情况逐批补）。
ALIASES = {
    "麻辣香锅": ["mala xiang guo", "malaxiangguo"],
    "水煮肉片": ["shuizhu roupian", "shuizhu"],
    "水煮鱼": ["shuizhu yu", "boiled fish sichuan"],
    "毛血旺": ["maoxuewang", "mao xue wang"],
    "辣子鸡": ["lazi ji", "chongqing chicken"],
    "干煸四季豆": ["ganbian sijidou", "dry fried beans"],
    "回锅肉": ["huiguo rou", "twice-cooked pork"],
    "宫保鸡丁": ["kung pao chicken", "gongbao jiding"],
    "麻婆豆腐": ["mapo tofu", "mapo doufu"],
    "鱼香肉丝": ["yuxiang rousi", "fish fragrant pork"],
    "鱼香茄子": ["yuxiang qiezi", "fish fragrant eggplant"],
    "肠粉": ["cheung fun", "rice noodle roll"],
    "云吞面": ["wonton noodle", "wonton soup noodle"],
    "干炒牛河": ["beef chow fun", "gon chao ngau ho"],
    "石锅拌饭": ["bibimbap", "dolsot bibimbap"],
    "部队锅": ["budae jjigae", "army stew"],
    "兰州牛肉拉面": ["lanzhou beef noodle", "lanzhou lamian"],
    "羊肉串": ["lamb skewer", "chuan"],
    "白灼虾": ["boiled prawns", "blanched shrimp"],
    "虾饺皇": ["har gow", "shrimp dumpling"],
    "烧鹅拼饭": ["roast goose rice", "siu ngo"],
    "蜜汁叉烧饭": ["char siu rice", "charsiu rice"],
    "白切鸡饭": ["white cut chicken", "bak chit gai"],
    "烧鸭饭": ["roast duck rice"],
    "皮蛋瘦肉粥": ["century egg congee", "pidan congee"],
    "酸辣土豆丝": ["shredded potato sour spicy", "tudousi"],
    "手撕包菜": ["hand torn cabbage", "shousi baocai"],
    "可乐鸡翅": ["cola chicken wings", "coke chicken wings"],
    "空气炸锅鸡翅": ["air fryer chicken wings", "fried chicken wings"],
    "空气炸锅薯条": ["french fries", "air fryer fries"],
    "电饭煲焖饭": ["rice cooker rice", "claypot rice"],
    "电饭煲茶叶蛋": ["tea egg", "chaye dan"],
    "电饭煲青菜粥": ["congee", "rice porridge vegetable"],
    "一锅出咖喱饭": ["curry rice", "japanese curry rice"],
    "一锅出番茄牛腩": ["beef brisket stew", "tomato beef stew"],
    "一锅出土豆炖鸡": ["chicken stew potato", "braised chicken potato"],
    "凉拌黄瓜": ["smashed cucumber", "cucumber salad"],
    "凉拌木耳": ["wood ear salad", "black fungus salad"],
    "凉拌鸡丝": ["shredded chicken salad"],
    "凉拌豆腐丝": ["tofu skin salad", "bean curd salad"],
    "西芹百合": ["celery lily bulb", "celery stir fry"],
    "蒜蓉西兰花": ["garlic broccoli", "broccoli stir fry"],
    "蒜蓉生菜": ["garlic lettuce", "lettuce stir fry"],
    "冬瓜排骨汤": ["winter melon soup", "wintermelon pork soup"],
    "玉米排骨汤": ["corn pork rib soup", "corn soup"],
    "菌菇鸡汤": ["chicken mushroom soup", "mushroom soup"],
    "排骨莲藕汤": ["lotus root soup", "pork rib soup"],
    "番茄蛋汤": ["tomato egg soup", "egg drop soup"],
    "紫菜蛋花汤": ["seaweed egg soup", "egg drop soup"],
    "老火靓汤": ["cantonese soup", "chinese soup"],
    "例汤": ["soup of the day", "chinese soup"],
    "清炒菜心": ["choy sum", "stir fried greens"],
    "砂锅豆腐": ["claypot tofu", "tofu hot pot"],
    "砂锅鸡": ["claypot chicken", "chicken hot pot"],
    # —— 第一批跑完仍缺的，补更口语/更宽的检索词 ——
    "酸辣土豆丝": ["shredded potato chili", "potato stir fry"],
    "青椒土豆丝": ["shredded potato", "potato stir fry"],
    "清汤牛肉面": ["beef noodle soup", "pho bo"],
    "酸菜牛肉面": ["beef noodle soup", "pickled mustard beef noodle"],
    "麻婆豆腐": ["mapo doufu", "spicy tofu"],
    "牛肉炒面片": ["fried noodles beef", "chow mein beef"],
    "全麦鸡肉卷": ["chicken wrap", "burrito chicken"],
    "五花肉烤肉套餐": ["samgyeopsal", "korean barbecue pork"],
    "烤牛肉拼盘": ["korean barbecue beef", "bulgogi"],
    "猪肚鸡汤": ["chicken soup", "chinese chicken soup"],
    "手撕包菜": ["cabbage stir fry", "fried cabbage"],
    "酸辣白菜": ["cabbage", "chinese cabbage dish"],
    "干煸豆角": ["green beans stir fry", "sichuan beans"],
    "空气炸锅烤茄子": ["roasted eggplant", "grilled eggplant"],
    "空气炸锅三文鱼": ["grilled salmon", "roasted salmon"],
    "凉拌木耳": ["wood ear mushroom", "black fungus"],
    "番茄麻辣烫": ["malatang", "hot pot bowl"],
    "骨汤麻辣烫": ["malatang", "hot pot bowl"],
}


def parse_plan() -> list[dict]:
    """从方案文档里读清单：序号 / 菜名 / 菜系 / dish_id / 文件名 / 检索词。"""
    rows: list[dict] = []
    pat = re.compile(
        r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\d,]+)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|"
    )
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        m = pat.match(line.strip())
        if m:
            rows.append(
                {
                    "index": int(m.group(1)),
                    "name": m.group(2).strip(),
                    "cuisine": m.group(3).strip(),
                    "ids": [int(x) for x in m.group(4).split(",")],
                    "file": m.group(5).strip(),
                    "query": m.group(6).strip(),
                }
            )
    if len(rows) < 90:
        raise SystemExit(f"清单解析异常：只有 {len(rows)} 行")
    return rows


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*"})
    # 注意：这台机器直连被 reset，必须让 requests 读系统（注册表）代理设置，
    # 也就是保留默认的 trust_env=True，别手动关掉。
    return s


_last_call = [0.0]
MIN_INTERVAL = 1.2  # Commons 对匿名 API 很敏感，1.2s 一次基本不会被 429


def throttle() -> None:
    gap = time.time() - _last_call[0]
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call[0] = time.time()


def search(s: requests.Session, query: str, limit: int = 12) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f'{query} filetype:bitmap',
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": "1200",
    }
    for attempt in range(4):
        throttle()
        try:
            r = s.get(API, params=params, timeout=25)
            if r.status_code == 429:
                wait = 8 * (attempt + 1)
                print(f"    429 限速，等 {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            pages = (data.get("query") or {}).get("pages") or {}
            return [p for p in pages.values() if p.get("imageinfo")]
        except Exception as exc:  # noqa: BLE001 - 网络抖动就重试
            print(f"    search retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return []


def score(page: dict, query: str) -> float:
    title = page.get("title", "").lower()
    info = page["imageinfo"][0]
    if (info.get("width") or 0) < MIN_SRC_WIDTH:
        return -1.0
    if re.search(r"\.(svg|gif|webm|tif?f)$", title):
        return -1.0
    if re.search(r"(logo|map|diagram|chart|sign|poster|menu|packag|label)", title):
        return -0.5
    tokens = [t for t in re.split(r"[\s\-_]+", query.lower()) if len(t) > 2]
    hits = sum(1 for t in tokens if t in title)
    base = hits / max(1, len(tokens))
    # 文件名里带这些词说明更像"成品菜"照片
    if re.search(r"(dish|bowl|plate|food|cuisine|cooked)", title):
        base += 0.15
    return base


def pick(candidates: list[dict], query: str) -> dict | None:
    ranked = sorted(candidates, key=lambda p: score(p, query), reverse=True)
    for page in ranked:
        if score(page, query) > 0.34:
            return page
    return None


def best_candidate(s: requests.Session, query: str, name: str) -> tuple[list[dict], dict | None]:
    """主查询 + 别名各搜一遍，合并去重后按"查询词与文件名重合度"选最佳。"""
    queries = [query] + ALIASES.get(name, [])
    pool: dict[str, dict] = {}
    for q in queries:
        for page in search(s, q):
            key = str(page.get("pageid") or page.get("title"))
            pool[key] = page
    cands = list(pool.values())
    for q in queries:
        page = pick(cands, q)
        if page:
            return cands, page
    return cands, None


def download(s: requests.Session, url: str) -> bytes | None:
    for attempt in range(3):
        throttle()
        try:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            if len(r.content) < 20000:
                return None
            return r.content
        except Exception as exc:  # noqa: BLE001
            print(f"    download retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(1.5)
    return None


def process(raw: bytes, dest: Path) -> tuple[int, int]:
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    src_w, src_h = img.size
    target_ratio = W / H
    if src_w / src_h > target_ratio:  # 太宽 → 裁左右
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:  # 太高 → 裁上下（顶部稍多留给菜品）
        new_h = int(src_w / target_ratio)
        top = max(0, int((src_h - new_h) * 0.35))
        img = img.crop((0, top, src_w, top + new_h))
    img = img.resize((W, H), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return (src_w, src_h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--only", type=str, default="", help="只跑这些序号，逗号分隔")
    args = ap.parse_args()

    rows = parse_plan()
    if args.only:
        wanted = {int(x) for x in args.only.split(",") if x.strip()}
        rows = [r for r in rows if r["index"] in wanted]
    elif args.limit:
        rows = rows[: args.limit]

    ledger: dict[str, dict] = {}
    if LEDGER.exists():
        ledger = {e["file"]: e for e in json.loads(LEDGER.read_text(encoding="utf-8"))}
    missing: list[dict] = []

    s = session()
    ok = 0
    for row in rows:
        dest = OUT_DIR / row["file"]
        if dest.exists() and not args.redo:
            ok += 1
            continue
        print(f'[{row["index"]:02d}] {row["name"]}  <- "{row["query"]}"')
        cands, page = best_candidate(s, row["query"], row["name"])
        if not page:
            missing.append(
                {
                    "name": row["name"],
                    "cuisine": row["cuisine"],
                    "file": row["file"],
                    "query": row["query"],
                    "tried": [f"Commons search: {row['query']} filetype:bitmap"],
                    "candidates": len(cands),
                }
            )
            print("    ✗ 没有合格候选")
            time.sleep(0.5)
            continue
        info = page["imageinfo"][0]
        url = info.get("thumburl") or info["url"]
        raw = download(s, url)
        if not raw:
            missing.append(
                {
                    "name": row["name"],
                    "cuisine": row["cuisine"],
                    "file": row["file"],
                    "query": row["query"],
                    "tried": [f"Commons 命中但下载失败: {info['url']}"],
                    "candidates": len(cands),
                }
            )
            print("    ✗ 下载失败")
            continue
        try:
            size = process(raw, dest)
        except Exception as exc:  # noqa: BLE001
            missing.append(
                {
                    "name": row["name"],
                    "cuisine": row["cuisine"],
                    "file": row["file"],
                    "query": row["query"],
                    "tried": [f"图片处理失败: {exc}"],
                    "candidates": len(cands),
                }
            )
            print(f"    ✗ 处理失败 {exc}")
            continue

        meta = info.get("extmetadata") or {}
        ledger[row["file"]] = {
            "name": row["name"],
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
        }
        ok += 1
        print(f'    ✓ {dest.name} ({dest.stat().st_size // 1024} KB) {ledger[row["file"]]["license"]}')
        time.sleep(0.6)

    LEDGER.write_text(json.dumps(sorted(ledger.values(), key=lambda e: e["file"]), ensure_ascii=False, indent=2), encoding="utf-8")
    # 成功的菜要从缺失清单里摘掉（历史失败记录不该长期挂着）
    if MISSING.exists():
        kept = [m for m in json.loads(MISSING.read_text(encoding="utf-8")) if m["file"] not in ledger]
        MISSING.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    if missing:
        prev = []
        if MISSING.exists():
            prev = json.loads(MISSING.read_text(encoding="utf-8"))
        merged = {m["file"]: m for m in prev}
        for m in missing:
            merged[m["file"]] = m
        MISSING.write_text(json.dumps(sorted(merged.values(), key=lambda e: e["file"]), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ndone: {ok} files ready, {len(missing)} missing this run, ledger {len(ledger)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
