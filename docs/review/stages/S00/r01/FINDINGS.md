# S00 缺陷冻结清单（FINDINGS）

日期：2026-10-25（Asia/Shanghai）

本文件是**待验清单**，不是通过结论。历史审查、开发方自测、旧截图和旧账本均不能替代当前版本的独立验收。

严重程度：P0 紧急 / P1 核心路径或决策红线 / P2 契约或数据边界 / P3 低风险。状态：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION` 表示代码已有补丁但当前基线未独立验收；`RESIDUAL_OPEN` 表示仍有明确缺口；`OPEN_NEW` 为本轮新发现；`DEFERRED` 仅用于用户明确延期的 S07。

## 汇总

| ID | 标题 | 等级 | 主步骤 | 状态 |
| --- | --- | --- | --- | --- |
| F01 | “海鲜”忌口漏掉鲜虾/虾皮，单人与群组同源过滤 | P1 | S04 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F02 | 全部候选被 VETO 仍选出赢家 | P1 | S04 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F03 | 最后连接断开会取消结算，房间停在 SWIPING | P1 | S06 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F04 | 已揭晓房间仍允许改票 | P1 | S06 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F05 | 断线/重入拿不到候选与完整揭晓 | P1 | S06 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F06 | 390×667 首页操作按钮被 Tab 遮住 | P1 | S05 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F07 | 身份优先级与资源归属仍有残留 | P2 | S01 | RESIDUAL_OPEN |
| F08 | 数值/向量边界已收紧，但部分向量更新仍整体覆盖 | P2 | S02 | RESIDUAL_OPEN |
| F09 | 冰箱时效已统一，但剩余天数取整在边界提前过期 | P2 | S03 | RESIDUAL_OPEN |
| F10 | 沙盒与首页卡组/群组 ω 的同源链路 | P2 | S05 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| F11 | 多人房间契约仍有校区、票型与划卡 UI 缺口 | P2 | S06 | PARTIAL_OPEN |
| F12 | 颜色出口与单色约束 | P2 | S08 | STATIC_PASS_PENDING_VISUAL |
| F13 | “换一批”重复 Top24 | P2 | S05 | FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION |
| N01 | 首页卸载异常阻断底部导航 | P1 | S05 | FIXED_PENDING_S05_REGRESSION |
| N02 | 双校区 campus 契约与过滤完全缺失 | P2 | S05 | OPEN_NEW |
| N03 | 软删除 deleted_at 未在推荐/目录/房间过滤 | P2 | S05 | OPEN_NEW |
| N04 | feature_vector 为 NULL 时被默认 0.5 向量参与推荐 | P2 | S04 | OPEN_NEW |
| N05 | 运行库与版本元数据基线漂移 | P3 | S05 | BASELINE_RISK |

## 逐项详情

### F01 — “海鲜”忌口漏掉鲜虾/虾皮，单人与群组同源过滤

- **等级**：P1
- **主步骤**：S04；关联：S01, S06
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `backend/algorithms/veto_rules.py（唯一忌口出口）`
  - `backend/algorithms/single_recommender.py:52-58`
  - `backend/algorithms/group_recommender.py:26-29,50-122`
  - `backend/tests/test_veto_and_consensus.py:56-96`
- **复现前置**：
  - 使用开发库 backend/eatwhat_dev_pre00_r02.db 或其临时副本
  - 演示角色 3 的 veto_tags=['海鲜']
  - 群组复现需要隔离库并建房；S00 不执行写操作
- **最小复现**（read_only_api）：GET /api/v1/users/3/profile 取 veto_tags；POST /api/v1/recommend/single（X-User-Id: 3，HOME_COOKING，limit=100），检查返回菜名与主辅料不得命中海鲜别名
  - 本轮是否执行：是；日志：`logs/10_f01_f13_readonly_probe.log`
- **当前表现**：开发库只读探针：35 道下厨候选，0 条命中海鲜忌口；『鱼香茄子』未被误判。群组 shortlist 未在本轮做真实写库复现，只确认代码走同一 veto_rules。
- **影响**：过敏原/绝对忌口红线；漏判会让用户点到明确排除的食材。
- **关闭所需证据**：
  - S04：独立期望值覆盖海鲜→虾/蟹/贝/鱼等别名、主料与辅料、误判反例（鱼香肉丝/豆腐）
  - S04：单人真实 API + 隔离库群组 shortlist，同一忌口集合结果一致
  - S04：不调用生产函数生成测试期望值；日志与 DB 前后状态归档
- **旧证据与局限**：
  - `docs/review/audit-2026-10-24/REPORT.md`：审查时点早于 PRE-00 迁移与后续补丁，且只复现虾类；不是当前版本的独立验收
  - `docs/AGENT_MEMORY.md §13`：开发方自报与历史测试，不等于 Codex 对当前基线的 PASS
  - `backend/tests/test_veto_and_consensus.py`：自测通过；群组真实数据与当前 dev 库未在 S00 独立复验

### F02 — 全部候选被 VETO 仍选出赢家

- **等级**：P1
- **主步骤**：S04；关联：S06, S07
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `backend/algorithms/group_recommender.py:222-232（eligible 过滤，winner=None）`
  - `backend/tests/test_veto_and_consensus.py:99-157`
- **复现前置**：
  - 隔离库/内存库；两道或更多候选全部投 VETO
  - S00 不建房、不写票
- **最小复现**（unit_test）：python -m pytest backend/tests/test_veto_and_consensus.py -q -k 'all_veto or no_votes'
  - 本轮是否执行：否；说明：本轮全量 pytest 已包含该文件；S04 需独立重算期望值并补真实 WS 场景
- **当前表现**：代码从未否决集合选赢家；全否决返回 winner_dish_id=None、has_consensus=False。当前全量测试通过，但未独立复算。
- **影响**：一票否决被零分掩盖，可能推荐全员拒绝的菜。
- **关闭所需证据**：
  - S04：固定投票样本独立手算；全否决/部分否决/零分与被否决同分三类
  - S06/S07：真实 WS 房间全 VETO 后无赢家并广播明确无共识
- **旧证据与局限**：
  - `docs/review/audit-2026-10-24/REPORT.md`：描述的是修复前缺陷；修复后未由审查方独立复验当前版本
  - `docs/AGENT_MEMORY.md §13`：开发方复现笔记，不是当前基线 PASS

### F03 — 最后连接断开会取消结算，房间停在 SWIPING

- **等级**：P1
- **主步骤**：S06；关联：S07
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `backend/routers/group_room.py:98-102（remaining_ms）、254-298（幂等结算）`
  - `backend/routers/group_room.py:480-500（deadline 落库）、489-505（定时器）`
  - `backend/models.py:152-154（deadline_at/settled_at）`
  - `backend/tests/test_room.py:230-281`
- **复现前置**：
  - 隔离库；两个独立身份；SWIPE_SECONDS 可临时缩短
  - S00 不建房
- **最小复现**（websocket_test）：隔离库把 SWIPE_SECONDS 设为 1；建房→join→START_SWIPING→关闭全部 WS→等待 1.3s→GET /rooms/{code}，期望 FINISHED 且报告完整
  - 本轮是否执行：否
- **当前表现**：代码以 deadline_at 为服务端事实，结算幂等；当前测试通过，但 S00 未独立跑真实 WS。
- **影响**：刷新、断线或进程重启会让一局永久卡住。
- **关闭所需证据**：
  - S06：真实 WS 双身份、全断开、重连、重复结算、进程重启恢复
  - S06：DB 中 status/settled_at/deadline_at 与广播一致
  - S07：真实浏览器断线/后台切回恢复（延期项，不挡 S06）
- **旧证据与局限**：
  - `docs/review/clearance-codex-r02-2026-10-24/browser-supplement/REPORT.md`：只验证房间入口，未做完整 WS 投票/断线/恢复
  - `backend/tests/test_room.py`：自测通过；S06 尚未独立复验当前基线

### F04 — 已揭晓房间仍允许改票

- **等级**：P1
- **主步骤**：S06；关联：S07
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `backend/routers/group_room.py:611-670（SUBMIT_VOTE 阶段/截止/候选校验）`
  - `backend/tests/test_room.py:207-229`
- **复现前置**：
  - 隔离库；SWIPING 结束或超过 deadline；已投过票
- **最小复现**（websocket_test）：完成一局→FINISHED 后同一连接再发 SUBMIT_VOTE，期望 ERROR 且 room_votes 不变；并发截止票另测
  - 本轮是否执行：否
- **当前表现**：FINISHED、非 SWIPING、remaining_ms<=0 均拒绝；代码已在写入前检查。
- **影响**：结算报告与投票事实冲突，污染足迹与实验。
- **关闭所需证据**：
  - S06：揭晓后改票、迟到票、并发截止、重复投票自动化
  - S06：DB 前后票数与报告一致
- **旧证据与局限**：
  - `backend/tests/test_room.py:207-229`：自测；未覆盖并发截止与真实 WS 重连

### F05 — 断线/重入拿不到候选与完整揭晓

- **等级**：P1
- **主步骤**：S06；关联：S07
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `backend/routers/group_room.py:177-217（RoomSnapshot 全量快照）`
  - `backend/schemas.py:390-415（winner/report/deadline/my_votes）`
  - `frontend/src/views/mobile/Room.vue:140-165（applySnapshot）`
  - `backend/tests/test_room.py:257-281`
- **复现前置**：
  - 隔离库；WAITING/SWIPING/FINISHED 三种阶段；刷新或重连
- **最小复现**（api_and_browser）：GET /api/v1/rooms/{code} 在三个状态返回 candidates/my_votes/deadline_at/winner_dish/consensus_report；S07 用真实浏览器刷新
  - 本轮是否执行：否
- **当前表现**：快照字段齐全，前端按 snapshot 恢复三阶段；后端自测通过。
- **影响**：漏收广播后无法恢复，用户看到空房或错误阶段。
- **关闭所需证据**：
  - S06：GET/重连快照三阶段一致，数据库为事实源
  - S07：真实浏览器刷新/断线重连/后台切回恢复（延期）
- **旧证据与局限**：
  - `docs/review/clearance-codex-r02-2026-10-24/browser-supplement/REPORT.md`：房间入口检查，不含完整阶段恢复

### F06 — 390×667 首页操作按钮被 Tab 遮住

- **等级**：P1
- **主步骤**：S05；关联：S08
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `frontend/src/views/mobile/Home.vue:487-605,718-740`
  - `frontend/src/layouts/MobileShell.vue:45-60`
  - `frontend/src/components/SwipeCardDeck.vue`
  - `scripts/home-fit.mjs:88-149`
- **复现前置**：
  - dev 后端 8000 指向 dev 库；Vite 5173
  - 390×844 与 390×667 两档
- **最小复现**（browser_geometry）：启动前后端后运行 node scripts/home-fit.mjs；并真实点击『换一个/就吃这个』
  - 本轮是否执行：否；说明：S00 只确认 CSS 结构、构建和脚本断言存在；真实两档几何留给 S05/S08
- **当前表现**：卡组 flex:1 1 auto、min-height:0，操作行与 Tab 分离；home-fit 断言含矩形不相交与 elementFromPoint 命中自身。
- **影响**：短屏核心操作不可用；scrollHeight 相等也不能证明装得下。
- **关闭所需证据**：
  - S05/S08：390×844、390×667 的 scrollHeight/scrollWidth、元素矩形、按钮中心命中、截图
  - S05：真实点击换一个/就吃这个后仍可导航
  - S08：全部移动页面同基线回归
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：2026-10-24 旧基线；PRE-00 迁移后未重测
  - `docs/review/clearance-codex-r02-2026-10-24/browser-supplement/REPORT.md`：历史浏览器补验；S05/S08 仍需当前基线的新证据

### F07 — 身份优先级与资源归属仍有残留

- **等级**：P2
- **主步骤**：S01；关联：S05, S06
- **状态**：`RESIDUAL_OPEN`
- **当前源码位置**：
  - `backend/deps.py:15-53（raw/current/resolve/ensure_self）`
  - `backend/routers/recommend.py:84（header 优先）`
  - `backend/routers/eating_log.py:53,90-93（打卡 header 优先；stats 路径无头校验）`
  - `backend/routers/fridge.py:86-88（GET 路径无头校验）`
  - `backend/routers/auth_user.py:108-130（profile/preferences ensure_self 403）`
  - `backend/routers/group_room.py:316（host_id = body.host_user_id or header）`
- **复现前置**：
  - dev 库只读探针；写身份冲突需隔离库
  - 两个演示角色 1/2
- **最小复现**（read_only_api_and_isolated_write）：GET /api/v1/fridge/2 与 GET /api/v1/logs/stats/2 携带 X-User-Id: 1，观察是否返回用户 2 数据；GET /users/2/profile 携带 X-User-Id: 1 观察 403；S01 在隔离库 POST /rooms/create 头 1 + body host_user_id=2，检查落库房主
  - 本轮是否执行：是；日志：`logs/22_current_state_summary.json`
- **当前表现**：只读探针：header=1 读取 fridge/2 返回 200（user_id=2，4 条），读取 stats/2 返回 200（用户 2 的周数据）；profile 路径冲突返回 403。代码显示 /rooms/create 仍由 body host_user_id 覆盖请求头。
- **影响**：可读他人冰箱/足迹；建房身份可被 body 改写；路径冲突 403 与 SSOT『按头解析』尚需裁决。
- **关闭所需证据**：
  - S01：入口矩阵覆盖 recommend/checkin/stats/fridge/shopping-list/profile/preferences/red-black/rooms create/join/WS
  - S01：跨用户读取/写入必须 403/404，且 DB 目标记录不变；建房身份按统一口径
  - S01：记录 403 与按头解析的最终契约决策（用户/Codex 确认）
  - S05：真实角色切换后所有后续请求携带新身份
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：当时只补了 body/path 部分洞；本轮只读探针仍发现 fridge/stats 跨用户读取
  - `backend/tests/test_identity_bounds_and_stock.py`：只覆盖 profile/preferences/red-black 路径，未覆盖 fridge/stats GET 与 rooms/create body 覆盖

### F08 — 数值/向量边界已收紧，但部分向量更新仍整体覆盖

- **等级**：P2
- **主步骤**：S02；关联：S01, S05
- **状态**：`RESIDUAL_OPEN`
- **当前源码位置**：
  - `backend/schemas.py:62-103（PreferenceUpdate 八键/0-1/预算/标签校验）`
  - `backend/schemas.py:147-182（推荐入参与 override 边界）`
  - `backend/routers/auth_user.py:130-131（base_vector 直接整体替换）`
  - `backend/tests/test_identity_bounds_and_stock.py:111-123`
- **复现前置**：
  - 隔离库；角色 1 的完整 8 维向量
  - S00 不写库
- **最小复现**（isolated_write）：隔离库 GET /users/1/profile 记录 8 键；PUT /users/1/preferences {"base_vector":{"spicy_level":0.9}}；再 GET，检查是否只剩 1 键
  - 本轮是否执行：否
- **当前表现**：Schema 会验证已提供的键，但 PUT 用 dict(payload.base_vector) 整体替换；现有测试只断言两个键，没有断言其余六键保留。
- **影响**：部分更新可把八维画像截断，推荐分数失真且数据库留下不完整向量。
- **关闭所需证据**：
  - S02：先裁决部分更新策略（合并旧值后八键 / 缺键拒绝）
  - S02：缺键、多键、空对象、NaN/Inf、越界、布尔、超长标签、负金额、无效 enum 的 4xx 与不落库断言
  - S02：推荐结果有限且 0–100；DB 八键完整
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：当时已发现偏好部分更新问题；当前代码仍整体替换
  - `backend/tests/test_identity_bounds_and_stock.py`：测试接受了 2 键向量且未检查其余键，不能证明部分更新安全

### F09 — 冰箱时效已统一，但剩余天数取整在边界提前过期

- **等级**：P2
- **主步骤**：S03；关联：S05
- **状态**：`RESIDUAL_OPEN`
- **当前源码位置**：
  - `backend/algorithms/fridge_clock.py:18-32（remaining_days/is_expired）`
  - `backend/algorithms/single_recommender.py:81-99（推荐索引）`
  - `backend/routers/fridge.py:45-70,118-130（展示/采购）`
  - `backend/tests/test_identity_bounds_and_stock.py:151-213`
- **复现前置**：
  - 固定时钟；expire_days=3；created_at 取 2.4/2.5/2.6/3.0 天前
- **最小复现**（pure_function_probe）：python docs/review/stages/S00/r01/data/probe_fridge_boundary.py；固定 now 构造 FridgeInventory(expire_days=3, created_at=now-2.5d)，调用 remaining_days/is_expired
  - 本轮是否执行：是；日志：`logs/09_fridge_boundary_probe.log`
- **当前表现**：2.5 天前入库、剩余 0.5 天时 remaining_days=0、is_expired=True，提前半天判过期；1.5 天剩余会 round 成 2。
- **影响**：展示、推荐加分、采购清单在边界不一致；临期/过期优先级可能提前或错位。
- **关闭所需证据**：
  - S03：先锁定 expire_days 与到期边界的取整语义
  - S03：固定时钟覆盖新鲜/临期/到期前一刻/恰好到期/到期后/跨日/同名新旧库存
  - S03：展示、推荐、采购三处同口径；过期不抵扣采购、不加分
- **旧证据与局限**：
  - `backend/tests/test_identity_bounds_and_stock.py`：有 30 天极端样本与过期样本，但没有 2.4/2.5 天边界；本轮探针证明仍有边界缺口

### F10 — 沙盒与首页卡组/群组 ω 的同源链路

- **等级**：P2
- **主步骤**：S05；关联：S06
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `frontend/src/views/mobile/Home.vue:72-80（reloadTick 防抖重取）`
  - `frontend/src/stores/algo.js:35-82（唯一参数与 exclude 请求）`
  - `backend/routers/group_room.py:223-251（建房快照 → 结算 ω）`
  - `backend/tests/test_room.py:303-367`
- **复现前置**：
  - dev 库；前端 5173；沙盒打开/关闭
  - 群组需隔离库
- **最小复现**（browser_and_api）：S05：拖动 β/λ 后比较抽屉 Top5 与首页卡组、请求 params_used；S06：建房时 override ω，结算用同一快照；运行 node scripts/sandbox-sync.mjs
  - 本轮是否执行：否
- **当前表现**：单人有 reloadTick + 320ms 防抖；群组结算读取 room.algo_params → config → 默认。历史测试通过，S00 未真实拖拽。
- **影响**：答辩时调参只改抽屉不改首页，或房间结算与开团参数不一致。
- **关闭所需证据**：
  - S05：真实拖拽、快速连续改参、关闭/重置后卡组与 Top5 同源；请求参数与响应 params_used 对照
  - S06：ω 两个端点、快照、重连/重启一致；DB 报告可追溯
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：旧基线单次拖拽证据；群组 ω 当时仍未闭环
  - `backend/tests/test_room.py:303-367`：自测；S05/S06 未独立复验

### F11 — 多人房间契约仍有校区、票型与划卡 UI 缺口

- **等级**：P2
- **主步骤**：S06；关联：S07
- **状态**：`PARTIAL_OPEN`
- **当前源码位置**：
  - `backend/schemas.py:417-443（RoomCreate/Join 无 campus）`
  - `backend/routers/group_room.py:310-380（create/join 无 campus 校验）`
  - `backend/algorithms/vector_spec.py:29-35（VOTE_SCORES 含 VETO=-999）`
  - `backend/routers/group_room.py:64,611-665（接受 TIMEOUT 并写票）`
  - `frontend/src/views/mobile/Room.vue:36-39,309（按钮投票，未接 SwipeCardDeck）`
  - `backend/tests/test_room.py:57-368`
- **复现前置**：
  - 隔离库；两个身份；真实 WS
  - S07 需真实浏览器/设备
- **最小复现**（api_ws_and_browser）：S06：检查 /rooms/create 请求/响应与 DB campus；WS 发 TIMEOUT 观察是否入库；S07：两标签页真实拖拽划卡
  - 本轮是否执行：否
- **当前表现**：create 路径/budget/10 候选/6 位数字码/WAITING-SWIPING-FINISHED/未 join 403 已对齐；仍无 campus；VOTE_SCORES 保留 VETO=-999 且接受 TIMEOUT；Room 使用按钮而非探探式划卡。
- **影响**：跨校区可拼桌；票型契约漂移；S07 交互未完成。
- **关闭所需证据**：
  - S06：REST/WS 契约矩阵、票型枚举、campus 必填/同校区、join 幂等、403、快照、ω、断线/重启/重复结算
  - S07：真实两/四身份拖拽 >60px、超时、重连、扫码、揭晓；延期项不得伪称完成
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：当时只检查房间入口
  - `backend/tests/test_room.py`：覆盖后端部分契约，但无 campus、无真实划卡；TIMEOUT 当前仍被接受

### F12 — 颜色出口与单色约束

- **等级**：P2
- **主步骤**：S08；关联：S05
- **状态**：`STATIC_PASS_PENDING_VISUAL`
- **当前源码位置**：
  - `frontend/src/styles/{main,glass-card,glass-tokens}.css（令牌出口）`
  - `frontend/src/utils/theme.js（ECharts/JS 侧出口）`
  - `scripts/check-colors.mjs（38 文件静态门禁）`
  - `docs/review/stages/PC03/r04/REVIEW.md（PC03 PASS）`
- **复现前置**：
  - 当前前端源码；真实浏览器渲染
- **最小复现**（static_and_browser）：node scripts/check-colors.mjs；S08 真实页面检查主题令牌、玻璃层级与图表渲染
  - 本轮是否执行：是；日志：`logs/04_check_colors.log`
- **当前表现**：静态门禁通过：38 个文件无裸 hex/rgb/hsl。真实渲染、玻璃配方、素材与低高度视觉未在 S00 检查。
- **影响**：静态零命中不等于页面视觉正确；玻璃/图表/动效仍可能在真实渲染中偏离。
- **关闭所需证据**：
  - S08：真实浏览器逐页视觉、三层架构/玻璃分级、图表与动效实际渲染
  - S08：build + home-fit + check-colors 同时通过
  - PC03/r04 只证明静态门禁，不替代 S08
- **旧证据与局限**：
  - `docs/review/stages/PC03/r04/REVIEW.md`：PC03 是静态颜色门禁 PASS；S08 的真实渲染未验收

### F13 — “换一批”重复 Top24

- **等级**：P2
- **主步骤**：S05；关联：S08
- **状态**：`FIXED_CODE_PENDING_INDEPENDENT_VERIFICATION`
- **当前源码位置**：
  - `frontend/src/views/mobile/Home.vue:62-70（seen 集合 + 本地兜底）`
  - `frontend/src/stores/algo.js:66-82（exclude_dish_ids）`
  - `backend/schemas.py:160-162（exclude_dish_ids）`
  - `backend/tests/test_api.py:330-363`
- **复现前置**：
  - dev 库；同一上下文连续请求
  - S00 不写库
- **最小复现**（read_only_api）：POST /recommend/single limit=24 取 first_ids；再以 exclude_dish_ids=first_ids 请求，检查 ID 不重叠
  - 本轮是否执行：是；日志：`logs/10_f01_f13_readonly_probe.log`
- **当前表现**：只读探针：第一批 24、第二批 24，交集为空。完整耗尽后的空态与重置仍需真实浏览器验证。
- **影响**：候选池被截断，用户误以为没菜可选。
- **关闭所需证据**：
  - S05：真实点击连续换批直至耗尽，ID 序列与后端记录；耗尽后空态/重置行为
  - S05：切换模式/角色/气泡时排除集按规则重置
  - S08：短屏空态可见、按钮命中
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：只验证单次换卡，没有连续耗尽
  - `backend/tests/test_api.py:330-363`：后端自测通过；前端完整耗尽未验证

### N01 — 首页卸载异常阻断底部导航

- **等级**：P1
- **主步骤**：S05；关联：S08
- **状态**：`FIXED_PENDING_S05_REGRESSION`
- **当前源码位置**：
  - `frontend/src/components/AlgoSandboxDrawer.vue:46-48（仅恢复 body overflow，无失效 timer 引用）`
  - `frontend/src/layouts/MobileShell.vue（router-view transition）`
- **复现前置**：
  - 真实浏览器；首页→足迹/我的；打开/关闭沙盒
- **最小复现**（browser_click）：打开 /m/home → 点『足迹』→ 等待目标内容可见；再打开沙盒、关闭后点『我的』；读取 console
  - 本轮是否执行：否
- **当前表现**：代码已移除 clearTimeout(timer)；历史点击回归 7 项通过，但未在 PRE-00 后重跑。
- **影响**：离开首页报 ReferenceError，目标页不渲染。
- **关闭所需证据**：
  - S05：真实点击首页→足迹→我的→首页，沙盒开关后重复；URL/标题/目标内容一致
  - S05：console error=0，body overflow 恢复；卸载后无异常
- **旧证据与局限**：
  - `docs/review/recheck-2026-10-24/REPORT.md`：旧基线真实点击证据；当前版本需重跑，不能直接沿用

### N02 — 双校区 campus 契约与过滤完全缺失

- **等级**：P2
- **主步骤**：S05；关联：S06, S08, BRIDGE-10
- **状态**：`OPEN_NEW`
- **当前源码位置**：
  - `backend/schemas.py:147-162（SingleRecommendRequest 无 campus）`
  - `backend/schemas.py:417-443（RoomCreate/Join 无 campus）`
  - `backend/algorithms/single_recommender.py:190-194（Dish/Restaurant 查询无 campus 过滤）`
  - `backend/algorithms/group_recommender.py:80-84（初筛无 campus）`
  - `backend/routers/group_room.py:310-380（建房/join 不写/不校验 campus）`
  - `frontend/src（无 campus 状态或切换入口）`
- **复现前置**：
  - dev 库 restaurants.campus 全为 NULL（20/20）
  - S10 独立库有 SIYUAN/JIANDA_YANTA 数据
- **最小复现**（read_only_api_and_schema_inspection）：POST /recommend/single 带 campus=SIYUAN 与不带，比较 ID；GET /openapi.json 检查 campus 字段；S06 在隔离库建房检查 group_rooms.campus
  - 本轮是否执行：是；日志：`logs/22_current_state_summary.json`
- **当前表现**：OpenAPI 中没有任何 campus 字段；带 campus 的请求被忽略，返回与不带完全相同的 Top5；开发库 20 家门店 campus 均为 NULL；前端无校区切换。
- **影响**：无法按 SSOT v2.3.4 过滤；接 S10 数据后会跨校区混算/拼桌。
- **关闭所需证据**：
  - S05：外食推荐 campus 必填/422、按校区过滤、响应不混算（若本步不实现则明确 BLOCKED 到 BRIDGE-10）
  - S06：建房必填 campus、join 同校区 409、跨校区禁止拼桌、快照/DB 一致
  - S08：前端校区切换后推荐/POI/统计同步（若本步范围含 UI）
  - BRIDGE-10：S10 双校区数据只读/导入边界与过滤验收
- **旧证据与局限**：
  - `MASTER_SPEC.md v2.3.4 §5.5`：这是契约，不是实现证据；当前代码没有 campus

### N03 — 软删除 deleted_at 未在推荐/目录/房间过滤

- **等级**：P2
- **主步骤**：S05；关联：S06, BRIDGE-10
- **状态**：`OPEN_NEW`
- **当前源码位置**：
  - `backend/algorithms/single_recommender.py:190-194`
  - `backend/algorithms/group_recommender.py:80-84,130,166`
  - `backend/routers/catalog.py:43,70`
  - `backend/routers/group_room.py:151-154`
- **复现前置**：
  - 隔离库插入 deleted_at 非空菜品/门店
  - dev 库当前 deleted 行=0，问题为潜在
- **最小复现**（isolated_db_probe）：隔离库复制一道菜并置 deleted_at=now；调用 recommend/shortlist/catalog，检查该 ID 是否仍出现
  - 本轮是否执行：否
- **当前表现**：所有查询都没有 deleted_at IS NULL 条件；dev 库 deleted_restaurants=0、deleted_dishes=0，因此当前演示不暴露。
- **影响**：S10 软删除后仍会被推荐/展示/入房，历史流水保留但新决策不应使用。
- **关闭所需证据**：
  - S05/S06：隔离库软删除行不出现在推荐、短名单、目录、房间候选
  - BRIDGE-10/S10：软删除口径与历史流水联表读取同时成立
- **旧证据与局限**：
  - `MASTER_SPEC.md 第三章 schema 迁移约束`：契约要求过滤，当前代码未实现

### N04 — feature_vector 为 NULL 时被默认 0.5 向量参与推荐

- **等级**：P2
- **主步骤**：S04；关联：S05, BRIDGE-10
- **状态**：`OPEN_NEW`
- **当前源码位置**：
  - `backend/algorithms/vector_spec.py:27,85-91（DEFAULT_FEATURE_VECTOR 全 0.5 + normalize_vector）`
  - `backend/algorithms/single_recommender.py:225-260（直接 normalize_vector(dish.feature_vector)）`
- **复现前置**：
  - 隔离库将一道菜 feature_vector 置 NULL
  - dev 库当前 NULL=0，问题为潜在
- **最小复现**（isolated_db_probe）：隔离库复制一道菜并置 feature_vector=NULL；调用推荐，检查该菜是否仍进入结果并带有 0.5 默认向量
  - 本轮是否执行：否
- **当前表现**：normalize_vector(None) 返回全 0.5，未打标菜仍可被评分/推荐；dev 库 0 条 NULL，当前演示不暴露。
- **影响**：S10/S11 未完成打标的菜被当成中性偏好推荐，与『NULL=未完成、不得默认向量蒙混』冲突。
- **关闭所需证据**：
  - S04：明确 NULL 向量菜品的处理（排除/标记未打标），并有独立测试
  - BRIDGE-10：S10 导入的 PENDING/NULL 菜品不进入正常推荐或明确降级
- **旧证据与局限**：
  - `MASTER_SPEC.md v2.3.3 第三章`：契约允许 NULL，但没有定义推荐消费策略；当前代码默认 0.5

### N05 — 运行库与版本元数据基线漂移

- **等级**：P3
- **主步骤**：S05；关联：S08, BRIDGE-10
- **状态**：`BASELINE_RISK`
- **当前源码位置**：
  - `backend/config.py:13-15（默认 DATABASE_URL 指向 backend/eatwhat.db）`
  - `backend/main.py:16-21,42（app version 2.3.2）`
  - `PRE-00 证据：docs/review/stages/PRE-00/r02/`
- **复现前置**：
  - 直接使用默认后端启动（未设置 DATABASE_URL）
- **最小复现**（startup_matrix）：分别以默认 DATABASE_URL 与 dev_pre00_r02 启动，调用 /health 与 /recommend/single；S00 不覆盖演示库
  - 本轮是否执行：否
- **当前表现**：演示库仍是旧 schema，直接作为运行库会在推荐/足迹 500；PRE-00 只迁移了 dev_pre00_r02。健康接口仍报 2.3.2，与 SSOT v2.3.5 不一致。
- **影响**：误用演示库会重现 500；版本报告与文档不一致，影响交付核对。
- **关闭所需证据**：
  - S05/BRIDGE-10：文档与脚本明确 dev 运行库；演示库只读保护继续有效
  - S08：交付版本号与 SSOT 一致或明确说明
- **旧证据与局限**：
  - `docs/review/stages/PRE-00/r02/SUBMISSION.md`：PRE-00 只修 dev 副本，不改变默认路径；这是运行约束，不是功能 PASS

## 当前代码中已确认存在的具体残留（本轮只读证据）

- F07：`X-User-Id: 1` 读取 `/api/v1/fridge/2` 返回 200（user_id=2，4 条）；读取 `/api/v1/logs/stats/2` 返回 200。`/users/2/profile` 头路径冲突返回 403。
- F09：固定时钟下 `expire_days=3`、已过 2.5 天时 `remaining_days=0`、`is_expired=True`。
- N02：OpenAPI 无任何 `campus` 字段；外食推荐带/不带 `campus=SIYUAN` 返回相同 Top5；开发库 20/20 门店 `campus=NULL`。
- N03/N04：开发库 `deleted_at` 非空=0、`feature_vector IS NULL`=0；问题为 S10 数据接入后的潜在缺口，当前不暴露。
- N05：演示库仍是旧 schema；只有 `eatwhat_dev_pre00_r02.db` 可直接运行；`/health` 报 `2.3.2`，SSOT 为 v2.3.5。

## 未执行项

- 未做任何建房、打卡、偏好保存、库存增删等业务写入；因此 F02/F03/F04/F05/F10群组/F11 的真实 WS/写库复现留给 S04/S06。
- 未启动真实浏览器点击；F06/F10单人/F13/N01 的浏览器证据留给 S05/S08。
- S07 保持 `DEFERRED`，未执行、未签通过。
