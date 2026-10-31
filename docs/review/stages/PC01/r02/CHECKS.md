# CHECKS —— PC01/r02

命令、工作目录、退出码与日志一一对应；时间取日志文件最后写入时间（`mtime`），不是人工填写。

| # | 命令 | cwd | 时间 | 退出码 | 日志 | 备注 |
|---|---|---|---|---|---|---|
| 1 | `python -u -m backend.algorithms.simulate_personas --seed 20261024 --write --out docs/review/simulation/benchmark_seed20261024.json` | `.` | 17:45:44 | 0 | `logs/01_simulate_seed20261024.log` | 全量主跑（200 人 × 60 天 × 2 餐 + 1000 场），约 11 分钟 |
| 2 | `python -u -m backend.algorithms.simulate_personas --seed 7 --lambda-val 0.8 --out docs/review/simulation/benchmark_seed7.json` | `.` | 17:45:44 | 0 | `logs/02_simulate_seed7_lambda0.8.log` | 换种子/换参数复跑，**不带 `--write`**，不写库 |
| 3 | `python -m backend.scripts.init_seed_data --force` | `.` | 17:46:02 | 0 | `logs/03_reseed.log` | 先刷新 `backend/scripts/benchmark_snapshot.json` 再播种 |
| 4 | `python docs/review/stages/PC01/r02/data/_db_check.py` | `.` | 17:46:02 | 0 | `logs/04_db_benchmark_check.log` | 库内四键结构与逐点曲线校验 |
| 5 | `python -m pytest -q` | `backend` | 17:46:18 | 0 | `logs/05_pytest.log` | 全量回归，131 passed |

## 未执行的检查项

| 检查 | 状态 | 原因 |
|---|---|---|
| 浏览器 / 截图 | 不适用 | R02 是后端仿真，无 UI 变化；见 `browser/NOT_APPLICABLE.md` |
| 前端构建 | 未执行 | 本轮未改前端源码（改的是 `backend/` 与 `backend/scripts/benchmark_snapshot.json`） |
