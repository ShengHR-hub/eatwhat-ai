"""模块 3 虚拟冰箱：接口行为回归。

覆盖四件事：
1. `GET /fridge/{user_id}` 的临期置顶排序；
2. `POST /fridge/{user_id}` 的幂等与 REMOVE 语义；
3. `POST /fridge/shopping-list` 的 owned / to_buy 切分；
4. 参数校验（空 dish_ids 400、菜谱全不存在 404）。

种子数据（用户 2 = 粤菜 yue_cai）冰箱里是 鸡蛋 / 青菜 / 番茄 / 豆腐，
其中鸡蛋、豆腐 expire_days <= 2，是天然的临期样本。
"""


def test_fridge_list_puts_expiring_first(client):
    response = client.get("/api/v1/fridge/2", headers={"X-User-Id": "2"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 2
    items = payload["items"]
    assert len(items) >= 4
    flags = [item["is_expiring_soon"] for item in items]
    # 一旦出现非临期，后面就只能是非临期
    assert flags == sorted(flags, reverse=True)
    assert items[0]["is_expiring_soon"] is True


def test_fridge_list_unknown_user_returns_404(client):
    response = client.get("/api/v1/fridge/99999", headers={"X-User-Id": "99999"})
    assert response.status_code == 404


def test_fridge_add_is_idempotent(client):
    body = {
        "ingredient_name": "牛油果",
        "category": "新鲜果蔬",
        "quantity_desc": "2 个",
        "expire_days": 4,
    }
    first = client.post("/api/v1/fridge/2", json=body, headers={"X-User-Id": "2"})
    assert first.status_code == 200

    second = client.post(
        "/api/v1/fridge/2", json={**body, "expire_days": 1}, headers={"X-User-Id": "2"}
    )
    assert second.status_code == 200

    items = second.json()["items"]
    names = [item["ingredient_name"] for item in items]
    assert names.count("牛油果") == 1
    assert items[0]["ingredient_name"] == "牛油果"
    assert items[0]["expire_days"] == 1


def test_fridge_remove_missing_returns_404(client):
    response = client.post(
        "/api/v1/fridge/2",
        json={"ingredient_name": "不存在的食材", "action": "REMOVE"},
        headers={"X-User-Id": "2"},
    )
    assert response.status_code == 404
    assert "不存在的食材" in response.json()["detail"]


def test_fridge_remove_existing_item(client):
    before = client.get(
        "/api/v1/fridge/2", headers={"X-User-Id": "2"}
    ).json()["items"]
    target = before[0]["ingredient_name"]
    response = client.post(
        "/api/v1/fridge/2",
        json={"ingredient_name": target, "action": "REMOVE"},
        headers={"X-User-Id": "2"},
    )
    assert response.status_code == 200
    names = [item["ingredient_name"] for item in response.json()["items"]]
    assert target not in names
    assert len(names) == len(before) - 1


def test_shopping_list_splits_owned_and_to_buy(client):
    catalog = client.get("/api/v1/catalog/dishes?ids=61").json()
    assert catalog, "目录接口应该能查到下厨菜谱"
    dish_id = catalog[0]["dish_id"]

    response = client.post(
        "/api/v1/fridge/shopping-list",
        json={"user_id": 2, "dish_ids": [dish_id]},
        headers={"X-User-Id": "2"},
    )
    assert response.status_code == 200
    payload = response.json()
    owned_names = {item["ingredient"] for item in payload["owned_ingredients"]}
    buy_names = {item["ingredient"] for item in payload["to_buy_ingredients"]}

    assert owned_names & {"鸡蛋", "番茄"}, owned_names
    assert owned_names.isdisjoint(buy_names)
    for item in payload["to_buy_ingredients"]:
        assert item["used_by"], "待买食材要带上「哪几道菜要用」"
        assert item["from_fridge"] is False


def test_shopping_list_rejects_empty_and_unknown(client):
    empty = client.post(
        "/api/v1/fridge/shopping-list",
        json={"user_id": 2, "dish_ids": []},
        headers={"X-User-Id": "2"},
    )
    assert empty.status_code == 400

    unknown = client.post(
        "/api/v1/fridge/shopping-list",
        json={"user_id": 2, "dish_ids": [99999]},
        headers={"X-User-Id": "2"},
    )
    assert unknown.status_code == 404
