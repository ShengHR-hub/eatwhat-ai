"""固定时钟冰箱时效边界探针（只计算，不读写业务数据库）。"""

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.algorithms.fridge_clock import remaining_days, is_expired  # noqa: E402


class Row:
    def __init__(self, expire_days, created_at):
        self.expire_days = expire_days
        self.created_at = created_at


NOW = datetime(2026, 10, 25, 12, 0, 0)

if __name__ == "__main__":
    print("now:", NOW.isoformat())
    for elapsed_days in (0, 1.4, 1.5, 2.0, 2.4, 2.5, 2.6, 3.0, 3.1):
        row = Row(3, NOW - timedelta(days=elapsed_days))
        print(
            {
                "expire_days": 3,
                "elapsed_days": elapsed_days,
                "remaining_days": remaining_days(row, NOW),
                "is_expired": is_expired(row, NOW),
            }
        )
    print(
        "note: remaining_days uses int(round(total-elapsed)); "
        "2.5 days elapsed -> 0.5 remaining -> round=0 -> expired half a day early"
    )
