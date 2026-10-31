"""重启测试第一步：建房、开局、投一票，然后留给服务端被强制停止。"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import websockets

BASE = "http://127.0.0.1:8025"
WS_BASE = "ws://127.0.0.1:8025"
OUT = Path(__file__).resolve().parent / "restart_room.json"
H1 = {"X-User-Id": "1"}

sys.stdout.reconfigure(encoding="utf-8")


async def recv_until(ws, want, timeout=15):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if message.get("type") == want:
            return message


async def main() -> None:
    client = httpx.Client(trust_env=False, timeout=20)
    created = client.post(
        f"{BASE}/api/v1/rooms/create",
        json={"mode_type": "OUT_DINING", "campus": "SIYUAN", "budget": 40},
        headers=H1,
    )
    assert created.status_code == 200, created.text
    room = created.json()
    code = room["room_code"]

    async with websockets.connect(f"{WS_BASE}/ws/room/{code}/1") as host:
        await recv_until(host, "ROOM_STATE")
        await host.send(json.dumps({"type": "START_SWIPING"}))
        started = await recv_until(host, "START_SWIPING")
        dish_id = started["candidates"][0]["dish_id"]
        await host.send(
            json.dumps({"type": "SUBMIT_VOTE", "dish_id": dish_id, "vote_type": "LIKE"})
        )
        await recv_until(host, "PROGRESS_UPDATE")

    payload = {
        "prepared_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "room_code": code,
        "candidate_count": len(started["candidates"]),
        "voted_dish_id": dish_id,
        "deadline_at_utc": started["deadline_at"],
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
