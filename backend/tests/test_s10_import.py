import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from backend.scripts.fetch_amap_poi import (
    import_canteens,
    import_pois,
    import_rejects,
)
from backend.scripts.import_open_recipes import generate_recipes, import_recipes
from backend.scripts.migrate_s10_data_schema import migrate
from backend.scripts.s10_common import make_session


def _poi(poi_id: str, campus: str = "SIYUAN", name: str = "测试餐厅") -> dict:
    return {
        "id": poi_id,
        "name": name,
        "type": "餐饮服务;中餐厅;中餐厅",
        "typecode": "050100",
        "address": "测试路 1 号",
        "location": "109.078487,34.234818",
        "distance": "0",
        "tag": None,
        "rating": None,
        "cost": None,
        "_distance_m": 0.0,
        "campus": campus,
        "is_synthetic": 0,
        "source_dataset": "amap_place_around_20261025",
    }


def _write_jsonl(path: Path, rows) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "import.db"
    first = migrate(db_path)
    second = migrate(db_path)
    # 新库由 Base.metadata.create_all 直接建全量列；首次仍会补建两个唯一索引。
    assert first["added_columns"] == []
    assert set(first["added_indexes"]) == {
        "ux_restaurants_source",
        "ux_dishes_source",
    }
    assert second["idempotent"] is True
    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}"))
    restaurant_columns = {column["name"] for column in inspector.get_columns("restaurants")}
    assert {"campus", "source_dataset", "source_record_id", "is_synthetic"} <= restaurant_columns
    dish_columns = {
        column["name"] for column in inspector.get_columns("dishes_and_recipes")
    }
    assert {"tagging_status", "allergen_tags", "feature_vector", "is_synthetic"} <= dish_columns


def _legacy_db(path: Path, feature_vector_not_null: bool) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        f"""
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY, name VARCHAR(128) NOT NULL,
            source_type VARCHAR(32) NOT NULL, category VARCHAR(64),
            avg_price FLOAT, rating FLOAT, longitude FLOAT, latitude FLOAT,
            distance_meters INTEGER, address VARCHAR(255)
        );
        CREATE TABLE dishes_and_recipes (
            id INTEGER PRIMARY KEY, name VARCHAR(128) NOT NULL,
            mode_type VARCHAR(16) NOT NULL, restaurant_id INTEGER,
            cuisine_type VARCHAR(64), dish_role VARCHAR(16) NOT NULL,
            price_or_cost FLOAT, cook_minutes INTEGER,
            appliance_tag JSON NOT NULL, ingredients_main JSON NOT NULL,
            ingredients_aux JSON NOT NULL, recipe_steps TEXT,
            feature_vector JSON {"NOT NULL" if feature_vector_not_null else ""},
            image_url VARCHAR(255)
        );
        CREATE TABLE group_rooms (
            id INTEGER PRIMARY KEY, room_code VARCHAR(10) NOT NULL,
            host_user_id INTEGER NOT NULL, mode_type VARCHAR(16) NOT NULL,
            status VARCHAR(16) NOT NULL, member_user_ids JSON NOT NULL,
            candidate_dish_ids JSON NOT NULL, winner_dish_id INTEGER,
            consensus_report JSON, created_at DATETIME NOT NULL
        );
        """
    )
    connection.commit()
    connection.close()


def test_migration_adds_nullable_columns_to_legacy_schema(tmp_path):
    db_path = tmp_path / "legacy.db"
    _legacy_db(db_path, feature_vector_not_null=False)
    first = migrate(db_path)
    second = migrate(db_path)
    assert "restaurants.campus" in first["added_columns"]
    assert "dishes_and_recipes.tagging_status" in first["added_columns"]
    assert first["idempotent"] is False
    assert second["idempotent"] is True


def test_migration_refuses_not_null_feature_vector(tmp_path):
    db_path = tmp_path / "legacy-notnull.db"
    _legacy_db(db_path, feature_vector_not_null=True)
    with pytest.raises(RuntimeError, match="feature_vector"):
        migrate(db_path)


def test_poi_import_and_reimport_are_idempotent(tmp_path):
    db_path = tmp_path / "import.db"
    migrate(db_path)
    input_path = tmp_path / "pois.jsonl"
    _write_jsonl(input_path, [_poi("A1"), _poi("A2"), _poi("A3")])
    engine, Session = make_session(db_path)
    db = Session()
    try:
        first = import_pois(db, "SIYUAN", input_path, "batch-1")
        second = import_pois(db, "SIYUAN", input_path, "batch-1")
        assert first["inserted"] == 3
        assert first["missing_fields"] == {"rating": 3, "cost": 3, "tag": 3}
        assert second["inserted"] == 0
        assert second["existing"] == 3
    finally:
        db.close()
        engine.dispose()


def test_invalid_poi_is_rejected_and_retryable(tmp_path):
    db_path = tmp_path / "import.db"
    migrate(db_path)
    input_path = tmp_path / "pois.jsonl"
    bad = _poi("B1", name="")
    _write_jsonl(input_path, [bad])
    reject_path = tmp_path / "rejects.jsonl"
    engine, Session = make_session(db_path)
    db = Session()
    try:
        result = import_pois(
            db, "SIYUAN", input_path, "batch-bad", reject_path=reject_path
        )
        assert result["rejected"] == 1
        assert result["inserted"] == 0
        assert reject_path.exists()
        retry_log = tmp_path / "retry.jsonl"
        fixed_reject = tmp_path / "fixed.jsonl"
        fixed_reject.write_text(
            json.dumps(
                {
                    "batch_id": "batch-bad",
                    "kind": "AMAP_POI",
                    "campus": "SIYUAN",
                    "reason": "missing_name",
                    "retryable": False,
                    "raw": _poi("B1", name="修正后的餐厅"),
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        retry = import_rejects(db, fixed_reject, "batch-retry", retry_log)
        assert retry["imported"] == 1
        assert retry["remaining"] == 0
    finally:
        db.close()
        engine.dispose()


def test_canteen_import_is_separated_and_idempotent(tmp_path):
    db_path = tmp_path / "import.db"
    migrate(db_path)
    input_path = tmp_path / "pois.jsonl"
    _write_jsonl(input_path, [_poi("C1")])
    engine, Session = make_session(db_path)
    db = Session()
    try:
        import_pois(db, "SIYUAN", input_path, "batch-canteen")
        first = import_canteens(db, "SIYUAN", "batch-canteen", limit=10)
        second = import_canteens(db, "SIYUAN", "batch-canteen", limit=10)
        assert first["inserted"] == 10
        assert second["existing"] == 10
        assert second["inserted"] == 0
        assert first["by_source_type"] == {"CANTEEN": 10}
        assert all(value >= 100 for value in first["anchor_min_distance_to_real_poi_m"].values())
    finally:
        db.close()
        engine.dispose()


def test_recipe_generation_unique_and_idempotent(tmp_path):
    rows = generate_recipes(50)
    assert len(rows) == 50
    assert len({row["name"] for row in rows}) == 50
    assert all(row["is_synthetic"] == 1 for row in rows)
    assert all(row["feature_vector"] is None for row in rows)
    assert all(row["tagging_status"] == "PENDING" for row in rows)

    db_path = tmp_path / "import.db"
    migrate(db_path)
    engine, Session = make_session(db_path)
    db = Session()
    try:
        first = import_recipes(db, "batch-recipe", count=50)
        second = import_recipes(db, "batch-recipe", count=50)
        assert first["inserted"] == 50
        assert first["null_feature_vector_inserted"] == 50
        assert second["existing"] == 50
        assert second["inserted"] == 0
    finally:
        db.close()
        engine.dispose()
