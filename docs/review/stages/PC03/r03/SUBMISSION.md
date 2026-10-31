# PC03 / r03 提交说明（F12 第三轮）

- 提交日期：2026-10-24（Asia/Shanghai）
- 对应审查项：**R2-04**（整行跳过导致漏检）、**R2-05**（组件本地造色绕过）
- 上一轮：`docs/review/stages/PC03/r02/`（判定 FAIL），本包不覆盖 r01/r02。

## 一、改了什么

| # | 路径 | 改动 |
|---|---|---|
| 1 | `scripts/check-colors.mjs` | 用词法状态机剔除注释（块注释 / 行注释 / 字符串三态，`//` 前一字符是 `:` 时不当注释，避免吃掉 `http://`），注释替换为等长空格，**保留行列且不再整行跳过**；`maskTokenDeclarations` 只对主题出口文件把 `--x: <value>;` 涂空；`THEME_EXPORT` 收到 `frontend/src/styles/{main,glass-card,glass-tokens}.css`；`UPSTREAM` 精确三个 Vue Bits 文件；非主题出口出现「带裸色的自定义属性」记 `token-literal` 违规。 |
| 2 | `scripts/gate_probes.py`（新） | 六类自动探针：通配选择器、注释后业务代码、令牌声明后业务代码、多行注释结束后的同行、组件里 `--local-red:#f00`、合法别名（唯一 exit 0）。 |

## 二、逐项对照

| 审查项 | 旧行为 | 现行为 | 证据 |
|---|---|---|---|
| R2-04 通配 `* { color:#ff0000 }` | 被 `startsWith('*')` 当注释整行跳过 → exit 0 | 命中并 exit 1 | `logs/21_check_colors_block_css.log` |
| R2-04 注释后业务代码 | 注释起始行整行返回 → exit 0 | 注释被涂空、同行业务代码照查 → exit 1 | 同上 |
| R2-04 令牌声明后业务代码 | 令牌行整行返回 → exit 0 | 只涂令牌段，其后声明照查 → exit 1 | 同上 |
| R2-04 多行注释结束后的同行 | 同上漏检 | exit 1 | 同上 |
| R2-05 组件本地造色 | `TOKEN_DECL` 对任意文件任意 `--*` 免检 → exit 0 | `token-literal` 违规 → exit 1 | `logs/22_check_colors_block_bits.log` |
| 正例不误伤 | — | 主题出口的真令牌、组件里 `--alias: var(--color-ink)` 均 exit 0 | `logs/23_check_colors_after_cleanup.log`、`logs/gate_probes.log` |

## 三、回归

```
node scripts/check-colors.mjs            → ✓ 38 个文件无裸 hex / rgb / hsl，exit 0
node scripts/gate_probes.py              → 6/6 PASS（4 exit1 + 1 exit1 + 1 exit0）
cd frontend; npm run build               → ✓ built in 7.71s，exit 0
node scripts/home-fit.mjs                → PASS 390x844 card 422px(50%) / PASS 390x667 card 261px(39%)，exit 0
cd backend; python -m pytest -q          → 140 passed
```

## 四、已知限制

1. 静态扫描覆盖不到运行时拼色（`getComputedStyle` 之后再做字符串拼接）。
2. 玻璃数值本身未改动——r02 已确认的 `--rgb-glass-*` 通道令牌与 10 处数值保持原样。
3. `components/bits/` 仍保留**精确三个文件**豁免（上游原件），新增文件不再自动豁免。
