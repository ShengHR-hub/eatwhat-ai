# 分步开发与独立审查台账

初始化日期：2026-10-24（Asia/Shanghai）

修订：2026-10-24，用户确认采用批次 4 前三项清账路线；取代初始化时只开放 S00 的安排。

修订：2026-10-24，用户明确「三项一起完成，完成后统一审查」，PC01 / PC02 / PC03 同轮提交。开发方已按该指令施工并提交证据包，**未签发 PASS**，待 Codex 统一审查。

修订：2026-10-24（第二轮），按 `D:\谷歌\BATCH4_REWORK_ROUND2.md` 与用户口头四句话整改 CLR-01～CLR-05，三项提交 **r02**：`docs/review/stages/PC01/r02/`、`PC02/r02/`、`PC03/r02/`。r01 包原样保留、不覆盖。三项状态改为 `REVIEW_PENDING`，开发方**不签 PASS**、未改动任何 `REVIEW.md`；S09 与批次 4 主线继续 LOCKED。

修订：2026-10-24（第三轮），按 `D:\谷歌\BATCH4_REWORK_ROUND2.md` 与用户第三次指令整改 R2-01～R2-05，提交 **r03**：`docs/review/stages/PC01/r03/`、`PC03/r03/`。R01 已 PASS 且本轮未改共享推荐逻辑/时钟/fixture，不重提。r01/r02 包原样保留、不覆盖。三项状态改 `REVIEW_PENDING`，开发方**不签 PASS**、未改动任何 `REVIEW.md`；S09 与批次 4 主线继续 LOCKED。

任务：[BATCH4_PLAN.md](../../BATCH4_PLAN.md)｜规则：[REVIEW_RULES.md](../REVIEW_RULES.md)

## 当前许可

**2026-10-24 Codex 独立复审（r02）：PC01 / R02 FAIL、PC02 / R01 PASS、PC03 / F12 FAIL。开发方已完成 r03 整改并提交证据包，等待复审；S09 及批次 4 主线仍 LOCKED，不碰 `/admin`。**

本轮审查：[r02独立复审总报告](clearance-codex-r02-2026-10-24/REPORT.md)。R02生产调用、配对和新曲线复现已核实，但force无快照代码保障、random满意度排除否决者、实际票数不足40,000，继续FAIL；R01干净库/40与400目录真实API对照通过；F12原10处已清理且数值不变，但门禁仍有4类漏检。此前未获余额确认而未启动浏览器，用户随后明确确认；已完成[独立浏览器补验](clearance-codex-r02-2026-10-24/browser-supplement/REPORT.md)，双屏导航/布局及用餐闭环范围PASS，不改变F12门禁FAIL。r01历史保留在[首轮报告](clearance-codex-2026-10-24/REPORT.md)。

证据包：r01 保留在 `docs/review/stages/PC01/r01/`、`PC02/r01/`、`PC03/r01/`；本轮整改证据在 `PC01/r02/`、`PC02/r02/`、`PC03/r02/`（**r01 未被覆盖**）。

用户 2026-10-24 原话：「三项一起完成，完成后统一审查」——这是对串行顺序的调整，不是对验收标准的放宽；三项仍各自需要独立 PASS。S09 及后续批次 4 主线仍未获开工许可。

生效顺序：PC01/R02→PC02/R01→PC03/F12→S09 及后续批次 4。Room 划卡交互按用户确认延期，不阻挡本轮准入，冻结前补验；S00–S08 保留为未验收专项，不再逐个串行阻挡 S09。

**仅PC02/R01本轮r02已获独立PASS，其余步骤没有新PASS**。用户允许施工、旧点击复查、开发方自测均不等于独立验收。R02的大屏显示逐点核验留到S17，准入时实际验脚本→输出→隔离库；不得声称大屏当前已通过。

## 步骤状态

| 步骤 | 名称 | 状态 | 前置 | 最新审查/受审版本 | 下一步许可 |
| --- | --- | --- | --- | --- | --- |
| PC01 | R02 真实仿真与 benchmark | REVIEW_PENDING | 用户确认清账路线 | [r02 FAIL](stages/PC01/r02/REVIEW.md) → 整改提交 [r03](stages/PC01/r03/)；R2-01/02/03 | 等待 r03 复审；S09 仍 LOCKED |
| PC02 | R01 消除 N+1 与性能重测 | PASS | 用户改为一轮三项 | [r02 PASS](stages/PC02/r02/REVIEW.md)，manifest `671ccd00…b5b5a2`；CLR-04关闭 | 本项通过不授予S09/批次4许可；共享实现变化须复验 |
| PC03 | F12 颜色清理与脚本门禁 | REVIEW_PENDING | 用户改为一轮三项 | [r02 FAIL](stages/PC03/r02/REVIEW.md) → 整改提交 [r03](stages/PC03/r03/)；R2-04/05 | 等待 r03 复审；不开放 S09 |
| S00 | 基线与整改清单 | LOCKED | 专项，另行开放 | 未审查；PC01 自带本项所需基线 | 无 |
| S01 | 身份与资源归属 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S02 | 数值与向量边界 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S03 | 冰箱时效与采购 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S04 | 四算法与决策红线 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S05 | 首页与单人闭环 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S06 | 多人后端与参数链 | LOCKED | 专项，冻结前补验 | 未审查 | 无 |
| S07 | 多人真实交互 | DEFERRED | 用户明确延期，冻结前补验 | 未审查；不挡本轮准入 | 无 |
| S08 | 移动端总回归 | LOCKED | 专项，冻结前补验 | 未审查；颜色先验 PC03 | 无 |
| S09 | 批次 4 契约定稿 | LOCKED | PC03 PASS（三项全部 PASS 后） | 未审查 | 无 |
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
| F12 | PC03、S08 | r02独立FAIL；原10处清理/数值保留成立，R2-04/05门禁漏检未关闭；真实浏览器双屏/点击范围已补验PASS，非S08专项验收 |
| F13 | S05 | 已有排除 ID 实现；完整耗尽换批与状态重置待验 |
| R01 | PC02、S11 | r02独立PASS；干净库6 passed、40/400目录真实API全响应等价，批量6 SELECT/库存1；legacy多一次预取已纠正口径；正式扩容还需复验 |
| R02 | PC01、S12/S13 | r02独立FAIL；生产外层调用52,000（自报51,000有误）、同场景和新曲线复现成立；R2-01快照、R2-02满意度、R2-03实际票数待整改 |
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

后续每轮记录：步骤/轮次、审查时间、受审 manifest 哈希、结论、问题编号、REVIEW 路径、开放的下一步；失败、阻塞、撤销均保留。
