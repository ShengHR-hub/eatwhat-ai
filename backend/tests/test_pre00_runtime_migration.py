"""PRE-00 回归：演示运行库兼容迁移必须幂等、可回滚、且拒绝碰原库。

这些用例只建临时 SQLite 文件，不读取也不写入 backend/eatwhat.db。
"""

import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

import backend.scripts.migrate_pre00_runtime_schema as migration
from backend.scripts.migrate_pre00_runtime_schema import (
    BATCH4_DB,
    DEMO_DB,
    migrate,
    schema_fingerprint,
)


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _state(path):
    connection = sqlite3.connect(path)
    try:
        rows = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("restaurants", "dishes_and_recipes", "group_rooms")
        }
    finally:
        connection.close()
    return {"sha256": _sha256(path), "schema": schema_fingerprint(path), "rows": rows}


def _legacy_db(path, feature_vector_nullable: bool = False) -> None:
    """v2.3.2 时代的 3 张关键表；不建 users 以缩小样本。"""
    not_null = "" if feature_vector_nullable else "NOT NULL"
    connection = sqlite3.connect(path)
    connection.executescript(
        f"""
        CREATE TABLE restaurants (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            category VARCHAR(64),
            avg_price FLOAT,
            rating FLOAT,
            longitude FLOAT,
            latitude FLOAT,
            distance_meters INTEGER,
            address VARCHAR(255)
        );
        CREATE TABLE dishes_and_recipes (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            mode_type VARCHAR(16) NOT NULL,
            restaurant_id INTEGER,
            cuisine_type VARCHAR(64),
            dish_role VARCHAR(16) NOT NULL,
            price_or_cost FLOAT,
            cook_minutes INTEGER,
            appliance_tag VARCHAR(32) NOT NULL,
            ingredients_main JSON NOT NULL,
            ingredients_aux JSON NOT NULL,
            recipe_steps TEXT,
            feature_vector JSON {not_null},
            image_url VARCHAR(255),
            FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
        );
        CREATE TABLE group_rooms (
            id INTEGER NOT NULL PRIMARY KEY,
            room_code VARCHAR(10) NOT NULL,
            host_user_id INTEGER NOT NULL,
            mode_type VARCHAR(16) NOT NULL,
            status VARCHAR(16) NOT NULL,
            member_user_ids JSON NOT NULL,
            candidate_dish_ids JSON NOT NULL,
            winner_dish_id INTEGER,
            consensus_report JSON,
            created_at DATETIME NOT NULL
        );
        INSERT INTO restaurants (id, name, source_type) VALUES (1, '测试门店', 'AMAP_POI');
        INSERT INTO dishes_and_recipes (
            id, name, mode_type, restaurant_id, dish_role, appliance_tag,
            ingredients_main, ingredients_aux, feature_vector
        ) VALUES (
            1, '测试菜', 'OUT_DINING', 1, 'MEAT', '["炒锅"]',
            '["土豆"]', '["盐"]',
            '{{"spicy_level":0.6,"oily_level":0.5,"soup_level":0.1,"temp_fit":0.5,"satiety_level":0.7,"prep_speed":0.6,"social_fit":0.4,"comfort_level":0.5}}'
        );
        """
    )
    connection.commit()
    connection.close()


def _columns(path, table):
    connection = sqlite3.connect(path)
    try:
        return {row[1]: row for row in connection.execute(f"PRAGMA table_info({table})")}
    finally:
        connection.close()


def test_adds_nullable_columns_relaxes_feature_vector_and_is_idempotent(tmp_path):
    db_path = tmp_path / "legacy.db"
    _legacy_db(db_path)
    before_sha = _sha256(db_path)

    first = migrate(db_path)
    assert "restaurants.campus" in first["added_columns"]
    assert "dishes_and_recipes.allergen_tags" in first["added_columns"]
    assert "group_rooms.campus" in first["added_columns"]
    assert first["rebuilt_tables"] == ["dishes_and_recipes"]
    assert first["idempotent"] is False
    assert first["sha256_before"] == before_sha
    assert first["sha256_after"] != before_sha
    assert first["foreign_key_check"] == []

    dishes = _columns(db_path, "dishes_and_recipes")
    assert dishes["feature_vector"][3] == 0, "feature_vector 必须放宽为可空"
    assert dishes["appliance_tag"][2] == "JSON"
    assert dishes["allergen_tags"][3] == 0

    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "SELECT name, feature_vector FROM dishes_and_recipes WHERE id = 1"
        ).fetchone()
    finally:
        connection.close()
    assert row[0] == "测试菜"
    assert json.loads(row[1])["spicy_level"] == 0.6

    after_first_sha = first["sha256_after"]
    second = migrate(db_path)
    assert second["idempotent"] is True
    assert second["added_columns"] == []
    assert second["rebuilt_tables"] == []
    assert second["schema_fingerprint_before"] == first["schema_fingerprint_after"]
    assert second["sha256_after"] == after_first_sha


def test_already_nullable_only_adds_columns(tmp_path):
    db_path = tmp_path / "nullable.db"
    _legacy_db(db_path, feature_vector_nullable=True)
    report = migrate(db_path)
    assert report["rebuilt_tables"] == []
    assert "dishes_and_recipes.allergen_tags" in report["added_columns"]
    assert _columns(db_path, "dishes_and_recipes")["feature_vector"][3] == 0


def test_refuses_demo_and_s10_databases():
    with pytest.raises(SystemExit, match="演示库|S10"):
        migrate(DEMO_DB)
    with pytest.raises(SystemExit, match="演示库|S10"):
        migrate(BATCH4_DB)


def test_refuses_hardlink_alias(tmp_path, monkeypatch):
    protected = tmp_path / "protected_demo.db"
    _legacy_db(protected)
    alias = tmp_path / "hardlink_alias.db"
    try:
        os.link(protected, alias)
    except OSError as exc:  # pragma: no cover - 依赖文件系统支持
        pytest.skip(f"当前文件系统不支持硬链接: {exc}")

    assert os.path.samefile(protected, alias)
    assert Path(alias).resolve() != Path(protected).resolve()
    monkeypatch.setattr(migration, "DEMO_DB", protected.resolve())
    before = _state(protected)
    with pytest.raises(SystemExit, match="演示库"):
        migration.migrate(alias)
    assert _state(protected) == before


def test_refuses_symlink_alias(tmp_path, monkeypatch):
    protected = tmp_path / "protected_s10.db"
    _legacy_db(protected)
    alias = tmp_path / "symlink_alias.db"
    try:
        alias.symlink_to(protected)
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - Windows 权限
        pytest.skip(f"当前环境不能创建符号链接: {exc}")

    assert os.path.samefile(protected, alias)
    monkeypatch.setattr(migration, "BATCH4_DB", protected.resolve())
    before = _state(protected)
    with pytest.raises(SystemExit, match="S10"):
        migration.migrate(alias)
    assert _state(protected) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows 大小写不敏感路径")
def test_refuses_case_alias(tmp_path, monkeypatch):
    protected = tmp_path / "protected_case.db"
    _legacy_db(protected)
    alias = Path(str(protected).replace("protected_case", "PROTECTED_CASE"))
    if not alias.exists():  # pragma: no cover - 非大小写不敏感文件系统
        pytest.skip("当前路径不改大小写也能定位同一文件")

    monkeypatch.setattr(migration, "DEMO_DB", protected.resolve())
    before = _state(protected)
    with pytest.raises(SystemExit, match="演示库"):
        migration.migrate(alias)
    assert _state(protected) == before


def test_missing_database_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        migrate(tmp_path / "does-not-exist.db")


def test_failure_rolls_back_every_change(tmp_path):
    db_path = tmp_path / "broken.db"
    _legacy_db(db_path)
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        ALTER TABLE group_rooms RENAME TO group_rooms_real;
        CREATE VIEW group_rooms AS SELECT * FROM group_rooms_real;
        """
    )
    connection.commit()
    connection.close()

    before_fingerprint = schema_fingerprint(db_path)
    before_sha = _sha256(db_path)
    with pytest.raises(RuntimeError):
        migrate(db_path)
    assert schema_fingerprint(db_path) == before_fingerprint
    assert _sha256(db_path) == before_sha
    assert "campus" not in _columns(db_path, "restaurants")
