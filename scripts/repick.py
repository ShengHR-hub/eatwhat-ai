"""人工挑选辅助：给一批菜名，打印 Commons 候选文件（标题/尺寸/授权），供人工指定。

用法：python scripts/repick.py        # 跑问题清单里的默认查询
      python scripts/repick.py "韭菜炒鸡蛋:chive omelette" ...
产物：docs/_data/repick_candidates.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import fetch_dish_images as f  # noqa: E402

# 第一轮自动选图明显不对的菜：换成更"菜品化"的查询再挑
DEFAULT = {
    "酸辣土豆丝": ["shredded potato", "potato salad chinese", "tudousi"],
    "宫保鸡丁": ["kung pao chicken", "gong bao ji ding"],
    "麻婆豆腐": ["mapo tofu", "mapo doufu"],
    "凉拌折耳根": ["houttuynia dish", "fish mint salad", "zheergen"],
    "烧鹅拼饭": ["roast goose", "siu ngo rice"],
    "藜麦鸡胸沙拉": ["chicken quinoa salad", "quinoa salad"],
    "番茄炒蛋": ["tomato egg stir fry", "fanqie chaodan"],
    "青椒土豆丝": ["shredded potato stir fry", "tudousi"],
    "蒜蓉西兰花": ["broccoli garlic stir fry", "stir fried broccoli"],
    "洋葱炒蛋": ["onion omelette", "scrambled eggs onion"],
    "韭菜炒鸡蛋": ["chive omelette", "jiucai chaodan"],
    "酸辣白菜": ["chinese cabbage stir fry", "sour cabbage"],
    "蒜蓉生菜": ["lettuce garlic", "stir fried lettuce"],
    "西芹百合": ["celery lily bulb", "stir fried celery"],
    "玉米排骨汤": ["corn soup chinese", "pork rib soup corn"],
    "电饭煲焖饭": ["rice cooker rice", "claypot rice chicken"],
    "腊肠煲仔饭": ["claypot rice sausage", "lap cheong rice"],
    "电饭煲青菜粥": ["congee vegetable", "rice porridge"],
    "空气炸锅薯条": ["french fries", "potato fries"],
    "凉拌木耳": ["wood ear salad", "black fungus salad"],
    "一锅出番茄牛腩": ["beef brisket tomato", "braised beef brisket"],
    "一锅出土豆炖鸡": ["chicken potato stew", "braised chicken"],
    "一锅出咖喱饭": ["curry rice", "japanese curry"],
    "排骨莲藕汤": ["lotus root soup", "pork rib lotus soup"],
    "酸菜牛肉面": ["beef noodle soup", "pickled cabbage noodle"],
    "鳗鱼饭": ["unagi don", "eel rice bowl"],
    "麻辣烫套餐": ["malatang", "mala tang"],
    "番茄麻辣烫": ["malatang tomato", "malatang"],
    "骨汤麻辣烫": ["malatang soup", "malatang"],
}


def main() -> None:
    pairs = list(DEFAULT.items())
    for arg in sys.argv[1:]:
        name, _, q = arg.partition(":")
        pairs.append((name, [q]))

    s = f.session()
    out = []
    for name, queries in pairs:
        out.append(f"\n=== {name} ===")
        seen = set()
        for q in queries:
            out.append(f"-- q: {q}")
            for page in f.search(s, q)[:8]:
                title = page.get("title", "")
                if title in seen:
                    continue
                seen.add(title)
                info = page["imageinfo"][0]
                meta = info.get("extmetadata") or {}
                lic = (meta.get("LicenseShortName") or {}).get("value", "?")
                out.append(f"   {title}  {info.get('width')}x{info.get('height')}  {lic}")
    text = "\n".join(out)
    Path("docs/_data/repick_candidates.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
