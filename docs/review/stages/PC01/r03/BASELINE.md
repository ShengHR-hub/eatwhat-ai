# BASELINE —— r03 审查基线

- 采样时间：2026-10-24 21:20 ~ 21:40（Asia/Shanghai）
- 版本控制状态：**仓库尚无任何 commit**（`git rev-parse HEAD` 无输出），因此以**文件级 SHA-256** 作锚点，见同目录 `SOURCE_MANIFEST.json`。
- 工作树：存在大量未跟踪文件（`frontend/`、`docs/`、`scripts/` 全部为新增），完整清单见 `data/git_status_short.txt`。
- 运行环境：Windows 11 / PowerShell 7 / Python 3.13.9 / Node v24.19.0 / npm 11.17.0；SQLite（SQLAlchemy 2.x）。
- 数据集身份：
  - 演示库 `backend/eatwhat.db`：20 门店 / 60 外食 / 40 下厨 / 4 演示角色 / 95 张菜品图（`/dishes/<id>-<slug>.jpg`）。
  - 仿真隔离库：`docs/review/simulation/sim_seed20261024_{ours,baseline,groups,absence}.db`。
- 复现命令见 `CHECKS.md`；证据为**生成物**，禁止手工编辑（`data/*.json` 均由脚本写出）。
