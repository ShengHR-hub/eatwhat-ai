# BASELINE —— PC01 / r04

- 采样时间：2026-10-24 22:30 ~ 23:30（Asia/Shanghai）
- 版本控制状态：**仓库尚无任何 commit**（`git rev-parse HEAD` 无输出），以文件级 SHA-256 作锚点，见 `SOURCE_MANIFEST.json`。
- 工作树：大量文件为新增/暂存状态，完整清单见 `data/git_status_short.txt`。
- 运行环境：Windows 11 / Git Bash + PowerShell / Python 3.13.9 / Node v24.19.0 / npm 11.17.0；
  SQLite（SQLAlchemy 2.x）。
- 数据集身份：
  - 演示库 `backend/eatwhat.db`：20 门店 / 60 外食 / 40 下厨 / 4 演示角色；本轮用文档化 CLI
    重新播种并写入新 benchmark（只改 `algo_configs.benchmark_json` 与种子数据，不写仿真房间/票）。
  - r04 仿真隔离库：`data/sim_seed20261024/`、`data/sim_seed7/`（各自 ours/baseline/groups/absence）。
  - r03 归档库：`docs/review/simulation/` 原样保留；其中 `sim_seed20261024_ours.db`
    是 8,000 行/20 天的截断旧证据，已在 `data/db_inventory.json` 标为废弃。
- 复现命令见 `CHECKS.md`；`data/*.json`、`data/*.jsonl` 均为脚本生成物，禁止手工编辑。
