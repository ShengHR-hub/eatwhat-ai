# S06 / r02 整改提交说明

提交日期：2026-10-27（Asia/Shanghai）
状态：**已提交，待 Codex 独立复审**。开发方未签 PASS，未创建/修改 `REVIEW.md`，未修改 `docs/review/STAGE_STATUS.md`。r01 包原样保留，未覆盖。

## 1. 背景与范围

r01 独立复审为 **FAIL（CHANGES_REQUIRED）**，两项 P2：

- **P2-S06-01**：`room_sweeper()` 遇到一次扫描级异常后 `return`，后续周期永久停止。
- **P2-S06-02**：既有成员在 `SWIPING/FINISHED` 重复 `join` 仍返回 200，违反 join 仅限 `WAITING`。

r02 只修这两项，并重跑 S06 回归、真实 REST/WS、重启、迁移、数据库保护。未改 S07 UI、`/admin`、S10 数据或后续步骤。

## 2. 代码整改

### P2-S06-01：周期任务异常后继续

位置：`backend/routers/group_room.py`。

- `room_sweeper(interval=None)`：每轮 `settle_overdue_rooms()` 外层捕获非取消异常，记录 `room_sweeper_failed` 后 **`continue`**，不再 `return`；`asyncio.CancelledError` 继续向上传播。
- 单房间失败仍由 `settle_overdue_rooms()` 内部逐房隔离；同轮其它房间继续。
- 成功结算增加 `room_sweep_settled count=... room_codes=[...]` 审计日志；为让应用 logger 的 INFO 真正进入服务日志，新增独立 `StreamHandler`、`propagate=False`（uvicorn 只配置自身 logger）。
- 新增 `interval` 参数仅用于测试注入短周期；生产默认仍为 `SETTLE_SWEEP_SECONDS=5`。

### P2-S06-02：join 只允许 WAITING

位置：`backend/routers/group_room.py::join_room`。

- 在房间锁内、处理校区/幂等成员/容量之前，统一检查 `room.status == WAITING`；**既有成员与新成员一律适用**。
- `SWIPING`/`FINISHED` 的重复 join 返回 **400**“这一局已经开始了，等下局吧”，不返回成功快照，不写成员/候选/票/报告。
- 恢复读取改由 `GET /rooms/{code}` 与 WS `ROOM_STATE` 承担；SSOT v2.3.6 已补此句。
- 既有成员在 WAITING 的幂等 join 行为不变。

### SSOT

`MASTER_SPEC.md` v2.3.6 两处澄清，不升版本：

1. join 只允许 WAITING，既有成员也不例外；SWIPING/FINISHED 一律 400，恢复走 GET/ROOM_STATE。
2. 周期任务单次扫描级异常只记录并继续下一周期；单房间失败隔离。

## 3. 新增回归

`backend/tests/test_s06_room_contract.py` 新增 3 条：

| 用例 | 覆盖 |
| --- | --- |
| `test_sweeper_continues_after_scan_error` | 第一次 `settle_overdue_rooms()` 抛异常，第二次成功并广播；`calls >= 2` |
| `test_sweep_isolates_single_room_failure` | 两间过期房，一间 `_settle_if_due` 抛错，另一间仍返回 payload |
| `test_existing_member_join_rejected_after_start_and_finish` | 既有成员 SWIPING/FINISHED join 均 400；成员/候选/票/报告无副作用 |

## 4. 真实隔离服务复验

### P2-S06-02

`data/p2_join_state.json`（房间 **381152**）：

- SWIPING 既有成员 join → **400**；FINISHED 既有成员 join → **400**；FINISHED 房主 join → **400**。
- 成员始终 `[1,2]`；候选 ID 不变；票数 0；赢家/报告不变；`no_side_effects=true`。
- 日志：`logs/09b_p2_join_state.log`。

### P2-S06-01

`data/p2_sweeper_fault.json`（房间 **970002**）：

- 直接向 r02 隔离库插入 `SWIPING`、已过截止的房间；**没有 WS START，因此没有内存定时器；没有房间客户端**。
- 独立 `sqlite3 BEGIN EXCLUSIVE` 持锁 30s，覆盖至少两轮 5s sweeper；服务日志先出现 `room_sweeper_failed`，锁释放后出现 `room_sweep_settled` 且包含 `970002`。
- 释放后不再向房间发任何 HTTP/WS，只读 DB：`status=FINISHED`、`settled_at=2026-10-27 15:31:18` > `deadline_at=15:30:50`、`winner_dish_id=101`、`vote_count=0`。
- `server_log.failure_before_recovery=true`、`room_code_in_settled_log=true`。
- 日志：`logs/09c_p2_sweeper_fault.log`、`logs/05_backend_start.log`。

## 5. 回归结果

| 项 | 结果 | 日志 |
| --- | --- | --- |
| S06 定向（room/identity/s02/s06） | **171 passed**（9.89s），exit 0 | `logs/06_s06_targeted_tests.log` |
| 后端全量 | **391 passed, 1 skipped**（18.29s），exit 0 | `logs/07_backend_full_tests.log` |
| 前端 build | 775 modules，built in 5.21s，exit 0 | `logs/08_frontend_build.log` |
| 颜色门禁 | 38 个文件通过，exit 0 | `logs/08b_check_colors.log` |
| 完整 REST/WS 回归 | **25 步全过** | `logs/09_rest_ws_flow.log`、`data/rest_ws_sequence.json` |
| 进程重启 | 重启后、任何客户端请求前 DB 已 FINISHED；1 票 | `data/restart_flow.json`、`logs/10c/10d` |
| 迁移 | 预启动创建唯一索引；复跑幂等 | `logs/02_migration.log`、`logs/02b...` |
| 启动前目标探针 | 22/22，空库 | `logs/04_db_target_probe.log` |
| 运行后目标探针 | exit 0 | `logs/04b_db_target_probe_post.log` |
| ω 手算 | A=60；B=24/46/68；赢家 A/A/B | `logs/12_omega_matrix_handcalc.log` |
| validation | **22/22** | `logs/14_build_validation.log` |

## 6. 数据库保护

| 库 | 结果 |
| --- | --- |
| `backend/eatwhat.db`（演示） | SHA `775da775…a60b` 不变 |
| `backend/eatwhat_batch4.db`（S10） | SHA `315eb3da…8c28` 不变 |
| `backend/eatwhat_dev_pre00_r02.db` / `_pre00.db` | SHA `b965e73e…a579` 不变 |
| `backend/eatwhat_s05_r01_iso.db` | SHA `8179f9fd…33ce` 不变 |
| **`backend/eatwhat_s06_r01_iso.db`** | **SHA `521d7380…b48b4` 不变**（9 房/51 票，r01 证据原样） |
| `backend/eatwhat_s06_r02_iso.db` | 唯一写入目标；最终 SHA `09db91f8…`，32 房/151 票（含 r02 重复回归/故障注入的隔离房间） |

r02 隔离库来自 `eatwhat_dev_pre00_r02.db`（SHA 相同），已加 `room_votes` 唯一索引与 `s06_fixture_v1`（思源 6 店 12 菜、建大 6 店 12 菜；20 家种子店保持 NULL）。fixture 未写入演示库或种子脚本。

## 7. 已知限制

- r02 隔离库包含多次复跑/故障注入的房间（32/151），证据 JSON 各自绑定最终房间码（381152、970002、617709 等）；这是隔离测试数据，不是演示数据。
- 演示版 OUT_DINING 在 S10 回填前仍 0 候选（种子 20 店 NULL）；下厨共享正常。
- S07 真实划卡/扫码/真机仍未验收；本轮未用浏览器点击替代 REST/WS。
- 唯一索引迁移只对 r02 隔离库执行；其他运行时库需显式运行迁移脚本。
- `/health` 应用版本串仍为历史 `2.3.2`；SSOT 已 v2.3.6。
- 1 skip 为既有符号链接/硬链接环境用例；10 warnings 为既有弃用/依赖/缓存提示。

## 8. 交付物

`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、`validation.json`、`SOURCE_MANIFEST.json`（最后生成）、`logs/`、`data/`。r01 包未改。

未创建/修改 `REVIEW.md`，未修改 `STAGE_STATUS.md`，未签 PASS；等待 Codex 独立复审。
