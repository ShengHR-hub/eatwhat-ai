# BASELINE —— 评审基线（PC03/r02）

## 时间与时区

- 生成时间：2026-10-24（Asia/Shanghai，UTC+8）
- 本轮返工针对的复审报告：`docs/review/clearance-codex-2026-10-24/REPORT.md`
- 返工指令：`D:\谷歌\BATCH4_REWORK_ROUND2.md` + 用户 2026-10-24 的口头四句话

## 版本控制状态

| 项 | 值 |
|---|---|
| `git rev-parse --verify HEAD` | **失败**：仓库尚无任何 commit |
| 工作树 | 315 个条目，全部为初始 staged（`A` / `AM`），无可比对基线提交 |
| 受审文件清单 | 见同目录 `SOURCE_MANIFEST.json`（逐个给字节数与 SHA-256） |

因为不存在 harness 基线，本轮不声称"与基线的 diff"，改以**文件级 SHA-256** 作为可复核锚点：
复审按 `SOURCE_MANIFEST.json` 的 `files[]` 逐个算哈希，一致即说明受审的就是这一版源码。

## 环境

| 项 | 值 |
|---|---|
| 系统 | Windows-11-10.0.22631 |
| Python | 3.13.9 |
| Node / npm | v24.19.0 / 11.17.0 |
| 浏览器（截图门禁） | headless Chrome，CDP 9222，视口 393×852 与 390×667 |
| 服务 | Vite 5173（`host 0.0.0.0`）+ Uvicorn 8000（仓库根 `python -m uvicorn backend.main:app`） |

## 数据集身份

- **演示库** `backend/eatwhat.db`：`init_seed_data.py --force` 播种（门店 20 / 外食 60 / 家常 40 / 演示角色 4），
  `algo_configs` 仅 `default_production` 一行。
- **仿真隔离库**（不写演示库）：`docs/review/simulation/sim_seed20261024_ours.db` / `_baseline.db` / `_groups.db`，
  由 `simulate_personas.py` 自己建表、自己灌人设，只从演示库**只读**复制 `restaurants` / `dishes_and_recipes`。
- 校验演示库未被写：重播种子之后 `select count(*) from group_rooms`（演示库）仍为 **0**。

## 工作树完整清单（附录）

见 `data/git_status_short.txt`（315 行，`git status --short` 原样输出）。
