# CHECKS —— PC02/r02

命令、工作目录、退出码与日志一一对应；时间取日志文件最后写入时间（`mtime`），不是人工填写。

| # | 命令 | cwd | 时间 | 退出码 | 日志 | 备注 |
|---|---|---|---|---|---|---|
| 1 | `$env:DATABASE_URL='sqlite:///D:/EatWhat/backend/tmp-clean-r02.db'; python -m pytest tests/test_query_budget.py -q` | `backend` | 17:46:37 | 0 | `logs/10_clean_db_pytest.log` | 干净库（不存在的文件）直接跑，6 passed，跑完文件仍未生成 |
| 2 | `python -u scripts/measure_recommend_sql.py --mode HOME_COOKING --limit 10` | `.` | 17:46:44 | 0 | `logs/11_measure_batched.log` | 批量实现：总 6 / 库存 1 |
| 3 | `python -u scripts/measure_recommend_sql.py --mode HOME_COOKING --limit 10 --legacy` | `.` | 17:46:45 | 0 | `logs/12_measure_legacy.log` | 旧逐菜实现：总 37 / 库存 32 |
| 4 | `python -u scripts/measure_recommend_sql.py --mode OUT_DINING --limit 10` | `.` | 17:46:47 | 0 | `logs/13_measure_out_dining.log` | 外食模式对照：总 6 / 库存 0 |

## 未执行的检查项

| 检查 | 状态 | 原因 |
|---|---|---|
| 浏览器 / 截图 | 不适用 | R01 只改测试与测量脚本，无 UI 变化 |
| 前端构建 | 未执行 | 同上 |
