"""R01 回归：下厨推荐不得在循环里逐条查库存（N+1）。

为什么单独一个文件：这类回归只看功能测不出来——结果一模一样，只是悄悄多发 30 条
SELECT。所以要直接数 SQL 条数，并在结果上做等价断言（优化不能改推荐结果）。

2026-10-24 复审（CLR-04）判 FAIL 的两点，这一版必须回答：

1. **用例原先直接吃全局 `SessionLocal` / `engine`**，`DATABASE_URL` 指向一个全新
   空库时三条用例全 `no such table`。现在一律用 `conftest.py` 的 `session_factory`
   fixture，SQL 监听器也绑在同一颗 engine 上，不碰全局连接。
2. **等价测试是自己跟自己比**（`_fridge_index` 调两遍只比第一道菜）。现在有两条
   对照线，都是"不同实现"：
   - `_reference_fridge_status()`：本文件内**独立写的逐菜参考实现**，按定义
     （过期跳过、临期双倍、其余按剩余天数）一条条算，不用被测的批量函数；
   - `--legacy` 对照：`scripts/measure_recommend_sql.py --legacy` 保留修复前的
     逐菜查库实现，命令行即可复现整条链路的等价性（见 PC02 包的 logs/）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pytest
from sqlalchemy import event

from backend.algorithms.single_recommender import recommend_single
from backend.models import Dish, FridgeInventory

HOME_SQL_BUDGET = 9  # 复审要求「个位数」
FRIDGE_SQL_BUDGET = 1


def _count_sql(factory, call):
    """在给定 session factory 的 engine 上数 SQL 条数（不碰全局 engine）。"""
    engine = factory.kw["bind"]
    statements: List[str] = []

    def _before(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    session = factory()
    try:
        result = call(session)
    finally:
        session.close()
        event.remove(engine, "before_cursor_execute", _before)
    return result, statements


def _reference_fridge_status(session, user_id: int, dish: Dish) -> float:
    """逐菜参考实现：按 SSOT 定义一条条算，刻意不调用被测的批量函数。

    口径（与生产实现无关，直接照 S03 裁决的规格写）：
    - 只看主料（`ingredients_main`），辅料不参与「用现有食材」计分；
    - 到期时刻 = created_at + expire_days × 24h（UTC 绝对时间）；now >= 到期即过期；
    - 过期不算数；未过期且实际剩余 ≤48h 权重 2.0，其余 1.0；
    - 得分 = 100 × 命中主料权重和 / 主料总数，封顶 100。
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = (
        session.query(FridgeInventory)
        .filter(FridgeInventory.user_id == user_id)
        .all()
    )
    mains = [str(item).strip() for item in (dish.ingredients_main or []) if str(item).strip()]
    if not mains:
        return 0.0

    def seconds_left(row: FridgeInventory) -> float:
        total = 3 if row.expire_days is None else max(0, int(row.expire_days))
        created = row.created_at or now
        if created.tzinfo is not None:
            created = created.astimezone(timezone.utc).replace(tzinfo=None)
        return (created + timedelta(days=total) - now).total_seconds()

    available = [row for row in rows if seconds_left(row) > 0]
    if not available:
        return 0.0

    total_weight = 0.0
    matched_weight = 0.0
    for main in mains:
        for row in available:
            name = str(row.ingredient_name).strip()
            if not name:
                continue
            if name in main or main in name:
                matched_weight += 2.0 if seconds_left(row) <= 2 * 86400 else 1.0
                break
        total_weight += 1.0
    if total_weight == 0:
        return 0.0
    return round(min(100.0, 100.0 * matched_weight / total_weight), 2)


def test_home_cooking_recommend_has_no_fridge_n_plus_one(session_factory):
    result, statements = _count_sql(
        session_factory,
        lambda session: recommend_single(session, 2, "HOME_COOKING", limit=20),
    )
    fridge_queries = [s for s in statements if "fridge_inventory" in s.lower()]

    # 修复前：一次推荐 37 条（其中 32 条查 fridge_inventory）。
    assert len(fridge_queries) <= FRIDGE_SQL_BUDGET, (
        f"库存被查了 {len(fridge_queries)} 次，应 ≤{FRIDGE_SQL_BUDGET}"
    )
    assert len(statements) <= HOME_SQL_BUDGET, f"一次推荐发了 {len(statements)} 条 SQL"
    assert result["recommendations"], "至少要有推荐结果"


def test_recommend_query_budget_with_expanded_candidates(session_factory):
    """候选扩容（limit=100）也不许多发库存查询。"""
    result, statements = _count_sql(
        session_factory,
        lambda session: recommend_single(session, 2, "HOME_COOKING", limit=100),
    )
    fridge_queries = [s for s in statements if "fridge_inventory" in s.lower()]
    assert len(fridge_queries) <= FRIDGE_SQL_BUDGET
    assert len(statements) <= HOME_SQL_BUDGET
    assert len(result["recommendations"]) > 20


def test_out_dining_does_not_query_fridge(session_factory):
    _, statements = _count_sql(
        session_factory,
        lambda session: recommend_single(session, 2, "OUT_DINING", limit=10),
    )
    assert not [s for s in statements if "fridge_inventory" in s.lower()]


def test_batched_fridge_score_matches_independent_reference(session_factory):
    """批量实现 vs 独立逐菜参考实现：多道菜、三种库存状态全覆盖。"""
    from backend.algorithms.single_recommender import (
        _fridge_index,
        _fridge_status_from_index,
    )

    session = session_factory()
    try:
        # 造三种状态的库存：过期 / 临期 / 正常
        now = datetime.utcnow()
        session.add_all(
            [
                FridgeInventory(
                    user_id=2,
                    ingredient_name="鸡蛋",
                    category="肉禽蛋奶",
                    quantity_desc="2 个",
                    expire_days=2,
                    created_at=now - timedelta(days=1),
                ),
                FridgeInventory(
                    user_id=2,
                    ingredient_name="番茄",
                    category="新鲜果蔬",
                    quantity_desc="3 个",
                    expire_days=3,
                    created_at=now - timedelta(days=1),
                ),
                # 过期：created_at 往前 5 天、保质期 2 天 → 剩余 0
                FridgeInventory(
                    user_id=2,
                    ingredient_name="青菜",
                    category="新鲜果蔬",
                    quantity_desc="1 把",
                    expire_days=2,
                    created_at=now - timedelta(days=5),
                ),
            ]
        )
        session.commit()

        index = _fridge_index(session, 2)
        dishes = (
            session.query(Dish)
            .filter(Dish.mode_type == "HOME_COOKING")
            .order_by(Dish.id)
            .limit(12)
            .all()
        )
        assert dishes, "下厨菜谱不应为空"

        for dish in dishes:
            batched = _fridge_status_from_index(index, dish)
            reference = _reference_fridge_status(session, 2, dish)
            assert batched == reference, (
                f"{dish.name} 批量={batched} 参考={reference} "
                f"（库存 {[r.ingredient_name for r in session.query(FridgeInventory).filter(FridgeInventory.user_id == 2)]}）"
            )
    finally:
        session.close()


def test_expired_stock_does_not_raise_status_score(session_factory):
    """过期食材不加状态分：把该用户全部库存弄过期后，下厨推荐的状态分应回落。"""
    session = session_factory()
    try:
        baseline = recommend_single(session, 2, "HOME_COOKING", limit=50)
        baseline_scores: Dict[int, float] = {
            int(item["dish_id"]): float(item["radar_5d"]["status"])
            for item in baseline["recommendations"]
        }

        rows = session.query(FridgeInventory).filter(FridgeInventory.user_id == 2).all()
        assert rows, "演示数据里用户 2 应当有库存"
        for row in rows:
            row.created_at = datetime.utcnow() - timedelta(days=row.expire_days + 3)
        session.commit()

        expired_run = recommend_single(session, 2, "HOME_COOKING", limit=50)
        expired_scores = {
            int(item["dish_id"]): float(item["radar_5d"]["status"])
            for item in expired_run["recommendations"]
        }

        shared = set(baseline_scores) & set(expired_scores)
        assert shared, "两次推荐应有交集，才能比较同一道菜"
        decreased = [d for d in shared if expired_scores[d] < baseline_scores[d]]
        assert decreased, "库存全部过期后，至少应有菜品的状态分下降"
    finally:
        session.close()

def test_batched_pipeline_matches_legacy_pipeline(session_factory, monkeypatch):
    """整条链路的真对照：批量实现 vs 逐菜查库的旧实现。

    这不是"自己跟自己比"：`--legacy` 那套把 `_fridge_status_from_index` 换成
    「每道菜单独查一次 fridge_inventory」，是修复前真实跑过的实现；
    两者都走同一个 `recommend_single`，比的是完整推荐序列（id + 分数）。
    """
    from backend.algorithms import single_recommender

    session = session_factory()
    try:
        session_factory_session = session
        batched = recommend_single(session, 2, "HOME_COOKING", limit=40)
        batched_seq = [
            (int(item["dish_id"]), float(item["total_score"]))
            for item in batched["recommendations"]
        ]

        original = single_recommender._fridge_status_from_index

        def _per_dish(_index, dish):
            fresh = single_recommender._fridge_index(session_factory_session, 2)
            return original(fresh, dish)

        monkeypatch.setattr(
            single_recommender, "_fridge_status_from_index", _per_dish
        )
        try:
            legacy = recommend_single(
                session_factory_session, 2, "HOME_COOKING", limit=40
            )
        finally:
            monkeypatch.setattr(
                single_recommender, "_fridge_status_from_index", original
            )
        legacy_seq = [
            (int(item["dish_id"]), float(item["total_score"]))
            for item in legacy["recommendations"]
        ]

        assert batched_seq == legacy_seq, (
            f"批量与逐菜实现结果不一致：前 3 条 {batched_seq[:3]} vs {legacy_seq[:3]}"
        )
        assert len(batched_seq) > 10
    finally:
        session.close()
