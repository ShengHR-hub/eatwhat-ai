"""BRIDGE-10：双校区读取边界与接线验证（API + SQL）。"""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BRIDGE = "http://127.0.0.1:8010/api/v1"
RUNTIME = "http://127.0.0.1:8000/api/v1"
BRIDGE_DB = ROOT / "backend" / "eatwhat_g2_bridge_iso.db"
RUNTIME_DB = ROOT / "backend" / "eatwhat_g1_s07_iso.db"
OUT = Path(__file__).resolve().parent / "bridge_api.json"


def call(base: str, path: str, method: str = "GET", user_id: int = 1, body: dict | None = None):
    request = urllib.request.Request(
        f"{base}{path}",
        method=method,
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-User-Id": str(user_id)},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return error.code, payload


def campuses_of(ids: list[int]) -> dict:
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    connection = sqlite3.connect(f"file:{BRIDGE_DB.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT id, campus, source_dataset FROM restaurants WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        return {str(row[0]): {"campus": row[1], "dataset": row[2]} for row in rows}
    finally:
        connection.close()


def campuses_by_name(names: list[str]) -> dict:
    if not names:
        return {}
    placeholders = ",".join("?" for _ in names)
    connection = sqlite3.connect(f"file:{BRIDGE_DB.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT name, campus, source_dataset FROM restaurants WHERE name IN ({placeholders})",
            names,
        ).fetchall()
        return {row[0]: {"campus": row[1], "dataset": row[2]} for row in rows}
    finally:
        connection.close()


def recommend(campus, mode: str = "OUT_DINING", limit: int = 10):
    body = {"mode_type": mode, "limit": limit, "bubbles": []}
    if campus is not None:
        body["campus"] = campus
    return call(BRIDGE, "/recommend/single", "POST", body=body)


def items(result) -> list:
    payload = result[1] if isinstance(result[1], dict) else {}
    return payload.get("recommendations", [])


def restaurant_ids(rows) -> list[int]:
    return sorted({int(row["restaurant_id"]) for row in rows if row.get("restaurant_id") is not None})


def main() -> None:
    siyuan = recommend("SIYUAN")
    jianda = recommend("JIANDA_YANTA")
    missing = recommend(None)
    home_siyuan = recommend("SIYUAN", "HOME_COOKING")
    home_jianda = recommend("JIANDA_YANTA", "HOME_COOKING")

    siyuan_map = campuses_of(restaurant_ids(items(siyuan)))
    group_siyuan_map = {}
    group_jianda_map = {}
    jianda_map = campuses_of(restaurant_ids(items(jianda)))

    group_siyuan = call(
        BRIDGE, "/rooms/create", "POST", body={"mode_type": "OUT_DINING", "campus": "SIYUAN"}
    )
    group_jianda = call(
        BRIDGE,
        "/rooms/create",
        "POST",
        user_id=3,
        body={"mode_type": "OUT_DINING", "campus": "JIANDA_YANTA"},
    )
    cross_join = None
    if group_siyuan[0] == 200:
        cross_join = call(
            BRIDGE,
            f"/rooms/{group_siyuan[1]['room_code']}/join",
            "POST",
            user_id=2,
            body={"campus": "JIANDA_YANTA"},
        )
    home_group_siyuan = call(
        BRIDGE, "/rooms/create", "POST", body={"mode_type": "HOME_COOKING", "campus": "SIYUAN"}
    )
    home_group_jianda = call(
        BRIDGE,
        "/rooms/create",
        "POST",
        body={"mode_type": "HOME_COOKING", "campus": "JIANDA_YANTA"},
    )
    if group_siyuan[0] == 200:
        group_siyuan_map = campuses_by_name(
            sorted({row["restaurant_name"] for row in group_siyuan[1].get("candidates", []) if row.get("restaurant_name")})
        )
    if group_jianda[0] == 200:
        group_jianda_map = campuses_by_name(
            sorted({row["restaurant_name"] for row in group_jianda[1].get("candidates", []) if row.get("restaurant_name")})
        )
    admin_stats = call(BRIDGE, "/admin/stats/overview")

    connection = sqlite3.connect(f"file:{BRIDGE_DB.as_posix()}?mode=ro", uri=True)
    try:
        counts = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT COALESCE(source_dataset,'NULL'), COUNT(*) FROM restaurants GROUP BY source_dataset"
            )
        }
        campus_counts = {
            "|".join(map(str, row[:3])): row[3]
            for row in connection.execute(
                "SELECT campus, source_type, source_dataset, COUNT(*) FROM restaurants "
                "WHERE campus IS NOT NULL GROUP BY campus, source_type, source_dataset"
            )
        }
        null_campus = connection.execute(
            "SELECT COUNT(*) FROM restaurants WHERE campus IS NULL"
        ).fetchone()[0]
    finally:
        connection.close()

    runtime_connection = sqlite3.connect(f"file:{RUNTIME_DB.as_posix()}?mode=ro", uri=True)
    try:
        runtime_datasets = {
            row[0]: row[1]
            for row in runtime_connection.execute(
                "SELECT COALESCE(source_dataset,'NULL'), COUNT(*) FROM restaurants GROUP BY source_dataset"
            )
        }
        runtime_users = runtime_connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        runtime_logs = runtime_connection.execute("SELECT COUNT(*) FROM eating_logs").fetchone()[0]
        runtime_fridge = runtime_connection.execute("SELECT COUNT(*) FROM fridge_inventory").fetchone()[0]
    finally:
        runtime_connection.close()

    result = {
        "bridge_api": BRIDGE,
        "runtime_api": RUNTIME,
        "bridge_db": str(BRIDGE_DB),
        "runtime_db": str(RUNTIME_DB),
        "recommend_out": {
            "siyuan_status": siyuan[0],
            "siyuan_count": len(items(siyuan)),
            "siyuan_restaurant_campuses": siyuan_map,
            "siyuan_all_within_campus": all(v["campus"] == "SIYUAN" for v in siyuan_map.values()),
            "jianda_status": jianda[0],
            "jianda_count": len(items(jianda)),
            "jianda_restaurant_campuses": jianda_map,
            "jianda_all_within_campus": all(v["campus"] == "JIANDA_YANTA" for v in jianda_map.values()),
            "missing_campus_status": missing[0],
            "missing_campus_detail": missing[1].get("detail") if isinstance(missing[1], dict) else missing[1],
            "no_null_campus_leak": all(v["campus"] is not None for v in siyuan_map.values())
            and all(v["campus"] is not None for v in jianda_map.values()),
        },
        "home_shared": {
            "siyuan_status": home_siyuan[0],
            "jianda_status": home_jianda[0],
            "siyuan_ids": [row["dish_id"] for row in items(home_siyuan)],
            "jianda_ids": [row["dish_id"] for row in items(home_jianda)],
            "same_ids": [row["dish_id"] for row in items(home_siyuan)]
            == [row["dish_id"] for row in items(home_jianda)],
        },
        "group_out": {
            "siyuan_create_status": group_siyuan[0],
            "siyuan_candidate_count": len(group_siyuan[1].get("candidates", []))
            if group_siyuan[0] == 200
            else None,
            "jianda_create_status": group_jianda[0],
            "jianda_candidate_count": len(group_jianda[1].get("candidates", []))
            if group_jianda[0] == 200
            else None,
            "cross_campus_join_status": cross_join[0] if cross_join else None,
            "cross_campus_detail": cross_join[1].get("detail")
            if cross_join and isinstance(cross_join[1], dict)
            else None,
            "siyuan_candidate_restaurant_campuses": group_siyuan_map,
            "jianda_candidate_restaurant_campuses": group_jianda_map,
            "siyuan_candidates_all_in_campus": bool(group_siyuan_map)
            and all(value["campus"] == "SIYUAN" for value in group_siyuan_map.values()),
            "jianda_candidates_all_in_campus": bool(group_jianda_map)
            and all(value["campus"] == "JIANDA_YANTA" for value in group_jianda_map.values()),
        },
        "group_home_shared": {
            "siyuan_status": home_group_siyuan[0],
            "jianda_status": home_group_jianda[0],
            "siyuan_ids": [row["dish_id"] for row in home_group_siyuan[1].get("candidates", [])]
            if home_group_siyuan[0] == 200
            else [],
            "jianda_ids": [row["dish_id"] for row in home_group_jianda[1].get("candidates", [])]
            if home_group_jianda[0] == 200
            else [],
            "same_ids": [row["dish_id"] for row in home_group_siyuan[1].get("candidates", [])]
            == [row["dish_id"] for row in home_group_jianda[1].get("candidates", [])]
            if home_group_siyuan[0] == 200 and home_group_jianda[0] == 200
            else False,
        },
        "admin_stats": {"status": admin_stats[0], "note": "统计接口属 S15，本组不实现"},
        "bridge_counts": {
            "by_dataset": counts,
            "campus_type_dataset": campus_counts,
            "null_campus_restaurants": null_campus,
        },
        "runtime_counts": {
            "by_dataset": runtime_datasets,
            "users": runtime_users,
            "eating_logs": runtime_logs,
            "fridge_inventory": runtime_fridge,
            "contains_s10_datasets": any(
                str(key).startswith("amap_")
                or key in {"synthetic_canteen_v1", "synthetic_recipe_v1"}
                for key in runtime_datasets
            ),
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("recommend_out", "home_shared", "group_out", "admin_stats")}, ensure_ascii=False, indent=2)[:2500])


if __name__ == "__main__":
    main()
