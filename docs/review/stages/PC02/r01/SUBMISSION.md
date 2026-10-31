# SUBMISSION — PC02 / R01：下厨推荐 N+1 消除

## 任务

`HOME_COOKING` 单人推荐原本对每道候选逐条查 `fridge_inventory`（N+1）。
改为「一次查询 + 内存判分」，并要求推荐结果与旧实现等价。

## 验收条目逐项自测

| 条目 | 自测结果 | 证据 |
|---|---|---|
| 库存查询从 N 次降到常数次 | ✔ `fridge_inventory` 查询 **32 → 1**；总语句 **37 → 6** | `data/before_after_summary.txt`、`logs/sql_*.log` |
| 结果不因批量化而改变 | ✔ `same top3: True`、`same count: True`（31 道） | 同上 |
| 外食模式不受影响 | ✔ `OUT_DINING` 6 → 6，库存查询 0 | `logs/sql_before_out_dining.log` / `sql_after_out_dining.log` |
| 有回归测试守住 | ✔ 新增 3 条：库存 ≤1 且总语句 ≤10、批量实现与逐菜实现等价、外食不查库存 | `logs/pytest_query_budget.log` |
| 全量测试 | ✔ 128 passed | `logs/pytest_full.log` |

## 变更路径

- `backend/algorithms/single_recommender.py`：新增 `_fridge_index(db, user_id)`（一次查出该用户库存并按 `fridge_clock` 预计算权重，过期跳过、临期 2.0）；新增 `_fridge_status_from_index(index, dish)`（纯内存）；主循环前按模式取一次索引；`_fridge_status_score()` 保留为单菜入口，内部复用同一套逻辑。
- 新增 `backend/scripts/measure_recommend_sql.py`：用 `sqlalchemy.event.before_cursor_execute` 计数，`--legacy` 走旧逐菜实现做同工具对比（避免拿两次不同工具的数字比）。
- 新增 `backend/tests/test_query_budget.py`（3 条）。

## 接口 / 迁移变化

无。`/recommend/single` 的请求与响应字段不变，`radar_5d.status` 的取值口径不变。

## 已知限制

- 基准固定 `user 2 / limit 40`（下厨菜共 40 道、可推荐 31 道）。用户库存行数越多，旧实现的差距越大；本条只证明「消除了随候选数线性增长的查询」。
- 索引在每次请求内重建，未加跨请求缓存——缓存会引入「库存改了但推荐不更新」的新问题，本轮不引入。

## 未做

- 未优化其它查询（菜品主表的 Eager 关系仍在），超出本条范围。
