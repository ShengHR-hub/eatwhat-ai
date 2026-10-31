# S06/r01 独立复审报告

审查时间：2026-10-27 22:35（Asia/Shanghai）  
审查方：Codex  
受审版本：`docs/review/stages/S06/r01/SOURCE_MANIFEST.json`，131 项，SHA-256 `8650ff6b65640068c8ebd12d8359cfc67ff041d9258311ab778174b949829633`  
证据清单：`data/evidence_inventory.json`，52 项，SHA-256 `94c48ac55f1d7c2e18067d4305e01817c6a9cb0894239d8e3c576a6af07178e9`  
最终结论：**FAIL（CHANGES_REQUIRED）**

## 结论

S06/r01 的源码清单、证据包内容、隔离数据库、回归与构建均已独立核验；但两个房间状态边界未满足 SSOT v2.3.6。完成房间的既有成员仍可经 `join` 获得 200，违反 join 仅允许 `WAITING` 的契约；后台周期结算任务遇到一次扫描级异常后直接退出，使之后无人访问的过期房间失去自动恢复。两项均记为 P2 契约/可靠性阻断，S06 不能 PASS，S07 不得开始。

## 验收结果

| 条目 | 独立检查 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| 前置状态 | 检查 `STAGE_STATUS.md` 与 S05/r01 PASS 原件 | 审查开始时 S06=READY，S05/r01 为 Codex PASS | PASS |
| SSOT/范围 | 对照 MASTER_SPEC v2.3.6 与 BATCH4_PLAN S06 | E1 fixture、校区过滤、D1–D9 和 S06/S07 范围一致 | PASS |
| 源码 manifest | 根目录逐项计算 SHA-256 与大小（审查结论登记前） | 131 项，缺失 0、失配 0；fingerprint 如上 | PASS |
| 证据 inventory | 对包内登记的 52 项重算 SHA-256 与大小 | 最终 52 项，缺失 0、失配 0 | PASS |
| 后端 S06 专项 | `python -m pytest tests/test_room.py tests/test_identity_s01.py tests/test_s02_numeric_bounds.py tests/test_s06_room_contract.py -q --basetemp D:\\EatWhat\\.tmp_codex_s06_ind_targetset_20261027`（cwd=`backend`） | 168 passed，exit 0 | PASS |
| S06 新增测试文件 | `python -m pytest -q tests/test_s06_room_contract.py --basetemp D:\\EatWhat\\.tmp_codex_s06_ind_targeted_20261027`（cwd=`backend`） | 23 passed，exit 0 | PASS |
| 后端全量 | `python -m pytest -q --basetemp D:\\EatWhat\\.tmp_codex_s06_ind_full_20261027`（cwd=`backend`） | 388 passed、1 skipped，exit 0；11 warnings | PASS |
| 前端构建 | `npm run build`（cwd=`frontend`） | 775 modules，构建成功，exit 0 | PASS |
| 颜色门禁 | `node scripts/check-colors.mjs`（仓库根） | 38 个文件通过，exit 0 | PASS |
| 双身份 REST/WS 状态流程 | S06 数据库字节副本 + 独立服务，创建、加入、开局、到期结算、完成后重复 join | 重复 join 返回 200，重现 P2-S06-02 | FAIL |
| 周期结算异常恢复 | 独立临时 pytest 探针使 `settle_overdue_rooms()` 单次抛出 RuntimeError，并断言 sweeper 调用次数 | `room_sweeper()` 记录异常后返回；无后续扫描，重现 P1-S06-01 | FAIL |
| 受保护数据库 | 对演示库、S10 库、开发源库、S05 隔离库重算 SHA；核查房间/投票数 | SHA 与提交包一致；保护库 `group_rooms=0, room_votes=0` | PASS |
| 浏览器点击 | 未执行 | S07 划卡/扫码交互已 DEFERRED；本轮 REST/WS 后端协议以独立真实服务复验，前端构建通过 | 非本轮放行条件 |

## 阻断问题

### P2-S06-01：周期结算任务在单次扫描级异常后永久退出

- 位置：`backend/routers/group_room.py`，`room_sweeper()`，约第 795–808 行。
- 复现：在隔离测试中让第一轮 `settle_overdue_rooms()` 抛出 `RuntimeError`。外层 `except Exception` 记录 `room_sweeper_failed` 后执行 `return`。探针断言 sleep 与 sweep 均只发生一次，退出码 0（断言问题行为成立）。
- 影响：数据库暂时不可用、扫描查询异常等瞬态故障后，应用仍在运行但 5 秒后台兜底任务已消失。无人 GET/WS 的过期房间不再自动结算，直到有请求触发惰性结算或应用重启。该行为破坏 v2.3.6 §5.5.6 要求的周期兜底与无客户端恢复。
- 要求：异常后 sweeper 必须继续下一周期；取消信号仍应传播；单个房间失败应继续隔离处理。增加“第一次扫描失败、下一次扫描成功并完成结算”的自动化回归，并验证真实隔离服务无人连接时能恢复。

### P2-S06-02：已开始/完成房间的既有成员仍可重复调用 join 并收到成功快照

- 位置：`backend/routers/group_room.py`，`join_room()`，约第 477–577 行；普通校区房间的状态校验仅在 `if is_new` 分支内。
- 复现：在独立数据库副本建房、用户 2 加入，WebSocket 开局；将截止时间设为过去并通过 GET 触发结算，确认状态为 `FINISHED`；用户 2 再次 `POST /rooms/{code}/join`，实际返回 HTTP 200 与 `status=FINISHED`。
- 影响：该请求不新增成员或改写数据，但 SSOT v2.3.6 §5.5.3 的 API 契约将 `join` 限定为校验 `WAITING`；当前接口允许非 WAITING 成员使用 join 取得成功响应，状态边界不一致。
- 要求：按已批准契约，在普通校区路径中对状态统一执行 WAITING 校验，再处理幂等成员检查；如需允许已加入成员在开始/结束后通过 join 读取快照，须先由用户批准并同步 SSOT。补测既有成员重复 join 在 SWIPING、FINISHED 的预期状态码与成员/投票/报告无副作用。

## 证据包复核与审查操作记录

- 初次检查时，误将 `data/prepare_s06_fixture.py --help` 当成只读帮助调用；该脚本没有 help 分支，实际重写了包内 `data/fixture.json` 为 308 字节的 `already_present=true` 摘要。这是审查操作造成的瞬时改写，不是提交方原始状态。
- 未覆盖原件：先将 308 字节版本存入本报告目录的 [`audit_artifacts/fixture_after_audit_probe.json`](audit_artifacts/fixture_after_audit_probe.json)，再从受源码 manifest 保护的 `logs/03_fixture.log` 以原 CP936 编码反解并恢复 UTF-8 内容。恢复文件为 2017 字节，SHA-256 `4c1e11024a35acf84fdf74e0068cca18c540c326e7e60e0c21b9ad357b58a4a6`，与提交时 evidence inventory 登记值逐字节匹配。
- 恢复后再次核验：SOURCE_MANIFEST 131/131 匹配；evidence inventory 52/52 匹配。`logs/15_evidence_inventory.log` 与 `logs/16_source_manifest.log` 存在但未列入 inventory，生成脚本 `data/build_evidence_inventory.py` 明确将其排除，原因是它们由 stdout 重定向生成、会造成自引用；属于有意排除，不计为遗漏。
- 复审报告和台账写入后再检查源码 manifest，当前有且只有 `docs/review/STAGE_STATUS.md` 一项与提交哈希不同，因为 Codex 按审查规则登记了本轮结论；其余 130 项仍匹配。该审查侧登记变更不属于开发方受审源码修改，也不覆盖提交 manifest。evidence inventory 的 52 项仍全匹配。
- 独立 REST/WS 探针只使用 `backend/eatwhat_s06_r01_iso.db` 的临时字节副本 `.tmp_codex_s06_live_repro.db`。临时服务已停止；探针脚本、临时测试文件、数据库和 pytest 临时目录已清理。提交隔离库未被本次 REST/WS 探针写入。
- 受保护库核验 SHA：演示库 `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b`；S10 库 `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28`；开发库 `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579`；S05 隔离库 `8179f9fd2a78c3ee50b9bf6b7bd49a72825db07aabd80d5e5dfa10c4d32833ce`。S06 隔离库仍为提交状态 SHA `521d73807a2f28768f75924af35c966ffecb07357fcc056058e94ee9f58b48b4`，9 房间/51 票。

## 最终判定

结论：**S06/r01 FAIL，台账状态 CHANGES_REQUIRED**。本步其余已核验项目通过，但 P2-S06-01 与 P2-S06-02 未关闭，不满足无影响本步 P0/P1/P2 的 PASS 门槛。

下一步：仅允许提交 `S06/r02` 整改证据包，保留 r01 原件；整改后由 Codex 重新复审。S07 仍 DEFERRED，不得开始；S08、S10 及后续锁定状态不变。
