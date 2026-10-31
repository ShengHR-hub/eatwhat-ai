"""8 维风味向量规范、状态气泡规则与天气映射（MASTER_SPEC v2.1.1 第二章）。"""

from typing import Dict, Iterable, List, Mapping, Sequence

FEATURE_KEYS = (
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
)

FEATURE_LABELS_CN = {
    "spicy_level": "辣度",
    "oily_level": "油腻度",
    "soup_level": "汤水感",
    "temp_fit": "适宜温度",
    "satiety_level": "饱腹度",
    "prep_speed": "出餐速度",
    "social_fit": "社交属性",
    "comfort_level": "抚慰指数",
}

DEFAULT_FEATURE_VECTOR: Dict[str, float] = {key: 0.5 for key in FEATURE_KEYS}

VOTE_SCORES = {
    "SUPER_LIKE": 120.0,
    "LIKE": 100.0,
    "PASS": 40.0,
    "VETO": -999.0,
}
TIMEOUT_SWIPE_SCORE = 60.0


STATUS_BUBBLE_RULES = {
    "exhausted": {
        "label": "😫 刚加完班累瘫",
        "modes": ("OUT_DINING", "HOME_COOKING"),
        "param_overrides": {"delta_status": 0.45},
        "target_vector": {"comfort_level": 0.9, "prep_speed": 0.9},
    },
    "broke_end_month": {
        "label": "💸 月底吃土模式",
        "modes": ("OUT_DINING",),
        "param_overrides": {"gamma_budget": 0.55},
        "hard_filter": "budget",
        "target_vector": {"satiety_level": 0.9},
    },
    "craving_heavy": {
        "label": "🌶️ 嘴馋想吃重口",
        "modes": ("OUT_DINING", "HOME_COOKING"),
        "param_overrides": {"alpha_taste": 0.50},
        "target_vector": {"spicy_level": 0.85, "oily_level": 0.75},
    },
    "light_healthy": {
        "label": "🥗 肠胃负担重想清淡",
        "modes": ("OUT_DINING", "HOME_COOKING"),
        "penalty": {"oily_level_gt": 0.5, "spicy_level_gt": 0.3},
        "penalty_multiplier": 0.2,
    },
    "need_hot_soup": {
        "label": "🍲 手脚冰凉想喝热汤",
        "modes": ("OUT_DINING", "HOME_COOKING"),
        "param_overrides": {"beta_weather": 0.45},
        "hard_filter": "hot_soup",
        "target_vector": {"soup_level": 0.95, "temp_fit": 0.15},
    },
    "lazy_one_pot": {
        "label": "🍚 只有电饭煲/不想洗碗",
        "modes": ("HOME_COOKING",),
        "hard_filter": "lazy_one_pot",
        # v2.3.2 审核裁决：只看厨具可用性，不再叠加出餐速度门槛
        "allowed_appliances": ("电饭煲", "一锅出"),
    },
}


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_vector(raw: Mapping[str, float] | None) -> Dict[str, float]:
    vector = dict(DEFAULT_FEATURE_VECTOR)
    if raw:
        for key in FEATURE_KEYS:
            if key in raw:
                vector[key] = clamp01(raw[key])
    return vector


def cosine_similarity(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    va = [float(a.get(k, 0.0)) for k in FEATURE_KEYS]
    vb = [float(b.get(k, 0.0)) for k in FEATURE_KEYS]
    dot = sum(x * y for x, y in zip(va, vb))
    norm_a = sum(x * x for x in va) ** 0.5
    norm_b = sum(y * y for y in vb) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def similarity_to_100(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    return round(max(0.0, min(1.0, cosine_similarity(a, b))) * 100.0, 2)


def mean_vector(vectors: Iterable[Mapping[str, float]]) -> Dict[str, float]:
    items = [normalize_vector(v) for v in vectors]
    if not items:
        return dict(DEFAULT_FEATURE_VECTOR)
    return {
        key: round(sum(v[key] for v in items) / len(items), 4) for key in FEATURE_KEYS
    }


def target_match_score(
    dish_vector: Mapping[str, float], target_vector: Mapping[str, float]
) -> float:
    diffs = [
        abs(clamp01(dish_vector.get(key, 0.5)) - clamp01(value))
        for key, value in target_vector.items()
        if key in FEATURE_KEYS
    ]
    if not diffs:
        return 60.0
    return round(max(0.0, 100.0 * (1.0 - sum(diffs) / len(diffs))), 2)


def weather_target_vector(temp_c: float, weather_text: str = "") -> Dict[str, float]:
    text = weather_text or ""
    rainy = any(token in text for token in ("雨", "雪", "雷"))
    if temp_c <= 5:
        temp_fit, soup_level = 0.05, 0.95
    elif temp_c <= 12:
        temp_fit, soup_level = 0.15, 0.85
    elif temp_c <= 20:
        temp_fit, soup_level = 0.35, 0.65
    elif temp_c <= 28:
        temp_fit, soup_level = 0.60, 0.35
    else:
        temp_fit, soup_level = 0.90, 0.15
    if rainy:
        soup_level = min(1.0, soup_level + 0.15)
        temp_fit = min(temp_fit, 0.35)
    return {
        "temp_fit": temp_fit,
        "soup_level": soup_level,
        "comfort_level": 0.75 if (rainy or temp_c <= 12) else 0.5,
    }


def weather_match_score(
    dish_vector: Mapping[str, float], temp_c: float, weather_text: str = ""
) -> float:
    target = weather_target_vector(temp_c, weather_text)
    temp_diff = abs(clamp01(dish_vector.get("temp_fit", 0.5)) - target["temp_fit"])
    soup_diff = abs(clamp01(dish_vector.get("soup_level", 0.5)) - target["soup_level"])
    return round(max(0.0, 100.0 * (1.0 - (0.6 * temp_diff + 0.4 * soup_diff))), 2)


def capsule_tip(temp_c: float, weather_text: str = "") -> str:
    text = weather_text or ""
    if any(token in text for token in ("雨", "雪", "雷")):
        return "外面在下雨，优先推荐步行可达的热乎饭菜"
    if temp_c <= 5:
        return "今天很冷，来点热汤热菜暖暖胃"
    if temp_c <= 12:
        return "降温了，推荐热乎的汤面或炖菜"
    if temp_c >= 32:
        return "天气炎热，推荐清爽凉菜或轻食"
    return "温度舒适，按你的口味放心选"


def resolve_bubble_effects(
    bubbles: Sequence[str], mode_type: str
) -> Dict[str, object]:
    effects: Dict[str, object] = {
        "param_overrides": {},
        "target_vector": {},
        "budget_filter": False,
        "hot_soup_filter": False,
        "lazy_filter": False,
        "light_penalty": False,
        "penalty_multiplier": 0.2,
        "allowed_appliances": (),
        "labels": [],
        "ignored": [],
    }
    merged_target: Dict[str, float] = {}
    for bubble_id in bubbles:
        rule = STATUS_BUBBLE_RULES.get(bubble_id)
        if rule is None or mode_type not in rule.get("modes", ()):
            effects["ignored"].append(bubble_id)
            continue
        effects["labels"].append(rule["label"])
        for key, value in rule.get("param_overrides", {}).items():
            effects["param_overrides"][key] = value
        merged_target.update(rule.get("target_vector", {}))
        hard_filter = rule.get("hard_filter")
        if hard_filter == "budget":
            effects["budget_filter"] = True
        elif hard_filter == "hot_soup":
            effects["hot_soup_filter"] = True
        elif hard_filter == "lazy_one_pot":
            effects["lazy_filter"] = True
            effects["allowed_appliances"] = tuple(rule.get("allowed_appliances", ()))
        if rule.get("penalty"):
            effects["light_penalty"] = True
            effects["penalty_multiplier"] = float(
                rule.get("penalty_multiplier", 0.2)
            )
    effects["target_vector"] = merged_target
    return effects


def light_healthy_hits(dish_vector: Mapping[str, float]) -> bool:
    rule = STATUS_BUBBLE_RULES["light_healthy"]["penalty"]
    return (
        float(dish_vector.get("oily_level", 0.0)) > rule["oily_level_gt"]
        or float(dish_vector.get("spicy_level", 0.0)) > rule["spicy_level_gt"]
    )


def build_explain_reason(
    taste: float,
    weather: float,
    budget: float,
    freshness: float,
    status: float,
    decay_weight: float,
    boost_fav: bool,
    labels: List[str],
) -> str:
    parts = [
        f"口味契合 {taste:.1f}",
        f"天气适配 {weather:.1f}",
        f"预算友好 {budget:.1f}",
        f"防腻新鲜度 {freshness:.1f}",
        f"状态匹配 {status:.1f}",
    ]
    if decay_weight < 0.5:
        parts.append(f"最近吃过同类，已降权至 {decay_weight:.2f}")
    if boost_fav:
        parts.append("命中红榜，享 1.15x 提权")
    if labels:
        parts.append("气泡：" + "、".join(labels))
    return "；".join(parts)
