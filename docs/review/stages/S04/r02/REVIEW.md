# S04 / r02 审查

审查时间：2026-10-26 23:44（Asia/Shanghai）  
审查方：Codex  
受审版本：SOURCE_MANIFEST fingerprint `f23f227014d275dc51171305fa7f635268a6d7d4ba1150f37c754378ba306350`；台账更新前 152/152 项匹配。  
审查报告：[S04/r02 独立复审报告](../../../clearance-codex-s04-r02/REPORT.md)

## 验收结果

| 条目 | 结果 |
| --- | --- |
| F01 已登记具体标签与类别标签 | 已测样本通过；单人与群组筛选集合一致 |
| F01 未知标签只精确匹配 | **失败**；未知「秋葵」误命中「秋葵炒蛋」，未知「核桃」误命中「核桃仁」 |
| F02 存活候选同分稳定性 | 通过；独立固定值为 52.8，winner 稳定 |
| N04 NULL 向量排除 | 通过；隔离 API/shortlist 未返回 NULL 菜 |
| 回归 | S04 定向 73 passed；后端全量 363 passed, 1 skipped, 61 warnings |
| 数据保护 | 三份受保护库当前 SHA 与提交证据一致 |
| r01 证据保留 | **存在例外**；r01 的 data/validation/logs 中多项被重建，原始字节无法恢复，详见总报告 |

## 问题

- `S04-F01-UNK-01`（P2）：未知标签匹配仍是子串匹配。`backend/algorithms/veto_rules.py:217` 未按已登记同义词与未知输入区分匹配策略；补精确匹配边界测试、未知标签 API/shortlist 反例，并修正 `data/decision_f01.json` 内部口径矛盾。
- `S04-EVID-01`（P2，审计例外）：r01 部分证据被 r02 输出路径重写，无法恢复原字节。后续不得再改写旧轮；S04 最终放行前需用户接受该历史例外或提供原始备份。

## 最终判定

结论：**FAIL**。登记台账状态 `CHANGES_REQUIRED`；**S05 仍 LOCKED**。不授权任何后续步骤。
