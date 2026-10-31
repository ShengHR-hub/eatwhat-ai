"""生成 S03/r01 clock_boundary.json：固定时钟下的边界表与时区/DST 对照。"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/EatWhat")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.algorithms import fridge_clock
from backend.models import FridgeInventory

OUT = ROOT / "docs" / "review" / "stages" / "S03" / "r01" / "data" / "clock_boundary.json"
NOW = datetime(2026, 10, 26, 12, 0, 0)
DAY = 86400


def row(expire_days=3, created_at=NOW):
    return FridgeInventory(
        user_id=1,
        ingredient_name="边界测试",
        category="新鲜果蔬",
        quantity_desc="适量",
        expire_days=expire_days,
        created_at=created_at,
    )


def snap(item, now=NOW):
    return {
        "expire_days": item.expire_days,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "remaining_days": fridge_clock.remaining_days(item, now),
        "is_expired": fridge_clock.is_expired(item, now),
        "is_expiring_soon": fridge_clock.is_expiring_soon(item, now),
    }


cases = []
for label, expire_days, elapsed in [
    ("入库", 3, 0),
    ("剩余 2.4 天", 3, int(0.6 * DAY)),
    ("剩余恰好 48h", 3, DAY),
    ("剩余 1.5 天", 3, int(1.5 * DAY)),
    ("剩余 0.6 天", 3, int(2.4 * DAY)),
    ("剩余 0.5 天（F09 原缺陷点）", 3, int(2.5 * DAY)),
    ("到期前 1 秒", 3, 3 * DAY - 1),
    ("恰好到期", 3, 3 * DAY),
    ("到期后 1 秒", 3, 3 * DAY + 1),
    ("保质期 1 天", 1, 0),
    ("保质期 0 天", 0, 0),
    ("缺省 expire_days", None, 0),
    ("负保质期按 0", -2, 0),
]:
    item = row(expire_days, NOW - timedelta(seconds=elapsed))
    cases.append(
        {
            "label": label,
            "elapsed_seconds": elapsed,
            "actual_remaining_seconds": 3 * DAY - elapsed if expire_days == 3 else None,
            **snap(item),
        }
    )

created = datetime(2026, 10, 30, 5, 30, 0)  # naive UTC, expiry 2026-11-01 05:30Z
tz_item = row(2, created)
timezone_cases = [
    {
        "label": "美国回拨日 01:30 -04:00（=到期时刻）",
        "now": "2026-11-01T01:30:00-04:00",
        **snap(tz_item, datetime(2026, 11, 1, 1, 30, tzinfo=timezone(timedelta(hours=-4)))),
    },
    {
        "label": "美国回拨日 01:30 -05:00（UTC 已晚 1 小时）",
        "now": "2026-11-01T01:30:00-05:00",
        **snap(tz_item, datetime(2026, 11, 1, 1, 30, tzinfo=timezone(timedelta(hours=-5)))),
    },
    {
        "label": "Asia/Shanghai 13:30 +08:00（=到期时刻）",
        "now": "2026-11-01T13:30:00+08:00",
        **snap(tz_item, datetime(2026, 11, 1, 13, 30, tzinfo=timezone(timedelta(hours=8)))),
    },
    {
        "label": "到期前 1 秒（naive UTC）",
        "now": "2026-11-01T05:29:59",
        **snap(tz_item, datetime(2026, 11, 1, 5, 29, 59)),
    },
    {
        "label": "美国春进日同一 UTC 时刻 -05:00",
        "now": "2026-03-08T01:30:00-05:00",
        **snap(tz_item, datetime(2026, 3, 8, 1, 30, tzinfo=timezone(timedelta(hours=-5)))),
    },
    {
        "label": "美国春进日同一 UTC 时刻 +08:00",
        "now": "2026-03-08T14:30:00+08:00",
        **snap(tz_item, datetime(2026, 3, 8, 14, 30, tzinfo=timezone(timedelta(hours=8)))),
    },
]

payload = {
    "step": "S03",
    "round": "r01",
    "fixed_now_utc": NOW.isoformat(),
    "rule": (
        "expires_at = created_at + expire_days*24h (UTC absolute); "
        "expired iff now >= expires_at; remaining_days = ceil(seconds_left/86400) "
        "for unexpired (min 1); is_expiring_soon iff 0 < seconds_left <= 48h."
    ),
    "boundary_cases": cases,
    "timezone_dst_cases": timezone_cases,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": len(cases), "timezone_cases": len(timezone_cases)}, ensure_ascii=False))
