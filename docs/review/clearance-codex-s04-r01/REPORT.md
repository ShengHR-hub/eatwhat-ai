# S04/r01 独立复审

审查时间：2026-10-26 22:53（Asia/Shanghai）  
审查方：Codex  
受审版本：`docs/review/stages/S04/r01/SOURCE_MANIFEST.json`，150 项；fingerprint `61c163e74d8a1cef08ab3a35e2778459b28afb62d67f501db04f4e4d185ad6df`。Codex 登记台账前逐项复算为 150/150 匹配；登记本报告后，清单内唯一差异是审查方更新的 `docs/review/STAGE_STATUS.md`（清单 SHA `e19e9e6a…275a22`，当前 SHA `73134b95…993760`），其余 149 项匹配。  
数据版本：S04 隔离库 `eatwhat_s04_r01_iso.db`；真实 HTTP 探针使用 `127.0.0.1:8016`。演示库、S10 库、开发源库的当前 SHA-256 与证据包记录一致。  
审查范围：F01、F02、N04 及 S04-C1～C5；未修改业务代码或数据库。

## 验收结果

| 条目 | 独立检查方法 | 实际结果 | 状态 |
| --- | --- | --- | --- |
| 证据身份 | 在台账更新前复算 manifest，并在登记后复核差异 | 提交版本 150 项全部匹配；登记后只有台账文件一项因 Codex 登记结论而变化，其他 149 项仍匹配；fingerprint 与提交值一致 | PASS |
| F01 类别忌口 | 核对别名实现、13 组固定样本、单人 API 与群组 shortlist 证据；重跑相关测试 | `海鲜` 对虾/蟹/贝/鱼及辅料命中，鱼香肉丝、豆腐、党参反例通过；两路径集合一致 | PASS（所测类别输入） |
| F01 具体忌口语义 | 内存库实际调用单人推荐与群组 shortlist：忌口 `鲜虾`，候选为鲜虾、鲈鱼、青菜 | 两条路径都只保留青菜；鲜虾以外的鲈鱼也被排除。当前 SSOT 未定义具体标签是否应扩成整个类别 | BLOCKED，待产品决策 |
| F02 否决与胜出 | 检查全 VETO、部分 VETO、缺席、稳定同分代码和固定期望；定向用例复跑 | 全 VETO 为无赢家；部分 VETO 不能复活；排序按 group score 降序、dish_id 稳定升序 | PASS（零分样本说明见问题记录） |
| N04 NULL 向量 | 检查四个消费点；核对真实隔离 HTTP 探针和数据前后状态 | 单人、初筛、先验、结算均排除 NULL；仅 NULL 候选时 API 200、空推荐、`combo=null` | PASS |
| S04-C3/C4 | 核对独立公式、固定样本和自动化输出 | 衰减、群组权重/刻度、单人权重、组合约束和采购样本与独立期望一致 | PASS |
| 数据保护 | 复算三份受保护库当前 SHA-256；检查隔离 HTTP 探针前后状态 | `eatwhat.db` `775da775…bd3a60b`；`eatwhat_batch4.db` `315eb3da…6918c28`；开发库 `b965e73e…706a579`，均未变。8016 无监听进程 | PASS |
| 回归 | 核对提交包日志并复跑 veto/consensus/NULL 相关用例 | S04 定向 70 passed；后端全量 360 passed, 1 skipped；本轮再跑相关筛选 6 passed。前端未改，不属于本步构建范围 | PASS |

## 问题与说明

### S04-F01-SEM-01：具体食材忌口会扩成整个类别

`backend/algorithms/veto_rules.py:127-155` 为每个别名建立 `_ALIAS_TO_CANONICAL`，而 `expand_tags()` 对命中的别名再加入该类别的全部别名。因此 `veto_tags=["鲜虾"]` 不只会匹配虾类，也会匹配鱼和螃蟹。复测结果：内存隔离库中受控菜 ID 为鲜虾 1、鲈鱼 2、青菜 3；单人推荐和群组 shortlist 都只返回 `[3]`。

前端 Profile 接受任意文本（`Profile.vue:169-175,338-339`），API 的 `veto_tags` 也没有类别白名单（`schemas.py:116`、`auth_user.py:146-147`）。SSOT 将其定义为绝对忌口/过敏原数组，并规定命中 `ingredients_main/aux` 时硬过滤，但没有规定“具体食材标签反向扩成上级类别”。工程记忆描述的是“类别 → 别名”展开，也未记录反向扩展。故此行为不能仅凭实现注释视为已获批准。

影响是用户输入一个具体食材时，算法会悄悄隐藏整个类别的有效菜品。请先裁决：

- 建议方案：仅类别标签（如“海鲜”）展开到类别成员；具体食材标签只匹配该食材及明确声明的同义词，不扩到整个上级类别。补单人与群组正反例，并保持两路径一致。
- 若确实希望任一成员标签代表整个类别，则需由用户确认，并把这一语义与前端提示同步写入 SSOT，再补验证用例。

这是 S04 的行为契约缺口，未得到裁决前不能签 PASS，开发方不得自行选定产品语义。

### S04-F02-EVIDENCE-01：零分同分测试名称与自报不符

`backend/tests/test_s04_algorithms.py:537-554` 的 `test_s04_zero_score_tie_among_survivors_is_stable` 使用四名成员全部投 `PASS`；Codex 在同一夹具上独立复算，两道存活菜的 `group_score` 都是 **52.8**，不是 0。固定样本 `group_consensus` 也只有 normal / partial_veto / all_veto / no_votes 四组，没有零分存活同分组。

这不构成当前排序代码缺陷：合法非空成员中，未被 VETO 的每张票最低为 `PASS=40`（缺席为 60），先验在 `[0,100]`，所以个体 `R >= 24`，群组均值、最低值及其凸组合 `G` 也至少为 24。零分候选只能是被 VETO 掩码的候选；存活集按掩码筛选，不按分数筛选。现有 52.8 同分测试仍验证了稳定的 `dish_id` 次序，全 VETO 另有独立无赢家测试。

请在下一轮证据中把测试/提交说明改称“存活候选同分稳定性”，并说明合法输入下零分存活候选不可达；不要为满足测试名称构造空成员等非法房间输入。此项是证据表述修正，不单独阻断本轮，F01 决策仍是总阻断项。

## 实际执行与范围

- manifest：台账更新前 150 项 SHA-256 全部匹配；登记后 149 项仍匹配，唯一变化是本次由 Codex 更新的 `STAGE_STATUS.md`（manifest `e19e9e6a…275a22` → 当前 `73134b95…993760`）。提交包原件与 fingerprint 未改。
- 相关测试复跑：`python -m pytest tests/test_s04_algorithms.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r01-codex-recheck -k "veto_alias or zero_score_tie or all_veto or partial_veto or null_vector"`：**6 passed, 19 deselected**。
- S04 定向与后端全量结果：**70 passed**；**360 passed, 1 skipped**（完整输出保存在送审包原日志）。
- 内存隔离数据探针：`veto_tags=["鲜虾"]` 下，鲜虾/鲈鱼/青菜候选 ID 为 1/2/3；单人和群组分别只返回 `[3]`。
- 隔离 HTTP 证据：两次推荐请求均 200；单人与 shortlist 控制集合一致；NULL 菜未返回；隔离库行数及受控记录不变。
- 本步未改前端、未运行浏览器；本步提交未包含 UI 改动。未触碰 `/admin`、S05–S10 或受保护数据库。

## 最终判定

结论：**BLOCKED**。F02 的核心无赢家/掩码行为、N04 NULL 排除及其余已测算法项通过；但 F01 对具体食材忌口的类别扩展没有 SSOT 或用户裁决，且会造成可复现的过度过滤。

下一步：**不允许开始 S05**。请用户先裁决 `鲜虾` 这类具体标签的匹配范围；裁决后由开发方提交新的 S04/r02 包，保留 r01 原件，按决定修正实现/文档并补正 F02 证据措辞，再由 Codex 独立复审。

台账更新：`docs/review/STAGE_STATUS.md` 将 S04 记为 `BLOCKED`；未放行任何后续步骤。
