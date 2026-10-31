# F12 颜色归一：从 157 处裸色值到 0

## 改法

1. `frontend/src/styles/main.css` 新增 **RGB 通道令牌**（出口）：`--rgb-white/black/ink/steel/mist/silver/grain-a/grain-c/chrome/chrome-max/panel/sheet`，
   并补 `--color-black / --color-panel / --color-sheet`。
2. `scripts/normalize_colors.py`（新）做机械搬移：
   - `rgb(255 255 255 / 0.06)`、`rgba(0, 0, 0, 0.3)` → `rgb(var(--rgb-white) / 0.06)`
   - `#17171A` → `var(--color-ink)`（另有 steel/mist/silver/white/chrome/chrome-max/grain-a 等映射）
   - 只动组件与页面，跳过令牌出口（`styles/`、`utils/theme.js`、`components/bits/`）。
3. 人工处理脚本不懂语义的部分：
   - `Home.vue` 的 `.toast--warn` 原来用暖色 `#ffe2c9` + `rgb(255 190 140 / .32)`，改为**反白底 + ink 字**，单色体系下靠明度反差而不是色相。
   - 同处还发现一段被 `@media (max-height: 700px)` 吞掉的重复样式（早前用 Substring 改 CSS 的遗留），一并清掉。
   - `Footprint.vue` 的 ECharts `itemStyle.borderColor` 不能写 CSS 变量（canvas 不解析），改走 `alpha(t.ink, 0.55)`（theme 令牌）。
4. `scripts/check-colors.mjs`（新）做门禁：扫 `frontend/src/**/*.{vue,js}`，禁裸 `#hex` / 数字 `rgb()/rgba()` / `hsl()`；
   放行 `var(--…)`、`rgb(var(--…))`、`transparent`、`currentColor`；跳过令牌出口与 Vue Bits 上游原件。

## 数字

- 归一前：**157 处 / 21 个文件**（`rgb` 家族 122、hex 35）。
- 归一后：`scripts/check-colors.mjs` → `✓ 31 个文件无裸 hex / rgb / hsl`。
- 暖色清零：全仓 `#ffe2c9`、`rgb(255 190 140` 已无。

## 拦截演示（可复现）

`docs/review/clearance/f12/gate_block_demo.txt` 记录了一次故意违规：

```
✗ check-colors: 2 处裸色值（扫描 32 个文件）
  frontend/src/components/ColorGateDemo.vue:8  [hex] #ff0000   color: #ff0000;
  frontend/src/components/ColorGateDemo.vue:9  [rgb] rgba(   background: rgba(255, 190, 140, 0.32);
demo exit code: 1
```

删掉该文件后重现 `✓ … 无裸 hex / rgb / hsl`，退出码 0。
