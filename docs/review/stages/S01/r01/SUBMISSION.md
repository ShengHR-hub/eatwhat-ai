# S01 / r01 提交说明

步骤：S01 身份与资源归属（F07）
轮次：r01
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
前置：S00/r01 由 Codex 独立复审 PASS；台账 S01 = READY

## 1. 本步范围与结论边界

本步只统一演示级身份解析与资源归属，关闭 S00 冻结的 F07：

- 所有需要用户上下文的 `/api/v1` 入口统一解析 `X-User-Id`；
- 缺失 / 空 / 非整数 / 非正整数 / 超出 SQLite INTEGER 范围：422，不回退用户 1；
- 未知用户：404；
- body / query 的 `user_id`、`host_user_id` 与请求头冲突：以请求头为准并记 `identity_conflict` 日志；
- 路径 `user_id` 与请求头冲突：沿用现有 403，并记录为待裁决设计缺口；
- 跨用户读取 / 写入路径、房间非成员访问、非房主操作、WebSocket 入口全部覆盖；
- 前端角色切换后，推荐、足迹、冰箱、偏好、红黑榜、房间请求统一携带新 `X-User-Id`，并清理旧角色缓存。

**未签 PASS；未修改台账；未创建 REVIEW.md；未开始 S02；未触碰 `/admin`、S10、LLM、统计大屏或 APK。** 本说明不构成独立验收结论。

## 2. 实际修改文件

后端：

| 文件 | 改动 |
| --- | --- |
| `backend/deps.py` | 唯一身份出口：`raw_user_id` / `parse_user_id` / `require_user_id` / `require_user` / `resolve_user_id` / `ensure_self` / `ensure_member`；统一 422/404/403 与冲突日志 |
| `backend/routers/auth_user.py` | profile / preferences / red-black 改为 `require_user` + `ensure_self`；demo-list 保持公开 |
| `backend/routers/recommend.py` | 请求头身份必填；body `user_id` 只参与冲突日志 |
| `backend/routers/eating_log.py` | checkin 请求头必填；stats 增加 `require_user` + `ensure_self` |
| `backend/routers/fridge.py` | GET/POST 路径增加 `ensure_self`；shopping-list 请求头必填 |
| `backend/routers/group_room.py` | 建房 `host_user_id` 不再压请求头；join 请求头必填；GET 房间仅成员可读；WS 增加用户存在、成员、路径/头冲突校验 |

测试：

| 文件 | 改动 |
| --- | --- |
| `backend/tests/test_identity_s01.py`（新增） | 35 条 S01 专项用例，覆盖公开入口、缺失/非法/未知身份、路径与 body 越权、房间 REST/WS、日志 |
| `backend/tests/test_identity_bounds_and_stock.py` | 旧的“无头放行”改为“无头 422”；其余用例补必填头 |
| `backend/tests/test_api.py` | 用户上下文调用补必填头；`test_single_recommend_defaults_to_user_1` 改为 `uses_header_user` |
| `backend/tests/test_eating_log.py` | stats/checkin 用例补必填头 |
| `backend/tests/test_fridge.py` | 冰箱读写与 shopping-list 用例补必填头 |
| `backend/tests/test_room.py` | 建房/join/快照用例补必填头 |

前端：

| 文件 | 改动 |
| --- | --- |
| `frontend/src/api/client.js` | 身份存储合法化；`setUserId` 拒绝非正整数；请求头始终携带当前身份；非法本地值告警并丢弃 |
| `frontend/src/api/index.js` | shopping-list / rooms create / join 不再在 body 携带 `user_id` / `host_user_id`，身份只走请求头 |
| `frontend/src/stores/persona.js` | 角色切换令牌，晚到的旧 profile 响应不得覆盖新角色；修正 demo 用户 `id` 字段 |
| `frontend/src/views/mobile/Fridge.vue` | 监听 `persona.userId`，切换后清空采购选择并重拉冰箱 |
| `frontend/src/views/mobile/Profile.vue` | 切换后同时刷新目录与冰箱摘要 |
| `frontend/src/views/mobile/Home.vue` | 切换后清空卡组/已划/已打卡记录并按新身份重取 |
| `frontend/src/views/mobile/Room.vue` | 适配 create/join 新签名（不再传 body 身份） |

未新增 TypeScript；前端新增/修改文件均为 `.js` / `.vue`。

## 3. 身份入口矩阵

机器可读版本：`data/identity_matrix.json`。

### 3.1 公开入口（无需身份）

| 入口 | 身份 | 说明 |
| --- | --- | --- |
| `GET /api/v1/users/demo-list` | 无 | 全局演示角色列表；带任意 `X-User-Id` 结果相同，不绑定当前用户 |
| `GET /api/v1/context/weather` | 无 | 环境上下文 |
| `GET /api/v1/catalog/dishes` | 无 | 只读目录 |
| `GET /api/v1/catalog/restaurants` | 无 | 只读目录 |
| `GET /health` | 无 | 健康检查 |

`POST /api/v1/auth/login` 仍为已删除状态（404/405），本步未复活。

### 3.2 私有入口

| 入口 | 身份来源 | 头/路径冲突 | 缺失/非法 | 未知 |
| --- | --- | --- | --- | --- |
| `GET /users/{user_id}/profile` | 路径 + 头 | 403 | 422 | 404 |
| `PUT /users/{user_id}/preferences` | 路径 + 头 | 403 | 422 | 404 |
| `POST /users/{user_id}/red-black-list` | 路径 + 头 | 403 | 422 | 404 |
| `POST /recommend/single` | 头；body `user_id` 非权威 | 头优先 + 日志 | 422 | 404 |
| `POST /logs/checkin` | 头；body `user_id` 非权威 | 头优先 + 日志 | 422 | 404 |
| `GET /logs/stats/{user_id}` | 路径 + 头 | 403 | 422 | 404 |
| `GET /fridge/{user_id}` | 路径 + 头 | 403 | 422 | 404 |
| `POST /fridge/{user_id}` | 路径 + 头 | 403 | 422 | 404 |
| `POST /fridge/shopping-list` | 头；body `user_id` 非权威 | 头优先 + 日志 | 422 | 404 |
| `POST /rooms/create` | 头；body `host_user_id` 非权威 | 头优先 + 日志 | 422 | 404 |
| `POST /rooms/{code}/join` | 头；body `user_id` 非权威 | 头优先 + 日志；重复 join 幂等 | 422 | 404 |
| `GET /rooms/{code}` | 头 + 成员身份 | 非成员 403 | 422 | 404 |
| `WS /ws/room/{room_code}/{user_id}` | 路径；可选 `X-User-Id` 必须一致 | 路径/头冲突 403；非成员 403；未知用户 403 | 路径必填 | 403 握手 |
| `WS START_SWIPING` | 路径成员 + 房主校验 | 非房主返回 `ERROR` | n/a | n/a |

当前没有以 query 参数承载身份的入口。

## 4. 冲突身份的最终行为

| 场景 | 最终行为 |
| --- | --- |
| 头缺失 / 空 / 非整数 / `0` / 负数 / `> 2^63-1` | **422**，不回退用户 1 |
| 头为未知正整数（如 999） | **404**，先校验头用户存在 |
| 头存在且路径 `user_id` 不同 | **403**；日志 `identity_rejected reason=path_header_mismatch` |
| body `user_id` / `host_user_id` 与头不同 | **按请求头身份执行**（通常 200）；日志 `identity_conflict field=... resolution=header` |
| 房间非成员 GET | **403**；日志 `reason=not_room_member`；不返回候选/成员/报告 |
| WS 未知用户 / 非成员 / 路径头冲突 | 握手 **HTTP 403**；日志记录具体 reason |
| WS 非房主开局 | 连接保留，返回 `ERROR: 只有房主能开团` |

### 设计缺口 S01-GAP-01（未自行改变产品语义）

- SSOT 只明确 body/query 身份“与请求头不一致时以请求头为准并记录”，没有明确**路径**身份冲突应返回 403 还是按头解析。
- S00/FINDINGS 与台账均记录“路径冲突 403 与按头解析尚需裁决”。
- 本步保留修复前已有的 403 语义，仅把“没带请求头时按路径放行”改为 422。
- 该缺口需要用户 / Codex 明确裁决后才能改变；本步未擅自改成另一种产品语义。

## 5. 正例与反例的状态码

### 5.1 正例

| 用例 | 结果 |
| --- | --- |
| 头=1 读/写用户 1 profile、preferences、red-black、fridge、stats、checkin | 200，资源属于用户 1 |
| 头=2 调 recommend / shopping-list / rooms create / join | 200，响应身份为 2 |
| 头=1 + body `user_id=2`：checkin | 200；用户 1 日志 3→4；用户 2 仍 2 |
| 头=1 + body `user_id=2`：recommend | 200；返回用户 1 画像（不含其黑榜/忌口菜） |
| 头=1 + body `user_id=2`：shopping-list | 200；结果等于头=1，不等同头=2 |
| 头=1 + body `host_user_id=2`：rooms/create | 200；`host_user_id=1`、`members=[1]` |
| 头=2 重复 join 同一房间 | 200；成员始终 `[1,2]` |
| 头=2 作为成员 GET 房间 | 200 |
| 公开 demo-list 无头 / 头=3 | 200 / 200，响应一致 |

### 5.2 反例

| 用例 | 结果 |
| --- | --- |
| 头=1 读 `/users/2/profile`、`/logs/stats/2`、`/fridge/2` | 403，目标数据前后完全一致 |
| 头=1 写 `/users/2/preferences`、`/users/2/red-black-list`、`POST /fridge/2` | 403，目标记录不变 |
| 缺 `X-User-Id`（12 个私有入口） | 422 |
| `X-User-Id` = `abc` / 空 / `0` / `-1` / `1.5` / `2^70` | 422 |
| `X-User-Id: 999`（12 个入口形态） | 404 |
| 头=2 在 join 前 GET 房间 | 403，不泄露候选名 |
| WS 未知用户 / 非成员 / 路径头冲突 | 握手 403 |
| WS 成员但非房主发 `START_SWIPING` | `ERROR: 只有房主能开团` |
| 目标用户写前/写后 | 偏好、冰箱、日志行数与内容一致 |

完整响应摘要见 `data/live_identity_probe.json` 与 `logs/18_live_identity_probe.log`。

## 6. 隔离库与数据保护

- 隔离运行库：`backend/eatwhat_s01_r01_iso.db`
  - 来源：`backend/eatwhat_dev_pre00_r02.db`
  - 复制前 SHA-256：`b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579`
  - 收尾 SHA-256：`b35e8b6015b7be50e736212f3b43b6e70932df2c05d98d22854cca334eb68884`
  - 收尾：`group_rooms=2`、`eating_logs=10`、`room_votes=0`
- 演示库 `backend/eatwhat.db`：`775da775…bd3a60b` 前后一致。
- S10 库 `backend/eatwhat_batch4.db`：`315eb3da…6918c28` 前后一致。
- 开发源库 `backend/eatwhat_dev_pre00_r02.db`：`b965e73e…706a579` 前后一致。
- 无 SQLite 旁文件。逐表行数、schema 指纹见 `data/db_protection.json`。

## 7. 测试与构建

- S01 红灯基线：24 failed / 11 passed（`logs/00_red_baseline.log`）。
- S01 专项：35 passed。
- 后端全量：**210 passed, 1 skipped**（`logs/20_backend_pytest.log`）。
- 前端构建：exit 0，775 modules（`logs/19_frontend_build_final.log`）。
- 四条界面/数据门禁均 exit 0：`logs/13_home_fit.log`、`logs/15_refill-fresh.log`、`logs/15_sandbox-sync.log`、`logs/16_check_colors.log`。
- 未新增 skip、未删除旧断言、未放宽容差。

## 8. 浏览器真实点击

使用独立 Chrome + CDP 真实鼠标事件，视口 390×844；操作顺序与截图见 `browser/`：

1. `/m/home` 用户 1 首页；
2. 底栏「我的」→ 用户 1 资料；
3. 「切换室友」→ 名单；
4. 名单第 2 行（养生阿明）→ 角色切换；
5. 「首页」→ 用户 2 推荐；
6. 「足迹」→ 用户 2 统计；
7. 「我的」→ 忌口预设「花生」→ PUT preferences；
8. 「黑榜菜品」→「移出」→ POST red-black-list；
9. 「虚拟冰箱」→ 用户 2 冰箱；
10. 「我的」→「多人干饭房间」→「创建房间」。

结果：13 次真实点击；切换前 7 个 API 请求头均为 1（错配 0）；切换后 17 个均为 2（错配 0）；profile 响应 `user_id=2`；fridge 响应 `user_id=2`；建房响应 `host_user_id=2`、`members=[2]`；console/未捕获异常 0，唯一失败资源是项目既有的 `/favicon.ico` 404。原始记录：`browser/browser_evidence.json`。

## 9. 未完成项与限制

1. S07 多人真实划卡、扫码、断线恢复仍为 `DEFERRED`；本步只覆盖 REST/WS 身份入口与非房主拒绝，不声称 S07 完成。
2. 路径冲突状态码（403）待在 S01-GAP-01 中裁决；本步未改变既有语义。
3. 前端非法本地身份在首次启动时会告警并回到演示角色 1；后端不对任何非法请求回退，二者边界已在 `client.js` 与 `deps.py` 注明。
4. `/admin`、S10 数据导入、LLM、统计大屏、APK 未执行、未验证。
5. 本包不修改 `docs/review/STAGE_STATUS.md`，不创建 `REVIEW.md`，不签 PASS，不开始 S02。

## 10. 停机声明

**SUBMITTED_FOR_REVIEW。** 证据包完成后已停止施工，等待 Codex 独立复审；不依据本包自行放行后续步骤。
