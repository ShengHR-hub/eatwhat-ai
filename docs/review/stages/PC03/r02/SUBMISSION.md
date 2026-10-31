# SUBMISSION —— PC03 / F12（颜色出口门禁）

- 步骤：PC03
- 轮次：r02（针对 `REPORT.md` 的 CLR-05）
- 状态：**REVIEW_PENDING**（开发方不自签 PASS）

## 一、这轮改了什么

| # | 文件 | 改动 |
|---|---|---|
| 1 | `frontend/src/styles/main.css` | `:root` 新增玻璃调色板**通道令牌**：`--rgb-glass-fill: 246 246 246`、`--rgb-glass-shade: 40 40 40`、`--rgb-glass-highlight: 230 230 230`、`--rgb-glass-edge: 208 208 208`、`--rgb-glass-ring: 232 232 232` |
| 2 | `frontend/src/styles/glass-tokens.css` | `.weather-pill` 的 7 条阴影由字面 `rgba(...)` 改写为 `rgb(var(--rgb-glass-*) / a)`，**数值逐项不变** |
| 3 | `frontend/src/styles/glass-card.css` | `.glass-card--matte` 的 `box-shadow` 同上改写 |
| 4 | `frontend/src/styles/main.css` | 报告点名的 7 处（145/150/247/260/268/278/282 行）全部归并到令牌 |
| 5 | `scripts/check-colors.mjs` | 重写：扫 `.vue` / `.js` / **`.css`**；`rbga?` / `hsla?` 加 `i` 支持大小写；白名单改为**精确文件**；新增三类合法放行 |

## 二、逐条验收自测

| # | 要求 | 自测结果 | 证据 |
|---|---|---|---|
| 1 | 10 处残留全部归并令牌 | 报告列出的 `main.css` 7 处 + `glass-card.css:117` + `glass-tokens.css:36,39` 全部改写为通道令牌表达式 | `data/token_map.md` |
| 2 | 不改已锁定的玻璃参数 | 只改"怎么写"，没改"写多少"：填充 246/0.48、阴影 40/230/208/232、模糊 60px 全部逐值保留 | `data/token_map.md` 对照表 |
| 3 | 扫描真实业务 `.vue/.js/.css` | 34 个文件全扫，`✓ check-colors: 34 个文件无裸 hex / rgb / hsl`、exit 0 | `logs/20_check_colors_pass.log` |
| 4 | 正例：违规必须被拦（CSS） | 临时塞 `#ff0000` / `RGB(255 0 0)` / `hsla(10,20%,30%,.5)` → `✗ 3 处`、**exit 1** | `logs/21_check_colors_block_css.log` |
| 5 | 白名单只豁免精确上游文件 | 在 `components/bits/` 放一个**非上游**业务 Vue 写 `#00ff00` → 被拦、exit 1（证明不再整目录豁免） | `logs/22_check_colors_block_bits.log` |
| 6 | 清理后回到全绿 | 删除探针文件后 `✓ 34 个文件`、exit 0 | `logs/23_check_colors_after_cleanup.log` |
| 7 | 构建与一屏门禁不被破坏 | `✓ built in 5.88s`；`home-fit` 两档 PASS（card 422px/261px、overlap 0） | `logs/24_build.log`、`logs/25_home_fit.log` |

## 三、白名单的最终口径

允许出现色值的位置只有三类，且都在 `scripts/check-colors.mjs` 里写死：

1. **令牌定义本身**：`--自定义属性` 声明行与跨多行声明体（`--glass-shadow:` 那种）。
2. **注释**（`/* */`、`//`、`*` 开头行）——不参与渲染。
3. **精确文件**：`components/bits/{Grainient,LiquidChrome,Silk}.vue`（Vue Bits 上游原件，只许改 props，shader 与内部实现不许碰）
   与 `utils/theme.js`（JS→CSS 唯一桥：`readVar()` 的 fallback 与 `main.css` 令牌同值，`alpha()` 只把已解析色值拆成 rgba 字符串）。

`components/bits/` **不再是目录级豁免**——除这三个文件名之外的新文件照样被扫（见验收第 5 条）。

## 四、已知限制

- 本包没有视觉回归基线（无截图 diff 工具），只能给"改前改后肉眼一致"的三张实拍 + 说明每张看什么；
  真正的像素级回归要等批次 4 的视觉基线工具。
- 门禁是**静态扫描**：`style="color: #fff"` 这类内联样式会被扫到，但运行时由 JS 拼出来的颜色不在覆盖范围内。
