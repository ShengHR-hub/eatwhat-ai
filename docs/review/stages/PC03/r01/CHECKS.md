# CHECKS — PC03 / F12

cwd 一律 `D:\EatWhat`，PowerShell 7，2026-10-24 16:30–16:35（Asia/Shanghai）。

| # | 命令 | 退出码 | 日志 |
|---|---|---|---|
| 1 | `node scripts/check-colors.mjs` | 0 | `logs/gate_pass.log` |
| 2 | `node scripts/check-colors.mjs --verbose` | 0 | `logs/gate_verbose.log` |
| 3 | 放入违规样例 `frontend/src/components/ColorGateDemo.vue` 后 `node scripts/check-colors.mjs` | **1** | `logs/gate_block_demo.log` |
| 4 | 删除样例后 `node scripts/check-colors.mjs` | 0 | `logs/gate_pass_again.log` |
| 5 | `python scripts/normalize_colors.py`（干跑） | 0 | `logs/normalize_dryrun.log` |
| 6 | `cd frontend; npm run build` | 0 | `logs/build.log` |
| 7 | `node scripts/home-fit.mjs` | 0 | `logs/home_fit.log` |

## 未执行

- 没有视觉回归基线对比（无基准截图库），改前/改后靠人工比对；`browser/` 里是改后截图。
- 未跑 `refill-fresh.mjs` / `sandbox-sync.mjs`：它们验的是交互契约，不是颜色；本轮已在上一次收口时通过。
- 未做 `prefers-color-scheme` 分支：规格无暗色主题。
