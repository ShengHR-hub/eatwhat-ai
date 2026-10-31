# CHECKS —— PC03 / r03（F12 颜色门禁 R2-04 / R2-05）

全部命令在仓库根 `D:\EatWhat` 下执行，时间取自对应日志文件的修改时间（Asia/Shanghai）。

| # | 命令 | 期望 | 退出码 | 日志 |
| --- | --- | --- | --- | --- |
| 1 | `node scripts/check-colors.mjs` | 38 文件 0 违规 | 0 | `logs/20_check_colors_pass.log` |
| 2 | `python scripts/gate_probes.py`（六类反例：通配选择器 / 注释后业务代码 / 令牌声明后业务代码 / 组件本地造色 / 多行注释后代码 / 合法别名） | 五个反例 exit 1、别名 exit 0、基线 exit 0 | 0（探针自检全 PASS） | `logs/gate_probes.log` + `logs/gate_probes.json` |
| 3 | 临时 CSS 探针（`_probe_wildcard.css` 等） | 被定位到具体文件行 | 1 | 见 `logs/gate_probes.log` 内嵌输出 |
| 4 | 清理探针后 `node scripts/check-colors.mjs` | 回到 38 文件 0 违规 | 0 | `logs/23_check_colors_after_cleanup.log` |
| 5 | `cd frontend; npm run build` | `✓ built` | 0 | `logs/24_build.log` |
| 6 | `node scripts/home-fit.mjs` | 两档 PASS | 0 | `logs/25_home_fit.log` |
| 7 | `python -m pytest -q`（全量，确认门禁改动未碰后端） | 140 passed | 0 | `../PC01/r03/logs/05_pytest.log` |

## 未执行项及原因

- **像素级视觉回归**：没有基线图与 diff 工具；改用「改动前后截图肉眼一致 + 令牌数值逐项比对」。
  截图在 `browser/`，数值比对见 `data/`。
- **运行时拼色扫描**：静态扫描覆盖不到 JS 里字符串拼接出的颜色值；这类只用 `utils/theme.js` 的
  `tokens()` 读取，已由代码评审覆盖，无自动化断言。

## 门禁行为说明（R2-04 / R2-05 之后）

- 注释与自定义属性值都按**词法范围**豁免，不再整行跳过：
  `stripComments()` 把注释替换成等长空格，`maskTokenDeclarations()` 只对
  `frontend/src/styles/{main,glass-card,glass-tokens}.css` 涂掉 `--x: <value>;`。
- 非主题出口文件里的「带裸色的自定义属性」单独记 `token-literal`（这就是组件自造
  `--local-red:#ff0000` 的绕过点）。
- `UPSTREAM` 白名单是三个精确的 Vue Bits 文件（`components/bits/{Grainient,LiquidChrome,Silk}.vue`），
  不是整个 `components/bits/` 目录。
