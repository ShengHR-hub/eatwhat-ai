# S06 / r01 提交说明 —— 多人后端协议与参数链

提交日期：2026-10-27（Asia/Shanghai）
状态：**已提交，待 Codex 独立审查**。开发方未签 PASS，未创建/修改 `REVIEW.md`，未修改 `docs/review/STAGE_STATUS.md`。

## 1. 本轮范围与已确认决策

只做 S06：多人房间 REST/WS、群组初筛、房间参数链、结算/恢复与对应测试。未实现 S07 真实划卡 UI，未触碰 `/admin`、S10 数据业务或后续步骤。

用户 2026-10-27 裁决（已按此施工）：

| 编号 | 决策 |
| --- | --- |
| D1 | A′：新房间必须明确校区；join 必须匹配；外食候选严格同校区，NULL 门店排除；历史 NULL 房间仅 WAITING 首 join 绑定并同事务重算，0 候选回滚拒绝 |
| D2 | A：前端只做默认 `SIYUAN` 最小透传，不做全局校区切换 UI |
| D3 | A：拒绝客户端 `TIMEOUT`，只收四个 SSOT 枚举 |
| D4 | A：缺席=内部 `TIMEOUT=60`；全员 0 票仍结算；VETO 仍为掩码 |
| D5 | A：重复投票 last-write-wins；新增 `room_votes(room_code,user_id,dish_id)` 唯一索引 |
| D6 | A：WAITING 新成员 join 后按全员约束重算；1–9 道如实返回；0 道允许加入但禁止开局 |
| D7 | A：建房时冻结有效 ω，只存 `omega_group`；结算只读快照 |
| D8 | A：启动扫描 + 5 秒周期兜底；所有结算入口共用原子 claim |
| D9 | 升 SSOT 至 v2.3.6，并同步 `AGENTS.md` 的版本引用 |

SSOT：`MASTER_SPEC.md` 已升 **v2.3.6**，新增 S06 小节（校区严格过滤、成员重算、投票/缺席、重复票、ω 冻结、原子结算与恢复、已知限制、数据边界、前端范围）。`AGENTS.md` 第 5 行版本引用已改为 v2.3.6。

## 2. 变更路径

| 路径 | 变更 |
| --- | --- |
| `backend/schemas.py` | `CampusType`；create/join 必填 `campus`；`RoomSnapshot` 增加只读 `campus`、`omega_group` |
| `backend/routers/group_room.py` | 严格校区校验/409；join 全员重算；历史 NULL 房间绑定；ω 建房冻结；客户端 TIMEOUT 拒绝；per-room 锁；写前重查截止；原子结算；启动/周期扫描；快照与 `MEMBER_SYNC` 带候选 |
| `backend/algorithms/group_recommender.py` | `shortlist_candidates` 增加 `campus`；外食严格同校区，NULL/无门店排除；公式未改 |
| `backend/models.py` | `RoomVote` 增加 `(room_code,user_id,dish_id)` 唯一约束 |
| `backend/scripts/migrate_s06_room_contract.py` | 新增幂等迁移：重复行预检、唯一索引、受保护库拒绝 |
| `backend/main.py` | lifespan 启动扫描 + 5 秒周期兜底，关闭时取消任务 |
| `backend/tests/conftest.py` | 新增测试专用 `campus_seed`（只改内存库，不写种子脚本/演示库） |
| `backend/tests/test_room.py` | 补 campus；ω 快照断言改为只存 `omega_group` |
| `backend/tests/test_identity_s01.py`、`test_s02_numeric_bounds.py` | 仅补 campus 字段，保留原身份/边界断言 |
| `backend/tests/test_s06_room_contract.py` | 新增 23 条 S06 专项 |
| `frontend/src/stores/mode.js`、`api/index.js`、`views/mobile/Room.vue` | 默认 `SIYUAN` 透传；无 UI、无颜色/样式改动 |
| `MASTER_SPEC.md`、`AGENTS.md` | v2.3.6 契约与版本引用 |

没有新增数据库字段；`group_rooms.campus/algo_params/deadline_at/settled_at` 均为既有字段。唯一 schema 变更是 `room_votes` 唯一索引。

## 3. 验收条目逐项

| S06 要求 | 结果 | 证据 |
| --- | --- | --- |
| 建房、6 位数字码、预算、校区、10 候选、三状态 | 通过 | `rest_ws_sequence.json` `create_siyuan_room`：码 309006，10 候选，campus SIYUAN，ω 0.9；`test_create_requires_campus_and_echoes_snapshot` |
| 建房房主自动入组 | 通过 | 建房响应 members=[1]；`test_create_requires_campus_and_echoes_snapshot` |
| join 是唯一成员入口且幂等 | 通过 | `join_siyuan_member` members=[1,2]；重复 join 仍 [1,2]；`test_join_cross_campus_409_and_idempotent` |
| WS 不写成员、未 join/非成员 403 | 通过 | `ws_non_member_403` 403；`test_ws_connect_does_not_write_members` |
| 跨校区 join 409 | 通过 | `cross_campus_join_409` 409，成员未写；`test_join_cross_campus_409_and_idempotent` |
| 成员变化后按全员硬约束重算 | 通过 | `test_join_recomputes_all_member_constraints`：黑名单菜移除，候选补足 10，辣椒忌口全部不出现；`MEMBER_SYNC` 带候选 |
| 票属于本房候选/正确阶段 | 通过 | WAITING、非候选、TIMEOUT、截止后均 ERROR；`test_duplicate_vote_last_write_wins_and_timeout_rejected`、`test_vote_rejected_in_waiting_and_after_deadline` |
| 非房主非法动作、非法状态转移 | 通过 | 非房主 START ERROR；重复 START ERROR；join after START 400；`test_start_guarded_by_candidates_and_state` |
| 重复投票 | 通过 | 同人同菜 LIKE→SUPER_LIKE，进度仍 1，DB 一行；`duplicate_vote_last_write_wins` |
| 截止后/完成后改票 | 通过 | 截止后 ERROR；完成后 ERROR；`late_vote_rejected`、`test_room.py::test_votes_after_finish_are_rejected` |
| 15 秒服务端唯一时间事实 | 通过 | `START_SWIPING` 下发 `deadline_at/remaining_ms`；实际 14989ms；`host_start` |
| 全员完成/超时结算 | 通过 | 早结算 `consensus_reveal`；超时 `zero_votes_settle`、`late_vote_rejected` |
| 全断开/进程重启后恢复或结算 | 通过 | `restart_flow`：重启后、任何客户端请求前，DB 已 FINISHED（settled_at 19:16:14 > deadline 19:16:02，1 票） |
| GET/WS 重连快照恢复 | 通过 | `snapshot_after_finish`、`reconnect_room_state_restored`：成员、候选、本人票、进度、截止、校区、ω、赢家、报告 |
| 重复结算幂等 | 通过 | `repeat_get_idempotent`：20 唯一票，报告/赢家不变；`test_settlement_idempotent_and_snapshot_recovery`、`test_settle_race_writes_once` |
| ω 两端/中间独立手算 | 通过 | `omega_matrix.json` + `test_fixed_omega_matrix_room_level`：A=60；B=24/46/68；赢家 A/A/B |
| ω 参数流可追溯 | 通过 | `omega_frozen_at_create`：快照 0.7，建房后 DB 改 0.1，结算仍 0.7；`omega_request_override` 0.2；`single_override_isolated` |
| 真实 REST/WS 使用隔离库 | 通过 | `db_target_probe.json`（pre）21 项；`db_target_probe_post.json`（post）；`db_protection.json` |
| 不写演示库/S10/开发源库 | 通过 | 五份受保护库 SHA 前后一致，`group_rooms/room_votes` 仍 0 |
| 不用浏览器代替后端验收 | 遵守 | 本轮无浏览器；S07 真实交互仍未验收 |

## 4. ω 参数链与冻结

| 时点 | 行为 |
| --- | --- |
| create | 有效 ω = 请求 `override_params.omega_group` → `algo_configs.default_production.omega_group` → 默认 0.5；写入 `group_rooms.algo_params={"omega_group": x}`，日志记录来源 |
| join | 不改 ω；只做校区校验、成员落库、全员候选重算 |
| START | 不改 ω；只写 status/deadline |
| SUBMIT_VOTE | 不改 ω |
| settle | 只读建房快照；报告写 `omega_group` |
| 重连/重启 | 快照/DB 恢复；旧房间缺快照才回退 DB → 默认并告警 |
| 单人 override | 请求级，不写 `algo_configs`、不改已建房间；单人推荐不消费 ω |

固定矩阵（独立手算，不调用生产函数）：

| 菜品 | R(u1,u2,u3,u4) | mean | min | ω=0 | ω=0.5 | ω=1 |
| --- | --- | --- | --- | --- | --- | --- |
| A（全员 LIKE，先验 0） | 60,60,60,60 | 60 | 60 | 60 | 60 | 60 |
| B（两 SUPER_LIKE 两 PASS，先验 100/100/0/0） | 112,112,24,24 | 68 | 24 | 24 | 46 | 68 |

赢家：ω=0 → A；ω=0.5 → A；ω=1 → B。VETO 掩码另测：全员 VETO → winner=None、has_consensus=False。

## 5. REST/WS 序列摘要

主序列（25 步，`data/rest_ws_sequence.json`）：

- SIYUAN 房间 309006：10 候选全部 `S06思源固定菜*`（ID 101–112），无建大/NULL 门店；JIANDA 房间 221281：10 候选全部 `S06建大固定菜*`（ID 113–124）。
- 跨校区 join 409；join 后 members=[1,2]、候选重算仍 10。
- 非成员 WS 403；非房主 START 被拒；重复票进度 1；TIMEOUT/非候选票 ERROR。
- 双方 10 票后早结算，赢家 103（`S06思源固定菜03`），group_score 81.51，ω=0.9；20 条唯一票。
- GET 两次报告/赢家不变；重连 `ROOM_STATE` 恢复本人 10 票、进度 10、campus、ω。
- ω 冻结：建房快照 0.7，建房后 DB 改 0.1，结算仍 0.7；override 0.2 优先；单人 override 0.95 后 DB 仍 0.1、房间仍 0.2。
- 全员 0 票：超时结算，赢家 103，存储票 0；全员 VETO：无赢家、无共识、10 道全否决。
- 截止后投票：ERROR“这一局已经结束了，不能再改票”。

重启序列（`data/restart_flow.json`）：房间 488981，开局后投 1 票 LIKE，强停服务、等待过截止、重启；在**任何 HTTP/WS 请求之前**只读 DB：status=FINISHED、settled_at=19:16:14、deadline=19:16:02、vote_count=1、report 10 道；随后 GET 快照一致。

## 6. 隔离库与数据库保护

| 库 | 处理 | 前后状态 |
| --- | --- | --- |
| `backend/eatwhat.db`（演示） | 只读 | SHA `775da775…a60b` 不变；rooms/votes=0/0 |
| `backend/eatwhat_batch4.db`（S10） | 只读 | SHA `315eb3da…8c28` 不变；rooms/votes=0/0 |
| `backend/eatwhat_dev_pre00_r02.db`（开发源） | 只读复制 | SHA `b965e73e…a579` 不变；rooms/votes=0/0 |
| `backend/eatwhat_dev_pre00.db` | 只读 | SHA `b965e73e…a579` 不变；rooms/votes=0/0 |
| `backend/eatwhat_s05_r01_iso.db` | 只读 | SHA `8179f9fd…33ce` 不变；rooms/votes=0/0 |
| `backend/eatwhat_s06_r01_iso.db` | 唯一写入目标 | 复制自 dev_pre00_r02（同 SHA），加唯一索引与 `s06_fixture_v1`；最终 9 房间/51 票 |

隔离库 fixture：思源 6 店 12 菜、建大 6 店 12 菜，`source_dataset=s06_fixture_v1`、`is_synthetic=1`；20 家种子店保持 `campus=NULL`，用于证明 NULL 排除。fixture 未写入演示库或种子脚本。

唯一索引迁移只对显式 `--db` 的非受保护副本执行；本轮只迁移 `eatwhat_s06_r01_iso.db`。现有运行时库需由运维显式执行 `backend/scripts/migrate_s06_room_contract.py`；演示库、S10 库、开发源库未被迁移。未迁移库上应用仍按“先 update、无行再 insert、冲突重试”工作，但跨进程唯一性保证只在执行迁移后生效。

## 7. 测试与门禁

| 命令 | 结果 | 日志 |
| --- | --- | --- |
| S06 专项（room/identity/s02/s06） | 168 passed，exit 0 | `logs/06_s06_targeted_tests.log` |
| 后端全量 | 388 passed, 1 skipped，exit 0 | `logs/07_backend_full_tests.log` |
| 前端 build | 775 modules，built in 5.43s，exit 0 | `logs/08_frontend_build.log` |
| 颜色门禁 | 38 个文件通过，exit 0 | `logs/08b_check_colors.log` |
| 迁移 | 唯一索引创建，exit 0 | `logs/02_migration.log` |
| 迁移幂等复跑 | idempotent=true，SHA 不变，exit 0 | `logs/02b_migration_idempotent.log` |
| 启动前目标探针 | 21/21，exit 0 | `logs/04_db_target_probe.log` |
| 运行后目标探针 | exit 0 | `logs/04b_db_target_probe_post.log` |
| 真实 REST/WS | 25 步，exit 0 | `logs/09_rest_ws_flow.log` |
| 重启准备/停止/重启/验证 | 全部 exit 0 | `logs/10a…10d` |
| 数据库保护 | 五库不变，exit 0 | `logs/11_db_protection.log` |
| ω 手算 | ok=true，exit 0 | `logs/12_omega_matrix_handcalc.log` |
| validation 汇总 | 20/20，exit 0 | `logs/14_build_validation.log` |

## 8. 已知限制与未验证范围

1. **演示版外食房间为空**：20 家种子店 `campus=NULL`，按 D1 A′ 全部排除；S10 回填前演示版 OUT_DINING 房间 0 候选，这是已知数据限制。下厨房间共享菜谱，仍有 10 候选。S06 的 10 候选证据使用隔离库 `s06_fixture_v1`。
2. **S07 未验收**：真实浏览器划卡、扫码、四身份、真机、Lottie/GSAP 揭晓均不在本步；本轮未用浏览器点击代替 REST/WS。
3. **单进程 hub**：WS 广播为进程内内存态，不支持多 worker；已在 SSOT 记录。
4. **无 leave/close 端点**：SSOT 未定义；房间结束以 FINISHED + 快照恢复表达。
5. **应用版本串**：`main.py` / `/health` 仍为历史 `2.3.2`，SSOT 已 v2.3.6；本轮未改该字符串，避免扩大范围。
6. **1 skip / 10 warnings**：1 skip 为既有 `test_pre00_runtime_migration.py` 的符号链接/硬链接环境依赖；10 warnings 为既有 `datetime.utcnow` 弃用、requests 依赖版本提示与缓存权限提示；均非本轮新增失败。
7. **未触碰**：`/admin`、S10 数据导入、S11–S20、APK、真实高德/LLM 付费调用。

## 9. 交付物

`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、`validation.json`、`SOURCE_MANIFEST.json`、`logs/`、`data/`（隔离库 provenance、迁移、fixture、目标探针、REST/WS 序列、重启、ω 手算、数据库保护）。

`SOURCE_MANIFEST.json` 最后生成；生成后不再修改包内文件。开发方未签 PASS，等待 Codex 独立审查。
