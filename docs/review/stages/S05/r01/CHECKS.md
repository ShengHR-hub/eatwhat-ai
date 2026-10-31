# S05 / r01 检查记录

日期：2026-10-27（Asia/Shanghai）
工作目录：`D:\EatWhat`
说明：所有命令均记录 cwd、时间、退出码与完整日志路径；失败记录保留，不删断言、不放宽条件。

## 1. 环境与隔离

| 步骤 | 命令 / 方式 | 时间 | 退出码 | 日志 |
| --- | --- | --- | --- | --- |
| 基线冻结 | `python docs/review/stages/S05/r01/data/capture_baseline.py` | 00:36:26 | 0 | `logs/00_baseline.log`、`data/baseline.json` |
| 与 S04/r03 源码比对 | 逐项重算 154 项 SHA-256 | 00:36 | 0 | `logs/01_source_drift_vs_s04r03.log` |
| 隔离库复制 | `cp backend/eatwhat_dev_pre00_r02.db backend/eatwhat_s05_r01_iso.db` | 00:36:42 | 0 | `logs/02_iso_db_provenance.log`（复制前后 SHA 相同） |
| 后端启动 | `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s05_r01_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` | 00:36 | — | `logs/03_backend_start.log` |
| 前端启动 | `cd frontend && npm run dev` | 00:37 | — | `logs/04_vite_start.log` |
| 哨兵验证 | `python …/data/probe_db_isolation.py` | 00:37:18 | **0** | `logs/05_db_isolation.log`、`data/db_isolation.json` |
| Chrome | `chrome --headless=new --remote-debugging-port=9222 …` | 00:37 | — | `logs/06_chrome_start.log` |
| 服务停止 | 停止 8000/5173/9222；删除临时 profile | 01:09:30 | 0 | `logs/70_service_shutdown.log`（端口无监听） |

哨兵结论：iso 库读路径返回哨兵昵称；写路径 `eating_logs 9→10`；清理后行数恢复；演示库/S10 库/dev 源库 SHA 前后不变。

## 2. 真实浏览器套件（最终）

| 项 | 值 |
| --- | --- |
| 命令 | `node docs/review/stages/S05/r01/data/browser_probe.mjs` |
| cwd | `D:\EatWhat` |
| 时间 | 2026-10-27 01:04:47 → 01:07:05（`browser_evidence.captured_at` / 日志 mtime） |
| 退出码 | **0** |
| 日志 | `logs/51_browser_final_definitive.log` |
| 证据 | `browser_evidence.json`、`browser/final/`（32 张）、`browser/failure_shots/`（失败时刻） |
| 输入方式 | CDP `Input.dispatchMouseEvent` / `dispatchKeyEvent`（真实浏览器输入，非 `element.click()`） |
| 视口 | 390×844、390×667（DPR 2，mobile emulation） |

最终输出：

```json
{
  "verdicts": {
    "home": "PASS",
    "nav": "PASS",
    "sandbox": "PASS",
    "role": "PASS",
    "checkin": "PASS",
    "refill": "PASS",
    "faults": "PASS"
  },
  "screenshots": 32,
  "network": 89,
  "console_errors": 0,
  "console_warnings": 0,
  "exceptions": 0,
  "page_errors": 0
}
```

网络与身份审计（同一份 `browser_evidence.json`）：

- 所有请求均经 `http://127.0.0.1:5173/api/v1/...`（Vite 代理），无直连后端域名。
- 非 `faults` 阶段所有响应 200；后端日志无 5xx / Traceback（唯一 404 是主动查询用户 999）。
- `faults` 阶段非 200 仅两条，均为受控注入：`500`（`Fetch.fulfillRequest`）与 `net::ERR_INTERNET_DISCONNECTED`（`Network.emulateNetworkConditions(offline)`）。
- 请求头审计：home/nav/sandbox/checkin/refill/faults 均为用户 1；role 阶段 1→2→1。

两档几何（最终套件，详见 `SUBMISSION.md` §4.3）：

- 390×844：`scrollHeight 844 / innerHeight 844`，`scrollWidth 390 / innerWidth 390`；顶卡 422（50%）；操作行 740–784，Tab 792–836，重叠 0；按钮/Tab/首候选命中自身；正文溢出 0。
- 390×667：`scrollHeight 667 / innerHeight 667`，`scrollWidth 390`；顶卡 261（39%）；操作行 563–607，Tab 615–659，重叠 0；按钮/Tab/首候选命中自身；正文溢出 0。

## 3. 修复前与探针失败记录（保留）

| 日志 | 退出码 | 结论 / 类型 |
| --- | --- | --- |
| `20_browser_home_pre_fix.log` | 0 | 修复前 home 通过 |
| `21_browser_nav_pre_fix.log` | 0 | 修复前 nav 通过（首版探针在旧 selector 上曾语法失败，已修正后重跑） |
| `22_browser_sandbox_pre_fix.log` | **1** | **应用缺陷 S05-R01-01**：离开首页后补发 1 次推荐请求 |
| `23_browser_role_pre_fix.log` | 0 | 修复前 role 通过 |
| `24_browser_checkin_pre_fix.log` | 0 | 修复前 checkin 通过 |
| `25_browser_refill_pre_fix.log` | 0 | 修复前 refill 通过 |
| `26_browser_faults_pre_fix.log` | **1** | **应用缺陷 S05-R01-03**：UI 显示原始 `Internal Server Error` |
| `27_manual_sandbox_resurrection_pre_fix.log` | — | **应用缺陷 S05-R01-02** 的手工 CDP 复现记录（非机器日志，明确标注） |
| `30_browser_sandbox_post_fix.log` | 0 | 修复后 sandbox 通过 |
| `31_browser_faults_post_fix.log` | 0 | 修复后 faults 通过 |
| `33_browser_full_post_fix.log` | **1** | **探针问题**：双次导航竞态 + 路由转场中点击；非应用回归 |
| `34_home_repeat_1/2/3.log` | 0 | 单独重复 home 3 次均通过，定位为探针竞态 |
| `35_browser_full_post_fix_run2.log` | **1** | **探针问题**：`DOMStorage` 无帧；改为文档前脚本注入 |
| `36_home_domstorage_fix.log` | 0 | 修正后 home 通过 |
| `37_browser_full_post_fix_run3.log` | 0 | 首次全阶段 7/7 通过 |
| `38_browser_full_stability_1/2.log` | 0 | 连续两次全阶段通过（加入 page error / unhandled rejection 采集） |
| `47_browser_final.log` | 0 | 全阶段通过（加入刷新与角色基因断言前） |
| `51_browser_final_definitive.log` | **0** | **最终受审运行** |

说明：`33`/`35` 的失败来自证据探针本身（同一页面二次导航读到旧文档、路由转场中点击、DOMStorage 无帧），通过“文档前注入 localStorage”和“等待转场结束”修正；未为迁就探针修改应用代码。`13_sandbox_pre_fix.log` 中 `used: null` 是门禁脚本旧选择器问题，已修复并加强（S05-R01-04）。

## 4. 自动化验证（最终源码）

| # | 命令 | cwd | 开始 | 结束 | 退出码 | 结果 | 日志 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `node scripts/home-fit.mjs` | `D:\EatWhat` | 01:07:26 | 01:07:29 | **0** | 两档 PASS | `logs/60_gate_home_fit_final.log` |
| 2 | `node scripts/refill-fresh.mjs` | `D:\EatWhat` | 01:07:29 | 01:07:50 | **0** | PASS | `logs/61_gate_refill_fresh_final.log` |
| 3 | `node scripts/sandbox-sync.mjs` | `D:\EatWhat` | 01:07:50 | 01:07:54 | **0** | PASS | `logs/62_gate_sandbox_sync_final.log` |
| 4 | `node scripts/check-colors.mjs` | `D:\EatWhat` | 01:07:54 | 01:07:54 | **0** | PASS | `logs/63_gate_check_colors_final.log` |
| 5 | `python -m pytest -q` | `D:\EatWhat\backend` | 01:07:58 | 01:08:23 | **0** | 365 passed, 1 skipped, 61 warnings | `logs/64_backend_pytest_final.log` |
| 6 | `npm run build` | `D:\EatWhat\frontend` | 01:08:23 | 01:08:32 | **0** | built | `logs/65_frontend_build_final.log` |
| 7 | `python …/probe_db_protection.py` | `D:\EatWhat` | 01:07:10 | 01:07:10 | **0** | 三库未变；+1 日志；schema 通过 | `logs/52_db_protection_final.log` |
| 8 | `python …/probe_api_compat.py` | `D:\EatWhat` | 01:04:10 | 01:04:10 | **0** | 8 项接口 200 / 未知用户 404 | `logs/49_api_compat.log` |

### 4.1 四道门禁完整输出

```text
$ node scripts/home-fit.mjs
PASS 390x844 | card 422px (50%) | actions 740-784 | tab 792-836 | overlap 0
PASS 390x667 | card 261px (39%) | actions 563-607 | tab 615-659 | overlap 0
exit_code=0
```

```text
$ node scripts/refill-fresh.mjs
swiped 24 张，第一批 24 道
refill 请求 exclude 24 个 | 返回 24 道
新首卡：干炒牛河
PASS 「换一批」给的是新候选
exit_code=0
```

```text
$ node scripts/sandbox-sync.mjs
card before: 招牌牛腩面
card after : 麻辣香锅
used       : λ 2.00 · ω 0.50 · β 0.25 · γ 0.20
requests   : 1 → 2
last ids   : 1,4,5,3,2,15 … (24)
PASS 沙盒与首页卡组同源
exit_code=0
```

```text
$ node scripts/check-colors.mjs
✓ check-colors: 38 个文件无裸 hex / rgb / hsl，颜色只从令牌出口取
exit_code=0
```

### 4.2 后端与构建

```text
$ cd backend && python -m pytest -q
365 passed, 1 skipped, 61 warnings in 18.36s
exit_code=0
```

警告均为既有 `datetime.utcnow()` 弃用与 requests/urllib3 版本提示，未新增失败。

```text
$ cd frontend && npm run build
✓ built in 6.81s
exit_code=0
```

## 5. 编码与日志说明

- `logs/05_db_isolation.log` 由未设置 `PYTHONIOENCODING` 的 Python 输出，中文按 cp936 写入；**权威数据以 UTF-8 的 `data/db_isolation.json` 为准**。其余 Python 证据日志均显式使用 UTF-8。
- `logs/06_chrome_start.log` 的 ERROR 行来自 Chrome 自身（扩展注册表/GCM 连接），不是页面异常；页面级 `exceptionThrown`、`window.error`、`unhandledrejection` 为 0。
- `browser/failure_shots/` 的文件名按每次运行重新编号，跨运行不具全局时间顺序；以 `logs/` 中的运行序号为准。非失败状态的中间截图与最终集重复，已删除；完整运行日志全部保留。
