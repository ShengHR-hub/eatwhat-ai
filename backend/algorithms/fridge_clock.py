"""冰箱库存时效的单一计算口径（S03 / F09）。

用户 2026-10-26 裁决（1A），已同步 MASTER_SPEC：

* `expire_days` 存的是**入库时的保质期（天）**，到期时刻
  `expires_at = created_at + expire_days × 24h`；统一按 UTC 绝对时间计算，
  时区 / DST 不改变结果。`now >= expires_at` 即过期。
* 过期返回 0 天；未过期时 `remaining_days = ceil(剩余秒数 / 86400)`，
  最小显示 1 天（实际剩余 2.4 天显示 3 天，剩余 0.5 天显示 1 天）。
* 临期 = 未过期且实际剩余 ≤ 48h。因此 `remaining_days <= 2` 与
  「实际剩余 ≤48h」严格等价，`is_expiring_soon` 只对该区间为真。

展示、下厨推荐、采购清单、组合采购都必须经这里计算，禁止各自再写一份。
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..models import FridgeInventory

EXPIRING_SOON_DAYS = 2
"""剩余 ≤2 天算临期：前端高亮，推荐里双倍提权（v2.3.1 第三章）。"""

SECONDS_PER_DAY = 86400.0


def now_utc() -> datetime:
    """当前 UTC 时间（naive，与 models.utcnow 的存储口径一致）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize(value: datetime) -> datetime:
    """aware datetime 归一到 UTC 后去掉 tzinfo；naive 视为已经是 UTC。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _shelf_days(row: FridgeInventory) -> int:
    raw = 3 if row.expire_days is None else int(row.expire_days)
    return max(0, raw)


def expires_at(
    row: FridgeInventory, now: Optional[datetime] = None
) -> datetime:
    """到期时刻。历史行缺 created_at 时按「刚入库」从 now 起算。"""
    current = _normalize(now) if now is not None else now_utc()
    created = current if row.created_at is None else _normalize(row.created_at)
    return created + timedelta(days=_shelf_days(row))


def _remaining_seconds(
    row: FridgeInventory, now: Optional[datetime] = None
) -> float:
    current = _normalize(now) if now is not None else now_utc()
    return (expires_at(row, current) - current).total_seconds()


def is_expired(row: FridgeInventory, now: Optional[datetime] = None) -> bool:
    """now >= 到期时刻即过期（恰好到期也算过期）。"""
    return _remaining_seconds(row, now) <= 0


def remaining_days(row: FridgeInventory, now: Optional[datetime] = None) -> int:
    """剩余整数天：过期返回 0；未过期向上取整，最小 1。"""
    seconds = _remaining_seconds(row, now)
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / SECONDS_PER_DAY))


def is_expiring_soon(
    row: FridgeInventory, now: Optional[datetime] = None
) -> bool:
    """临期 = 未过期且实际剩余 ≤48h；过期项不算临期。"""
    seconds = _remaining_seconds(row, now)
    return 0 < seconds <= EXPIRING_SOON_DAYS * SECONDS_PER_DAY
