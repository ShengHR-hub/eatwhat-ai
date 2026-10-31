"""S01 隔离库真实 HTTP/WS 反例探针。

只连接 127.0.0.1:8000（DATABASE_URL 指向 backend/eatwhat_s01_r01_iso.db）。
不写演示库 / S10 库。
"""

import asyncio
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

import websockets

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000"
DB = "backend/eatwhat_s01_r01_iso.db"
OUT = "docs/review/stages/S01/r01/data/live_identity_probe.json"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(method, path, body=None, headers=None):
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with opener.open(req, timeout=15) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            payload = json.loads(text)
        except Exception:
            payload = text
        return exc.code, payload


def db_rows():
    con = sqlite3.connect(DB)
    try:
        return {
            "logs": {
                str(uid): con.execute(
                    "select count(*) from eating_logs where user_id=?", (uid,)
                ).fetchone()[0]
                for uid in (1, 2)
            },
            "rooms": con.execute("select count(*) from group_rooms").fetchone()[0],
            "user2_prefs": con.execute(
                "select default_budget,veto_tags,blacklist_dish_ids "
                "from user_preferences where user_id=2"
            ).fetchone(),
            "user2_fridge": con.execute(
                "select count(*) from fridge_inventory where user_id=2"
            ).fetchone()[0],
        }
    finally:
        con.close()


async def ws_connect(path, headers=None):
    try:
        async with websockets.connect(
            WS + path, additional_headers=headers, proxy=None, open_timeout=8
        ) as ws:
            first = await asyncio.wait_for(ws.recv(), timeout=8)
            return {"accepted": True, "first": json.loads(first)}
    except Exception as exc:
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return {"accepted": False, "error": type(exc).__name__, "status": status, "detail": str(exc)}


async def main():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": DB,
        "before": db_rows(),
        "http": [],
        "ws": [],
    }

    cases = [
        ("header1_reads_user2_profile", "GET", "/api/v1/users/2/profile", {"X-User-Id": "1"}),
        ("header1_reads_user2_stats", "GET", "/api/v1/logs/stats/2", {"X-User-Id": "1"}),
        ("header1_reads_user2_fridge", "GET", "/api/v1/fridge/2", {"X-User-Id": "1"}),
        ("missing_header", "GET", "/api/v1/fridge/1", {}),
        ("empty_header", "GET", "/api/v1/fridge/1", {"X-User-Id": ""}),
        ("non_integer_header", "GET", "/api/v1/fridge/1", {"X-User-Id": "abc"}),
        ("zero_header", "GET", "/api/v1/fridge/1", {"X-User-Id": "0"}),
        ("negative_header", "GET", "/api/v1/fridge/1", {"X-User-Id": "-1"}),
        ("huge_header", "GET", "/api/v1/fridge/1", {"X-User-Id": str(2**70)}),
        ("unknown_header", "GET", "/api/v1/fridge/1", {"X-User-Id": "999"}),
        (
            "recommend_body_conflict",
            "POST",
            "/api/v1/recommend/single",
            {"X-User-Id": "1"},
            {"user_id": 2, "mode_type": "OUT_DINING", "limit": 5},
        ),
        (
            "checkin_body_conflict",
            "POST",
            "/api/v1/logs/checkin",
            {"X-User-Id": "1"},
            {"user_id": 2, "dish_id": 61, "mode_type": "HOME_COOKING"},
        ),
        (
            "shopping_body_conflict",
            "POST",
            "/api/v1/fridge/shopping-list",
            {"X-User-Id": "1"},
            {"user_id": 2, "dish_ids": [61]},
        ),
        (
            "room_create_body_host_conflict",
            "POST",
            "/api/v1/rooms/create",
            {"X-User-Id": "1"},
            {"host_user_id": 2, "mode_type": "OUT_DINING"},
        ),
    ]

    room_code = None
    for case in cases:
        name, method, path, headers = case[:4]
        body = case[4] if len(case) > 4 else None
        status, payload = request(method, path, body=body, headers=headers)
        item = {"name": name, "method": method, "path": path, "status": status}
        if isinstance(payload, dict):
            item["detail"] = payload.get("detail")
            item["user_id"] = payload.get("user_id")
            item["host_user_id"] = payload.get("host_user_id")
            item["members"] = [m.get("user_id") for m in payload.get("members", [])]
            item["recommendations"] = [
                row.get("name") for row in payload.get("recommendations", [])
            ][:5]
            item["owned"] = [
                row.get("ingredient") for row in payload.get("owned_ingredients", [])
            ]
        if name == "room_create_body_host_conflict":
            room_code = payload.get("room_code")
            item["room_code"] = room_code
        report["http"].append(item)

    # 房间成员边界（复用上面 header1 建出的房间）
    if room_code:
        status, payload = request(
            "GET", f"/api/v1/rooms/{room_code}", headers={"X-User-Id": "2"}
        )
        report["http"].append(
            {
                "name": "non_member_get_room",
                "status": status,
                "detail": payload.get("detail"),
                "room_code": room_code,
            }
        )
        status, payload = request(
            "POST", f"/api/v1/rooms/{room_code}/join", body={}, headers={"X-User-Id": "2"}
        )
        report["http"].append(
            {
                "name": "join_as_user2",
                "status": status,
                "members": [m["user_id"] for m in payload.get("members", [])],
            }
        )
        status, payload = request(
            "POST", f"/api/v1/rooms/{room_code}/join", body={}, headers={"X-User-Id": "2"}
        )
        report["http"].append(
            {
                "name": "repeat_join_user2",
                "status": status,
                "members": [m["user_id"] for m in payload.get("members", [])],
            }
        )
        status, payload = request(
            "POST",
            f"/api/v1/rooms/{room_code}/join",
            body={"user_id": 1},
            headers={"X-User-Id": "2"},
        )
        report["http"].append(
            {
                "name": "join_body_conflict",
                "status": status,
                "members": [m["user_id"] for m in payload.get("members", [])],
            }
        )
        status, payload = request(
            "GET", f"/api/v1/rooms/{room_code}", headers={"X-User-Id": "2"}
        )
        report["http"].append(
            {
                "name": "member_get_room",
                "status": status,
                "room_code": payload.get("room_code") if isinstance(payload, dict) else None,
            }
        )

        # WS 边界
        report["ws"].append(
            {
                "name": "ws_non_member",
                **(
                    await ws_connect(f"/ws/room/{room_code}/999")
                ),
            }
        )
        report["ws"].append(
            {
                "name": "ws_path_header_conflict",
                **(
                    await ws_connect(
                        f"/ws/room/{room_code}/2", headers={"X-User-Id": "1"}
                    )
                ),
            }
        )
        accepted = await ws_connect(
            f"/ws/room/{room_code}/2", headers={"X-User-Id": "2"}
        )
        report["ws"].append({"name": "ws_member_accept", **accepted})
        if accepted.get("accepted"):
            # 非房主开局必须被拒
            try:
                async with websockets.connect(
                    WS + f"/ws/room/{room_code}/2",
                    additional_headers={"X-User-Id": "2"},
                    proxy=None,
                    open_timeout=8,
                ) as ws:
                    while True:
                        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
                        if message.get("type") == "ROOM_STATE":
                            break
                    await ws.send(json.dumps({"type": "START_SWIPING"}))
                    while True:
                        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
                        if message.get("type") == "ERROR":
                            report["ws"].append(
                                {
                                    "name": "ws_non_host_start",
                                    "accepted": True,
                                    "error": message.get("detail"),
                                }
                            )
                            break
            except Exception as exc:
                report["ws"].append(
                    {"name": "ws_non_host_start", "accepted": False, "error": str(exc)}
                )

    # 公开入口
    status_a, demo_a = request("GET", "/api/v1/users/demo-list")
    status_b, demo_b = request(
        "GET", "/api/v1/users/demo-list", headers={"X-User-Id": "3"}
    )
    report["public"] = {
        "demo_list_status": [status_a, status_b],
        "identical": demo_a == demo_b,
        "user_ids": [u["id"] for u in (demo_a or [])],
    }

    report["after"] = db_rows()
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2)[:12000])


if __name__ == "__main__":
    asyncio.run(main())
