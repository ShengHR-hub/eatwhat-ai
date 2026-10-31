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

修订：2026-10-24（S09/r01 独立复审），Codex 独立运行证据校验和基线探针，复核数据来源、规模算术、stats/大屏矩阵、schema 缺口和实验协议。证据包保护检查通过，但 D01/D02/D04–D06/D11/D16–D20 及 C08/C10/C11/C13/C17 等关键决策未完成，且尚未同步 SSOT；S09 判定 `BLOCKED`，不得进入 S10。详见 [S09/r01 REVIEW](stages/S09/r01/REVIEW.md)。

任务：[BATCH4_PLAN.md](../../BATCH4_PLAN.md)｜规则：[REVIEW_RULES.md](../REVIEW_RULES.md)

## 当前许可

**2026-10-25 S09/r02 独立复审已完成：思源单校区证据基本成立，但双校区范围、D03 裁决和 r02 manifest 完整性未闭合，S09 判定 BLOCKED；S10–S20、`/admin` 与未验收专项继续 LOCKED。** [S09/r02 REVIEW](stages/S09/r02/REVIEW.md)｜[r04 总报告](clearance-codex-r04-2026-10-24/REPORT.md)｜[S09/r01 REVIEW](stages/S09/r01/REVIEW.md)

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
| S00 | 基线与整改清单 | LOCKED | 专项，另行开放 | 未审查；PC01 自带本项所需基线 | 无 |
| S01 | 身份与资源归属 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S02 | 数值与向量边界 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S03 | 冰箱时效与采购 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S04 | 四算法与决策红线 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S05 | 首页与单人闭环 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S06 | 多人后端与参数链 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S07 | 多人真实交互 | DEFERRED | 用户明确延期，冻结前补验 | 未审查；不挡本轮准入 | 无 |
| S08 | 移动端总回归 | LOCKED | 专项，冻结前补验 | 未审查；颜色先验 PC03 | 无 |
| S09 | 批次 4 契约定稿 | BLOCKED | PC01/PC02/PC03 PASS（三项全部 PASS 后） | r02 独立复审 BLOCKED；思源真实 POI 605 + 200 合成食堂=805；建大雁塔真实 POI 6,659 + 合成食堂 200=6,859 已试抓；思源 D03 未裁决，r02 manifest 失配 | 创建 S09/r03，完成双校区契约与思源 D03 裁决后重新审查；S10 仍 LOCKED |
| S10 | 基础数据导入 | LOCKED | S09 PASS | 未审查 | 无 |
| S11 | LLM 打标与查询扩容 | LOCKED | S10 PASS | 未审查 | 无 |
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
| F01/F02 | S04 | 已有整改与历史测试，待新基线独立复核 |
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

后续每轮记录：步骤/轮次、审查时间、受审 manifest 哈希、结论、问题编号、REVIEW 路径、开放的下一步；失败、阻塞、撤销均保留。
