"""生成 docs/DISH_IMAGES_PLAN.md 的菜品清单表（从 docs/_data/dishes.json 读，避免手抄）。"""
import json
import re
from pathlib import Path

rows = json.loads(Path("docs/_data/dishes.json").read_text(encoding="utf-8"))

# 中英对照检索词表（常见中餐，人工维护；没有就用拼音兜底）
EN = {
    "麻辣香锅": "mala xiang guo spicy stir fry",
    "水煮肉片": "sichuan boiled pork slices",
    "辣子鸡": "chongqing spicy chicken",
    "干煸四季豆": "dry fried green beans",
    "酸辣土豆丝": "hot and sour shredded potato",
    "青椒肉丝": "shredded pork with green pepper",
    "鱼香肉丝": "yuxiang shredded pork",
    "宫保鸡丁": "kung pao chicken",
    "麻婆豆腐": "mapo tofu",
    "西红柿炒蛋": "tomato scrambled eggs",
    "紫菜蛋花汤": "seaweed egg drop soup",
    "蜜汁叉烧饭": "char siu rice",
    "白切鸡饭": "white cut chicken rice",
    "烧鸭饭": "roast duck rice",
    "清炒菜心": "stir fried choy sum",
    "例汤": "cantonese soup",
    "红烧牛肉面": "braised beef noodle soup",
    "清汤牛肉面": "beef noodle soup clear broth",
    "番茄鸡蛋面": "tomato egg noodle soup",
    "牛肉粉丝汤": "beef vermicelli soup",
    "麻辣烫套餐": "malatang",
    "番茄麻辣烫": "tomato malatang",
    "骨汤麻辣烫": "malatang bone broth",
    "招牌麻辣烫": "malatang bowl",
    "鸡胸肉沙拉": "chicken breast salad",
    "低脂鸡胸饭": "grilled chicken rice bowl",
    "南瓜浓汤": "pumpkin soup",
    "皮蛋瘦肉粥": "century egg congee",
    "肠粉": "rice noodle roll",
    "云吞面": "wonton noodles",
    "干炒牛河": "beef chow fun",
    "石锅拌饭": "bibimbap",
    "部队锅": "budae jjigae army stew",
    "兰州牛肉拉面": "lanzhou beef noodles",
    "牛肉炒面片": "fried noodle pieces beef",
    "羊肉串": "lamb skewers",
    "排骨莲藕汤": "lotus root pork rib soup",
    "砂锅豆腐": "claypot tofu",
    "砂锅鸡": "claypot chicken",
    "毛血旺": "maoxuewang",
    "水煮鱼": "sichuan boiled fish",
    "回锅肉": "twice cooked pork",
    "凉拌折耳根": "houttuynia salad",
    "虾饺皇": "har gow shrimp dumpling",
    "白灼虾": "boiled shrimp",
    "烧鹅拼饭": "roast goose rice",
    "老火靓汤": "cantonese slow soup",
    "招牌牛腩面": "beef brisket noodles",
    "酸菜牛肉面": "pickled cabbage beef noodles",
    "藜麦鸡胸沙拉": "quinoa chicken salad",
    "三文鱼沙拉": "salmon salad",
    "全麦鸡肉卷": "whole wheat chicken wrap",
    "五花肉烤肉套餐": "korean bbq pork belly",
    "烤牛肉拼盘": "korean bbq beef platter",
    "烤蔬菜拼盘": "grilled vegetables platter",
    "三文鱼刺身": "salmon sashimi",
    "鳗鱼饭": "unagi rice",
    "韩式炸鸡": "korean fried chicken",
    "红烧狮子头": "lion head meatball",
    "猪肚鸡汤": "pork tripe chicken soup",
    "番茄炒蛋": "tomato scrambled eggs",
    "青椒土豆丝": "shredded potato green pepper",
    "蒜蓉西兰花": "garlic broccoli",
    "手撕包菜": "hand torn cabbage",
    "可乐鸡翅": "cola chicken wings",
    "红烧排骨": "braised pork ribs",
    "清蒸鲈鱼": "steamed sea bass",
    "香菇滑鸡": "chicken with shiitake",
    "洋葱炒蛋": "onion scrambled eggs",
    "韭菜炒鸡蛋": "chive scrambled eggs",
    "酸辣白菜": "hot and sour cabbage",
    "蒜蓉生菜": "garlic lettuce",
    "西芹百合": "celery with lily bulb",
    "冬瓜排骨汤": "winter melon pork rib soup",
    "番茄蛋汤": "tomato egg soup",
    "玉米排骨汤": "corn pork rib soup",
    "菌菇鸡汤": "mushroom chicken soup",
    "电饭煲焖饭": "rice cooker rice",
    "电饭煲茶叶蛋": "tea egg",
    "电饭煲红烧肉": "braised pork belly",
    "电饭煲青菜粥": "vegetable congee",
    "空气炸锅鸡翅": "air fryer chicken wings",
    "空气炸锅薯条": "air fryer fries",
    "空气炸锅烤茄子": "air fryer eggplant",
    "空气炸锅三文鱼": "air fryer salmon",
    "凉拌黄瓜": "smashed cucumber salad",
    "凉拌木耳": "wood ear mushroom salad",
    "凉拌豆腐丝": "tofu skin salad",
    "凉拌鸡丝": "shredded chicken salad",
    "一锅出番茄牛腩": "tomato beef brisket stew",
    "一锅出土豆炖鸡": "potato chicken stew",
    "一锅出咖喱饭": "curry rice",
    "鱼香茄子": "yuxiang eggplant",
    "干煸豆角": "dry fried long beans",
    "腊肠煲仔饭": "claypot rice chinese sausage",
}


def slug(dish_id, name):
    raw = EN.get(name, name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return f"{dish_id:03d}-{s[:26].strip('-')}"


seen = {}
for r in rows:
    seen.setdefault(r["name"], []).append(r)

unique = []
for name, group in seen.items():
    ids = [r["id"] for r in group]
    unique.append((min(ids), name, group[0]["cuisine_type"], ids, group[0]["mode_type"]))

unique.sort()

lines = ["| # | 菜名 | 菜系 | dish_id | 拟用文件 `frontend/public/dishes/` | 主检索词 |", "|---|---|---|---|---|---|"]
for i, (first_id, name, cuisine, ids, _mode) in enumerate(unique, 1):
    ids_s = ",".join(str(x) for x in ids)
    f = slug(first_id, name) + ".jpg"
    kw = EN.get(name, name)
    lines.append(f"| {i} | {name} | {cuisine} | {ids_s} | `{f}` | {kw} |")

table = "\n".join(lines)
Path("docs/_data/dishes_table.md").write_text(table, encoding="utf-8")
print("unique:", len(unique), "total dishes:", len(rows))
print("dupes:", {k: len(v) for k, v in seen.items() if len(v) > 1})
