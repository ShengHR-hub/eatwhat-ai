# 分步开发与独立审查台账

初始化日期：2026-10-24（Asia/Shanghai）

修订：2026-10-24，用户确认采用批次 4 前三项清账路线；取代初始化时只开放 S00 的安排。

修订：2026-10-24，用户明确「三项一起完成，完成后统一审查」，PC01 / PC02 / PC03 同轮提交。开发方已按该指令施工并提交证据包，**未签发 PASS**，待 Codex 统一审查。

修订：2026-10-24（第二轮），按 `D:\谷歌\BATCH4_REWORK_ROUND2.md` 与用户口头四句话整改 CLR-01～CLR-05，三项提交 **r02**：`docs/review/stages/PC01/r02/`、`PC02/r02/`、`PC03/r02/`。r01 包原样保留、不覆盖。三项状态改为 `REVIEW_PENDING`，开发方**不签 PASS**、未改动任何 `REVIEW.md`；S09 与批次 4 主线继续 LOCKED。

修订：2026-10-24（第三轮），按 `D:\谷歌\BATCH4_REWORK_ROUND2.md` 与用户第三次指令整改 R2-01～R2-05，提交 **r03**：`docs/review/stages/PC01/r03/`、`PC03/r03/`。R01 已 PASS 且本轮未改共享推荐逻辑/时钟/fixture，不重提。r01/r02 包原样保留、不覆盖。三项状态改 `REVIEW_PENDING`，开发方**不签 PASS**、未改动任何 `REVIEW.md`；S09 与批次 4 主线继续 LOCKED。

修订：2026-10-24（第四轮），按 r03 报告 §8 只整改 **R3-01 / R3-03 / R3-02**，提交 **r04**：`docs/review/stages/PC01/r04/`、`PC03/r04/`。PC01 同时更正 R02 证据身份说明（截断旧库标废弃）。PC02/R01 未改共享推荐逻辑/时钟/fixture，维持 PASS，不重提。r01/r02/r03 包原样保留、不覆盖。PC01/R02 与 PC03/F12 状态改 `REVIEW_PENDING`，开发方**不签 PASS**、未改动任何 `REVIEW.md`；S09 与批次 4 主线继续 LOCKED。

修订：2026-10-24（r04 独立复审），Codex 对 PC01/R02、PC02/R01、PC03/F12 分项完成源码核验、真实 CLI/隔离库复验、固定样本复算、颜色隔离探针、pytest 与前端 build。结论为三项 **PASS**。受审 manifest：PC01/r04 `13d6c57b204dd6545198153cd64f7e40e718e6acbb8356801a0a952ca823389f`；PC03/r04 `375bd6aede2e38544452b4012048c40d7a3397e99993e9e4ea0a76f4f0d203db`。S09 现开放为 `READY`；S10–S20、`/admin` 和 S00–S08 专项仍按本台账逐步验收。

修订：2026-10-25（S09/r02），用户确认批次 4 数据/统计/实验口径，SSOT 升至 v2.3.3；提交 `docs/review/stages/S09/r02/`。S09 状态改为 `REVIEW_PENDING`，S10–S20 继续 LOCKED；开发方不签 PASS。

修订：2026-10-25（v2.3.4 双校区文档同步），用户确认双校区/校区过滤/1700 与 17 纠错；更新 MASTER_SPEC、DASHBOARD_EXPANSION 与 S09/r02 文档。**未改任何步骤状态**：S09/r02 仍 `REVIEW_PENDING`，S10–S20 仍 LOCKED；r03 历史结论（R02 FAIL、F12 FAIL、R01 PASS）与 r04 后续 PASS 记录均保留。

修订：2026-10-25（v2.3.5 建大试抓），建大雁塔中心 `108.967153,34.236991`、真实 POI 6,659 + 合成食堂 200=6,859 已试抓；思源 605+200=805，思源 D03 仍未裁决。S09/r02 状态不变（`BLOCKED`），S10–S20 仍 LOCKED；r03 历史与 r04 PASS 记录保留。

修订：2026-10-25（S09/r02 独立复审），Codex 独立核验思源 3km POI、证据 JSON、manifest 与后端基线。思源只读数据证据基本成立，但双校区新增范围尚未形成可复核的建大试抓、校区过滤契约与验收证据；D03 仍未裁决，且 r02 manifest 被提交后的 SSOT/大屏文档变更打破。S09/r02 判定 `BLOCKED`，不开放 S10；r02 原包保留，下一轮必须提交 S09/r03。

修订：2026-10-25（建大试抓补证），Codex r02 REVIEW 指出的建大数据缺口已补：中心 `108.967153,34.236991`，真实 POI 6,659 + 合成食堂 200=6,859，0 未完成；思源 605 vs 目标 1500+ 仍未裁决。r02 结论仍为 `BLOCKED`，不因补证自动改判；下一步仍应提交 S09/r03 由 Codex 复审，S10 仍 LOCKED。

修订：2026-10-25（S09/r04 B3 独立复审），Codex 只读核验 `verify_sealed.py`：90 项 manifest 0 失配、80 项 snapshot 全匹配、0 额外文件、0 封存后写入；三份历史失配文件均已在快照中固定。B3 判定 `PASS`，S09 具备解封条件，S10 具备开放条件。详见 [S09/r04 B3 复审报告](clearance-codex-s09-r04/REPORT.md)。

修订：2026-10-26（S04/r02 独立复审），Codex 复核 r02 manifest 152 项全匹配并重跑 S04 定向及后端全量测试。F02、N04 与已登记标签行为通过；未知标签仍被子串匹配，且 r01 部分 data/log 证据曾被 r02 脚本重写。S04 判定 `FAIL`，状态改为 `CHANGES_REQUIRED`；S05 保持 `LOCKED`。详见 [S04/r02 复审报告](clearance-codex-s04-r02/REPORT.md)。

修订：2026-10-27（S04/r03 独立复审及用户裁决），Codex 核验未知标签修复、隔离 API/shortlist、F02/N04、后端回归与证据哈希；用户明确回复“接受该历史证据例外”。r01 五个重建件仍标记原始字节不可恢复，未声称恢复原件。S04/r03 最终判定 `PASS`，S05 改为 `READY`；仅开放 S05，后续步骤仍按各自门禁。详见 [S04/r03 REVIEW](stages/S04/r03/REVIEW.md) 与 [独立复审报告](clearance-codex-s04-r03/REPORT.md)。

修订：2026-10-25（PRE-00/r02 独立复审），Codex 独立核对 66 项 manifest、真实硬链接文件身份守卫、CLI 反例、全新副本迁移、接口和后端回归。r01 的 FAIL-01 已关闭，PRE-00/r02 判定 `PASS`。详见 [PRE-00/r02 独立复审报告](clearance-codex-pre00-r02/REPORT.md)。当前开放步骤为 S00；S10 原有的 S09 解封资格保留为历史条件，但在 PRE-S10 清理计划的 S00–S08 与 BRIDGE-10 完成前不得施工。

修订：2026-10-25（S00/r01 独立复审），Codex 独立核对 143 项源码 manifest、重新运行后端全量/前端 build/颜色门禁、只读复测接口与 F07/N02/F09 现状，并复核三库保护和 18 项缺陷/矩阵。S00/r01 判定 `PASS`；S01 改为 `READY`；S07 继续 `DEFERRED`；S10 仍 `LOCKED`，BRIDGE-10 前不得施工。详见 [S00/r01 独立复审报告](clearance-codex-s00-r01/REPORT.md)，受审 manifest fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0`。

修订：2026-10-24（S09/r01 独立复审），Codex 独立运行证据校验和基线探针，复核数据来源、规模算术、stats/大屏矩阵、schema 缺口和实验协议。证据包保护检查通过，但 D01/D02/D04–D06/D11/D16–D20 及 C08/C10/C11/C13/C17 等关键决策未完成，且尚未同步 SSOT；S09 判定 `BLOCKED`，不得进入 S10。详见 [S09/r01 REVIEW](stages/S09/r01/REVIEW.md)。

修订：2026-10-31（文档同步，非审查事件），按用户要求「更新所有相关文档、同步项目进度」核对实际代码与数据，发现**台账记录的许可状态与实际施工已脱节**：S10–S20 对应的功能（万级数据导入通道、LLM 打标队列、后台 CRUD、13 个统计接口、DataManage、实验大屏、APK）多数已在主库实现并自测，`pytest -q` 为 430 passed / 1 skipped，但**均未经统一独立审查**。因此本台账**不据此改任何步骤状态、不签任何 PASS**，仅在文末新增「2026-10-31 实际施工快照」说明差距。SSOT 同步升至 v2.3.7（身份体系升级 + 6 张新表 + 大屏抽屉化）。S07 仍为 `READY`、S10–S20 仍为 `LOCKED`，历史审查记录全部保留。

任务：[BATCH4_PLAN.md](../../BATCH4_PLAN.md)｜规则：[REVIEW_RULES.md](../REVIEW_RULES.md)

## 当前许可

**当前许可：用户于 2026-10-28 改为合并大组连续开发、全部完成后统一独立审查。当前 G1（S07+S08）=READY；G2–G5 按合并计划顺序待施工，不再要求每个 S 子步骤先获 Codex PASS 才能继续。S07 仍未验收，不得记 PASS；其真实交互纳入 G1。S10–S20 的旧子步骤状态保留为历史审查状态，执行许可由本段和 [合并计划](CONSOLIDATED_REMAINDER_PLAN.md) 解释。** [S06/r02 REVIEW](stages/S06/r02/REVIEW.md)｜[S06/r02 独立复审报告](clearance-codex-s06-r02/REPORT.md)｜[S06/r01 REVIEW](stages/S06/r01/REVIEW.md)｜[S06/r01 独立复审报告](clearance-codex-s06-r01/REPORT.md)｜[S04/r03 REVIEW](stages/S04/r03/REVIEW.md)｜[S05/r01 REVIEW](stages/S05/r01/REVIEW.md)｜[S05/r01 独立复审报告](clearance-codex-s05-r01/REPORT.md)｜[S09/r04 B3 REVIEW](clearance-codex-s09-r04/REPORT.md)｜[S09/r02 REVIEW](stages/S09/r02/REVIEW.md)

2026-10-28 合并审查节奏：G1 S07+S08 → G2 BRIDGE-10+S10+S11 → G3 S12+S13 → G4 S14–S17 → G5 S18–S20。每组需完成组内自测和证据封存；五组完成后 Codex 一次性复核并逐项登记子步骤结论。任何人工手测“没问题”只记录为用户手测反馈，不等价于复审 PASS。

上一轮独立审查：[r03 独立复审总报告](clearance-codex-r03-2026-10-24/REPORT.md)。PC01/R02 FAIL（R3-01 快照校验/时序、R3-03 统计口径）、PC02/R01 维持 PASS、PC03/F12 FAIL（R3-02 词法漏检）；R2-03/R2-05 已 PASS。r04 已按该报告 §8 完成三项整改并由本轮独立复审关闭问题。

证据包：r01 保留在 `PC01/r01/`、`PC02/r01/`、`PC03/r01/`；r02 在 `PC01/r02/`、`PC02/r02/`、`PC03/r02/`；r03 在 `PC01/r03/`、`PC03/r03/`；r04 在 `PC01/r04/`、`PC03/r04/`。历史包均未被覆盖。

用户 2026-10-24 原话：「三项一起完成，完成后统一审查」——这是对串行顺序的调整，不是对验收标准的放宽；三项已各自取得独立 PASS。S09 已按本轮结论开放，后续批次 4 主线仍需逐步取得对应 PASS。

生效顺序：PC01/R02→PC02/R01→PC03/F12→S09 及后续批次 4。Room 划卡交互按用户确认延期，不阻挡本轮准入，冻结前补验；S00–S08 保留为未验收专项，不再逐个串行阻挡 S09。

**历史记录：仅 PC02/R01 在 r02 复审时已获独立 PASS；本轮 r04 已补发 PC01/R02 与 PC03/F12 的独立 PASS。** 用户允许施工、旧点击复查、开发方自测均不等于独立验收。R02 的大屏显示逐点核验留到 S17，后续准入时仍需实际验脚本→输出→隔离库；不得声称大屏当前已通过。

## 步骤状态

| 步骤 | 名称 | 状态 | 前置 | 最新审查/受审版本 | 下一步许可 |
| --- | --- | --- | --- | --- | --- |
| PC01 | R02 真实仿真与 benchmark | PASS | 用户确认清账路线 | [r04 PASS](stages/PC01/r04/REVIEW.md)，manifest `13d6c57b204dd6545198153cd64f7e40e718e6acbb8356801a0a952ca823389f`；R3-01/R3-03关闭 | 本项通过；S09 可进入 READY，S12/S13仍按后续步骤验收 |
| PC02 | R01 消除 N+1 与性能重测 | PASS | 用户改为一轮三项 | [r02 PASS](stages/PC02/r02/REVIEW.md)，manifest `671ccd00…b5b5a2`；CLR-04关闭 | 本项通过不授予S09/批次4许可；共享实现变化须复验 |
| PC03 | F12 颜色清理与脚本门禁 | PASS | 用户改为一轮三项 | [r04 PASS](stages/PC03/r04/REVIEW.md)，manifest `375bd6aede2e38544452b4012048c40d7a3397e99993e9e4ea0a76f4f0d203db`；R3-02关闭 | 本项通过；S09 可进入 READY，S08仍需专项验收 |
| S00 | 基线与整改清单 | PASS | PRE-00/r02 PASS | [S00/r01 PASS](clearance-codex-s00-r01/REPORT.md)；manifest fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0` | 本步通过；开放 S01 |
| S01 | 身份与资源归属 | PASS | S00/r01 PASS | [S01/r01 PASS](clearance-codex-s01-r01/REPORT.md)；manifest `3caa7db0…c4ad29` | 本步通过；开放 S02 |
| S02 | 数值与向量边界 | PASS | S01/r01 PASS | [S02/r02 PASS](clearance-codex-s02-r02/REPORT.md)；manifest fingerprint `2c8cc39d…c9556a`；r01 两项阻断关闭 | 本步通过；开放 S03 |
| S03 | 冰箱时效与采购 | PASS | S02/r02 PASS | [S03/r01 PASS](clearance-codex-s03-r01/REPORT.md)；manifest fingerprint `cd3d7c23…8c8fe`；F09 关闭 | 本步通过；开放 S04 |
| S04 | 四算法与决策红线 | PASS | S03/r01 PASS | [r03 PASS](stages/S04/r03/REVIEW.md)，[Codex 报告](clearance-codex-s04-r03/REPORT.md)；受审 manifest fingerprint `9767c3c1af3b96052c80a2ce27b88b0c21159cca8eb93eaeb36f7cf1ca38da02`；用户 2026-10-27 接受 S04-EVID-01 | F01/F02/N04 与历史证据例外均已关闭；开放 S05 |
| S05 | 首页与单人闭环 | PASS | S04/r03 PASS | [S05/r01 PASS](stages/S05/r01/REVIEW.md)；源码 manifest fingerprint 92ccd30d34e2a28210dc3bb78dd048185756f2aebd8d4d8fb6b031976d7cc5f9；基本点击由用户手测并确认 | 本步通过；开放 S06 |
| S06 | 多人后端与参数链 | PASS | S05/r01 PASS | [S06/r02 PASS](stages/S06/r02/REVIEW.md)；[独立复审报告](clearance-codex-s06-r02/REPORT.md)；manifest SHA-256 `cf50030fa624c5556fa6a47e47f4b32e3d11ce73b5a570d76228f39e1ee8628b`；r01 的 P2-S06-01/02 已关闭 | 本步通过；S07 保持 DEFERRED，按 PRE-S10 清理计划进入 S08 |
| S07 | 多人真实交互 | READY | 用户先前延期；现纳入 G1 合并补验 | 用户反馈本轮实际手测无问题（用户手测通过）；完整拖拽/扫码/多身份/恢复范围尚无可复核证据 | G1 完成并在统一审查通过后记正式 PASS |
| S08 | 移动端总回归 | READY | S06/r02 PASS；现与 S07 合并为 G1 | S06/r02 PASS；颜色先验 PC03 已 PASS；G1 尚未施工 | G1 完成后继续 G2，无中间 Codex PASS 门槛 |
| S09 | 批次 4 契约定稿 | PASS | PC01/PC02/PC03 PASS（三项全部 PASS 后） | [r04 B3 PASS](clearance-codex-s09-r04/REPORT.md)；r03 B1/B2/C10 与前置 PASS 沿用；S09 封存已闭合 | S09 已解封；可开始 S10，S10 施工仍需单独下达任务 |
| S10 | 基础数据导入 | LOCKED | G2 内先完成 BRIDGE-10，再依赖 S09 契约 | 尚无统一审查结论；按 G2 合并计划连续施工，证据保留在独立导入库 | 完成 G2 证据后进入 G3；最终统一审查前不得记 PASS |
| S11 | LLM 打标与查询扩容 | LOCKED | G2 内 S10 导入自测完成 | 尚无统一审查结论；调用规模/模型/费用确认仍是硬前置 | 依 G2 计划；外部调用未授权则 BLOCKED |
| S12 | 200 人行为仿真 | LOCKED | S11 PASS | 未审查 | 无 |
| S13 | 两组真实实验 | LOCKED | S12 PASS | 未审查 | 无 |
| S14 | 后台 CRUD 接口 | LOCKED | S13 PASS | 未审查 | 无 |
| S15 | 统计接口组 | LOCKED | S14 PASS | 未审查 | 无 |
| S16 | DataManage 页面 | LOCKED | S15 PASS | 未审查 | 无 |
| S17 | 17 项大屏 | LOCKED | S16 PASS | 未审查 | 无 |
| S18 | APK 真机验收 | LOCKED | S17 PASS | 未审查 | 无 |
| S19 | 批次 1–4 冻结 | LOCKED | S18 PASS | 未审查 | 无 |
| S20 | 展示壳与答辩交付 | LOCKED | S19 PASS | 未审查 | 无 |

状态含义：READY 可开始本步；IN_PROGRESS 本步施工；REVIEW_PENDING 待审且停手；CHANGES_REQUIRED 必须整改；BLOCKED 缺少必要条件；PASS 已通过指定版本；REOPENED 原证据失效需重审；DEFERRED 用户明确延期且未验收；LOCKED 不可开工。

只有 Codex 独立签发 PASS 并记录受审版本后，才可将主线的下一步改为 READY（不是机械解锁表格下一行）。任何当前步骤的必需项缺失或影响其结果的 P0/P1/P2 未关闭，不得写“条件通过”。

## 已知整改与对应步骤

此表只是待复核定位，不等于已重新出具缺陷结论。

| 编号 | 对应步骤 | 当前证据状态 |
| --- | --- | --- |
| F01/F02 | S04 | F02 通过；F01 的类别/具体标签语义已裁决，r03 未知标签精确匹配修复通过；S04-EVID-01 已由用户明确接受，S04 PASS |
| F03/F04/F05 | S06、S07 | 后端已有整改，完整多端时序与恢复待验 |
| F06 | S05 | 旧复查两档尺寸通过，绑定新基线回归 |
| F07 | S01 | 新增 ensure_self 与测试；所有用户上下文入口及冲突契约待验 |
| F08 | S02 | 新增校验；八维缺键/部分覆盖及合法边界待验 |
| F09 | S03 | 新增时效公共实现；精确到期边界与全部消费端待验 |
| F10 | S05、S06 | 单人有旧点击证据；群组参数作用域和传递仍待闭环 |
| F11 | S06、S07 | REST/WS 与真实划卡、扫码需分别验收 |
| F12 | PC03、S08 | PC03/r04 已 PASS；R3-02 按 JS/CSS/Vue 词法处理，23 隔离探针与 baseline 全PASS；原10处/五玻璃令牌数值保留，R2-05关闭；浏览器证据沿用历史，S08仍需专项验收 |
| F13 | S05 | 已有排除 ID 实现；完整耗尽换批与状态重置待验 |
| R01 | PC02、S11 | r02独立PASS；干净库6 passed、40/400目录真实API全响应等价，批量6 SELECT/库存1；legacy多一次预取已纠正口径；正式扩容还需复验 |
| R02 | PC01、S12/S13 | PC01/r04 已 PASS；R3-01 时间/结构/时序守卫与9例真实CLI、R3-03 聚合后封顶与 R>100 固定样本；两 seed 全量 40,000 票；截断旧库已标废弃；S12/S13 仍在对应步骤验收 |
| N01 | S05 | 抽屉 timer 卸载异常已有一行修复与旧点击证据，保留回归 |

## 审查历史

| 日期 | 事件 | 结论/许可 | 记录 |
| --- | --- | --- | --- |
| 2026-10-24 | 用户要求恢复逐步开发、Codex 审查后放行；建立本台账 | 仅 S00 READY；无实现验收 PASS | 开发细则与审查规则 v1.0 |
| 2026-10-24 | 用户确认按清账文件开始，逐项交 Codex 充分测试审查 | 当前改为仅 PC01 READY；Room 延期；仍无 PASS | BATCH4_PRE_CLEARANCE.md；细则/规则 v1.1 |
| 2026-10-24 | 用户调整为三项同轮提交；Codex 按 R02→R01→F12 独立审查 r01 | 三项 FAIL / CHANGES_REQUIRED；无新 PASS；S09 LOCKED | `clearance-codex-2026-10-24/REPORT.md`；三份 r01 REVIEW 绑定 manifest 哈希 |
| 2026-10-24（第二轮） | 开发方按 CLR-01～05 整改，提交 r02 三包 | 三项 REVIEW_PENDING；开发方未签 PASS；S09 与批次 4 仍 LOCKED | `stages/PC01/r02/`、`PC02/r02/`、`PC03/r02/`（含 SUBMISSION/BASELINE/CHECKS/SOURCE_MANIFEST/logs/data/browser） |
| 2026-10-24（r02独立复审） | Codex完整默认仿真、参数复跑、两seed原库只读复算、真实API40/400对照、颜色13探针、pytest/build | PC01 FAIL / PC02 PASS / PC03 FAIL；S09及批次4仍LOCKED | [r02总报告](clearance-codex-r02-2026-10-24/REPORT.md)；三份r02 REVIEW分别绑定完整manifest SHA；R2-01至05 |
| 2026-10-24（20:36–20:54补验） | 用户明确确认浏览器余额后，独立库/端口进行双屏真实点击、角色切换、用餐足迹闭环及日志检查 | 本次浏览器范围PASS；三包仍FAIL/PASS/FAIL，S09及批次4仍LOCKED | [新增浏览器报告](clearance-codex-r02-2026-10-24/browser-supplement/REPORT.md)；原始证据/最终数据保护均保留 |
| 2026-10-24（r03独立复审） | 两组完整规模仿真插桩、原库只读复算、真实seed CLI隔离反例、22颜色探针及语法核验、140 tests、6查询tests、build、双屏浏览器点击 | PC01 FAIL / PC02维持PASS / PC03 FAIL；R2-03/05 PASS；R3-01～03待整改；S09及批次4继续LOCKED | [r03总报告](clearance-codex-r03-2026-10-24/REPORT.md)；[PC01 REVIEW](stages/PC01/r03/REVIEW.md)、[PC03 REVIEW](stages/PC03/r03/REVIEW.md)绑定完整manifest SHA |
| 2026-10-24（r04提交） | 开发方按 r03 §8 只整改 R3-01/R3-03/R3-02；两组全量仿真、9例真实CLI、159 tests、24颜色探针、build | PC01/PC03 改 REVIEW_PENDING，开发方未签 PASS；PC02维持PASS；S09及批次4继续LOCKED | `stages/PC01/r04/`、`stages/PC03/r04/`（含 SUBMISSION/BASELINE/CHECKS/SOURCE_MANIFEST/logs/data/probes） |
| 2026-10-24（r04独立复审） | Codex 对 r04 证据包进行独立源码、CLI、隔离库、固定样本、颜色探针、pytest/build 核验；两份 manifest 全部匹配 | PC01/R02 PASS；PC02/R01 维持 PASS；PC03/F12 PASS；S09 改 READY；S10–S20 及未验收专项仍 LOCKED | [r04总报告](clearance-codex-r04-2026-10-24/REPORT.md)；[PC01 REVIEW](stages/PC01/r04/REVIEW.md)；[PC03 REVIEW](stages/PC03/r04/REVIEW.md) |
| 2026-10-25（S09/r02提交） | 用户确认中心点/合成数据/13 stats/schema/大屏指标/实验默认口径；开发方更新 SSOT v2.3.3，真实采集 3km POI（605，目标 1500+ 未达），提交 r02 | S09 改 REVIEW_PENDING；开发方未签 PASS；S10–S20 继续 LOCKED；D03 待裁决 | `stages/S09/r02/`（含 CONTRACT/DATA_PLAN/EXPERIMENT/DECISIONS/SUBMISSION/BASELINE/CHECKS/SOURCE_MANIFEST/validation/data/logs） |
| 2026-10-24（S09/r01独立复审） | Codex 独立运行 `validate_evidence.py`、`baseline_probe.py`，复核 13 stats/17 图矩阵、数据来源/许可证、规模算术、schema 和实验协议 | S09 BLOCKED；证据包和演示库保护通过，但关键决策未完成、SSOT 未同步；S10 继续 LOCKED | [S09/r01 REVIEW](stages/S09/r01/REVIEW.md) |
| 2026-10-25（S09/r02独立复审） | Codex 独立重算思源 POI、校验证据 JSON/manifest、运行后端基线；复核双校区变更影响 | S09 BLOCKED；思源证据基本成立，但双校区试抓/契约缺失、D03 未裁决、r02 manifest 失配；S10 继续 LOCKED | [S09/r02 REVIEW](stages/S09/r02/REVIEW.md) |
| 2026-10-25（S09/r04 B3独立复审） | Codex 只运行 `verify_sealed.py`，核对 90 项 manifest、80 项 snapshot、历史失配文件与封存后写入 | B3 PASS；S09 具备解封条件，S10 具备开放条件；S10 尚未施工 | [S09/r04 B3 REVIEW](clearance-codex-s09-r04/REPORT.md) |
| 2026-10-25（S00/r01独立复审） | Codex 核对 143 项 manifest、后端 175 tests、前端 build、颜色门禁、只读 API/F07/N02/F09、三库 SHA/schema/行数及 18 项缺陷矩阵 | S00 PASS；S01 READY；S07 DEFERRED；S10 仍 LOCKED | [S00/r01 REVIEW](clearance-codex-s00-r01/REPORT.md)，manifest fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0` |
| 2026-10-26（S02/r02独立复审） | Codex 重算 146 项 manifest、独立内存库 HTTP 反例、专项 96 条、隔离 basetemp 后端全量 | S02 PASS；S03 READY；其余步骤状态不变 | [S02/r02 REVIEW](clearance-codex-s02-r02/REPORT.md)，manifest fingerprint `2c8cc39df3a00c8f11c15ecf77d768da47e969447ba6a4fb5140885829c9556a` |
| 2026-10-26（S03/r01独立复审） | Codex 重算 147 项 manifest、固定时钟与时区边界、专项 63 条、后端全量 335 条、临时隔离 HTTP/数据库保护 | S03 PASS；S04 READY；其余步骤状态不变 | [S03/r01 REVIEW](clearance-codex-s03-r01/REVIEW.md)，manifest fingerprint `cd3d7c233fb347913a22e1bf6f67d84b185b40837f903931c2f643a15ec8c8fe` |
| 2026-10-26（S04/r01独立复审） | Codex 复算 150 项 manifest；复核 F01/F02/N04、固定样本、隔离 HTTP 与三库保护；定向 70 passed、后端 360 passed/1 skipped | F02/N04 与 C3/C4 通过；F01 具体忌口反向扩类待用户裁决；S04 BLOCKED，S05 不开放 | [S04/r01 REVIEW](stages/S04/r01/REVIEW.md)；[完整报告](clearance-codex-s04-r01/REPORT.md) |
| 2026-10-27（S04/r03独立复审） | 复核 154 项 manifest；核对未知标签精确匹配调用链、固定负例、隔离 HTTP/API-shortlist parity；复跑定向 75 passed、后端全量 365 passed/1 skipped；复核 r01 五个重建件哈希 | F01 修复、F02/N04 与数据库保护通过；S04-EVID-01 尚待用户接受，S04 BLOCKED，S05 继续 LOCKED | [S04/r03 REVIEW](stages/S04/r03/REVIEW.md)；[完整报告](clearance-codex-s04-r03/REPORT.md)，manifest fingerprint `9767c3c1af3b96052c80a2ce27b88b0c21159cca8eb93eaeb36f7cf1ca38da02` |
| 2026-10-27（S04-EVID-01用户裁决） | 用户明确接受 r01 五个文件为重建件、原始字节不可恢复的历史例外；Codex据此更新最终审查状态 | S04/r03 最终 PASS；S05 改为 READY；S05 之外步骤状态不变 | [S04/r03 最终 REVIEW](stages/S04/r03/REVIEW.md)；裁决与版本记录见 [独立报告](clearance-codex-s04-r03/REPORT.md) |
| 2026-10-27（S05/r01独立复审） | Codex 重算源码/证据清单，复跑后端全量、build、颜色门禁并核对受保护库；未执行真实浏览器点击，按用户明确选择 BLOCKED 收尾 | S05 BLOCKED；S06 继续 LOCKED | [S05/r01 REVIEW](stages/S05/r01/REVIEW.md)；manifest fingerprint 92ccd30d34e2a28210dc3bb78dd048185756f2aebd8d4d8fb6b031976d7cc5f9；[完整报告](clearance-codex-s05-r01/REPORT.md) |

| 2026-10-27（S05/r01用户手测补充） | 用户在已启动的本地页面完成手动检查并反馈无问题；Codex 接受用户明确指定的手测替代方式，不声称执行自动化点击；隔离库日志 16→20，三份受保护库未变 | S05/r01 最终 PASS；S06 改 READY；S07 DEFERRED、S08 仍 LOCKED | [S05/r01 REVIEW](stages/S05/r01/REVIEW.md)；manifest fingerprint `92ccd30d34e2a28210dc3bb78dd048185756f2aebd8d4d8fb6b031976d7cc5f9`；[复审报告](clearance-codex-s05-r01/REPORT.md) |
| 2026-10-27（S06/r01独立复审） | Codex 独立核对源码/证据 manifest、复跑 168 项定向与 388 项后端全量、build/颜色门禁；临时隔离库 REST/WS 复现完成后重复 join 仍 200，并用故障注入复现 sweeper 遇单次扫描异常即永久退出；受保护库哈希不变 | S06/r01 FAIL，改为 CHANGES_REQUIRED；P2-S06-01、P2-S06-02 未关闭；S07 仍 DEFERRED、S08/S10 继续 LOCKED | [S06/r01 REVIEW](stages/S06/r01/REVIEW.md)；受审 manifest SHA-256 `8650ff6b65640068c8ebd12d8359cfc67ff041d9258311ab778174b949829633`；[完整报告](clearance-codex-s06-r01/REPORT.md) |
| 2026-10-27（S06/r02独立复审） | Codex 核对 133 项源码与 60 项证据清单、独立重跑 S06 定向 171 passed/后端全量 391 passed、build/颜色门禁；临时隔离服务复验 SWIPING/FINISHED 重复 join=400、SQLite 锁瞬态故障后无人请求的 sweeper 自动完成结算；保护库哈希不变 | S06/r02 PASS；S07 保持 DEFERRED；S08 改 READY；S10 仍因 BRIDGE-10 未通过而 LOCKED | [S06/r02 REVIEW](stages/S06/r02/REVIEW.md)；manifest SHA-256 `cf50030fa624c5556fa6a47e47f4b32e3d11ce73b5a570d76228f39e1ee8628b`；[完整报告](clearance-codex-s06-r02/REPORT.md) |

后续每轮记录：步骤/轮次、审查时间、受审 manifest 哈希、结论、问题编号、REVIEW 路径、开放的下一步；失败、阻塞、撤销均保留。

## 2026-10-31 实际施工快照（**不构成验收，不改步骤状态**）

本节由文档同步轮补充，用于说明「台账许可」与「实际代码」之间的差距。**本节任何内容都不得被引用为 PASS 依据**；正式结论仍须由统一独立审查按 `REVIEW_RULES.md` 出具。

**自测基线（开发方自测）**：`pytest -q` → **430 passed / 1 skipped / 0 failed**；`npm run build` 通过；`app-debug.apk` 已产出。数据底座：门店 7,704 / 菜品 6,560 / 用户 7 / 流水 23 / 投票 0 / 反馈 1。

| 步骤 | 台账状态 | 实际代码状态 | 差距说明 |
|---|---|---|---|
| S07 多人真实交互 | READY | 用户手测反馈无问题；无自动化点击证据 | 与台账一致，仍缺可复核证据 |
| S08 移动端总回归 | READY | 五页可用，本轮又改背景渲染与评价入口 | 未做总回归，改动后更需重跑 |
| S10 基础数据导入 | LOCKED | **主库已有 7,704 门店 / 6,560 菜品**（含 6,400 条 `is_synthetic`）；另有后台 CSV/XLSX 导入页 | 导入通道已通，但数据来源、许可证与可复算性未留证据包 |
| S11 LLM 打标与查询扩容 | LOCKED | `tagging_status=SUCCESS` 6,560（全部打完）；打标已改为**任务队列** | 外部调用规模/模型/费用未在台账登记；缺 `allergen_tags` 843 道 |
| S12 200 人行为仿真 | LOCKED | **未入库**。G3 产出 48,000 流水 / 40,000 票仍在 JSONL | 直接后果：热力、桑基、周竞赛无数据支撑，相关图已从大屏移除 |
| S13 两组真实实验 | LOCKED | 仅有 `benchmark_json` 的算法对比曲线 | 缺「用了系统 vs 不用」的对照实验 |
| S14 后台 CRUD 接口 | LOCKED | 门店/菜品 CRUD、审计日志均已实现 | 未审查 |
| S15 统计接口组 | LOCKED | 13 个 `/admin/stats/*` 全部实现并接前端 | 未审查；口径改动过多次（质量指标、热力、词云） |
| S16 DataManage 页面 | LOCKED | 已实现，含质量面板、待补标签筛选、打标队列 | 未审查 |
| S17 17 项大屏 | LOCKED | **已收敛为三主题抽屉式，实际 13 项图表**（移除热力/桑基/周竞赛） | 与原「17 项」契约不一致，需审查时确认删减是否可接受 |
| S18 APK 真机验收 | LOCKED | `app-debug.apk` 已产出 | 未真机验收 |
| S19 批次 1–4 冻结 | LOCKED | 未冻结 | — |
| S20 展示壳与答辩交付 | LOCKED | **未开工** | — |

**台账外新增、尚未分配步骤编号的功能**（审查时需决定归入哪一步或新开步骤）：

1. 账号体系（注册/登录/登出/me + Bearer 令牌 + `require_admin`）
2. 用户管理页 + 角色切换（含防自锁）
3. 算法参数配置页（λ/ω/α/β/γ/δ 落库 + 热加载）
4. 单用户画像页（`GET /admin/users/{id}/overview`）
5. 数据导入页（CSV/XLSX + 字段映射 + 预览）
6. 移动端行为闭环：打卡结果面板、足迹评价（`dish_feedback`）、资料编辑、头像上传、背景全局、去哪吃跳转
7. 八维向量 → 自然语言解释（`utils/dishTalk.js`）

**结论**：项目在功能层面已覆盖批次 1–4 的主体，但**证据包与审查记录严重滞后**。若要走正式验收，缺口不在代码而在「证据封存 + 独立审查」，且 S12/S13 的数据与实验是硬缺口。
