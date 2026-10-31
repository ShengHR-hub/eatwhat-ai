# S04 / r03 提交说明

步骤：S04 四算法与决策红线（F01 / F02 / N04）
轮次：r03
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
上一轮：[S04/r02 FAIL](../r02/REVIEW.md)、[独立复审报告](../../../clearance-codex-s04-r02/REPORT.md)
用户裁决：D-S04-02 方案 A（2026-10-26，语义未变）

**未签 PASS；未修改 `docs/review/STAGE_STATUS.md`；未创建/修改任何 `REVIEW.md`；未开始 S05–S10；未触碰 `/admin`。** r01/r02 包保留，r03 不再写入 r01/r02。

## 1. 对 r02 两个问题的回应

| 问题 | 状态 | 处理 | 证据 |
| --- | --- | --- | --- |
| `S04-F01-UNK-01` 未知标签仍做子串匹配 | 已修复 | `_expand` 把未知 token 放入 `exact` 集合；`_search` 对 `exact` 只做规范化后全等；只有类别/具体同义词组做包含匹配 | `data/live_api_probe.json#unknown_tag`、`data/fixed_samples.json#veto_matrix` |
| `S04-EVID-01` r01 包内证据被重写 | 已冻结现状，待用户接受例外 | 5 个受影响文件标记为重建件并在 `data/r01_reconstructed_manifest.json` 固定当前 SHA-256；明确原始字节不可恢复；r03 未再写 r01/r02 | `data/r01_reconstructed_manifest.json`、`BASELINE.md` §5 |

## 2. 未知标签修复（S04-F01-UNK-01）

- `核桃` 不再命中 `核桃仁/核桃碎`；`秋葵` 不再命中 `秋葵炒蛋/秋葵籽`；`核桃仁` 不再反向命中 `核桃`。
- 精确候选 `秋葵` + 标签 `秋葵` 仍命中。
- 未登记的未知输入不扩到任何类别，也不做前缀/后缀/子串匹配。
- 已登记类别/具体同义词行为不变：`海鲜` 仍覆盖整类、`鲜虾` 只排虾类、`牛肉` 不排羊肉/猪肉。
- `data/decision_f01.json` 的 `semantics.unknown` 已改为“只做规范化后的全等”，与 statement 一致；修正 r02 的自相矛盾，不改变用户语义。

## 3. 实际修改文件

| 文件 | 改动 | 原因 |
| --- | --- | --- |
| `backend/algorithms/veto_rules.py` | 新增 `_expand()`，返回（已知包含 token、未知全等 token、类别 token）；`_search` 未知 token 全等、已知 token 包含、词尾规则只服务类别 | S04-F01-UNK-01 |
| `backend/tests/test_s04_algorithms.py` | 新增 `test_s04_unknown_tag_is_exact_only`、`test_s04_unknown_tag_parity_single_and_shortlist`；共 30 条 | 补未知标签全等正例/包含反例与单/群组 parity |
| `backend/algorithms/single_recommender.py` | 未改（N04 r01 已通过） | 保持 |
| `backend/algorithms/group_recommender.py` | 未改（N04 r01 已通过） | 保持 |
| `backend/algorithms/combo_optimizer.py` | 未改（r01 已按 SSOT 改措辞） | 保持 |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、`docs/review/STAGE_STATUS.md`、`REVIEW.md`、`/admin`、S05–S20。

## 4. 验证结果（真实输出）

| 项目 | 结果 | 日志 |
| --- | --- | --- |
| 修复前未知标签红灯 | **2 failed, 28 deselected**；exit 1 | `logs/00_red_unknown_tag.log` |
| S04 定向 | **75 passed**；exit 0 | `logs/01_s04_target.log` |
| 后端全量 | **365 passed, 1 skipped, 61 warnings**；exit 0 | `logs/10_backend_pytest_full.log` |
| 隔离真实 HTTP | 4 次调用均 200（类别正常 + 具体正常 + 未知正常 + 类别仅 NULL 空候选）；三用户 API/shortlist 集合一致；NULL 未返回；空候选 0 条 | `logs/21_live_probe.log`、`logs/20_live_server.log`、`data/live_api_probe.json` |
| 固定样本 | 42 忌口 + 6 衰减 + 5 共识 + 7 套餐 + 1 单人公式，`all_match=true` | `logs/23_fixed_samples.log`、`data/fixed_samples.json` |
| 数据库保护 | 三受保护库 SHA 不变；r03 隔离库 schema 与源库一致 | `logs/22_db_protection.log`、`data/db_protection.json` |

## 5. 隔离探针细节

[`data/live_api_probe.json`](data/live_api_probe.json)：

- **类别用户** `["海鲜"]`：保留 3、排除 7；单人与 shortlist 一致。
- **具体用户** `["鲜虾"]`：保留 8、排除 2（鲜虾/虾皮）；鲈鱼/螃蟹/扇贝保留；单人与 shortlist 一致。
- **未知用户** `["核桃"]`：保留 11（原 10 道受控菜 + 核桃仁），只排除精确的核桃；`核桃仁` 保留、`核桃` 不出现；单人与 shortlist 一致；证明未知标签不扩到类别、不做子串。
- NULL 菜在三个用户下均未返回；仅 NULL 候选时 API 200、`recommendations=[]`、`combo=null`。
- 数据库前后行数、三个受控用户偏好与受控菜不变；三受保护库 SHA 不变。

## 6. r01 证据例外（S04-EVID-01）

- r01 5 个受影响文件已固定当前哈希（见 `data/r01_reconstructed_manifest.json`），状态为 `RECONSTRUCTED_ORIGINAL_BYTES_UNRECOVERABLE`。
- r01 的 `SOURCE_MANIFEST.json`、`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、`REVIEW.md`、复审报告未改；r02 包未改；r03 未写入 r01/r02。
- **最终 PASS 仍需用户明确接受该历史例外，或提供可验证的原始备份。** r03 不把语义等价表述成字节原件恢复。

## 7. F02 / N04（保持 r02 已通过项）

- F02：`survivor_tie=52.8`，`test_s04_survivor_tie_is_stable`；合法非空成员下 `R>=24`，零分存活候选不可达；排序逻辑未改。
- N04：单人/初筛/先验/结算排除 `feature_vector IS NULL`；仅 NULL 时 API 200、空列表、`combo=null`；未新增响应字段。

## 8. 已知限制与未验证范围

- 未改前端：未跑 `npm run build`、界面门禁或浏览器。
- 未验真实房间 WS：广播、断线恢复、真实划卡与前端揭晓留给 S06/S07。
- 具体标签只对 `SPECIFIC_SYNONYMS` 中显式列出的组展开；未列出的具体食材与所有未知文本只做全等。
- 类别标签只有 `海鲜/海味/内脏/牛奶/辣` 五项。
- 单字从严的既有取舍：`蟹味菇/贝贝南瓜/蚝油` 仍可能被相应类别或同义词组挡掉。
- `VOTE_SCORES` 仍含 `VETO=-999` 作为枚举键（`group_room.VALID_VOTE_TYPES` 依赖），属于 F11/S06 口径项；推荐侧不读取。
- 无票 `TIMEOUT=60` 为现有实现口径，SSOT 未定义；房间级语义留给 S06。
- SSOT/AGENT_MEMORY 未改；D-S04-02 决策记录在包内。
- `campus` 过滤（N02）、`deleted_at` 软删除（N03）、`/admin`、S10–S20、APK 不在本步。

## 9. 证据索引

| 文件 | 内容 |
| --- | --- |
| `BASELINE.md` | 源码/工作树/数据库身份/r01 重建件/环境/未执行项 |
| `CHECKS.md` | 命令、cwd、起止时间、退出码、日志路径 |
| `SOURCE_MANIFEST.json` | 受审源码/测试/配置/文档/数据库 SHA-256 |
| `validation.json` | 验收矩阵、测试摘要、探针、固定样本、数据库保护、证据例外 |
| `data/decision_f01.json` | D-S04-02 修正后的具体/类别/未知标签语义 |
| `data/decision_n04.json` | D-S04-01（r01 确认，r03 保持） |
| `data/r01_reconstructed_manifest.json` | r01 5 个重建件的当前哈希与不可恢复声明 |
| `data/live_api_probe.json` | 类别/具体/未知三用户真实 HTTP、shortlist、NULL、DB 前后状态 |
| `data/fixed_samples.json` | 独立期望值、生产 observed、match |
| `data/db_protection.json` | 三受保护库、r03 隔离库 schema/行数/NULL 计数 |
| `logs/` | 红灯、定向、全量、探针、固定样本、库保护、validation、manifest |
| `data/build_*.py` | 上述数据的可重跑脚本 |

提交后立即停手，等待 Codex 独立复审。S05 保持 LOCKED；最终 PASS 前需用户接受 S04-EVID-01 历史例外或提供原始备份。
