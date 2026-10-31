"""统计一次推荐发出的 SQL 条数（审查 R01 的验收工具）。

用法（仓库根目录）：
    python -m backend.scripts.measure_recommend_sql            # 默认用户 2 / 下厨
    python -m backend.scripts.measure_recommend_sql --user 1 --mode OUT_DINING

为什么要它：R01 是「循环里逐条查库存」的 N+1，光看代码容易漏，必须实测
"一次推荐到底发了几条 SELECT"。修复前实测 45 条（其中 40 条查 fridge_inventory），
修复后压到个位数，同一次调用的推荐结果必须保持一致。
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, List

from sqlalchemy import event

from ..algorithms import single_recommender
from ..algorithms.single_recommender import recommend_single
from ..database import SessionLocal, engine


def measure(
    user_id: int, mode_type: str, limit: int = 10, legacy: bool = False
) -> Dict[str, object]:
    """跑一次推荐并统计 SQL。

    `legacy=True` 时把批量化入口换回「每道菜查一次库存」的旧实现，
    这样修复前后的数字来自同一套测量代码，避免拿两次不同工具的结果对比。
    """
    statements: List[str] = []
    original = single_recommender._fridge_status_from_index
    session = SessionLocal()
    if legacy:
        # 复刻旧实现：每道菜单独用主 session 查一次库存（不能走 _fridge_status_score，
        # 它会再次调用本函数造成递归）
        def _per_dish(index, dish):
            index_fresh = single_recommender._fridge_index(session, user_id)
            return original(index_fresh, dish)

        single_recommender._fridge_status_from_index = _per_dish

    def _before(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        result = recommend_single(
            session, user_id=user_id, mode_type=mode_type, limit=limit
        )
    finally:
        session.close()
        event.remove(engine, "before_cursor_execute", _before)
        single_recommender._fridge_status_from_index = original

    fridge_hits = sum("fridge_inventory" in s.lower() for s in statements)
    return {
        "user_id": user_id,
        "mode_type": mode_type,
        "limit": limit,
        "total_statements": len(statements),
        "fridge_inventory_statements": fridge_hits,
        "returned": len(result.get("recommendations", [])),
        "top3": [
            (item["dish_id"], item["name"], item["total_score"])
            for item in result.get("recommendations", [])[:3]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", type=int, default=2)
    parser.add_argument(
        "--mode", choices=["OUT_DINING", "HOME_COOKING"], default="HOME_COOKING"
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--legacy", action="store_true", help="用旧的逐菜查询实现对照")
    args = parser.parse_args()

    print(
        json.dumps(
            measure(args.user, args.mode, args.limit, legacy=args.legacy),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
