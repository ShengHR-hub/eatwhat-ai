# CHECKS — PC02 / R01

cwd 一律 `D:\EatWhat`，PowerShell 7，2026-10-24 16:30（Asia/Shanghai）。

| # | 命令 | 退出码 | 日志 |
|---|---|---|---|
| 1 | `python -m backend.scripts.measure_recommend_sql --user 2 --mode HOME_COOKING --legacy` | 0 | `logs/sql_before_home_cooking.log` |
| 2 | `python -m backend.scripts.measure_recommend_sql --user 2 --mode HOME_COOKING` | 0 | `logs/sql_after_home_cooking.log` |
| 3 | `python -m backend.scripts.measure_recommend_sql --user 2 --mode OUT_DINING --legacy` | 0 | `logs/sql_before_out_dining.log` |
| 4 | `python -m backend.scripts.measure_recommend_sql --user 2 --mode OUT_DINING` | 0 | `logs/sql_after_out_dining.log` |
| 5 | `python -m pytest backend/tests/test_query_budget.py -q` | 0 | `logs/pytest_query_budget.log` |
| 6 | `python -m pytest -q` | 0 | `logs/pytest_full.log` |

## 未执行

- 未跑前端构建与浏览器：R01 是后端查询改造，无 UI 变化。
- 未做压测：本条目标是消除 N+1 结构，不是吞吐量。
