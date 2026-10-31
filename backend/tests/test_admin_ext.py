"""管理后台扩展接口的回归用例。

这批端点（角色提权、算法参数热更新、导入、打标队列）此前在 tests/ 下
零引用——require_admin 被误删、参数热更新失效、导入静默丢行都不会让测试变红。
"""

import io

import pytest

from backend.models import Dish, User


def _csv_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)


def _ensure_admin_preference(session_factory):
    """给 fixture 管理员补一份饮食基因配置。

    admin_client 带 Bearer 令牌，而 require_user_id 是「令牌优先」，
    请求头 X-User-Id 会被忽略——推荐接口实际用的是管理员身份。
    管理员是测试夹具临时建的，种子里没有它的 UserPreference。
    """
    from backend.models import User, UserPreference

    with session_factory() as session:
        admin_id = session.query(User.id).filter(User.role == "ADMIN").first()[0]
        exists = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == admin_id)
            .first()
        )
        if exists is None:
            src = session.query(UserPreference).first()
            session.add(
                UserPreference(
                    user_id=admin_id,
                    base_vector=dict(src.base_vector or {}),
                    default_budget=float(src.default_budget or 25),
                    veto_tags=[],
                    preferred_cuisines=[],
                    favorite_dish_ids=[],
                    blacklist_dish_ids=[],
                    blacklist_restaurant_ids=[],
                )
            )
            session.commit()
    return admin_id


class TestAdminExtAuth:
    """鉴权负例：这是整份审查里最该补的一块。"""

    def test_no_token_rejected(self, client, session_factory):
        resp = client.post(
            "/api/v1/admin/restaurants",
            json={"name": "无令牌门店", "source_type": "CANTEEN", "category": "测试", "campus": "SIYUAN"},
        )
        assert resp.status_code in (401, 403), resp.text

    def test_plain_user_cannot_delete_restaurant(self, user_client, session_factory):
        from backend.models import Restaurant

        with session_factory() as session:
            rid = session.query(Restaurant.id).first()[0]

        resp = user_client.delete(f"/api/v1/admin/restaurants/{rid}")
        assert resp.status_code == 403, resp.text

        # 数据必须没变
        with session_factory() as session:
            row = session.get(Restaurant, rid)
            assert row is not None and row.deleted_at is None

    def test_plain_user_cannot_change_algo(self, user_client):
        resp = user_client.put("/api/v1/admin/settings/algo", json={"lambda_decay": 0.9})
        assert resp.status_code == 403, resp.text

    def test_plain_user_cannot_promote_self(self, user_client, session_factory):
        with session_factory() as session:
            uid = session.query(User.id).filter(User.role == "USER").first()[0]
        resp = user_client.patch(f"/api/v1/admin/users/{uid}/role", json={"role": "ADMIN"})
        assert resp.status_code == 403, resp.text


class TestAlgoHotReload:
    """后台改参必须真的影响打分——之前被 algo_configs 的固定行覆盖掉了。"""

    @pytest.fixture(autouse=True)
    def _restore_runtime_params(self):
        """改参写的是进程级全局缓存，测试完必须还原。

        不还原会污染后续用例：test_s04 的归一化断言、test_single_recommender
        的权重期望都读同一份 current_algo_params()。
        """
        from backend.config import DEFAULT_ALGO_PARAMS, set_algo_params

        set_algo_params(dict(DEFAULT_ALGO_PARAMS))
        yield
        set_algo_params(dict(DEFAULT_ALGO_PARAMS))

    @pytest.fixture(autouse=True)
    def _restore_runtime_params(self):
        """改参写的是进程级全局缓存，测试完必须还原。

        不还原会污染后续用例：test_s04 的归一化断言、test_single_recommender
        的权重期望都读同一份 current_algo_params()。
        """
        from backend.config import DEFAULT_ALGO_PARAMS, set_algo_params

        set_algo_params(dict(DEFAULT_ALGO_PARAMS))
        yield
        set_algo_params(dict(DEFAULT_ALGO_PARAMS))

    def test_saved_param_actually_used(self, admin_client, session_factory):
        put = admin_client.put(
            "/api/v1/admin/settings/algo",
            json={"lambda_decay": 0.93, "alpha_taste": 0.4},
        )
        assert put.status_code == 200, put.text

        _ensure_admin_preference(session_factory)

        rec = admin_client.post(
            "/api/v1/recommend/single",
            json={
                "mode_type": "OUT_DINING",
                "campus": "SIYUAN",
                "bubbles": [],
                "weather_temp": 20,
                "weather_text": "晴",
                "limit": 3,
                "combo_mode": False,
            },
        )
        assert rec.status_code == 200, rec.text
        used = rec.json().get("params_used") or {}
        # 四权重会被归一化，λ 不是权重、应原样回传
        assert abs(float(used.get("lambda_decay")) - 0.93) < 1e-6, used

    def test_zero_weights_rejected_or_safe(self, admin_client, session_factory):
        """四权重同时为 0 不能让后续推荐 500。"""
        admin_client.put(
            "/api/v1/admin/settings/algo",
            json={"alpha_taste": 0, "beta_weather": 0, "gamma_budget": 0, "delta_status": 0},
        )
        _ensure_admin_preference(session_factory)
        rec = admin_client.post(
            "/api/v1/recommend/single",
            json={
                "mode_type": "OUT_DINING",
                "campus": "SIYUAN",
                "bubbles": [],
                "weather_temp": 20,
                "weather_text": "晴",
                "limit": 3,
                "combo_mode": False,
            },
        )
        assert rec.status_code == 200, rec.text


class TestImportCommit:
    """导入的三种静默失败：表头空格、非法价格、GBK 编码。"""

    def _payload(self, mapping, rows):
        """mapping 的键是字段名（name/price_or_cost/...），值是源列名。"""
        return {"mapping": mapping, "rows": rows}

    def test_header_with_spaces_still_maps(self, admin_client, session_factory):
        """表头带首尾空格时，预览列名与行键必须同源，否则提交后 0 条。"""
        resp = admin_client.post(
            "/api/v1/admin/import/commit",
            json=self._payload(
                {"name": "  名称  ", "price_or_cost": "价格/成本"},
                [{"  名称  ": "空格表头菜", "价格/成本": "12"}],
            ),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["created"] == 1, resp.text

        with session_factory() as session:
            assert session.query(Dish).filter(Dish.name == "空格表头菜").first() is not None

    def test_invalid_price_reported_not_silently_dropped(self, admin_client, session_factory):
        resp = admin_client.post(
            "/api/v1/admin/import/commit",
            json=self._payload(
                {"name": "名称", "price_or_cost": "价格/成本"},
                [{"名称": "价格坏掉的菜", "价格/成本": "约25元"}],
            ),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["created"] == 0
        assert body["skipped"] == 1
        assert body["errors"], "非法价格必须进 errors，而不是静默写 None"
        assert body["errors"][0]["field"] == "price_or_cost"

        with session_factory() as session:
            assert session.query(Dish).filter(Dish.name == "价格坏掉的菜").first() is None

    def test_invalid_role_reported(self, admin_client):
        resp = admin_client.post(
            "/api/v1/admin/import/commit",
            json=self._payload(
                {"name": "名称", "dish_role": "角色"},
                [{"名称": "角色非法的菜", "角色": "DESSERT"}],
            ),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["created"] == 0
        assert any(e["field"] == "dish_role" for e in body["errors"]), body

    def test_gbk_csv_decodes_without_garbling(self, admin_client, session_factory):
        """中文 Excel 默认导出 GBK，以前 errors='replace' 会把菜名写成乱码入库。"""
        text = "名称,价格/成本\n番茄牛腩煲,28\n"
        resp = admin_client.post(
            "/api/v1/admin/import/preview",
            files={"file": ("gbk.csv", _csv_bytes(text, "gb18030"), "text/csv")},
        )
        assert resp.status_code == 200, resp.text
        columns = resp.json()["columns"]
        assert "名称" in columns, columns


class TestRoleChange:
    def test_promote_and_demote(self, admin_client, session_factory):
        with session_factory() as session:
            uid = session.query(User.id).filter(User.role == "USER").first()[0]

        up = admin_client.patch(f"/api/v1/admin/users/{uid}/role", json={"role": "ADMIN"})
        assert up.status_code == 200, up.text
        with session_factory() as session:
            assert session.get(User, uid).role == "ADMIN"

        down = admin_client.patch(f"/api/v1/admin/users/{uid}/role", json={"role": "USER"})
        assert down.status_code == 200, down.text

    def test_cannot_demote_self(self, admin_client, session_factory):
        me = admin_client.get("/api/v1/auth/me").json()
        resp = admin_client.patch(
            f"/api/v1/admin/users/{me['user_id']}/role", json={"role": "USER"}
        )
        assert resp.status_code == 409, resp.text


class TestLoginRateLimit:
    def test_repeated_failures_locked(self, client):
        from backend.routers import auth_local

        auth_local._login_failures.clear()
        codes = []
        for _ in range(6):
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "no_such_user", "password": "wrong-pass"},
            )
            codes.append(resp.status_code)
        assert codes[:5] == [401] * 5, codes
        assert codes[5] == 429, codes

    def test_success_resets_counter(self, client, session_factory):
        from backend.models import AuthCredential, User
        from backend.routers import auth_local
        from backend.routers.auth_local import _hash_password

        auth_local._login_failures.clear()
        with session_factory() as session:
            user = User(username="ratelimit_probe", nickname="限流探针", role="USER", is_demo_persona=False)
            session.add(user)
            session.flush()
            session.add(AuthCredential(user_id=user.id, password_hash=_hash_password("rightpass")))
            session.commit()

        for _ in range(3):
            client.post("/api/v1/auth/login", json={"username": "ratelimit_probe", "password": "bad"})
        ok = client.post(
            "/api/v1/auth/login", json={"username": "ratelimit_probe", "password": "rightpass"}
        )
        assert ok.status_code == 200, ok.text
        assert ("ratelimit_probe", "testclient") not in auth_local._login_failures
