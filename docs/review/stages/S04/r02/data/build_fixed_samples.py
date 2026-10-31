"""S04 固定样本与独立计算过程。

原则：expected 由本文件内的手算/独立小实现产生；生产函数只用于输出
`observed`，两者分别记录并给出 match。不把生产函数当作 expected 来源。

输出：docs/review/stages/S04/r02/data/fixed_samples.json
"""

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path("D:/EatWhat")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.algorithms.combo_optimizer import optimize_combo  # noqa: E402
from backend.algorithms.group_recommender import (  # noqa: E402
    compute_group_consensus,
)
from backend.algorithms.single_recommender import recommend_single  # noqa: E402
from backend.algorithms.time_decay import compute_decay_weights  # noqa: E402
from backend.algorithms.veto_rules import hits as veto_hits  # noqa: E402
from backend.database import Base  # noqa: E402
from backend.models import (  # noqa: E402
    Dish,
    EatingLog,
    User,
    UserPreference,
)

OUT = ROOT / "docs" / "review" / "stages" / "S04" / "r02"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
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
NEUTRAL = {key: 0.5 for key in FEATURE_KEYS}


def vec(**overrides):
    base = {key: 0.0 for key in FEATURE_KEYS}
    base.update(overrides)
    return base


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    return engine, factory


def add_user(session, name, vector, *, budget=25.0, veto=(), fav=(), black=()):
    user = User(
        username=name,
        nickname=name,
        avatar="",
        persona_title="",
        is_demo_persona=False,
    )
    session.add(user)
    session.flush()
    session.add(
        UserPreference(
            user_id=user.id,
            base_vector=dict(vector),
            default_budget=budget,
            veto_tags=list(veto),
            preferred_cuisines=[],
            favorite_dish_ids=list(fav),
            blacklist_dish_ids=list(black),
            blacklist_restaurant_ids=[],
        )
    )
    session.commit()
    return user


def add_dish(
    session,
    name,
    *,
    mode="OUT_DINING",
    role="MEAT",
    price=10.0,
    vector=NEUTRAL,
    mains=(),
    aux=(),
    cuisine="S04固定样本",
):
    dish = Dish(
        name=name,
        mode_type=mode,
        restaurant_id=None,
        cuisine_type=cuisine,
        dish_role=role,
        price_or_cost=price,
        cook_minutes=10,
        appliance_tag=["炒锅"],
        ingredients_main=list(mains),
        ingredients_aux=list(aux),
        recipe_steps="",
        feature_vector=dict(vector) if vector is not None else None,
        image_url="",
    )
    session.add(dish)
    session.commit()
    return dish


# --------------------------------------------------------------------------- #
# 独立实现
# --------------------------------------------------------------------------- #


def expected_decay(lam, dt_exact, dt_similar):
    if dt_exact == 0:
        return 0.05
    exact = 1.0 if dt_exact is None else 1.0 - math.exp(-lam * dt_exact)
    similar = (
        1.0
        if dt_similar is None
        else 1.0 - 0.4 * math.exp(-lam * dt_similar)
    )
    return max(0.0, min(1.0, exact * similar))


def cos100(left, right):
    a = [float(left[key]) for key in FEATURE_KEYS]
    b = [float(right[key]) for key in FEATURE_KEYS]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return round(max(0.0, min(1.0, dot / (norm_a * norm_b))) * 100.0, 2)


def r_value(prior, swipe):
    return 0.4 * prior + 0.6 * swipe


def g_value(rs, omega):
    return omega * (sum(rs) / len(rs)) + (1.0 - omega) * min(rs)


def budget_score(price, budget):
    if price <= budget:
        return 85.0 + 15.0 * (1.0 - price / budget)
    return 85.0 * math.exp(-3.0 * (price - budget) / budget)


def weather_score(vector, temp_c):
    if temp_c <= 5:
        target = (0.05, 0.95)
    elif temp_c <= 12:
        target = (0.15, 0.85)
    elif temp_c <= 20:
        target = (0.35, 0.65)
    elif temp_c <= 28:
        target = (0.60, 0.35)
    else:
        target = (0.90, 0.15)
    diff = 0.6 * abs(vector["temp_fit"] - target[0]) + 0.4 * abs(
        vector["soup_level"] - target[1]
    )
    return 100.0 * (1.0 - diff)


# --------------------------------------------------------------------------- #
# 1. 忌口矩阵（expected 硬编码）
# --------------------------------------------------------------------------- #


def veto_matrix():
    cases = [
        ("海鲜", ["鲜虾"], True),
        ("海鲜", ["紫菜", "鸡蛋", "虾皮"], True),
        ("海鲜", ["螃蟹"], True),
        ("海鲜", ["扇贝"], True),
        ("海鲜", ["鱼"], True),
        ("海鲜", ["草鱼"], True),
        ("海鲜", ["生菜", "蚝油"], True),
        ("海鲜", ["猪里脊", "木耳", "胡萝卜"], False),
        ("海鲜", ["豆腐", "肉末"], False),
        ("海鲜", ["鸡肉", "党参"], False),
        ("海鲜", ["鱼香肉丝"], False),
        ("香菜", ["牛肉", "香菜"], True),
        ("花生", ["花生米", "菠菜"], True),
        # D-S04-02：具体标签只在本组内展开，不跨类别。
        ("鲜虾", ["鲜虾"], True),
        ("鲜虾", ["虾仁"], True),
        ("鲜虾", ["虾皮"], True),
        ("鲜虾", ["鲈鱼"], False),
        ("鲜虾", ["螃蟹"], False),
        ("鲜虾", ["扇贝"], False),
        ("鲜虾", ["生蚝"], False),
        ("鲈鱼", ["鲈鱼"], True),
        ("鲈鱼", ["草鱼"], False),
        ("鲈鱼", ["三文鱼"], False),
        ("牛肉", ["牛腩"], True),
        ("牛肉", ["羊肉"], False),
        ("牛肉", ["猪肉"], False),
        # 五项类别标签各自展开，不跨类别。
        ("海鲜", ["鲈鱼"], True),
        ("海味", ["紫菜"], True),
        ("海味", ["鲈鱼"], False),
        ("内脏", ["猪肝"], True),
        ("内脏", ["牛肉"], False),
        ("牛奶", ["淡奶油"], True),
        ("牛奶", ["辣椒"], False),
        ("辣", ["辣椒"], True),
        ("辣", ["牛奶"], False),
    ]
    rows = []
    for tag, ingredients, expected in cases:
        observed = bool(veto_hits(ingredients, [tag]))
        rows.append(
            {
                "tag": tag,
                "ingredients": ingredients,
                "expected_hit": expected,
                "observed_hit": observed,
                "match": observed == expected,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# 2. 防腻衰减
# --------------------------------------------------------------------------- #


def decay_samples():
    now = datetime(2026, 10, 26, 12, 0, 0)
    cases = [
        ("same_day", 0.5, 0, 0),
        ("exact3_similar1", 0.5, 3, 1),
        ("similar_only_same_day", 0.5, None, 0),
        ("fourteen_days", 0.5, 14, None),
        ("fifteen_days_window_out", 0.5, None, None),
        ("lambda1_exact3_similar1", 1.0, 3, 1),
    ]
    rows = []

    for name, lam, dt_exact, dt_similar in cases:
        engine, factory = make_session()
        session = factory()
        try:
            user = add_user(session, f"decay_{name}", NEUTRAL)
            target = add_dish(
                session,
                f"S04固定衰减-{name}",
                cuisine=f"S04衰减-{name}",
                mains=[f"S04衰减料-{name}"],
            )
            if dt_exact is not None:
                session.add(
                    EatingLog(
                        user_id=user.id,
                        dish_id=target.id,
                        mode_type="OUT_DINING",
                        cost_amount=0.0,
                        weather_snapshot="",
                        status_bubbles=[],
                        eaten_at=now - timedelta(days=dt_exact),
                    )
                )
            if dt_similar is not None:
                similar = add_dish(
                    session,
                    f"S04固定衰减同系-{name}",
                    cuisine=target.cuisine_type,
                    mains=[f"S04衰减乙料-{name}"],
                )
                session.add(
                    EatingLog(
                        user_id=user.id,
                        dish_id=similar.id,
                        mode_type="OUT_DINING",
                        cost_amount=0.0,
                        weather_snapshot="",
                        status_bubbles=[],
                        eaten_at=now - timedelta(days=dt_similar),
                    )
                )
            if name == "fifteen_days_window_out":
                # 唯一一条记录在 15 天前，窗口外。
                session.add(
                    EatingLog(
                        user_id=user.id,
                        dish_id=target.id,
                        mode_type="OUT_DINING",
                        cost_amount=0.0,
                        weather_snapshot="",
                        status_bubbles=[],
                        eaten_at=now - timedelta(days=15),
                    )
                )
            session.commit()

            expected = expected_decay(lam, dt_exact, dt_similar)
            observed = compute_decay_weights(
                session, user.id, [target], lambda_decay=lam, now=now
            )[target.id]
            rows.append(
                {
                    "case": name,
                    "lambda": lam,
                    "dt_exact": dt_exact,
                    "dt_similar": dt_similar,
                    "expected": round(expected, 6),
                    "observed": observed,
                    "abs_diff": round(abs(expected - observed), 8),
                    "match": abs(expected - observed) <= 5e-5,
                }
            )
        finally:
            session.close()
            engine.dispose()
    return rows


# --------------------------------------------------------------------------- #
# 3. 群组固定票矩阵
# --------------------------------------------------------------------------- #


def group_samples():
    vectors = {
        "u1": vec(spicy_level=1.0),
        "u2": vec(oily_level=1.0),
        "u3": vec(spicy_level=0.6, oily_level=0.8),
        "u4": vec(spicy_level=0.8, oily_level=0.6),
    }
    dish_vectors = {
        "d1": vec(spicy_level=1.0),
        "d2": vec(oily_level=1.0),
        "d3": vec(spicy_level=0.6, oily_level=0.8),
        "d5": vec(spicy_level=0.6, oily_level=0.8),
    }
    votes_matrix = {
        "normal": [
            ("u1", "d1", "SUPER_LIKE"),
            ("u2", "d1", "LIKE"),
            ("u3", "d1", "PASS"),
            ("u4", "d1", "SUPER_LIKE"),
        ],
        "partial_veto": [
            ("u1", "d1", "SUPER_LIKE"),
            ("u2", "d1", "SUPER_LIKE"),
            ("u3", "d1", "SUPER_LIKE"),
            ("u4", "d1", "VETO"),
            ("u1", "d2", "PASS"),
            ("u2", "d2", "PASS"),
            ("u3", "d2", "PASS"),
            ("u4", "d2", "PASS"),
        ],
        "all_veto": [
            ("u1", "d1", "VETO"),
            ("u2", "d1", "VETO"),
            ("u3", "d1", "VETO"),
            ("u4", "d1", "VETO"),
        ],
        "no_votes": [],
        "survivor_tie": [
            ("u1", "d3", "PASS"),
            ("u2", "d3", "PASS"),
            ("u3", "d3", "PASS"),
            ("u4", "d3", "PASS"),
            ("u1", "d5", "PASS"),
            ("u2", "d5", "PASS"),
            ("u3", "d5", "PASS"),
            ("u4", "d5", "PASS"),
        ],
    }
    swipe = {"SUPER_LIKE": 120.0, "LIKE": 100.0, "PASS": 40.0, "TIMEOUT": 60.0}

    engine, factory = make_session()
    session = factory()
    try:
        users = {
            name: add_user(session, f"group_{name}", vector)
            for name, vector in vectors.items()
        }
        dishes = {
            name: add_dish(session, f"S04固定共识-{name}", vector=vector)
            for name, vector in dish_vectors.items()
        }
        member_ids = [users[name].id for name in ("u1", "u2", "u3", "u4")]
        priors = {
            dish: {
                member: cos100(vectors[member], dish_vectors[dish])
                for member in vectors
            }
            for dish in dish_vectors
        }

        rows = []
        for name, raw_votes in votes_matrix.items():
            involved = sorted({dish for _, dish, _ in raw_votes}) or ["d1"]
            votes = [
                {
                    "user_id": users[member].id,
                    "dish_id": dishes[dish].id,
                    "vote_type": kind,
                }
                for member, dish, kind in raw_votes
            ]
            candidate_ids = [dishes[dish].id for dish in involved]

            expected = {}
            for dish in involved:
                rs = []
                masked = False
                for member in ("u1", "u2", "u3", "u4"):
                    kind = next(
                        (
                            vote_type
                            for voter, voted_dish, vote_type in raw_votes
                            if voter == member and voted_dish == dish
                        ),
                        "TIMEOUT",
                    )
                    if kind == "VETO":
                        masked = True
                        continue
                    rs.append(r_value(priors[dish][member], swipe[kind]))
                if masked:
                    expected[dish] = {
                        "masked": True,
                        "mean": None,
                        "least": None,
                        "group": 0.0,
                    }
                else:
                    expected[dish] = {
                        "masked": False,
                        "mean": sum(rs) / len(rs),
                        "least": min(rs),
                        "group": g_value(rs, 0.5),
                    }

            report = compute_group_consensus(
                session, member_ids, candidate_ids, votes, omega_group=0.5
            )
            observed = {
                item["dish_id"]: {
                    "masked": item["masked_by_veto"],
                    "mean": item["mean_satisfaction"],
                    "least": item["least_misery"],
                    "group": item["group_score"],
                }
                for item in report["dishes"]
            }
            matches = []
            for dish in involved:
                exp = expected[dish]
                obs = observed[dishes[dish].id]
                matches.append(exp["masked"] == obs["masked"])
                if not exp["masked"]:
                    matches.append(abs(exp["mean"] - obs["mean"]) <= 0.01)
                    matches.append(abs(exp["least"] - obs["least"]) <= 0.01)
                    matches.append(abs(exp["group"] - obs["group"]) <= 0.01)
                else:
                    matches.append(obs["group"] == 0.0)

            survivors = [
                (dish, exp["group"])
                for dish, exp in expected.items()
                if not exp["masked"]
            ]
            if survivors:
                winner_key = max(
                    survivors,
                    key=lambda pair: (pair[1], -dishes[pair[0]].id),
                )[0]
                expected_winner_id = dishes[winner_key].id
            else:
                winner_key = None
                expected_winner_id = None
            matches.append(report["winner_dish_id"] == expected_winner_id)
            matches.append(report["has_consensus"] == bool(survivors))

            rows.append(
                {
                    "case": name,
                    "dish_keys": {dish: dishes[dish].id for dish in involved},
                    "priors": priors,
                    "votes": raw_votes,
                    "omega": 0.5,
                    "expected": expected,
                    "expected_winner_key": winner_key,
                    "expected_winner_id": expected_winner_id,
                    "observed_winner": report["winner_dish_id"],
                    "expected_has_consensus": bool(survivors),
                    "observed_has_consensus": report["has_consensus"],
                    "observed": observed,
                    "match": all(matches),
                }
            )
        return rows
    finally:
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 4. 单人公式与归一化
# --------------------------------------------------------------------------- #


def single_sample():
    vector = {
        "spicy_level": 0.85,
        "oily_level": 0.75,
        "soup_level": 0.5,
        "temp_fit": 0.5,
        "satiety_level": 0.5,
        "prep_speed": 0.5,
        "social_fit": 0.5,
        "comfort_level": 0.5,
    }
    engine, factory = make_session()
    session = factory()
    try:
        user = add_user(session, "single_formula", vector, budget=25.0)
        dish = add_dish(
            session,
            "S04固定单人公式",
            price=10.0,
            vector=vector,
            mains=["S04公式料"],
            cuisine="S04公式菜系",
        )
        result = recommend_single(
            session,
            user.id,
            "OUT_DINING",
            budget=25.0,
            bubbles=["craving_heavy"],
            weather_temp=20.0,
            weather_text="晴",
            limit=10,
        )
        item = next(
            entry
            for entry in result["recommendations"]
            if entry["dish_id"] == dish.id
        )
        weights = {
            "alpha_taste": 0.50 / 1.15,
            "beta_weather": 0.25 / 1.15,
            "gamma_budget": 0.20 / 1.15,
            "delta_status": 0.20 / 1.15,
        }
        radar = {
            "taste": 100.0,
            "weather": weather_score(vector, 20.0),
            "budget": budget_score(10.0, 25.0),
            "freshness": 100.0,
            "status": 100.0,
        }
        raw = sum(
            weights[key] * radar[radar_key]
            for key, radar_key in (
                ("alpha_taste", "taste"),
                ("beta_weather", "weather"),
                ("gamma_budget", "budget"),
                ("delta_status", "status"),
            )
        )
        expected = {
            "params": {key: round(value, 6) for key, value in weights.items()},
            "radar": {key: round(value, 2) for key, value in radar.items()},
            "raw_score": round(raw, 6),
            "display_score": round(min(100.0, raw), 1),
        }
        observed = {
            "params": {
                key: result["params_used"][key]
                for key in (
                    "alpha_taste",
                    "beta_weather",
                    "gamma_budget",
                    "delta_status",
                )
            },
            "radar": item["radar_5d"],
            "raw_score": item["raw_score"],
            "display_score": item["total_score"],
        }
        return {
            "input": {
                "base_vector": vector,
                "bubble": "craving_heavy",
                "price": 10.0,
                "budget": 25.0,
                "weather_temp": 20.0,
            },
            "expected": expected,
            "observed": observed,
            "match": all(
                abs(expected["params"][key] - observed["params"][key]) <= 1e-4
                for key in expected["params"]
            )
            and all(
                abs(expected["radar"][key] - observed["radar"][key]) <= 0.01
                for key in expected["radar"]
            )
            and abs(expected["raw_score"] - observed["raw_score"]) <= 1e-4
            and abs(expected["display_score"] - observed["display_score"]) <= 1e-9,
        }
    finally:
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 5. 套餐约束
# --------------------------------------------------------------------------- #


def item(dish_id, role, price, score, oily):
    return {
        "dish_id": dish_id,
        "name": f"S04固定组合-{dish_id}",
        "dish_role": role,
        "price": price,
        "score": score,
        "oily_level": oily,
    }


def combo_samples():
    cases = {
        "feasible_budget_boundary": {
            "candidates": [
                item(1, "MEAT", 10.0, 80.0, 0.2),
                item(2, "VEG", 5.0, 60.0, 0.2),
                item(3, "SOUP", 5.0, 40.0, 0.2),
            ],
            "budget": 20.0,
            "expected_ids": [1, 2, 3],
            "expected_price": 20.0,
            "expected_oily": 0.2,
        },
        "budget_just_short": {
            "candidates": [
                item(1, "MEAT", 10.0, 80.0, 0.2),
                item(2, "VEG", 5.0, 60.0, 0.2),
                item(3, "SOUP", 5.0, 40.0, 0.2),
            ],
            "budget": 19.99,
            "expected_ids": None,
        },
        "oily_exact_065": {
            "candidates": [
                item(1, "MEAT", 10.0, 80.0, 0.65),
                item(2, "VEG", 5.0, 60.0, 0.65),
                item(3, "SOUP", 5.0, 40.0, 0.65),
            ],
            "budget": 100.0,
            "expected_ids": [1, 2, 3],
            "expected_price": 20.0,
            "expected_oily": 0.65,
        },
        "oily_over_065_rejected": {
            "candidates": [
                item(1, "MEAT", 10.0, 80.0, 0.6500001),
                item(2, "VEG", 5.0, 60.0, 0.65),
                item(3, "SOUP", 5.0, 40.0, 0.65),
            ],
            "budget": 100.0,
            "expected_ids": None,
        },
        "missing_role": {
            "candidates": [
                item(1, "MEAT", 10.0, 80.0, 0.2),
                item(2, "VEG", 5.0, 60.0, 0.2),
            ],
            "budget": 100.0,
            "expected_ids": None,
        },
        "top20_excludes_soup": {
            "candidates": [
                item(index, "MEAT", 1.0, 100.0 - index, 0.1)
                for index in range(1, 11)
            ]
            + [
                item(index, "VEG", 1.0, 100.0 - index, 0.1)
                for index in range(11, 21)
            ]
            + [item(21, "SOUP", 1.0, 1.0, 0.1)],
            "budget": 100.0,
            "expected_ids": None,
        },
        "high_score_oily_not_bypass": {
            "candidates": [
                item(1, "MEAT", 10.0, 999.0, 0.95),
                item(2, "MEAT", 10.0, 10.0, 0.2),
                item(3, "VEG", 5.0, 50.0, 0.95),
                item(4, "SOUP", 5.0, 40.0, 0.2),
            ],
            "budget": 100.0,
            "expected_ids": [2, 3, 4],
        },
    }
    rows = []
    for name, case in cases.items():
        result = optimize_combo(case["candidates"], budget=case["budget"])
        observed_ids = (
            [dish["dish_id"] for dish in result["dishes"]]
            if result is not None
            else None
        )
        row = {
            "case": name,
            "budget": case["budget"],
            "candidate_count": len(case["candidates"]),
            "expected_dish_ids": case["expected_ids"],
            "observed_dish_ids": observed_ids,
            "match": observed_ids == case["expected_ids"],
        }
        if result is not None:
            row["observed_total_price"] = result["total_price"]
            row["observed_avg_oily"] = result["avg_oily_level"]
            if "expected_price" in case:
                row["expected_total_price"] = case["expected_price"]
                row["match"] = row["match"] and abs(
                    result["total_price"] - case["expected_price"]
                ) <= 1e-6
            if "expected_oily" in case:
                row["expected_avg_oily"] = case["expected_oily"]
                row["match"] = row["match"] and abs(
                    result["avg_oily_level"] - case["expected_oily"]
                ) <= 1e-3
        rows.append(row)
    return rows


def main():
    payload = {
        "generated_at": NOW,
        "method": (
            "expected 由本脚本内的独立公式/硬编码矩阵给出；"
            "observed 由生产函数在隔离内存库上输出；两者分开记录。"
        ),
        "veto_matrix": veto_matrix(),
        "decay": decay_samples(),
        "group_consensus": group_samples(),
        "single_formula": single_sample(),
        "combo": combo_samples(),
    }
    payload["all_match"] = (
        all(row["match"] for row in payload["veto_matrix"])
        and all(row["match"] for row in payload["decay"])
        and all(row["match"] for row in payload["group_consensus"])
        and payload["single_formula"]["match"]
        and all(row["match"] for row in payload["combo"])
    )
    (OUT / "data" / "fixed_samples.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "veto_rows": len(payload["veto_matrix"]),
                "decay_rows": len(payload["decay"]),
                "group_rows": len(payload["group_consensus"]),
                "combo_rows": len(payload["combo"]),
                "single_match": payload["single_formula"]["match"],
                "all_match": payload["all_match"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload["all_match"] else 1


if __name__ == "__main__":
    sys.exit(main())
