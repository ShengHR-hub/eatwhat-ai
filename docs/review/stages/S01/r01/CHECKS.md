# S01 / r01 检查记录（CHECKS）

日期：2026-10-26（Asia/Shanghai）
所有命令均在本机执行；日志在 `logs/`，数据在 `data/`，浏览器证据在 `browser/`。

## 1. 命令总表

| # | 命令 | cwd | 开始 | 结束 | 退出码 | 结果 | 日志 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `python -m pytest -q -p no:cacheprovider tests/test_identity_s01.py` | `D:/EatWhat/backend` | 未捕获（日志完成于 00:14:33） | 2026-10-26 00:14:33 | **1（预期红灯）** | 24 failed, 11 passed | `logs/00_red_baseline.log` |
| 2 | 同 #1（实现后） | `D:/EatWhat/backend` | 未捕获（在全量前单独执行） | 未捕获 | 0 | 35 passed | 已并入 #3 |
| 3 | `python -m pytest -q -p no:cacheprovider` | `D:/EatWhat/backend` | 00:23:08 | 00:23:25 | **0** | **210 passed, 1 skipped** | `logs/20_backend_pytest.log` |
| 4 | `npm run build` | `D:/EatWhat/frontend` | 00:23:28 | 00:23:37 | **0** | 775 modules transformed，built in 7.03s | `logs/19_frontend_build_final.log` |
| 5 | `node scripts/home-fit.mjs` | `D:/EatWhat` | 00:19:34 | 00:19:55 | **0** | 390×844 / 390×667 两档 PASS，overlap 0 | `logs/13_home_fit.log` |
| 6 | `node scripts/refill-fresh.mjs` | `D:/EatWhat` | 00:19:58 | 00:20:17 | **0** | 排除 24、返回 24 道新候选 | `logs/15_refill-fresh.log` |
| 7 | `node scripts/sandbox-sync.mjs` | `D:/EatWhat` | 00:20:17 | 00:20:20 | **0** | 请求 1→2，卡组与沙盒同源 | `logs/15_sandbox-sync.log` |
| 8 | `node scripts/check-colors.mjs` | `D:/EatWhat` | 00:20:20 | 00:20:20 | **0** | 38 文件，无裸 hex/rgb/hsl | `logs/16_check_colors.log` |
| 9 | `node docs/review/stages/S01/r01/browser/run_role_switch.mjs` | `D:/EatWhat` | 00:30:41 | 00:31:03 | **0** | 13 次真实点击；切换前 0 个错配、切换后 17 个 API 请求全部 `X-User-Id:2`、0 错配；非 favicon console/异常 0 | `logs/17_browser_role_switch.log` |
| 10 | `python docs/review/stages/S01/r01/data/live_identity_probe.py` | `D:/EatWhat` | 00:31:11 | 00:31:12 | **0** | 19 个 HTTP 用例 + 4 个 WS 用例，结果符合契约 | `logs/18_live_identity_probe.log` |
| 11 | `python docs/review/stages/S01/r01/data/build_manifest.py` | `D:/EatWhat` | 未捕获 | 00:25:32 | **0** | 144 项，fingerprint `3caa7db0…c4ad29` | `data/build_manifest.stdout.txt` |

> 红灯保留：`00_red_baseline.log` 是修复前执行产生的真实失败，不是事后伪造；修复后同一文件 35 条全部通过。

## 2. 后端专项与全量

- 专项文件：`backend/tests/test_identity_s01.py`，35 条。
  - 公开入口：demo-list / weather / catalog / health 无身份 200；demo-list 带不同身份结果完全一致。
  - 缺失身份：12 个私有入口全部 422。
  - 非法身份：`abc`、空串、`0`、`-1`、`1.5`、`2^70` 全部 422。
  - 未知身份：12 个入口形态全部 404。
  - 路径越权：profile / preferences / red-black / stats / fridge GET / fridge POST 全部 403，目标用户偏好、冰箱、日志前后一致。
  - body 冲突：checkin / recommend / shopping-list 全部按请求头身份执行，`user_id=2` 未写入用户 2；冲突日志存在。
  - 建房：`header=1 + body host_user_id=2` 落库房主为 1，成员只有 1；冲突日志 `field=host_user_id`。
  - 房间：非成员 GET 403 且不泄露候选名；重复 join 幂等；非房主开局返回 ERROR。
  - WebSocket：未知用户、非成员、路径/请求头冲突均握手 403；合法成员可连接并收到 `ROOM_STATE`。
- 全量：**210 passed, 1 skipped, 507 warnings**。warning 均为既有 `datetime.utcnow()` 弃用与 requests/urllib3 版本提示；skip 为既有 Windows 符号链接权限用例。
- 未新增 skip、未删除旧断言、未扩大容差；旧测试仅补上现在必填的 `X-User-Id`，原断言保留。

## 3. 前端构建与门禁

- `npm run build`：exit 0，775 modules，7.03s。
- `home-fit`：
  - 390×844：card 422px（50%），actions 740–784，tab 792–836，overlap 0。
  - 390×667：card 261px（39%），actions 563–607，tab 615–659，overlap 0。
- `refill-fresh`：exclude 24，返回 24，新首卡「藜麦鸡胸沙拉」。
- `sandbox-sync`：请求 1→2，卡组与沙盒用同一批参数。
- `check-colors`：38 个文件 exit 0。

## 4. 真实浏览器操作

脚本 `browser/run_role_switch.mjs` 使用 CDP `Input.dispatchMouseEvent` 点击真实屏幕坐标；未用 `page.evaluate` 改 DOM 或写状态。视口 390×844，DPR 2。

操作顺序：

1. 打开 `/m/home`，确认用户 1 首页与卡组（`01_home_user1.png`）。
2. 真实点击底栏「我的」，确认用户 1 资料（`02_profile_user1.png`）。
3. 真实点击「切换室友」，打开名单（`03_switch_menu.png`）。
4. 真实点击名单第 2 行（养生阿明），等待 localStorage、资料卡、请求头全部变为 2（`04_profile_user2.png`）。
5. 真实点击「首页」，确认问候语与推荐均属于用户 2（`05_home_user2.png`）。
6. 真实点击「足迹」，确认统计请求与页面（`06_footprint_user2.png`）。
7. 真实点击「我的」→ 预设「花生」，触发 `PUT /users/2/preferences`（`07_preferences_user2.png`）。
8. 真实点击「黑榜菜品」→「移出」，触发 `POST /users/2/red-black-list`（`08`、`09`）。
9. 真实点击「虚拟冰箱」，确认 4 件食材（`10_fridge_user2.png`）。
10. 真实点击「我的」→「多人干饭房间」→「创建房间」，确认建房身份与房主均为 2（`11`、`12`）。

Network 摘要：

- 切换前 7 个 API 请求全部 `X-User-Id: 1`。
- 切换后 17 个 API 请求全部 `X-User-Id: 2`；错配 0。
- 切换后包括 `GET /users/2/profile`、`GET /fridge/2`、`POST /recommend/single`、`GET /logs/stats/2`、`PUT /users/2/preferences`、`POST /users/2/red-black-list`、`POST /rooms/create`。
- 响应核对：profile `user_id=2`；fridge `user_id=2`；rooms/create `host_user_id=2`、`members=[2]`。
- console error 0、未捕获异常 0、`Log.entryAdded` 非 favicon error 0。唯一失败资源是项目既有的 `/favicon.ico` 404（与身份无关，已单独记录在 `browser_evidence.json` 的 `failed_resources`）。

原始操作与网络：`browser/browser_evidence.json`。

## 5. 隔离库真实 HTTP / WS 探针

`data/live_identity_probe.json`（后端指向 `backend/eatwhat_s01_r01_iso.db`）：

| 用例 | 状态 | 结果 |
| --- | --- | --- |
| `header1_reads_user2_profile` | 403 | 路径冲突，未返回用户 2 数据 |
| `header1_reads_user2_stats` | 403 | 同上 |
| `header1_reads_user2_fridge` | 403 | 同上 |
| 缺失 / 空 / `abc` / `0` / `-1` / `2^70` | 422 | 六类非法身份均明确拒绝 |
| `unknown_header=999` | 404 | 用户不存在 |
| `recommend_body_conflict` | 200 | 按用户 1 返回，推荐前 5 名符合用户 1 画像 |
| `checkin_body_conflict` | 200 | 用户 1 日志 3→4；用户 2 保持 2 |
| `shopping_body_conflict` | 200 | 按用户 1 冰箱计算 |
| `room_create_body_host_conflict` | 200 | `host_user_id=1`，`members=[1]` |
| `non_member_get_room` | 403 | 不泄露房间候选 |
| `join_as_user2` / `repeat_join_user2` / `join_body_conflict` | 200 | 成员始终 `[1,2]`，重复 join 不重复 |
| `member_get_room` | 200 | 成员可读 |
| WS 非成员 / 路径头冲突 | 握手 403 | `HTTP 403` |
| WS 合法成员 | 接受 | 首帧 `MEMBER_SYNC`，成员含 1、2 |
| WS 非房主开局 | ERROR | `只有房主能开团` |
| 公开 demo-list 无头 / 头 3 | 200 / 200 | 响应完全一致，4 个角色 |

服务端日志中的身份事件（`logs/11_backend_uvicorn.log`）包含 `missing_header`、`invalid_header`、`unknown_user`、`path_header_mismatch`、`identity_conflict`（`field=user_id` / `field=host_user_id`）、`not_room_member`、`unknown_ws_user`、`ws_path_header_mismatch`。

## 6. 未执行项

- S07 多人真实划卡 / 扫码 / 断线恢复：继续 `DEFERRED`，本步未执行，未签通过；只验证 REST/WS 身份入口与非房主拒绝。
- `/admin`、S10 数据导入、LLM、统计大屏、APK：未触碰。
- 未修改 `docs/review/STAGE_STATUS.md`；未创建 `REVIEW.md`；未签 PASS。
