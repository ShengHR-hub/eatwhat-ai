# S05 / r01 提交说明

步骤：S05 首页与单人闭环
轮次：r01
状态：**已提交待审（SUBMITTED_FOR_REVIEW）**
日期：2026-10-27（Asia/Shanghai）
开发方：未签 PASS、未修改 `docs/review/STAGE_STATUS.md`、未创建/修改 `REVIEW.md`、未开始 S06

## 1. 本轮范围

在 PRE-00 开发运行库的隔离副本上，真实验证并修复：

- 首页首屏真实推荐；错误/空候选的稳定可见状态；
- 真实点击「换一批」的 dish_id 不重复、合格池耗尽空态、模式/角色/气泡切换后的排除集规则；
- 真实点击「就吃这个」→ 确认 → 打卡，足迹次数/金额更新，刷新后一致；
- 首页 → 足迹 → 我的 → 首页、页面刷新、我的 → 冰箱 → 返回；
- 演示角色切换后的请求头、推荐、偏好、足迹日志；
- 沙盒参数 → 请求 → 首页候选/顶卡/解释/抽屉 Top5 同源，快速连续改参取最后一次，恢复默认；
- 离开首页/关闭沙盒后的定时器、控制台与导航；
- F06 / F10（单人部分）/ F13 / N01 回归；
- PRE-00 开发运行库上的 `allergen_tags` 等 schema/API 兼容面。

**未触碰**：S06/S07/S08、`/admin`、S10 业务、APK、任何台账或审查结论。

## 2. 变更文件（仅 3 个，均无后端改动）

| 路径 | 变更 | 原因 | 影响面 | SHA-256 |
| --- | --- | --- | --- | --- |
| `frontend/src/views/mobile/Home.vue` | 新增 `onBeforeUnmount`：清除 320ms 沙盒防抖与 toast 计时器，并关闭 `algo.sandboxOpen` | 离开首页后防抖仍会补发 `/recommend/single`；抽屉开关存在 Pinia，返回首页会凭空重开且滚动锁不一致 | 仅 Home 卸载生命周期；不影响算法/接口 | `7ded94b886e7bc0cf0705bfff9e195cca5831c5a32da962f5855cbcae60b4563` |
| `frontend/src/api/client.js` | `status >= 500` 统一映射为「服务暂时开小差了，请稍后重试」；非字符串 4xx `detail` 不再 `JSON.stringify` 直出 | 首页/足迹会把 `Internal Server Error` 原文展示给用户 | 所有经 `api` 出口的页面；原始响应仍保存在 `ApiError.detail` | `54d56817f34d6a8cdc341547ccb43b5b9024fd8bba59d2e7df1a018e58b570d3` |
| `scripts/sandbox-sync.mjs` | 选择器 `.sandbox__used` → `.used__v`；新增「候选条 = 最后响应 dish_id」「抽屉 Top5 名称/分数 = 首页前五」「生效权重逐项 = params_used」断言 | 旧脚本读不到生效权重（恒为 `null`）却仍 PASS，未真正验证同源；属于过时门禁，按原验收语义修复并加强 | 仅门禁脚本 | `eb15d8054d4b54a5503e3dbc09c74943dfe0d7d93918d57d19063bd6900544b0` |

**后端**：`backend/` 下无任何文件变化；本轮未改 schema、接口、算法或数据库默认路径。PRE-00 已迁移的 `eatwhat_dev_pre00_r02.db` 只作复制来源。

**新增证据工具**（不算业务源码）：`data/capture_baseline.py`、`data/probe_db_isolation.py`、`data/browser_probe.mjs`、`data/probe_db_protection.py`、`data/probe_api_compat.py`。

## 3. 复现到的真实缺陷与修复

| 编号 | 级别 | 复现（修复前） | 根因 | 修复 | 复验 |
| --- | --- | --- | --- | --- | --- |
| S05-R01-01 | P2 | 拖沙盒滑块后 320ms 内离开首页，足迹页上仍补发 1 次 `/recommend/single`（`logs/22_browser_sandbox_pre_fix.log`） | Home 的 `reloadTimer`/`toastTimer` 在卸载时未清理 | `onBeforeUnmount` 清除两个计时器 | 最终套件 `quick_leave.late_requests_after_navigation=0` |
| S05-R01-02 | P2 | 开着沙盒离开首页再返回，抽屉自动重开，`body.overflow=''`（`logs/27_manual_sandbox_resurrection_pre_fix.log`） | `sandboxOpen` 存在 Pinia，跨路由保留 | 卸载时 `algo.toggleSandbox(false)` | 最终套件 `return_home={sandbox_open:false, body_overflow:""}` |
| S05-R01-03 | P2 | 受控 500 时首页展示原文 `Internal Server Error`（`logs/26_browser_faults_pre_fix.log`） | `client.js` 直接把响应 `detail` 当用户文案 | 5xx 统一可读文案；原文仅留 `detail` | 最终套件 `controlled_500.message=服务暂时开小差了，请稍后重试` |
| S05-R01-04 | 门禁 | `sandbox-sync.mjs` 打印 `used: null` 仍 PASS（`logs/13_sandbox_pre_fix.log`） | 选择器写成不存在的 `.sandbox__used`；Top5 同源未断言 | 修正选择器并补 3 类同源断言 | `logs/62_gate_sandbox_sync_final.log`，exit 0，`used` 为真实权重 |

## 4. 验收矩阵

### 4.1 用户指定流程

| 验收项 | 实际执行 | 结果 | 证据 |
| --- | --- | --- | --- |
| 真实浏览器 首页→足迹→我的→首页 | CDP 真实鼠标点击 Tab；等待 URL/标题/内容；再开/关沙盒重复 | PASS：`/m/footprint`→`/m/profile`→`/m/home`，标题与目标内容一致；console 0 error | `browser_evidence.json` `phases.nav.steps`；`browser/final/04…06` |
| 我的 → 冰箱入口 → 返回 | 真实点击 `.entry[href="/m/fridge"]`；内容出现“冰箱里有什么”；合成 Alt+Left 后退回 `/m/profile` | PASS | `phases.nav.steps`；`browser/final/08-nav-fridge.png` |
| 足迹/我的刷新后仍可用 | `Page.reload` 后等待内容 | PASS：`/m/footprint` 标题「足迹 · 食刻 EatWhat」，`/m/profile` 标题「我的 · 食刻 EatWhat」 | `phases.nav.steps` reload 项；`browser/final/05,07` |
| 首页首次加载真实推荐 | 真实请求 `X-User-Id:1`，200，24 条；候选条顺序 = 响应 dish_id 顺序 | PASS：首卡「低脂鸡胸饭」，问候「辣妹小赵，想吃点什么？」 | `phases.home.first_load` |
| 错误/空候选稳定状态、不展示原始 500 | CDP `Fetch` 受控注入 500 与 200 空候选；离线用 `Network.emulateNetworkConditions` | PASS：500 显示「没算出来 / 服务暂时开小差了，请稍后重试」；离线显示「后端没连上…」；空候选稳定显示「本轮推荐已看完」+ 重置 | `phases.faults.results`；`browser/final/26…30` |
| 「换一批」记录每批 ID、新批不得含已展示菜 | 真实点击 24 次「换一个」→「换一批」，循环至耗尽 | PASS：批次 24 / 24 / 10，合计 58 = 用户 1 外食合格池；批间交集为空；响应顺序 = 候选条顺序 | `phases.refill.batches` |
| 连续耗尽合格池明确空态、不伪造/不循环 | 最后一批划完后「换一批」返回 0 | PASS：显示「本轮推荐已看完」+「重置再看一轮」，不再提供「换一批」 | `phases.refill.final_state`；`browser/final/22` |
| 切换模式/角色/气泡后排除集按既有规则重置 | 重置后切「下厨」、再点「重口」气泡 | PASS：两次请求均无 `exclude_dish_ids`，模式/气泡正确 | `phases.refill.mode_switch/bubble_switch` |
| 「就吃这个」完成打卡，隔离库日志增加，足迹次数/金额更新，刷新一致 | 真实点击「就吃这个」→「确认就吃这个」 | PASS：打卡 200；足迹本周 8→9 次、花费 154→173（+¥19）；刷新后仍一致；隔离库 `eating_logs` 15→16，新增 `id=16,user=1,dish=19,cost=19` | `phases.checkin`；`data/db_protection.json` |
| 角色切换后请求头/推荐/偏好/日志属于当前角色 | 真实点击「切换室友」→「养生阿明」 | PASS：推荐与足迹请求头均为 `2`；页面昵称、人设、忌口、八维基因值全部等于用户 2；足迹次数/金额 = `/logs/stats/2`；切回用户 1 后恢复 | `phases.role`；`browser/final/14,15` |
| 沙盒参数 → 请求/候选/顶卡/解释同源 | 真实点击 λ 滑轨 + End 键到 2.0 | PASS：请求 `override_params.lambda_decay=2`；`params_used.lambda_decay=2`；候选条 = 响应 ids；抽屉 Top5 名称/分数 = 首页前五；顶卡名称/匹配度/解释 = 响应首项 | `phases.sandbox.single_change` |
| 快速连续改参最后一次生效 | β 先 Home 再 End（40ms 内） | PASS：只发 1 次请求，override β=1；生效值按 SSOT 归一化为 0.5714；抽屉「本次生效权重」= params_used | `phases.sandbox.rapid` |
| 恢复默认可用 | 真实点击「恢复默认参数」 | PASS：请求不带 `override_params`，`params_used` 回到 λ .5 / ω .5 / α .35 / β .25 / γ .2 / δ .2 | `phases.sandbox.reset` |
| 关闭/离开沙盒后无残留定时器/异常/导航故障 | 改参后 320ms 内 `history.back()` 离开首页；以及正常关闭后 450ms 再导航 | PASS：离开后迟到请求 0，console error 0，exception 0，返回首页不再弹抽屉 | `phases.sandbox.quick_leave/return_home` |

### 4.2 S00 验证矩阵 S05-C1…C9

| 用例 | 结果 | 关键数据 |
| --- | --- | --- |
| S05-C1 两档一屏 | PASS | 390×844：`scrollHeight=844`、`scrollWidth=390`；390×667：667/390；两档均无纵/横滚动 |
| S05-C2 按钮命中/不重叠 | PASS | 操作行与 Tab：844 `740–784` vs `792–836`（间隔 8，重叠 0）；667 `563–607` vs `615–659`（间隔 8，重叠 0）；换一个/就吃这个/Tab×3/首候选中心 `elementFromPoint` 全部命中自身 |
| S05-C3 连续换批/耗尽/重置 | PASS | 24+24+10=58，交集 0，耗尽空态，重置后 24 张且无 exclude |
| S05-C4 导航 + 沙盒后重复 | PASS | URL/标题/内容一致；console error 0；异常 0 |
| S05-C5 打卡→足迹 | PASS | 次数 +1、金额 +¥19；刷新一致；DB 行 `id=16` |
| S05-C6 角色切换 | PASS | 请求头 1→2→1；推荐/足迹/偏好全部按当前用户 |
| S05-C7 沙盒同源/最后一次/关闭重置 | PASS | 见 4.1；`params_used` 与抽屉逐项一致 |
| S05-C8 失败/空候选/4xx/断网 | PASS | 受控 500、离线、空候选三种状态均稳定可见；无原始 500；重试恢复 |
| S05-C9 F06/F10/F13/N01 | PASS | F06 两档几何；F10 单人同源；F13 耗尽与重置；N01 导航/卸载 0 异常 |

### 4.3 两档几何明细（最终套件）

| 元素 | 390×844 | 390×667 |
| --- | --- | --- |
| 状态行 `.home__head` | 26–70（44） | 26–70（44） |
| 控制面板 `.panel` | 92–232（140，17%vh） | 92–230（138） |
| 卡组 `.deck-host` | 244–696（452，54%） | 240–519（279，42%） |
| 顶卡 `.deck__top` | 244–666（422，**50%**） | 240–501（261，**39%**） |
| 候选条 `.candidates` | 704–732（28） | 527–555（28） |
| 操作行 `.deck-actions` | 740–784（44） | 563–607（44） |
| Tab 栏 `.tabbar` | 792–836（44） | 615–659（44） |
| 下一张露边 | 27px / 13px | 35px / 17px |
| 卡片正文溢出 | 0 | 0 |
| 最大单元素 | 452（54%） | 279（42%） |

两档 `greeting/panel/top_card/candidates/actions` 均完整位于视口内；`scrollWidth == clientWidth`；未使用 `overflow:hidden` 掩盖溢出。

## 5. 证据索引

| 证据 | 路径 |
| --- | --- |
| 基线 JSON / 日志 | `data/baseline.json`、`logs/00_baseline.log` |
| 与 S04/r03 源码漂移 | `logs/01_source_drift_vs_s04r03.log` |
| 隔离库来源 / 哨兵 | `logs/02_iso_db_provenance.log`、`logs/05_db_isolation.log`、`data/db_isolation.json` |
| 浏览器证据（最终） | `browser_evidence.json`、`browser/final/`（32 张） |
| 失败时刻截图 | `browser/failure_shots/`（15 张，见 `browser/INDEX.md`） |
| DB 前后状态 | `data/db_protection.json`、`logs/52_db_protection_final.log`、`data/pre_final_counts.json` |
| API 兼容面 | `data/api_compat.json`、`logs/49_api_compat.log` |
| 门禁/构建/测试 | `logs/60…65`（见 `CHECKS.md`） |
| 机器可读汇总 | `validation.json` |

## 6. 未通过、未执行与遗留

- **未通过项**：无。最终浏览器套件 7/7 PASS；四道门禁 exit 0；后端 365 passed / 1 skipped；前端 build exit 0。所有验收动作均为 CDP 真实鼠标/键盘输入与真实 HTTP；API/数据库探针只作补充，不替代浏览器操作。未删除旧断言、未放宽门禁；`sandbox-sync.mjs` 只做了加强（新增同源断言）。
- **未执行项及原因**：
  - 在线天气（高德 API）：无 `AMAP_API_KEY`，只验离线兜底与「离线」角标；不声称在线通过。
  - 冰箱增删改/采购清单：属于 S03 已 PASS 的范围，本步只验「我的→冰箱入口→返回」。
  - S06/S07 多人协议与真实划卡、S08 总回归、`/admin`、S10、APK：按台账未开放。
  - APK/真机：无设备与 SDK，不在本步。
- **遗留（未在本步扩大范围）**：
  - N02 双校区 `campus` 过滤未实现（S06/BRIDGE-10）。
  - N03 软删除过滤未实现（需要同时覆盖推荐、目录、S06 房间；当前三库 `deleted_at` 非空行=0）。
  - N05 `/health` 仍报 2.3.2、演示库仍是旧 schema（S08/BRIDGE-10；本步只用隔离运行库）。
  - 沙盒参数变化会**保留**已划集合（既有规则；Findings F13 只要求模式/角色/气泡重置）。关闭抽屉不会取消已排队的参数应用（320ms 后应用一次），这是 F10 的既有设计；卸载会取消。
- **受控错误与浏览器噪声**：
  - `faults` 阶段网络记录中的 500 与 `ERR_INTERNET_DISCONNECTED` 均为 CDP 主动注入；对应 console 的 2 条 `log-error` 是浏览器网络层记录，不是未处理异常。受控 500 不来自后端，后端日志无 5xx/Traceback。
  - `logs/06_chrome_start.log` 含 Chrome 自身的 GCM/扩展注册 ERROR，页面 `Runtime.exceptionThrown`、`window.error`、`unhandledrejection` 均为 0。

## 7. 停手声明

本包提交后立即停手：不修改台账、不创建/修改 REVIEW、不签 PASS、不开始 S06，等待 Codex 独立复审。
