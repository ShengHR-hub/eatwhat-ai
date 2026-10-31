"""忌口匹配（F01 修复：单一出口）。

问题背景
--------
早期实现（`single_recommender._hit_veto` / `group_recommender._hit_veto`）只做
**双向子串匹配**：

    if tag in ingredient or ingredient in tag

用户在忌口里写「海鲜」，菜谱写「鲜虾」「虾皮」「虾仁」时，两个字符串互不包含，
于是"命中了忌口却照常推荐"。审查报告 F01 指的就是这条。

本模块的做法（D-S04-02，2026-10-26 用户裁决）
----------------------------------------------
1. **类别标签**（`海鲜`/`海味`/`内脏`/`牛奶`/`辣`）各自展开到
   `VETO_SYNONYMS` 中明确列出的成员，**不跨类别**。
2. **具体食材标签**只匹配自身及明确同义词组（`SPECIFIC_SYNONYMS`）：
   「鲜虾」= 虾类同义词，不会排掉鲈鱼/螃蟹/扇贝；「鲈鱼」不扩到草鱼/三文鱼；
   「牛肉」不扩到羊肉/猪肉。未知文本只做精确匹配。
3. **匹配**：仍然做包含匹配（中文食材名常带修饰词，如「新鲜虾仁」），
   但只对**展开后的别名**做，且单字别名必须在白名单 `STRONG_SINGLE` 里
   —— 否则「鱼」会命中「鱼香肉丝」（该菜并没有鱼）。
4. **单一出口**：单人推荐与群组初筛都调这里，禁止再各写一份，
   否则两套规则会再次漂移（F01 的根因就是"两份实现"）。

新增类别成员只改 `VETO_SYNONYMS`；新增具体同义词组只改 `SPECIFIC_SYNONYMS`。
"""

from typing import Dict, Iterable, Optional, Sequence, Set, Tuple

#: 类别别名表：canonical（用户可能写的类别名）→ 该类别下的具体食材
VETO_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "海鲜": (
        "虾仁",
        "鲜虾",
        "虾皮",
        "虾滑",
        "虾米",
        "海米",
        "基围虾",
        "明虾",
        "大虾",
        "龙虾",
        "螃蟹",
        "蟹肉",
        "蟹柳",
        "蟹黄",
        "扇贝",
        "蛤蜊",
        "花蛤",
        "蛏子",
        "牡蛎",
        "生蚝",
        "蚝油",
        "鱿鱼",
        "墨鱼",
        "章鱼",
        "海参",
        "鲍鱼",
        "三文鱼",
        "鲈鱼",
        "带鱼",
        "鳕鱼",
        "金枪鱼",
        "鳗鱼",
        "刺参",
        "鱼丸",
        "鱼片",
        "鱼豆腐",
        "干贝",
        # 单字「鱼」只做全等匹配（不在 STRONG_SINGLE），因此不会命中「鱼香肉丝」。
        "鱼",
        "虾",
        "蟹",
        "贝",
        "蚝",
    ),
    "海味": ("紫菜", "海带", "海苔", "裙带菜"),
    "香菜": ("香菜", "芫荽"),
    "花生": ("花生米", "花生碎", "花生酱", "花生仁", "花生"),
    "牛奶": ("淡奶油", "炼乳", "芝士", "奶酪", "黄油", "奶油", "牛奶"),
    "内脏": (
        "猪肝",
        "鸡肝",
        "鸭肝",
        "猪腰",
        "腰花",
        "大肠",
        "肥肠",
        "猪肚",
        "牛肚",
        "毛肚",
        "鸭肠",
        "鸡胗",
        "鸭胗",
        "鸡心",
        "猪心",
        "肝",
        "肚",
    ),
    "折耳根": ("折耳根", "鱼腥草"),
    "羊肉": ("羊肉卷", "羊肉", "羊排", "羊腿", "肥羊"),
    "牛肉": ("牛肉片", "牛肉丸", "牛肉", "牛腩", "牛柳", "牛排", "肥牛"),
    "猪肉": ("五花肉", "里脊", "排骨", "猪蹄", "猪肉", "肉末"),
    "鸡蛋": ("鹌鹑蛋", "鸡蛋", "鸭蛋", "蛋液", "蛋花", "蛋白", "蛋黄", "蛋"),
    "辣": ("干辣椒", "小米辣", "朝天椒", "辣椒油", "豆瓣酱", "辣椒", "辣"),
}

#: D-S04-02：只有这五个是“类别标签”，展开到各自明确列出的成员。
CATEGORY_TAGS: Set[str] = {"海鲜", "海味", "内脏", "牛奶", "辣"}

#: 具体食材/同义词组：非类别 canonical 组 + 类别成员的窄同义词组。
#: 具体标签只在本组内展开，绝不反向上扩到类别。
SPECIFIC_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    name: aliases
    for name, aliases in VETO_SYNONYMS.items()
    if name not in CATEGORY_TAGS
}
SPECIFIC_SYNONYMS.update(
    {
        "鲜虾": (
            "鲜虾",
            "虾仁",
            "虾皮",
            "虾滑",
            "虾米",
            "海米",
            "基围虾",
            "明虾",
            "大虾",
            "虾",
        ),
        "螃蟹": ("螃蟹", "蟹肉", "蟹柳", "蟹黄", "蟹"),
        "扇贝": ("扇贝", "干贝"),
        "生蚝": ("生蚝", "牡蛎", "蚝油", "蚝"),
        "鲈鱼": ("鲈鱼",),
        "草鱼": ("草鱼",),
        "三文鱼": ("三文鱼",),
    }
)

#: 允许参与匹配的单字别名。中餐食材列表里单字太容易误命中，必须显式放行。
STRONG_SINGLE: Set[str] = {
    "虾",
    "蟹",
    "贝",
    "蚝",
    "肝",
    "肚",
    "蛋",
    "辣",
}

#: 「词尾即类别」规则：草鱼、黑鱼、鲳鱼… 列举不完，靠尾缀兜住。
#: 只对**词尾**生效，所以「鱼香肉丝」（尾缀是「丝」）不会被误判成海鲜。
#: 只在用户输入类别标签（CATEGORY_TAGS）时启用；具体标签不借词尾跨类别。
SUFFIX_RULES: Dict[str, Tuple[str, ...]] = {
    # 「参」不能做词尾：会误伤党参/人参；海参/刺参已进别名表。
    "海鲜": ("鱼", "虾", "蟹", "贝", "蛤", "螺", "鱿", "鲍"),
    "内脏": ("肝", "肚", "肠", "胗", "腰"),
}

#: 具体标签/别名 → 同义词组反查（鲜虾、虾仁、虾皮 都归到「鲜虾」组）。
_SPECIFIC_ALIAS_TO_GROUP: Dict[str, str] = {}
for _group, _aliases in SPECIFIC_SYNONYMS.items():
    _SPECIFIC_ALIAS_TO_GROUP[_group] = _group
    for _alias in _aliases:
        _SPECIFIC_ALIAS_TO_GROUP.setdefault(_alias, _group)


def normalize_tag(value: object) -> str:
    """去掉空白与全角空格，统一大小写（英文忌口如 "peanut"）。"""
    text = str(value or "").strip().replace("\u3000", " ")
    return "".join(text.split()).lower()


def _expand(
    tags: Iterable[object],
) -> Tuple[Set[str], Set[str], Set[str]]:
    """拆出 (可包含匹配的已知 token, 必须全等的未知 token, 命中的类别标签)。

    只有类别展开成员与明确登记的同义词组可以做包含匹配；未知输入必须
    规范化后全等，不能因为候选食材包含它就被判命中。
    """
    contains: Set[str] = set()
    exact: Set[str] = set()
    categories: Set[str] = set()
    for raw in tags or []:
        tag = normalize_tag(raw)
        if not tag:
            continue
        if tag in CATEGORY_TAGS:
            categories.add(tag)
            contains.add(tag)
            for alias in VETO_SYNONYMS.get(tag, ()):
                contains.add(normalize_tag(alias))
            continue
        group = _SPECIFIC_ALIAS_TO_GROUP.get(tag)
        if group:
            contains.add(group)
            for alias in SPECIFIC_SYNONYMS[group]:
                contains.add(normalize_tag(alias))
            continue
        exact.add(tag)
    return contains, exact, categories


def expand_tags(tags: Iterable[object]) -> Set[str]:
    """返回展开 token 的并集（调试/兼容用）。

    匹配器请使用 `_expand`：并集会丢失“未知 token 必须全等”的类型信息。
    """
    contains, exact, _ = _expand(tags)
    return contains | exact


def _token_matches(token: str, ingredient: str) -> bool:
    """已知类别/同义词 token 的包含匹配；未知 token 由 `_search` 全等处理。

    只做「token 出现在食材名里」这个方向，不做反向包含。反向包含会造出
    假阳性：别名池里有「鱼豆腐」，食材「豆腐」反过来包含于「鱼豆腐」，
    于是麻婆豆腐会被判成海鲜 —— 这正是第一版实现踩到的坑。
    """
    if not token or not ingredient:
        return False
    if len(token) == 1 and token not in STRONG_SINGLE:
        # 单字非白名单：只认全等，避免「鱼」命中「鱼香肉丝」、「牛」命中「牛油果」
        return token == ingredient
    return token == ingredient or token in ingredient


def _search(
    ingredients: Iterable[object], veto_tags: Iterable[object]
) -> Tuple[Optional[str], Optional[str]]:
    """唯一匹配实现：返回 (命中的忌口词, 命中的食材)。"""
    contains, exact, categories = _expand(veto_tags)
    if not contains and not exact:
        return None, None
    normalized = [normalize_tag(i) for i in (ingredients or []) if normalize_tag(i)]

    # 未知输入：规范化后全等；「核桃」不得命中「核桃仁」。
    for token in sorted(exact, key=len, reverse=True):
        for ingredient in normalized:
            if token == ingredient:
                return token, ingredient

    # 已登记的类别成员/同义词：允许包含（「虾皮」命中「新鲜虾皮」）。
    for token in sorted(contains, key=len, reverse=True):
        for ingredient in normalized:
            if _token_matches(token, ingredient):
                return token, ingredient

    # 词尾规则只服务类别标签；具体/未知标签不借词尾跨类别。
    for canonical, suffixes in SUFFIX_RULES.items():
        if canonical not in categories:
            continue
        for ingredient in normalized:
            if len(ingredient) >= 2 and ingredient.endswith(suffixes):
                return canonical, ingredient
    return None, None


def find_hit(
    ingredients: Iterable[object], veto_tags: Iterable[object]
) -> Optional[str]:
    """返回第一个命中的忌口词（展开后的），没命中返回 None。"""
    return _search(ingredients, veto_tags)[0]


def hits(ingredients: Iterable[object], veto_tags: Iterable[object]) -> bool:
    return find_hit(ingredients, veto_tags) is not None


def explain(ingredients: Sequence[object], veto_tags: Iterable[object]) -> Dict[str, object]:
    """给接口/调试用的命中明细：哪条忌口命中了哪味食材。"""
    token, ingredient = _search(ingredients, veto_tags)
    return {
        "matched": token is not None,
        "tag": token,
        "ingredient": ingredient,
    }
