# BASELINE —— PC03 / r04

- 采样时间：2026-10-24 22:30 ~ 23:00（Asia/Shanghai）
- 版本控制状态：**仓库尚无任何 commit**（`git rev-parse HEAD` 无输出），以文件级 SHA-256 作锚点，见 `SOURCE_MANIFEST.json`。
- 工作树：大量文件为新增/暂存状态，完整清单见 `data/git_status_short.txt`。
- 运行环境：Windows 11 / Git Bash + PowerShell / Python 3.13.9 / Node v24.19.0 / npm 11.17.0。
- 本轮变更面：`scripts/check-colors.mjs`、`scripts/gate_probes.py`；业务页面、`frontend/src/styles/` 与玻璃令牌**未改**。
- 门禁扫描面：`frontend/src/**/*.{vue,js,css}`，真实目录 38 个文件。
- 复现命令见 `CHECKS.md`；`logs/gate_probes.json` 由脚本写出，禁止手工编辑。
