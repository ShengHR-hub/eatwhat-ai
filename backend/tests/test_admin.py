import json

import pytest

from backend.models import Dish, EatingLog, Restaurant, RoomVote
from backend.routers import admin as admin_router
from backend.routers.admin_experiments import DEFAULT_BENCHMARK_PATH


VECTOR = {
    "spicy_level": 0.1,
    "oily_level": 0.2,
    "soup_level": 0.3,
    "temp_fit": 0.4,
    "satiety_level": 0.5,
    "prep_speed": 0.6,
    "social_fit": 0.7,
    "comfort_level": 0.8,
}


def test_restaurant_crud_soft_delete_preserves_history(admin_client, db):
    restaurant = db.query(Restaurant).first()
    dish = db.query(Dish).filter(Dish.restaurant_id == restaurant.id).first()
    log = EatingLog(user_id=1, dish_id=dish.id, mode_type="OUT_DINING")
    db.add(log)
    db.commit()
    log_id = log.id

    created = admin_client.post(
        "/api/v1/admin/restaurants",
        json={
            "name": "G4 隔离门店",
            "source_type": "AMAP_POI",
            "campus": "SIYUAN",
            "longitude": 109.078487,
            "latitude": 34.234818,
            "avg_price": 23.5,
            "rating": 4.2,
        },
    )
    assert created.status_code == 201
    restaurant_id = created.json()["id"]
    assert created.json()["deleted_at"] is None

    listed = admin_client.get(
        "/api/v1/admin/restaurants",
        params={"restaurant_id": restaurant_id, "campus": "SIYUAN"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = admin_client.put(
        f"/api/v1/admin/restaurants/{restaurant_id}", json={"rating": None, "category": "测试分类"}
    )
    assert updated.status_code == 200
    assert updated.json()["rating"] is None
    assert updated.json()["category"] == "测试分类"

    deleted = admin_client.delete(f"/api/v1/admin/restaurants/{restaurant_id}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
    assert admin_client.get(f"/api/v1/admin/restaurants/{restaurant_id}").status_code == 200
    assert admin_client.delete(f"/api/v1/admin/restaurants/{restaurant_id}").status_code == 404

    # 既有外食门店下架会级联软删除菜品，但历史流水仍在且外键不变。
    offlined = admin_client.delete(f"/api/v1/admin/restaurants/{restaurant.id}")
    assert offlined.status_code == 200
    assert offlined.json()["dishes_offlined"] >= 1
    db.expire_all()
    assert db.get(Dish, dish.id).deleted_at is not None
    assert db.get(EatingLog, log_id).dish_id == dish.id


def test_dish_crud_filters_and_binding_validation(admin_client, db):
    restaurant_id = db.query(Restaurant.id).first()[0]
    payload = {
        "name": "G4 隔离菜谱",
        "mode_type": "HOME_COOKING",
        "cuisine_type": "G4_TEST",
        "dish_role": "ONE_MEAL",
        "price_or_cost": 8,
        "appliance_tag": ["电饭煲", "一锅出"],
        "ingredients_main": ["鸡肉", "土豆"],
        "ingredients_aux": ["香菇"],
        "feature_vector": VECTOR,
        "allergen_tags": ["香菜"],
        "is_synthetic": True,
    }
    created = admin_client.post("/api/v1/admin/dishes", json=payload)
    assert created.status_code == 201
    dish_id = created.json()["id"]
    assert created.json()["tagging_status"] == "SUCCESS"
    assert created.json()["campus"] == "SHARED"

    response = admin_client.get(
        "/api/v1/admin/dishes",
        params={"dish_id": dish_id, "mode_type": "HOME_COOKING", "cuisine_type": "G4_TEST"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["appliance_tag"] == ["电饭煲", "一锅出"]

    updated = admin_client.put(
        f"/api/v1/admin/dishes/{dish_id}", json={"feature_vector": None, "cook_minutes": 25}
    )
    assert updated.status_code == 200
    assert updated.json()["feature_vector"] is None
    assert updated.json()["tagging_status"] == "PENDING"

    rejected = admin_client.put(
        f"/api/v1/admin/dishes/{dish_id}", json={"restaurant_id": restaurant_id}
    )
    assert rejected.status_code == 422
    db.expire_all()
    assert db.get(Dish, dish_id).restaurant_id is None

    assert admin_client.delete(f"/api/v1/admin/dishes/{dish_id}").status_code == 200
    assert admin_client.get("/api/v1/admin/dishes", params={"dish_id": dish_id}).json()["total"] == 0
    assert admin_client.get(f"/api/v1/admin/dishes/{dish_id}").json()["deleted_at"] is not None


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "坏向量", "mode_type": "HOME_COOKING", "feature_vector": {"spicy_level": 0.2}},
        {"name": "坏厨具", "mode_type": "HOME_COOKING", "appliance_tag": ["电磁炉"]},
        {"name": "缺门店", "mode_type": "OUT_DINING"},
        {"name": "布尔金额", "mode_type": "HOME_COOKING", "price_or_cost": True},
    ],
)
def test_dish_invalid_input_is_rejected_without_writes(admin_client, db, payload):
    before = db.query(Dish).count()
    response = admin_client.post("/api/v1/admin/dishes", json=payload)
    assert response.status_code == 422
    assert db.query(Dish).count() == before


def test_admin_not_found_and_empty_update(admin_client):
    assert admin_client.get("/api/v1/admin/restaurants/999999").status_code == 404
    assert admin_client.get("/api/v1/admin/dishes/999999").status_code == 404
    assert admin_client.put("/api/v1/admin/restaurants/1", json={}).status_code == 422
    assert admin_client.put("/api/v1/admin/dishes/1", json={}).status_code == 422


def test_llm_tag_requires_real_configuration(admin_client, monkeypatch):
    dish_id = admin_client.post(
        "/api/v1/admin/dishes",
        json={"name": "待打标隔离菜", "mode_type": "HOME_COOKING"},
    ).json()["id"]
    for key in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    response = admin_client.post("/api/v1/admin/llm-tag", json={"dish_ids": [dish_id]})
    assert response.status_code == 503
    assert "未发起调用" in response.json()["detail"]


def test_llm_tag_success_and_skip_use_existing_validator(admin_client, db, monkeypatch):
    dish_id = admin_client.post(
        "/api/v1/admin/dishes",
        json={"name": "真实返回隔离菜", "mode_type": "HOME_COOKING", "dish_role": "VEG"},
    ).json()["id"]
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    content = json.dumps(
        [
            {
                "dish_name": "真实返回隔离菜",
                "dish_role": "MEAT",
                "feature_vector": VECTOR,
                "allergen_tags": ["花生"],
            }
        ],
        ensure_ascii=False,
    )

    def fake_call(base_url, api_key, model, messages):
        assert "真实返回隔离菜" in messages[1]["content"]
        return content, {"id": "req-g4", "model": model, "usage": {"prompt_tokens": 1}}

    monkeypatch.setattr(admin_router, "call_model", fake_call)
    response = admin_client.post("/api/v1/admin/llm-tag", json={"dish_ids": [dish_id]})
    assert response.status_code == 200
    assert response.json()["success_count"] == 1
    db.expire_all()
    row = db.get(Dish, dish_id)
    assert row.dish_role == "MEAT"
    assert row.feature_vector == VECTOR
    assert row.allergen_tags == ["花生"]
    assert row.llm_meta["request_id"] == "req-g4"

    skipped = admin_client.post("/api/v1/admin/llm-tag", json={"dish_ids": [dish_id]})
    assert skipped.status_code == 200
    assert skipped.json()["success_count"] == 0
    assert skipped.json()["skipped"] == [dish_id]


def test_llm_tag_invalid_model_response_marks_failure(admin_client, db, monkeypatch):
    dish_id = admin_client.post(
        "/api/v1/admin/dishes",
        json={"name": "失败可见隔离菜", "mode_type": "HOME_COOKING"},
    ).json()["id"]
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setattr(admin_router, "call_model", lambda *args: ("not-json", {"id": "bad"}))
    response = admin_client.post("/api/v1/admin/llm-tag", json={"dish_ids": [dish_id]})
    assert response.status_code == 200
    assert response.json()["failed_count"] == 1
    db.expire_all()
    row = db.get(Dish, dish_id)
    assert row.tagging_status == "FAILED"
    assert row.feature_vector is None
    assert row.tagging_error == "json_parse_error"


def test_experiments_never_falls_back_to_seed_or_smoke(admin_client, monkeypatch, tmp_path):
    """基准文件缺失时必须返回 available=False，不能拿种子/冒烟数据顶替。

    原写法把主断言包在 `if not DEFAULT_BENCHMARK_PATH.exists()` 里，而该文件
    在仓库里实际存在（43KB），等于主断言从未执行——环境相关的假绿。
    现在无条件把路径指到不存在的文件，断言一定跑。
    """
    monkeypatch.delenv("G3_BENCHMARK_PATH", raising=False)
    missing = tmp_path / "missing.json"
    monkeypatch.setenv("ADMIN_BENCHMARK_PATH", str(missing))

    response = admin_client.get("/api/v1/admin/experiments")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["available"] is False
    assert body["duplication_rate_curve"]["days"] == []
    assert body["group_satisfaction_bars"]["strategies"] == []


def test_experiments_reads_valid_real_json_and_rejects_other_params(admin_client, monkeypatch, tmp_path):
    path = tmp_path / "parallel_benchmark_full.json"
    payload = {
        "generated_at": "2026-10-29T12:00:00",
        "sample": {"personas": 200, "days": 60, "meals_per_day": 2, "rooms": 1000, "members_per_room": 4},
        "duplication_rate_curve": {
            "days": list(range(1, 15)),
            "ours_lambda_0.5": [0.01] * 14,
            "baseline_no_decay": [0.02] * 14,
        },
        "group_satisfaction_bars": {
            "strategies": ["mixed_omega_0.5", "average_omega_1.0", "random"],
            "avg_scores": [80, 81, 60],
            "least_misery_scores": [70, 65, 30],
        },
        "params": {"lambda_val": 0.5, "omega_val": 0.5, "seed": 7, "errors": []},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("ADMIN_BENCHMARK_PATH", str(path))
    response = admin_client.get("/api/v1/admin/experiments", params={"lambda_val": 0.5, "omega_val": 0.5})
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["sample"]["rooms"] == 1000
    assert response.json()["duplication_rate_curve"] == payload["duplication_rate_curve"]
    assert response.json()["meta"]["seed"] == 7

    unsupported = admin_client.get("/api/v1/admin/experiments", params={"lambda_val": 0.8})
    assert unsupported.status_code == 200
    assert unsupported.json()["available"] is False
    filtered = admin_client.get("/api/v1/admin/experiments", params={"campus": "SIYUAN"})
    assert filtered.json()["applicable"] is False
    assert filtered.json()["meta"]["scope"] == "GLOBAL"
