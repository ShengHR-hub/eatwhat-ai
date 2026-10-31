"""按地址做高德地名搜索，Key 只从 AMAP_API_KEY 读取，输出不含 Key。"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", required=True)
    parser.add_argument("--city", default="西安")
    parser.add_argument("--out", default="amap_campus_geocode.json")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
    key = os.getenv("AMAP_API_KEY", "").strip()
    result = {
        "checked_at": checked_at,
        "address": args.address,
        "city": args.city,
        "key_present": bool(key),
        "key": "<redacted>",
        "endpoint": "https://restapi.amap.com/v3/geocode/geo",
        "status": "BLOCKED",
    }
    if not key:
        result["reason"] = "AMAP_API_KEY missing in process environment"
    else:
        s = requests.Session()
        s.trust_env = True
        r = None
        body = None
        last_error = None
        for attempt in range(3):
            try:
                r = s.get(
                    "https://restapi.amap.com/v3/geocode/geo",
                    params={"key": key, "address": args.address, "city": args.city},
                    timeout=25,
                )
                body = r.json()
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        if body is None:
            # 绝不输出异常原文中的完整 URL（可能含 key）
            reason = str(last_error or "unknown").replace(key, "<redacted>")
            result.update({
                "status": "ERROR",
                "error_type": type(last_error).__name__ if last_error else "Unknown",
                "reason": reason[:300],
            })
            out = DATA / args.out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1
        geos = body.get("geocodes") or []
        result.update(
            {
                "http_status": r.status_code,
                "api": {k: body.get(k) for k in ("status", "info", "infocode", "count")},
                "request": {"address": args.address, "city": args.city, "key": "<redacted>"},
                "results": [
                    {k: g.get(k) for k in ("formatted_address", "province", "city", "district", "location", "level", "adcode")}
                    for g in geos[:5]
                ],
            }
        )
        if geos and geos[0].get("location"):
            result["status"] = "OK"
            result["center_gcj02"] = geos[0]["location"]
            result["center_source"] = "AMap geocode/geo 实际返回"
            fmt = str(geos[0].get("formatted_address") or "")
            if "草堂" in fmt or "草堂" in args.address:
                result["status"] = "NEED_USER_DECISION"
                result["reason"] = "高德返回草堂校区，按要求停止并询问用户"
            elif "雁塔" not in fmt:
                result["status"] = "NEED_USER_DECISION"
                result["reason"] = "高德返回地址未明确包含雁塔，停止并询问用户"
        else:
            result["reason"] = "geocode returned no location"
    out = DATA / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"OK", "NEED_USER_DECISION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
