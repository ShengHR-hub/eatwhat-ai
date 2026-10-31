# CHECKS —— PC01 / r03

| # | 命令 | cwd | 退出码 | 日志 |
|---|---|---|---|---|
| 1 | `python -u -m backend.algorithms.simulate_personas --seed 20261024 --write --out docs/review/simulation/benchmark_seed20261024.json` | repo 根 | 0 | `logs/01_simulate_seed20261024.log` |
| 2 | `python -m backend.scripts.init_seed_data --force`（刷新快照后） | repo 根 | 0 | `logs/03_reseed.log` |
| 3 | 检查库内 `algo_configs.benchmark_json` 与存档逐点一致 | repo 根 | 0 | `logs/04_db_benchmark_check.log` |
| 4 | `cd backend; python -m pytest -q` | `backend/` | 0 | `logs/05_pytest.log`（140 passed） |
| 5 | 植入陈旧快照后 `python -m backend.scripts.init_seed_data --force` | repo 根 | **1（预期失败）** | `logs/06_stale_snapshot_blocked.log` |
| 6 | `cd backend; python -m pytest tests/test_seed_guard.py tests/test_simulation_metrics.py -q` | `backend/` | 0 | `logs/07_r2_01_r2_02_tests.log`（9 passed） |

未执行项：
- 浏览器/UI 检查：R02 是离线仿真，无界面可点；界面回归在 PC03 包内。

### 主规模运行的 stdout 说明（必读）

`logs/01_simulate_seed20261024.log` 为空：主规模那次是通过后台任务执行的，
stdout 没有落到文件，**这是本轮证据的已知缺口**，不辩解。

替代证据（都在本包内，可独立复核）：

1. `data/benchmark_seed20261024.json`：主规模运行的完整输出（四键 + params.calls + group 汇总）。
2. `data/detail_seed20261024.jsonl`：48,000 行逐餐明细（11.2 MB），来自同一次运行。
3. `data/db_benchmark_check.txt`：库内 `algo_configs.benchmark_json` 与上述 JSON 逐点一致。
4. 隔离库 `docs/review/simulation/sim_seed20261024_groups.db`：`group_rooms=1000`、`room_votes=40000`。
5. `logs/02_simulate_seed7.log`：**另一组完整规模运行的 stdout 全量**（seed 7，40,000 票、1,000 房满票），
   证明同一份代码跑满规模时的输出形态与计数。

**取证教训（已写入 `docs/AGENT_MEMORY.md` §19.6）**：长任务必须一开始就把 stdout 重定向到证据目录，
不能只依赖后台任务的捕获输出——否则事后只能补跑，而补跑会覆盖同名的明细文件。
