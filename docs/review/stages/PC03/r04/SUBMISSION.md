# PC03 / r04 提交说明（F12 第四轮）

- 提交日期：2026-10-24（Asia/Shanghai）
- 对应审查项：**R3-02**（颜色门禁仍有合法语法漏检）
- 上一轮：`docs/review/stages/PC03/r03/`（判定 FAIL），本包不覆盖 r01/r02/r03。
- 本轮只改门禁脚本与探针；**没有改任何业务页面、主题令牌或玻璃材质**。

## 一、改了什么

| # | 路径 | 改动 |
|---|---|---|
| 1 | `scripts/check-colors.mjs` | 把 r03 的单一注释状态机拆成按语言处理：`maskJsComments()` 识别字符串/模板字符串/**正则字面量**/行块注释；`maskCssComments()` 识别字符串与 **`url(...)`**、只把 `/* */` 当注释；`maskHtmlComments()` 只吃 `<!-- -->`；`maskVue()` 按 `<script>`/`<style>` 分段。注释仍替换为等长空格，行列不变。 |
| 2 | `scripts/gate_probes.py` | 改为在 `docs/review/stages/PC03/r04/sandbox/` 复制同一份 checker，保持 `frontend/src` 相对布局，逐例跑真实 Node 子进程；不再向真实 `frontend/src` 注入探针。共 23 个探针 + sandbox 基线：旧 6 类 + JS 正则 + CSS URL + Vue HTML 注释 + JS 除号/字符串 + CSS 注释 URL + RGB/HSLA 大小写 + bits 精确豁免 + 主题多行令牌。 |

## 二、逐项对照（R3-02）

| 审查反例 | 旧行为 | 现行为 | 证据 |
|---|---|---|---|
| 合法 JS `const pattern = /[/*]/; const color = "#ff0000";` | `/*` 被当块注释，后者消失 → exit 0 | 正则整体跳过，字符串内裸色被定位 → exit 1 | `logs/gate_probes.json` `js_regex_then_color` |
| 合法 CSS `url(https://example.com//a.png);color:#ff0000` | URL 的 `//` 被当行注释 → exit 0 | `url(...)` 整体跳过，同行裸色被定位 → exit 1 | `css_url_then_color` |
| Vue `<template><!-- color:#ff0000 --><p>ok</p></template>` | 误报 exit 1 | HTML 注释被剔除 → exit 0 | `vue_html_comment_ok` |
| 通配选择器 / 注释后同行代码 / 令牌后同行代码 / 多行注释后同行 | r03 已修 | 保持 exit 1 | 旧 4 例 |
| 组件本地 `--local-red:#ff0000` | r03 已修 | 保持 exit 1（`token-literal` + `literal`） | `local_token_in_component` |
| 合法别名 `--x: var(--color-ink)` | r03 已修 | 保持 exit 0 | `alias_ok` |
| 主题出口多行令牌结束后同行业务 | 未覆盖 | 令牌段被涂空，后续 `.x{color:#ff0000}` → exit 1 | `theme_multiline_token_then_code` |
| 主题出口只有令牌 + 合法消费 | — | exit 0 | `theme_token_only_ok` |
| 精确上游 `bits/Grainient.vue` 豁免 / 非上游 `bits/BusinessCard.vue` | — | 前者 exit 0，后者 exit 1 | `upstream_exact_file_ok`、`non_upstream_bits` |

## 三、回归

- 真实目录 `node scripts/check-colors.mjs` → `✓ 38 个文件`，exit 0（`logs/20_check_colors_real.log`）。
- `python scripts/gate_probes.py` → 23 个探针 + sandbox 基线全部 PASS（`logs/21_gate_probes.log`、`logs/gate_probes.json`）。
- `cd frontend; npm run build` → `✓ built in 7.07s`，exit 0（`logs/20_build.log`）。
- `cd backend; python -m pytest -q` → 161 passed，exit 0（`../PC01/r04/logs/05_pytest.log`）。
  一次以 review 目录作 pytest basetemp 时出现 1 个 `os.replace` PermissionError，
  同一命令重跑通过；属 Windows 文件占用瞬态，不是断言失败。

## 四、未执行项

- **浏览器/UI 回归**：本轮没有改前端业务源码或样式，只改扫描脚本；r03 的双屏真实点击证据仍保留。
  因此 `browser/NOT_APPLICABLE.md` 说明原因，不把 r03 的浏览器结果冒充 r04 新结果，也不据此声称 S08 通过。
- **运行时拼色**：静态扫描仍覆盖不到 `getComputedStyle` 后拼接的颜色；这类只允许走 `utils/theme.js`，
  属代码评审范围。

## 五、结论

开发方自测：R3-02 的三个新反例与旧探针均符合预期，真实目录扫描和构建通过。
**不签 PASS**；等待 Codex 独立复审本包，S09 与批次 4 仍 LOCKED。
