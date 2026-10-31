# SUBMISSION — PC03 / F12：颜色只有一个出口

## 任务

把散落在组件与页面里的裸 hex / 数字 rgb 全部归并到设计令牌，清掉残留暖色，
并新增脚本级门禁，能拦住后续违反。

## 验收条目逐项自测

| 条目 | 自测结果 | 证据 |
|---|---|---|
| 裸色值清零 | ✔ 157 处 / 21 文件 → **0** | `data/token_map.md`、`data/after_scan.txt` |
| 残留暖色清零 | ✔ 搜 `ffe2c9` / `255 190 140` 零命中 | `data/warm_color_grep.txt`（0 字节＝无命中） |
| 令牌只有一个出口 | ✔ `main.css` 定义 `--color-*` 与 `--rgb-*`；组件只用 `var(...)` | `SOURCE_MANIFEST.json` 内的 `main.css` |
| 门禁能拦截 | ✔ 故意写 `#ff0000` + `rgba(255,190,140,.32)` 的临时组件被 `exit 1` 打回 | `logs/gate_block_demo.log` |
| 门禁不误伤 | ✔ `rgb(var(--rgb-white) / 0.06)` 这类正确写法放行，31 个文件全绿 | `logs/gate_pass.log`、`logs/gate_verbose.log` |
| 搬移工具已无待办 | ✔ 干跑 `DRY-RUN: 0 个文件需要改写` | `logs/normalize_dryrun.log` |
| 界面未被改坏 | ✔ 构建通过 + 两档屏高门禁 PASS + 截图对照 | `logs/build.log`、`logs/home_fit.log`、`browser/*.png` |

## 变更路径

- `frontend/src/styles/main.css`：新增 `--color-black/panel/sheet` 与 12 个 RGB 通道令牌（`--rgb-white/black/ink/steel/mist/silver/grain-a/grain-c/chrome/chrome-max/panel/sheet`）。
- 21 个组件/页面：颜色表达式改为 `var(--color-x)` 或 `rgb(var(--rgb-x) / a)`。
- `frontend/src/views/mobile/Home.vue`：`.toast--warn` 暖色 → 反白底 + ink 字；同时删掉 `@media (max-height: 700px)` 里一段历史遗留的重复样式。
- `frontend/src/views/mobile/Footprint.vue`：ECharts `itemStyle.borderColor` 改走 `alpha(t.ink, 0.55)`（CSS 变量在 canvas 上非法）。
- 新增 `scripts/normalize_colors.py`（搬移工具，`--write` 才落盘）。
- 新增 `scripts/check-colors.mjs`（门禁，退出码 0/1）。

## 接口 / 迁移变化

无后端接口变化；无数据库变化。纯前端样式与工具脚本。

## 已知限制

- `components/bits/`（Grainient / LiquidChrome / Silk）是 Vue Bits 上游原件，shader 内颜色属实现细节，**豁免**本门禁；它们的配色仍由调用处 props 传入令牌。
- 门禁只管 `frontend/src/**/*.{vue,js}`，不扫 `.css`（样式文件本身就是令牌出口）。
- 颜色没有视觉回归测试：截图由人工比对，`browser/` 里给了 393×852 / 390×667 / 足迹页三张。

## 未做

- 未做暗色模式（规格里没有暗色主题，单色体系只有一套）。
