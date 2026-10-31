# S06/r02 独立复审报告

审查时间：2026-10-27（Asia/Shanghai）  
审查方：Codex  
受审版本：`docs/review/stages/S06/r02/SOURCE_MANIFEST.json`，133 项、16 项标记为 S06 变更；manifest 文件 SHA-256 `cf50030fa624c5556fa6a47e47f4b32e3d11ce73b5a570d76228f39e1ee8628b`  
证据清单：`data/evidence_inventory.json`，60 项，文件 SHA-256 `7d249495b6ee69eb1fe928c77d79854e288aa36890c8d9e9e911db27832b0367`  
最终结论：**PASS**

## 结论

S06/r02 关闭 r01 的两项 P2，其他 S06 契约与回归仍成立。提交源码 manifest 和 evidence inventory 均逐项核对，0 失配、0 缺失。Codex 重跑了定向及全量后端测试、前端 build 和颜色门禁；并在临时数据库副本和独立服务上重新验证 join 状态限制及 sweeper 异常恢复。S06/r02 判定 PASS；S07 仍为用户延期项 DEFERRED，不阻挡独立专项 S08 开放。S08 改为 READY，S10 继续 LOCKED。

## 验收结果

| 条目 | 独立检查 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| 前置状态 | 台账、S06/r01 REVIEW 与其独立报告 | S06=CHANGES_REQUIRED；r02 只整改两项 P2 | PASS |
| 源码 manifest | 仓库根逐项核对路径、SHA-256、文件大小 | 133 项，缺失 0、失配 0 | PASS |
| 证据 inventory | r02 包内逐项核对路径、SHA-256、文件大小 | 60 项，缺失 0、失配 0 | PASS |
| P2-S06-01：扫描级错误恢复 | 定向测试 + SQLite 锁定故障后的真实隔离服务复测 | 初次扫描失败后 sweeper 继续；锁释放后无客户端请求即结算 | PASS |
| P2-S06-01：房间失败隔离 | `test_sweep_isolates_single_room_failure` | 单房失败不阻断同轮其余房间 | PASS |
| P2-S06-02：join 状态守卫 | 定向测试 + 独立 REST/WS 服务 | WAITING 幂等仍可用；SWIPING/FINISHED 已有成员和 FINISHED 房主均 400，无副作用 | PASS |
| S06 定向测试 | `python -m pytest tests/test_room.py tests/test_identity_s01.py tests/test_s02_numeric_bounds.py tests/test_s06_room_contract.py -q --basetemp D:\\EatWhat\\.tmp_codex_s06_r02_targeted_20261027`，cwd=`backend` | 171 passed，exit 0 | PASS |
| 后端全量 | `python -m pytest -q --basetemp D:\\EatWhat\\.tmp_codex_s06_r02_full_20261027`，cwd=`backend` | 391 passed、1 skipped，exit 0；11 warnings | PASS |
| 前端 build | `npm run build`，cwd=`frontend` | 775 modules，exit 0 | PASS |
| 颜色门禁 | `node scripts/check-colors.mjs`，仓库根 | 38 个文件通过，exit 0 | PASS |
| SSOT 与范围 | 对照 MASTER_SPEC v2.3.6、BATCH4_PLAN S06/S07 | r02 两处契约澄清已同步；S07 真实划卡/扫码仍 deferred | PASS |
| 隔离与数据库保护 | 审查临时副本 REST/WS；受保护库和 r01/r02 数据库 SHA 复核 | 审查服务只写临时副本；正式证据库与所有受保护库保持提交哈希 | PASS |
| 服务收尾 | 检查端口 18026/8026/8000/5173 与临时文件 | 服务已停止，审查临时副本及探针目录已移除 | PASS |

## 两项 P2 复核

### P2-S06-01：周期 sweeper 在扫描级异常后退出

`backend/routers/group_room.py::room_sweeper` 现对非取消异常记录后 `continue`，`CancelledError` 仍传播。Codex 重跑专项中的 `test_sweeper_continues_after_scan_error` 与 `test_sweep_isolates_single_room_failure`，包含在 171 项定向测试中，均通过。

真实复测未直接写 r02 证据库：先以文件副本创建 `backend/.tmp_codex_s06_r02_live.db`，独立启动于 18026。直接在副本插入已过期 SWIPING 房间，确认无 WS client/无 START 定时器；用 `BEGIN EXCLUSIVE` 锁定覆盖多个 5 秒周期，观察到 `room_sweeper_failed`；锁释放后不发房间 HTTP/WS 请求，DB 最终为 FINISHED，`settled_at > deadline_at`，日志出现包含该房间码的 `room_sweep_settled`。审查临时副本与日志随后清理。

### P2-S06-02：SWIPING/FINISHED 重复 join 返回 200

`join_room` 在房间锁内统一先校验 `WAITING`，然后再处理校区、容量及幂等成员。Codex 在临时副本复跑 REST/WS 序列：用户 2 WAITING join 成功；开局后重复 join=400；结算后成员和房主重复 join 均=400。前后比对成员、候选、票数、赢家和报告，未发生变化。恢复读取仍由 GET/ROOM_STATE 提供。

## 数据保护

当前文件 SHA-256 与 r02 提交声明一致：

- 演示库 `eatwhat.db`：`775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b`
- S10 库 `eatwhat_batch4.db`：`315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28`
- 开发源库 `eatwhat_dev_pre00_r02.db`：`b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579`
- S05 隔离库：`8179f9fd2a78c3ee50b9bf6b7bd49a72825db07aabd80d5e5dfa10c4d32833ce`
- S06/r01 隔离库：`521d73807a2f28768f75924af35c966ffecb07357fcc056058e94ee9f58b48b4`
- S06/r02 隔离库：`09db91f8151badfbc23a755ef9eaa72dd80ed80aa7e5245c2cd74275fc2c1b61`

演示、S10、开发源和 S05/r01 数据库仍 `group_rooms=0, room_votes=0`；r01 隔离库仍 9 房/51 票；r02 隔离库 32 房/151 票，仅为已声明的隔离回归数据。

## 范围与限制

- 未做 S07 真实浏览器拖拽、扫码、四身份或真机验收；S07 按用户决定保持 DEFERRED，本报告不将该项记作 PASS。
- 未改 `/admin`、S10 数据业务或演示库；未复验高德、LLM 在线服务。
- 后端 1 skip 为既有 Windows 符号链接/硬链接环境用例；11 warnings 为依赖版本、`datetime.utcnow` 弃用与 pytest 缓存权限提示，不影响本轮检查退出码。
- 无发现其他影响 S06/r02 正确性的 P0/P1/P2。

源码 manifest 和 evidence inventory 在登记本轮审查结果前分别为 133/133、60/60 全匹配。台账更新后重新核算源码清单，只有其中作为 context 文件的 `docs/review/STAGE_STATUS.md` 与提交时哈希不同（审查侧状态登记）；其余 132 项仍匹配。evidence inventory 仍 60/60 全匹配。

## 最终判定

**S06/r02：PASS**，绑定源码 manifest SHA-256 `cf50030fa624c5556fa6a47e47f4b32e3d11ce73b5a570d76228f39e1ee8628b`。  
S06 两项 r01 问题关闭。S07 保持 DEFERRED；S08 作为下一项独立专项改为 READY。S10 仍因 PRE-S10/BRIDGE-10 清理计划未完成而 LOCKED，不开放。  
台账更新：S06=PASS、S08=READY；S07 DEFERRED、S10 LOCKED。
