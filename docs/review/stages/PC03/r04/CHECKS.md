# CHECKS —— PC03 / r04（F12 颜色门禁 R3-02）

全部命令在仓库根 `D:\EatWhat` 下执行，时间取自日志文件修改时间（Asia/Shanghai）。

| # | 命令 | 期望 | 退出码 | 日志 |
| --- | --- | --- | --- | --- |
| 1 | `node scripts/check-colors.mjs` | 38 文件 0 违规 | 0 | `logs/20_check_colors_real.log` |
| 2 | `python scripts/gate_probes.py` | 23 个探针全部符合预期；sandbox 基线 exit 0 | 0 | `logs/21_gate_probes.log`、`logs/gate_probes.json` |
| 3 | `cd frontend; npm run build` | `✓ built` | 0 | `logs/20_build.log` |
| 4 | `cd backend; python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-r04` | 161 passed | 0 | `../PC01/r04/logs/05_pytest.log` |
| 5 | 同 #4，basetemp 放在 review 目录 | 一次 1 failed（`os.replace` PermissionError），重跑通过（当时 159；加入新用例后全量 161） | 0（重跑） | `../PC01/r04/logs/05a_pytest_review_basetemp.log`；不把瞬态当成断言失败 |

## 未执行项

- **浏览器/UI**：本轮只改 `scripts/check-colors.mjs` 与探针，不改前端业务源码/样式；
  r03 的 390×844、390×667 真实点击证据仍有效，但**不记作 r04 新结果**，也不声称 S08 通过。
- **像素级视觉回归**：没有基线图/diff 工具；玻璃令牌数值未改，由 r03 证据保留。

## 门禁行为说明（R3-02 之后）

- JS/Vue script：字符串、模板字符串、正则字面量整体跳过；`//`、`/* */` 按词法剔除。
- CSS/Vue style：字符串与 `url(...)` 整体跳过；CSS 没有 `//` 行注释，只剔除 `/* */`。
- Vue template/HTML：只剔除 `<!-- -->`，`style="color:#f00"` 仍会被定位。
- 非主题出口的裸色自定义属性仍单独记 `token-literal`；`UPSTREAM` 仍是三个精确文件。
