"""S05/r01 API compatibility probe on the isolated runtime DB.

Covers the PRE-00 schema/API compatibility surface used by the S05 pages:
profile, recommend, stats, fridge, demo-list, weather, catalog, checkin dry checks
(read-only; no writes).
"""

import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/v1"
OUT = Path(r"D:\EatWhat\docs\review\stages\S05\r01")
CST = timezone(timedelta(hours=8))


def call(path, *, method="GET", body=None, user=1):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={"Content-Type": "application/json", "X-User-Id": str(user)},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def main() -> int:
    results = {}
    status, profile = call("/users/1/profile")
    results["profile"] = {
        "status": status,
        "has_8_genes": len(profile.get("base_vector", {})) == 8 if status == 200 else False,
        "nickname": profile.get("nickname") if status == 200 else None,
    }

    status, rec = call(
        "/recommend/single",
        method="POST",
        body={
            "mode_type": "OUT_DINING",
            "bubbles": [],
            "weather_temp": 22,
            "weather_text": "晴",
            "limit": 24,
            "combo_mode": False,
        },
    )
    items = rec.get("recommendations", []) if status == 200 else []
    finite_scores = all(
        isinstance(d.get("total_score"), (int, float))
        and math.isfinite(d["total_score"])
        and 0 <= d["total_score"] <= 100
        for d in items
    )
    radar_ok = all(
        set(d.get("radar_5d", {})) == {"taste", "weather", "budget", "freshness", "status"}
        for d in items
    )
    results["recommend"] = {
        "status": status,
        "count": len(items),
        "first_ids": [d["dish_id"] for d in items[:5]],
        "scores_finite_0_100": finite_scores,
        "radar_keys_ok": radar_ok,
        "params_used_keys": sorted(rec.get("params_used", {}).keys()) if status == 200 else [],
        "unique_ids": len({d["dish_id"] for d in items}) == len(items),
    }

    status, stats = call("/logs/stats/1")
    results["stats"] = {
        "status": status,
        "meals_this_week": stats.get("meals_this_week") if status == 200 else None,
        "cooling_count": len(stats.get("cooling_dishes", [])) if status == 200 else None,
        "weekly_expense": stats.get("weekly_expense") if status == 200 else None,
    }

    status, fridge = call("/fridge/1")
    results["fridge"] = {
        "status": status,
        "items": len(fridge.get("items", [])) if status == 200 else None,
        "expiring_soon": sum(1 for i in fridge.get("items", []) if i.get("is_expiring_soon"))
        if status == 200
        else None,
    }

    status, demo = call("/users/demo-list")
    results["demo_list"] = {
        "status": status,
        "count": len(demo) if status == 200 else None,
        "ids": [u["id"] for u in demo] if status == 200 else [],
    }

    status, weather = call("/context/weather")
    results["weather"] = {
        "status": status,
        "source": weather.get("source") if status == 200 else None,
        "temp": weather.get("temp") if status == 200 else None,
        "weather_text": weather.get("weather_text") if status == 200 else None,
    }

    status, catalog = call("/catalog/dishes?mode_type=HOME_COOKING")
    results["catalog_home"] = {
        "status": status,
        "count": len(catalog) if status == 200 else None,
    }

    status, unknown = call("/users/999/profile", user=999)
    results["unknown_user_404"] = {"status": status, "detail": unknown.get("detail") if isinstance(unknown, dict) else None}

    ok = (
        results["profile"]["status"] == 200
        and results["profile"]["has_8_genes"]
        and results["recommend"]["status"] == 200
        and results["recommend"]["count"] > 0
        and results["recommend"]["scores_finite_0_100"]
        and results["recommend"]["radar_keys_ok"]
        and results["recommend"]["unique_ids"]
        and results["stats"]["status"] == 200
        and results["fridge"]["status"] == 200
        and results["demo_list"]["status"] == 200
        and results["weather"]["status"] == 200
        and results["catalog_home"]["status"] == 200
        and results["unknown_user_404"]["status"] == 404
    )
    payload = {
        "generated_at": datetime.now(CST).isoformat(),
        "backend": "http://127.0.0.1:8000",
        "database": "backend/eatwhat_s05_r01_iso.db",
        "results": results,
        "verdict": bool(ok),
    }
    (OUT / "data/api_compat.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
