# S04/r03 独立复审报告

审查时间：2026-10-27 00:12（Asia/Shanghai）  
审查方：Codex  
受审版本：`docs/review/stages/S04/r03/SOURCE_MANIFEST.json`，fingerprint `9767c3c1af3b96052c80a2ce27b88b0c21159cca8eb93eaeb36f7cf1ca38da02`  
审查范围：S04/r03 对 r02 未知忌口标签缺陷的修复，以及 S04-EVID-01 历史证据例外。S05 及其他后续步骤不在本轮放行范围。

## 结论

**最终结论：S04/r03 PASS；S05 READY。** 初审时因 S04-EVID-01 判为 BLOCKED；用户于 2026-10-27 明确回复“接受该历史证据例外”后，该流程阻断解除。原始字节仍不可恢复，接受例外不等于恢复原件。

用户所问的轮次问题：r02 报告要求在新的整改轮处理未知标签精确匹配；r03 是合适且已完成的独立整改轮。r03 没有回写 r01/r02，但也不能把重建件描述成原始字节已恢复。

## 逐项复核

| 条目 | Codex 独立核验 | 结论 |
| --- | --- | --- |
| r02 缺陷复现 | r02 原报告记录 `秋葵` 命中 `秋葵炒蛋`、`核桃` 命中 `核桃仁`。r03 修复前红灯日志复现两项错误；修复后的固定负例均不再命中。 | PASS |
| 未知标签匹配 | `veto_rules.py` 的 `_expand` 将未知 token 与登记类别/同义词分开；`_search` 对未知 token 只作规范化后全等。单人和群组推荐仍调用同一个 `veto_hits`；检索未发现生产代码调用会丢失 token 类型的 `expand_tags`。 | PASS |
| 已登记标签回归 | 类别标签、`鲜虾` 同义词组、`鲈鱼` 与 `牛肉` 的具体标签边界保留；相关正反例在 S04 测试中覆盖。 | PASS |
| 单人/群组一致性 | 检查隔离 HTTP 探针与 shortlist：类别、具体标签、未知标签三组 API 与 shortlist 结果集合一致；未知用户精确保留 `核桃仁`、排除精确 `核桃`。 | PASS |
| F02 / N04 | 独立固定样本中忌口/衰减/群组/套餐分别 42/6/5/7 组匹配，`survivor_tie=52.8`；NULL 向量菜未进入单人、shortlist 或空候选 API 结果。 | PASS |
| 自动化回归 | r03 定向测试 `75 passed`；后端全量 `365 passed, 1 skipped, 61 warnings`。单个 skip 是既有 Windows 符号链接权限限制；日志所列 warnings 为既有弃用/依赖提示。 | PASS |
| 隔离与库保护 | 探针使用独立副本；r03 记录三份受保护库 SHA 不变、隔离库状态前后不变，manifest 对应文件哈希复核一致。 | PASS |
| r01 历史证据 | 五个重建件的当前哈希均与 `r01_reconstructed_manifest.json` 一致；用户明确接受该历史例外。哈希固定只能证明当前重建件稳定，不能证明它们等同于原件。 | PASS（接受例外） |

## 证据与方法

- r02 独立报告要求：未知输入只做规范化后全等；补精确正例和包含负例；保留已登记类别/同义词行为；真实隔离 API/shortlist 复测。参见 [r02 报告](../clearance-codex-s04-r02/REPORT.md) 与 [r02 REVIEW](../stages/S04/r02/REVIEW.md)。
- 源码调用点：[`veto_rules.py`](../../../backend/algorithms/veto_rules.py:177)、[`single_recommender.py`](../../../backend/algorithms/single_recommender.py:58)、[`group_recommender.py`](../../../backend/algorithms/group_recommender.py:28)。未知词正反例及 API/shortlist parity 测试见 [`test_s04_algorithms.py`](../../../backend/tests/test_s04_algorithms.py:296)。
- 提交日志：`../stages/S04/r03/logs/00_red_unknown_tag.log`、`01_s04_target.log`、`10_backend_pytest_full.log`、`21_live_probe.log`、`23_fixed_samples.log`、`22_db_protection.log`。
- 提交身份：154 项 manifest；审查登记前逐项重算，缺失/哈希不符为 0。r01 重建件清单为 5 项，逐项哈希不符为 0。
- 三组隔离探针结果：海鲜类别保留 3/排除 7；鲜虾具体标签保留 8/排除 2；未知核桃标签保留 11/排除 1。各组单人 API 与 shortlist 一致，NULL 菜未返回。
- 未改前端，浏览器/build 不适用于本轮后端算法范围；未运行房间 WebSocket 或真实划卡，留在相应步骤验收。

## S04-EVID-01

r02 的 `CHECKS.md` 披露，r02 准备时输出目录误指向 r01，导致以下五个 r01 文件被重建：`data/fixed_samples.json`、`data/live_api_probe.json`、`data/db_protection.json`、`validation.json`、`logs/20_live_server.log`。执行端无法提供可验证的原始备份。r03 已将这些文件标记为 `RECONSTRUCTED_ORIGINAL_BYTES_UNRECOVERABLE` 并冻结当前哈希；r03 未继续写入 r01/r02。用户于 2026-10-27 明确回复“接受该历史证据例外”。

用户已接受该例外。S04/r03 最终判定为 PASS，S05 改为 READY；S05 仍须按自己的开工卡和验收标准执行。

## 台账与 manifest 变更

审查开始时，r03 manifest 中 `docs/review/STAGE_STATUS.md` 的 SHA-256 为 `3fbe1c60cae52137d6f7edc7f99e84a2f2724e652ca34d3035ae1a18453dfb10`。初审登记 BLOCKED 后该值变为 `730b56e507e1b08c8eaa91f94bea2fb757c0588970be9ed452d50b4c753d06b8`；记录用户接受并最终放行后，当前值为 `7fbc62c0c49b99299266d0950357605bf2caa7196a82a7e342d40b5b7d8e0846`。这仍是唯一由审查登记造成的清单差异；未变更业务源码或数据库。154 项 manifest fingerprint 代表提交时的 r03 版本。

新增文件：[S04/r03 REVIEW](../stages/S04/r03/REVIEW.md)。未改 r01/r02 的提交包或历史报告。

## 用户裁决补记

2026-10-27（Asia/Shanghai），用户明确回复“接受”。Codex 据此关闭 S04-EVID-01 的流程阻断，将 S04/r03 最终登记为 `PASS`，并按 S05 前置条件将 S05 登记为 `READY`。该裁决接受的是证据例外，不改变五个文件为重建件的事实，也不恢复其原始字节。
