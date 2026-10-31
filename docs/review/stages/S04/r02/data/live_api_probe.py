"""S04 隔离库真实 HTTP 探针：单人推荐 API 与群组 shortlist 同口径。

只写 `backend/eatwhat_s04_r02_iso.db`（由开发源库复制），保护演示库、
S10 库与开发源库。服务在 127.0.0.1:8016 启动，脚本自行拉起/停止。

验证：
1. 用户忌口 = ["海鲜"] 时，单人 API 与群组 shortlist 对同一批受控菜给出
   完全一致的保留集合；
2. 鲜虾/虾皮(辅料)/螃蟹/扇贝/鱼/草鱼/蚝油(辅料) 被排除；
3. 鱼香肉丝/麻婆豆腐/党参鸡汤 不被误判；
4. API/shortlist 调用前后，受控菜与用户偏好行完全不变；
5. 三受保护库 SHA-256 前后一致。
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path("D:/EatWhat")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.algorithms.group_recommender import shortlist_candidates  # noqa: E402
from backend.models import Dish, User, UserPreference  # noqa: E402

ISO_DB = ROOT / "backend" / "eatwhat_s04_r02_iso.db"
DEV_DB = ROOT / "backend" / "eatwhat_dev_pre00_r02.db"
OUT = ROOT / "docs" / "review" / "stages" / "S04" / "r02"
LOG = OUT / "logs" / "20_live_server.log"
BASE = "http://127.0.0.1:8016/api/v1"

PROTECTED = {
    "demo": ROOT / "backend" / "eatwhat.db",
    "s10_import": ROOT / "backend" / "eatwhat_batch4.db",
    "dev_source": DEV_DB,
}
EXPECTED_PROTECTED = {
    "demo": "775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b",
    "s10_import": "315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28",
    "dev_source": "b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579",
}

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

# name -> (ingredients_main, ingredients_aux, expected_keep)
CONTROLLED = {
    "S04探针鲜虾": (["鲜虾"], ["姜"], False),
    "S04探针虾皮": (["紫菜", "鸡蛋"], ["虾皮", "盐"], False),
    "S04探针螃蟹": (["螃蟹"], ["姜"], False),
    "S04探针扇贝": (["扇贝", "粉丝"], ["蒜"], False),
    "S04探针鱼": (["鱼"], ["姜"], False),
    "S04探针草鱼": (["草鱼"], ["豆芽"], False),
    "S04探针蚝油": (["生菜"], ["蚝油", "蒜"], False),
    "S04探针鱼香肉丝": (["猪里脊", "木耳", "胡萝卜"], ["豆瓣酱", "醋"], True),
    "S04探针麻婆豆腐": (["豆腐", "肉末"], ["豆瓣酱", "花椒"], True),
    "S04探针党参鸡汤": (["鸡肉", "党参"], ["姜", "盐"], True),
}
EXPECTED_KEEP = {
    name for name, (_, _, keep) in CONTROLLED.items() if keep
}
EXPECTED_DROP = set(CONTROLLED) - EXPECTED_KEEP
NULL_DISH_NAME = "S04探针未打标"
SPECIFIC_TAG = "鲜虾"
SPECIFIC_DROP = {"S04探针鲜虾", "S04探针虾皮"}
SPECIFIC_EXPECTED_KEEP = set(CONTROLLED) - SPECIFIC_DROP


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table_counts(session):
    from sqlalchemy import text

    names = [
        "users",
        "user_preferences",
        "restaurants",
        "dishes_and_recipes",
        "fridge_inventory",
        "eating_logs",
        "group_rooms",
        "room_votes",
    ]
    return {
        name: int(session.execute(text(f"select count(*) from {name}")).scalar())
        for name in names
    }


def controlled_state(session, user_id):
    from sqlalchemy import text

    dishes = session.execute(
        text(
            "select id, name, ingredients_main, ingredients_aux, feature_vector "
            "from dishes_and_recipes where name like 'S04探针%' order by id"
        )
    ).fetchall()
    prefs = session.execute(
        text(
            "select veto_tags, base_vector, default_budget, "
            "blacklist_dish_ids, blacklist_restaurant_ids "
            "from user_preferences where user_id=:uid"
        ),
        {"uid": user_id},
    ).fetchone()
    return {
        "dishes": [
            {
                "id": int(row[0]),
                "name": row[1],
                "ingredients_main": json.loads(row[2] or "[]"),
                "ingredients_aux": json.loads(row[3] or "[]"),
                "feature_vector": json.loads(row[4]) if row[4] else None,
            }
            for row in dishes
        ],
        "prefs": {
            "veto_tags": json.loads(prefs[0] or "[]"),
            "base_vector": json.loads(prefs[1] or "{}"),
            "default_budget": prefs[2],
            "blacklist_dish_ids": json.loads(prefs[3] or "[]"),
            "blacklist_restaurant_ids": json.loads(prefs[4] or "[]"),
        },
    }


def start_server():
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{ISO_DB.as_posix()}"
    handle = open(LOG, "wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8016",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        if process.poll() is not None:
            handle.close()
            raise RuntimeError(f"uvicorn 提前退出，详见 {LOG}")
        try:
            health = requests.get("http://127.0.0.1:8016/health", timeout=1)
            if health.status_code == 200:
                return process, handle, health
        except requests.RequestException:
            pass
        time.sleep(0.5)
    process.terminate()
    handle.close()
    raise RuntimeError("uvicorn 30 秒内未就绪")


def stop_server(process, handle):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    handle.close()


def main():
    assert ISO_DB.parent.exists()
    shutil.copyfile(DEV_DB, ISO_DB)
    source_copy_sha = sha256(ISO_DB)
    assert source_copy_sha == EXPECTED_PROTECTED["dev_source"]
    protected_before = {name: sha256(path) for name, path in PROTECTED.items()}
    assert protected_before == EXPECTED_PROTECTED, protected_before

    engine = create_engine(f"sqlite:///{ISO_DB.as_posix()}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        user = User(
            username="s04_probe_user",
            nickname="S04探针用户",
            avatar="",
            persona_title="",
            is_demo_persona=False,
        )
        specific_user = User(
            username="s04_probe_specific_user",
            nickname="S04探针鲜虾用户",
            avatar="",
            persona_title="",
            is_demo_persona=False,
        )
        session.add_all([user, specific_user])
        session.flush()
        session.add_all(
            [
                UserPreference(
                    user_id=user.id,
                    base_vector=dict(NEUTRAL),
                    default_budget=25.0,
                    veto_tags=["海鲜"],
                    preferred_cuisines=[],
                    favorite_dish_ids=[],
                    blacklist_dish_ids=[],
                    blacklist_restaurant_ids=[],
                ),
                UserPreference(
                    user_id=specific_user.id,
                    base_vector=dict(NEUTRAL),
                    default_budget=25.0,
                    veto_tags=[SPECIFIC_TAG],
                    preferred_cuisines=[],
                    favorite_dish_ids=[],
                    blacklist_dish_ids=[],
                    blacklist_restaurant_ids=[],
                ),
            ]
        )
        dish_rows = []
        for name, (mains, aux, _) in CONTROLLED.items():
            dish = Dish(
                name=name,
                mode_type="OUT_DINING",
                restaurant_id=None,
                cuisine_type="S04探针菜系",
                dish_role="MEAT",
                price_or_cost=10.0,
                cook_minutes=10,
                appliance_tag=["炒锅"],
                ingredients_main=list(mains),
                ingredients_aux=list(aux),
                recipe_steps="",
                feature_vector=dict(NEUTRAL),
                image_url="",
            )
            session.add(dish)
            dish_rows.append(dish)

        # N04 / D-S04-01：插一道 feature_vector 为 SQL NULL 的菜。
        null_dish = Dish(
            name=NULL_DISH_NAME,
            mode_type="OUT_DINING",
            restaurant_id=None,
            cuisine_type="S04探针菜系",
            dish_role="MEAT",
            price_or_cost=0.0,
            cook_minutes=10,
            appliance_tag=["炒锅"],
            ingredients_main=["S04未打标主料"],
            ingredients_aux=["盐"],
            recipe_steps="",
            feature_vector=None,
            image_url="",
        )
        session.add(null_dish)
        session.commit()
        user_id = int(user.id)
        specific_user_id = int(specific_user.id)
        controlled_ids = {int(dish.id) for dish in dish_rows}
        null_dish_id = int(null_dish.id)
        controlled_ids.add(null_dish_id)
        out_dining_ids = {
            int(row.id)
            for row in session.query(Dish)
            .filter(Dish.mode_type == "OUT_DINING")
            .all()
        }
        null_count = (
            session.query(Dish)
            .filter(
                Dish.mode_type == "OUT_DINING",
                Dish.feature_vector.is_(None),
            )
            .count()
        )
    finally:
        session.close()

    # API limit 上限 100；用 exclude_dish_ids 排掉种子菜，确保受控菜不被展示截断，
    # 从而区分「被忌口过滤」与「被 limit 截断」。
    exclude_seed_ids = sorted(out_dining_ids - controlled_ids)
    exclude_all_but_null = sorted(
        (out_dining_ids | controlled_ids) - {null_dish_id}
    )

    setup_sha = sha256(ISO_DB)
    session = Session()
    try:
        counts_before = table_counts(session)
        state_before = {
            "category_user": controlled_state(session, user_id),
            "specific_user": controlled_state(session, specific_user_id),
        }
        shortlist = shortlist_candidates(
            session, [user_id], "OUT_DINING", top_n=200
        )
        shortlist_ids = {int(item["dish_id"]) for item in shortlist}
        specific_shortlist = shortlist_candidates(
            session, [specific_user_id], "OUT_DINING", top_n=200
        )
        specific_shortlist_ids = {
            int(item["dish_id"]) for item in specific_shortlist
        }
    finally:
        session.close()

    process, handle, health = start_server()
    try:
        assert health.status_code == 200, health.text
        response = requests.post(
            f"{BASE}/recommend/single",
            json={
                "mode_type": "OUT_DINING",
                "limit": 100,
                "weather_temp": 20.0,
                "exclude_dish_ids": exclude_seed_ids,
            },
            headers={"X-User-Id": str(user_id)},
            timeout=30,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        api_ids = {int(item["dish_id"]) for item in payload["recommendations"]}
        assert null_dish_id not in api_ids, "NULL 向量菜进入了单人推荐"

        # D-S04-02：具体标签「鲜虾」只排虾类，不波及鲈鱼/螃蟹/扇贝。
        specific_response = requests.post(
            f"{BASE}/recommend/single",
            json={
                "mode_type": "OUT_DINING",
                "limit": 100,
                "weather_temp": 20.0,
                "exclude_dish_ids": exclude_seed_ids,
            },
            headers={"X-User-Id": str(specific_user_id)},
            timeout=30,
        )
        assert specific_response.status_code == 200, specific_response.text
        specific_payload = specific_response.json()
        specific_api_ids = {
            int(item["dish_id"]) for item in specific_payload["recommendations"]
        }
        assert null_dish_id not in specific_api_ids

        # 只剩 NULL 向量菜时，必须沿用现有空结果语义（不反向补回）。
        empty_response = requests.post(
            f"{BASE}/recommend/single",
            json={
                "mode_type": "OUT_DINING",
                "limit": 100,
                "weather_temp": 20.0,
                "combo_mode": True,
                "exclude_dish_ids": exclude_all_but_null,
            },
            headers={"X-User-Id": str(user_id)},
            timeout=30,
        )
        assert empty_response.status_code == 200, empty_response.text
        empty_payload = empty_response.json()
        assert empty_payload["recommendations"] == [], empty_payload
        assert empty_payload["combo"] is None, empty_payload
    finally:
        stop_server(process, handle)

    session = Session()
    try:
        counts_after = table_counts(session)
        state_after = {
            "category_user": controlled_state(session, user_id),
            "specific_user": controlled_state(session, specific_user_id),
        }
    finally:
        session.close()

    name_by_id = {
        item["id"]: item["name"]
        for item in state_before["category_user"]["dishes"]
    }
    api_controlled = {name_by_id[i] for i in api_ids & controlled_ids}
    shortlist_controlled = {name_by_id[i] for i in shortlist_ids & controlled_ids}
    specific_api_controlled = {
        name_by_id[i] for i in specific_api_ids & controlled_ids
    }
    specific_shortlist_controlled = {
        name_by_id[i] for i in specific_shortlist_ids & controlled_ids
    }

    assert api_controlled == EXPECTED_KEEP, api_controlled
    assert shortlist_controlled == EXPECTED_KEEP, shortlist_controlled
    assert api_controlled == shortlist_controlled
    assert EXPECTED_DROP.isdisjoint(api_controlled)
    assert EXPECTED_DROP.isdisjoint(shortlist_controlled)
    assert specific_api_controlled == SPECIFIC_EXPECTED_KEEP, specific_api_controlled
    assert (
        specific_shortlist_controlled == SPECIFIC_EXPECTED_KEEP
    ), specific_shortlist_controlled
    assert specific_api_controlled == specific_shortlist_controlled
    assert SPECIFIC_DROP.isdisjoint(specific_api_controlled)
    assert SPECIFIC_DROP.isdisjoint(specific_shortlist_controlled)
    assert null_dish_id not in api_ids
    assert null_dish_id not in shortlist_ids
    assert null_dish_id not in specific_api_ids
    assert null_dish_id not in specific_shortlist_ids
    assert null_count == 1
    assert counts_before == counts_after
    assert state_before == state_after

    protected_after = {name: sha256(path) for name, path in PROTECTED.items()}
    assert protected_after == protected_before == EXPECTED_PROTECTED

    result = {
        "base_url": "http://127.0.0.1:8016",
        "iso_db": str(ISO_DB),
        "iso_source": str(DEV_DB),
        "iso_sha256_source_copy": source_copy_sha,
        "iso_sha256_after_setup": setup_sha,
        "iso_sha256_after": sha256(ISO_DB),
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_before == protected_after,
        "user_id": user_id,
        "specific_user_id": specific_user_id,
        "controlled_dish_ids": sorted(controlled_ids),
        "expected_keep": sorted(EXPECTED_KEEP),
        "expected_drop": sorted(EXPECTED_DROP),
        "api": {
            "status": 200,
            "controlled_returned": sorted(api_controlled),
            "recommendation_count": len(payload["recommendations"]),
            "excluded_seed_dish_count": len(exclude_seed_ids),
        },
        "group_shortlist": {
            "controlled_returned": sorted(shortlist_controlled),
            "candidate_count": len(shortlist),
        },
        "category_tag": {
            "tag": "海鲜",
            "expected_keep": sorted(EXPECTED_KEEP),
            "expected_drop": sorted(EXPECTED_DROP),
            "sets_equal": api_controlled == shortlist_controlled,
        },
        "specific_tag": {
            "tag": SPECIFIC_TAG,
            "expected_keep": sorted(SPECIFIC_EXPECTED_KEEP),
            "expected_drop": sorted(SPECIFIC_DROP),
            "api_status": specific_response.status_code,
            "api_returned": sorted(specific_api_controlled),
            "shortlist_returned": sorted(specific_shortlist_controlled),
            "sets_equal": specific_api_controlled == specific_shortlist_controlled,
            "excluded_shrimp_only": sorted(SPECIFIC_DROP),
        },
        "null_vector": {
            "dish_id": null_dish_id,
            "dish_name": NULL_DISH_NAME,
            "out_dining_null_count_before": null_count,
            "out_dining_null_count_after": sum(
                1
                for dish in state_after["category_user"]["dishes"]
                if dish["feature_vector"] is None
            ),
            "api_returned": null_dish_id in api_ids,
            "shortlist_returned": null_dish_id in shortlist_ids,
            "specific_api_returned": null_dish_id in specific_api_ids,
            "specific_shortlist_returned": null_dish_id
            in specific_shortlist_ids,
            "empty_candidate_api": {
                "status": empty_response.status_code,
                "recommendation_count": len(empty_payload["recommendations"]),
                "combo": empty_payload["combo"],
            },
        },
        "sets_equal": api_controlled == shortlist_controlled
        and specific_api_controlled == specific_shortlist_controlled,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "state_before": state_before,
        "state_after": state_after,
        "db_state_unchanged": counts_before == counts_after
        and state_before == state_after,
        "passed": True,
    }
    (OUT / "data" / "live_api_probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if "state" not in key},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
