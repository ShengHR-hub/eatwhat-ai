# S04 / r02 提交说明

步骤：S04 四算法与决策红线（F01 / F02 / N04）
轮次：r02
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
上一轮：[S04/r01 BLOCKED](../r01/REVIEW.md)、[独立复审报告](../../../clearance-codex-s04-r01/REPORT.md)
用户裁决：**D-S04-02 方案 A**（2026-10-26）

**未签 PASS；未修改 `docs/review/STAGE_STATUS.md`；未创建/修改任何 `REVIEW.md`；未开始 S05–S10；未触碰 `/admin`。** r01 原件保留，不覆盖。

## 1. 对 r01 两个问题的回应

| 问题 | 状态 | 处理 | 证据 |
| --- | --- | --- | --- |
| `S04-F01-SEM-01` 具体食材标签扩成整个类别 | 已按用户裁决修复 | `鲜虾` 只匹配虾类同义词组；`鲈鱼` 不扩到草鱼/三文鱼；`牛肉` 不扩到羊肉/猪肉；五项类别标签各自展开，不跨类 | `data/decision_f01.json`、`data/live_api_probe.json#specific_tag`、`data/fixed_samples.json#veto_matrix` |
| `S04-F02-EVIDENCE-01` “零分同分”名称与自报不符 | 已修正文案 | 测试改名为“存活候选同分稳定性”，固定样本补 `survivor_tie=52.8`；说明合法非空成员下 `R>=24`，零分存活候选不可达；排序逻辑未改 | `test_s04_survivor_tie_is_stable`、`fixed_samples.json#group_consensus` |

## 2. 用户裁决与落地

D-S04-02 原文要点：

- 五项类别标签：`海鲜`、`海味`、`内脏`、`牛奶`、`辣`，各自只展开到明确列出的成员，不跨类别。
- 具体食材标签只匹配自身及明确的同义词组：
  - `鲜虾` 不扩大到鱼/蟹/贝；
  - `鲈鱼` 不扩大到草鱼/三文鱼；
  - `牛肉` 不扩大到羊肉/猪肉；
  - 未知文本只精确匹配。
- 单人推荐与群组初筛继续共用同一规则。

落地：[`data/decision_f01.json`](data/decision_f01.json)、[`veto_rules.py`](../../../../backend/algorithms/veto_rules.py)。

## 3. 实际修改文件

| 文件 | 改动 | 原因 |
| --- | --- | --- |
| `backend/algorithms/veto_rules.py` | 新增 `CATEGORY_TAGS`（五项）、`SPECIFIC_SYNONYMS`、`_SPECIFIC_ALIAS_TO_GROUP`；`expand_tags` 按“类别/具体/未知”三分支；删除 `_ALIAS_TO_CANONICAL` 的反向类别扩展；更新说明 | S04-F01-SEM-01 / D-S04-02 |
| `backend/tests/test_s04_algorithms.py` | 新增 3 条具体标签/类别测试；F02 同分测试改名并断言 52.8；共 28 条 | 补正正反例与证据措辞 |
| `backend/algorithms/single_recommender.py` | 未改（N04 r01 已通过） | 保持 |
| `backend/algorithms/group_recommender.py` | 未改（N04 r01 已通过） | 保持 |
| `backend/algorithms/combo_optimizer.py` | 未改（r01 已按 SSOT 改措辞） | 保持 |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、`docs/review/STAGE_STATUS.md`、`REVIEW.md`、`/admin`、S05–S20。

## 4. F01 具体标签：验收结果

### 4.1 红灯（修复前）

[`logs/00_red_specific_tag.log`](logs/00_red_specific_tag.log)：**2 failed, 1 passed, 25 deselected**，exit 1。

- `hits(["鲈鱼"], ["鲜虾"]) == True`（应 False）；
- 单人推荐在 `veto_tags=["鲜虾"]` 下只保留青菜，鲈鱼/螃蟹/扇贝被误杀。

### 4.2 固定样本（35 行，expected 硬编码）

[`data/fixed_samples.json#veto_matrix`](data/fixed_samples.json)：

- `鲜虾`：鲜虾/虾仁/虾皮 命中；鲈鱼/螃蟹/扇贝/生蚝 不命中。
- `鲈鱼`：鲈鱼 命中；草鱼/三文鱼 不命中。
- `牛肉`：牛腩/肥牛 命中；羊肉/猪肉 不命中。
- `海鲜`：鲈鱼 命中（类别仍覆盖整类）。
- `海味`：紫菜 命中；鲈鱼 不命中。
- `内脏`：猪肝 命中；牛肉 不命中。
- `牛奶`：淡奶油 命中；辣椒 不命中。
- `辣`：辣椒 命中；牛奶 不命中。
- 原有类别/反例（鱼香肉丝/豆腐/党参）全部保持。

### 4.3 隔离库真实 HTTP 与群组 shortlist

[`data/live_api_probe.json`](data/live_api_probe.json)：

- **类别用户** `veto_tags=["海鲜"]`：单人 API 与 shortlist 都保留 3 道（鱼香肉丝/麻婆豆腐/党参鸡汤），排除 7 道海鲜类；两路径集合一致。
- **具体用户** `veto_tags=["鲜虾"]`：单人 API 与 shortlist 都保留 8 道（螃蟹/扇贝/鱼/草鱼/蚝油/鱼香肉丝/麻婆豆腐/党参鸡汤），只排除鲜虾与虾皮；`鲈鱼/螃蟹/扇贝` 不再被误杀；两路径集合一致。
- NULL 向量菜在两个用户下均未返回；数据库前后行数与受控数据不变；三受保护库 SHA 不变。

## 5. F02 证据措辞修正

- 测试改名：`test_s04_survivor_tie_is_stable`。
- 固定样本新增 `survivor_tie`：d3/d5 同向量、全员 PASS，独立手算 `R=[48,56,64,62.4]`、`mean=57.6`、`least=48`、`G=52.8`。
- 文案明确：合法非空成员下，未被 VETO 的最低票为 PASS=40（缺席 60），先验在 `[0,100]`，因此个体 `R>=24`，群组 `G>=24`；零分只属于被 VETO 掩码的候选，存活集按掩码筛选，不按分数筛选。
- 没有为凑“零分”构造空成员等非法房间输入；排序逻辑未改。

## 6. N04（保持 r01 PASS）

- 单人候选、群组初筛、先验、结算均跳过 `feature_vector IS NULL`；不回退 0.5。
- 仅 NULL 候选时 API 200、`recommendations=[]`、`combo=null`；群组无赢家/无共识。
- r02 隔离库 `feature_vector IS NULL` = 1；两个用户的 API/shortlist 均未返回该菜；DB 前后不变。
- 未新增响应字段，API/前端不变。

## 7. 验证结果（真实输出）

| 项目 | 结果 | 日志 |
| --- | --- | --- |
| 修复前具体标签红灯 | **2 failed, 1 passed, 25 deselected**；exit 1 | `logs/00_red_specific_tag.log` |
| S04 定向 | **73 passed**；exit 0 | `logs/01_s04_target.log` |
| 后端全量 | **363 passed, 1 skipped, 61 warnings**；exit 0 | `logs/10_backend_pytest_full.log` |
| 隔离真实 HTTP | 共 3 次调用均 200（类别正常 + 类别仅 NULL 空候选 + 具体正常）；两路径集合一致；NULL 未返回；空候选 0 条；`passed=true` | `logs/21_live_probe.log`、`logs/20_live_server.log`、`data/live_api_probe.json` |
| 固定样本 | 35 忌口 + 6 衰减 + 5 共识 + 7 套餐 + 1 单人公式，`all_match=true` | `logs/23_fixed_samples.log`、`data/fixed_samples.json` |
| 数据库保护 | 三受保护库 SHA 不变；r02 隔离库 schema 与源库一致 | `logs/22_db_protection.log`、`data/db_protection.json` |

## 8. 已知限制与未验证范围

- **未改前端**：未跑 `npm run build`、界面门禁或浏览器。
- **未验真实房间 WS**：广播、断线恢复、真实划卡与前端揭晓留给 S06/S07。
- **具体标签范围**：只对 `SPECIFIC_SYNONYMS` 中显式列出的组展开；未列出的具体食材（如鱿鱼、紫菜、猪肝、淡奶油、辣椒）只做精确匹配。需要更宽的同义词组时另立决策。
- **类别标签固定五项**：其他标签不享受类别展开。
- **单字从严的既有取舍**：`蟹味菇/贝贝南瓜/蚝油` 仍可能被相应类别或同义词组挡掉；本步未改变这一从严口径。
- **VOTE_SCORES 仍含 `VETO=-999` 作为枚举键**：`group_room.VALID_VOTE_TYPES` 依赖它，属于 F11/S06 口径项；推荐侧不读取。
- **无票 TIMEOUT=60**：SSOT 未定义，房间级语义留给 S06。
- **SSOT/AGENT_MEMORY 未改**：D-S04-02 决策记录在包内；如需同步 SSOT，请用户确认后再改。
- `campus` 过滤（N02）、`deleted_at` 软删除（N03）、`/admin`、S10–S20、APK 不在本步。

## 9. r01 保留与披露

- r01 的 `SOURCE_MANIFEST.json`（fingerprint `61c163e7…ad6df`）、`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、Codex 的 `REVIEW.md` 与复审报告均未改动。
- r02 准备期间，r02 脚本的 `OUT` 曾误指向 r01，导致 r01 的 `data/{fixed_samples,live_api_probe,db_protection}.json`、`validation.json` 与 `logs/20_live_server.log` 被重写；随后用 **r01 自己的脚本**按 r01 路径重新生成，语义与 r01 提交一致（13/6/4/7 样本、类别用户 3 保留/7 排除、NULL 排除），但 `generated_at`、隔离库 SHA 与部分日志时间已不同，**无法恢复逐字节原件**。
- r01 manifest 不覆盖包内 data/logs，因此 150 项源码清单不受影响；但 r01 包内证据的字节身份已改变，特此披露，供 Codex 判断是否需要另立 r01 补证。

## 10. 证据索引

| 文件 | 内容 |
| --- | --- |
| `BASELINE.md` | 源码/工作树/数据库身份/环境/未执行项 |
| `CHECKS.md` | 命令、cwd、起止时间、退出码、日志路径 |
| `SOURCE_MANIFEST.json` | 受审源码/测试/配置/文档/数据库 SHA-256 |
| `validation.json` | 验收矩阵、测试摘要、探针、固定样本、数据库保护 |
| `data/decision_f01.json` | D-S04-02 用户裁决与具体/类别展开规则 |
| `data/decision_n04.json` | D-S04-01（r01 确认，r02 保持） |
| `data/live_api_probe.json` | 类别/具体两个用户的真实 HTTP、shortlist、NULL、DB 前后状态 |
| `data/fixed_samples.json` | 独立期望值、生产 observed、match |
| `data/db_protection.json` | 三受保护库、r02 隔离库 schema/行数/NULL 计数 |
| `logs/` | 红灯、定向、全量、探针、固定样本、库保护、validation、manifest |
| `data/build_*.py` | 上述数据的可重跑脚本 |

提交后立即停手，等待 Codex 独立复审。S05 保持 LOCKED。
