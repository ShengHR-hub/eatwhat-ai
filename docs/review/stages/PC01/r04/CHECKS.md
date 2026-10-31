# CHECKS —— PC01 / r04（R02 返工：R3-01 / R3-03）

全部命令在仓库根 `D:\EatWhat` 下执行（pytest 在 `backend/`），时间为 Asia/Shanghai。

| # | 命令 | 期望 | 退出码 | 日志 |
| --- | --- | --- | --- | --- |
| 1 | `python -u -m backend.algorithms.simulate_personas --seed 20261024 --lambda-val 0.5 --omega-val 0.5 --data-dir docs/review/stages/PC01/r04/data/sim_seed20261024 --out docs/review/stages/PC01/r04/data/benchmark_seed20261024.json` | 完整 60 天、两臂各 24,000 餐、1,000 房/40,000 票 | — | `logs/01_simulate_seed20261024.log` |
| 2 | `python -u -m backend.algorithms.simulate_personas --seed 7 --lambda-val 0.8 --omega-val 0.6 --data-dir docs/review/stages/PC01/r04/data/sim_seed7 --out docs/review/stages/PC01/r04/data/benchmark_seed7.json` | 同上，换参数复跑 | — | `logs/02_simulate_seed7.log` |
| 3 | `python docs/review/stages/PC01/r04/probes/metric_probe.py` | 五类固定样本与 R>100 样本符合独立参考 | 0 | `logs/03_metric_probe.log` |
| 4 | `python docs/review/stages/PC01/r04/probes/seed_probe.py` | 9 个真实 CLI 用例全部符合预期 | 0 | `logs/04_seed_probe.log`、`data/seed-results.json` |
| 5 | `cd backend; python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-r04` | 161 passed | 0 | `logs/05_pytest.log` |
| 6 | `python docs/review/stages/PC01/r04/probes/recompute_bars.py` | 用归档 40,000 票复算，交叉核对 | 0 | `logs/06_recompute_bars.log`、`data/bars_recomputed.json` |
| 7 | `python -m backend.scripts.init_seed_data --force --benchmark-from docs/review/stages/PC01/r04/data/benchmark_seed20261024.json` | 快照刷新 + 演示库重播 | 0 | `logs/07_reseed.log` |
| 8 | `python -m backend.scripts.init_seed_data --force` | 连续执行，不误判旧快照 | 0 | `logs/08_repeat_reseed.log` |
| 9 | `python docs/review/stages/PC01/r04/probes/db_check.py` | 库/快照/存档逐点一致；票数 40,000 | 0 | `logs/09_db_check.log`、`data/db_benchmark_check.json`、`data/db_inventory.json` |

## 未执行项

- **浏览器/UI**：R02 是离线仿真，无界面可点；界面回归在 PC03 包与 r03 浏览器证据中，不混入本包。
- **完整多人 WS / APK / `/admin`**：不在本轮范围，S09 与批次 4 仍 LOCKED。

## pytest 说明

首次以 review 目录作为 pytest basetemp 时，`test_refresh_then_repeat_is_idempotent`
出现 1 次 `os.replace` PermissionError；同一命令重跑通过，改用工作区外 basetemp 后
161 passed。判定为 Windows 文件占用瞬态，不是断言失败；当前通过日志在 `logs/05_pytest.log`。
