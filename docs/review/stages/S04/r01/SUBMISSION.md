# S04 / r01 提交说明

步骤：S04 四算法与决策红线（F01 / F02 / N04）
轮次：r01
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
前置：[S03/r01 独立复审 PASS](../../../clearance-codex-s03-r01/REPORT.md)，受审 manifest fingerprint `cd3d7c233fb347913a22e1bf6f67d84b185b40837f903931c2f643a15ec8c8fe`

**未签 PASS；未修改 `docs/review/STAGE_STATUS.md`；未创建/修改任何 `REVIEW.md`；未开始 S05–S10；未触碰 `/admin`。** 本步只改后端算法与测试，未改前端、schema、迁移或数据库数据。

## 1. 用户裁决与落地

| 裁决 | 内容 | 落地 |
| --- | --- | --- |
| **D-S04-01 = A** | `feature_vector IS NULL` 的菜品不进入单人推荐候选、群组初筛及后续群组候选/结算；不得用 `normalize_vector(None)` 补 0.5；候选不足/为空时不回退纳入；API 契约和前端不变；排除数量记录在测试与证据 | `single_recommender.recommend_single`、`group_recommender.shortlist_candidates`、`member_prior_scores`、`compute_group_consensus` 四处加 `is None` 守卫；未新增响应字段 |

裁决记录：[`data/decision_n04.json`](data/decision_n04.json)。SSOT 未改（SSOT 允许 NULL 但未定义消费策略），API/schema/frontend 未改。

## 2. 实际修改文件

| 文件 | 改动 | 原因 |
| --- | --- | --- |
| `backend/algorithms/veto_rules.py` | 补「刺参」与单字「鱼」精确别名；从海鲜词尾规则移除「参」；抽出 `_search` 供 `find_hit`/`explain` 共用 | F01：`hits(["鱼"], ["海鲜"])` 原为漏判；`党参/人参` 原被「参」词尾误判；`explain` 原缺词尾规则，与 `hits` 不一致 |
| `backend/algorithms/single_recommender.py` | 候选组装跳过 `feature_vector is None` | D-S04-01：NULL 不进入单人推荐，不做 0.5 回退 |
| `backend/algorithms/group_recommender.py` | 初筛跳过 NULL；`member_prior_scores` 查询排除 NULL；结算候选排除 NULL；删除 VETO 分支的死分值读取 | D-S04-01；F02 的「VETO 只做掩码」语义显式化 |
| `backend/algorithms/combo_optimizer.py` | 仅改模块/函数说明为「Top-20 角色分组枚举 + 约束筛选」 | SSOT 第四章措辞锁定；枚举/剪枝逻辑未改 |
| `backend/tests/test_s04_algorithms.py` | **新增 25 条** | F01/F02/N04/C3/C4 的独立期望值与边界 |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、`docs/review/STAGE_STATUS.md`、`REVIEW.md`、`/admin`、S05–S20。

## 3. F01 忌口与黑榜：验收结果

### 3.1 红灯证据

修复前同一用例：[`logs/00_red_f01.log`](logs/00_red_f01.log)

- `hits(["鱼"], ["海鲜"]) == False`（漏判）；
- `hits(["鸡肉", "党参"], ["海鲜"]) == True`（误判），导致 `S04党参鸡汤` 被错误排除。

同一批 4 条用例：**1 failed, 3 passed, 16 deselected**，exit 1。

### 3.2 独立期望矩阵

`data/fixed_samples.json#veto_matrix`（13 行，expected 为硬编码）：

| 忌口 | 食材 | 期望 | 实际 |
| --- | --- | --- | --- |
| 海鲜 | 鲜虾 | 命中 | 命中 |
| 海鲜 | 紫菜/鸡蛋/虾皮（辅料） | 命中 | 命中 |
| 海鲜 | 螃蟹 | 命中 | 命中 |
| 海鲜 | 扇贝 | 命中 | 命中 |
| 海鲜 | 鱼（单字精确） | 命中 | 命中 |
| 海鲜 | 草鱼（词尾） | 命中 | 命中 |
| 海鲜 | 生菜/蚝油（辅料） | 命中 | 命中 |
| 海鲜 | 猪里脊/木耳/胡萝卜（鱼香肉丝） | 不命中 | 不命中 |
| 海鲜 | 豆腐/肉末（麻婆豆腐） | 不命中 | 不命中 |
| 海鲜 | 鸡肉/党参 | 不命中 | 不命中 |
| 海鲜 | 鱼香肉丝（作为食材名） | 不命中 | 不命中 |
| 香菜 | 牛肉/香菜 | 命中 | 命中 |
| 花生 | 花生米/菠菜 | 命中 | 命中 |

### 3.3 单人 API 与群组 shortlist 同口径

隔离副本 `backend/eatwhat_s04_r01_iso.db`，用户忌口 `["海鲜"]`，10 道受控菜（7 道应排除、3 道应保留）：

- 单人真实 HTTP：`POST /api/v1/recommend/single`，`X-User-Id` 为受控用户，`limit=100`，`exclude_dish_ids` 排掉 60 道种子菜。
- 群组 shortlist：同一隔离库直接调用 `shortlist_candidates(..., top_n=200)`。
- 两边受控保留集合**完全相同**：`S04探针鱼香肉丝`、`S04探针麻婆豆腐`、`S04探针党参鸡汤`。
- 7 道排除：鲜虾、虾皮（辅料）、螃蟹、扇贝、鱼、草鱼、蚝油（辅料）。
- 调用前后：受控菜行、用户偏好行、全部表行数与 `iso` 文件均由 [`data/live_api_probe.json`](data/live_api_probe.json) 记录；`db_state_unchanged=true`。

### 3.4 黑榜与硬约束

`test_s04_veto_and_blacklists_share_semantics_between_single_and_shortlist` 与 `test_s04_group_shortlist_uses_union_of_members_veto_and_blacklists` 覆盖：

- 菜品黑榜、门店黑榜（仅外食）与忌口在单人和群组初筛同口径；
- 群组取全体成员忌口/两类黑榜并集；
- 被排除的菜即使加入收藏、或用 `alpha=1` 权重覆盖，也不能回到结果；
- `broke_end_month` 的预算硬过滤不会被收藏绕过。

## 4. F02 全 VETO 与群组共识：验收结果

固定票矩阵的 expected 由手算 `R = 0.4×prior + 0.6×swipe`、`G = ω×mean + (1-ω)×min` 给出；先验由测试内独立余弦实现计算，不调用生产函数。详见 [`data/fixed_samples.json#group_consensus`](data/fixed_samples.json)。

| 场景 | 票型 | 独立期望 | 生产实际 |
| --- | --- | --- | --- |
| 正常 4 人，ω=0.5 | SL/LIKE/PASS/SL | R=[112,60,48,104]，mean=81，least=48，G=64.5 | 一致，winner=d1 |
| 同上，ω=1.0 / 0.0 | 同上 | G=81 / 48 | 一致 |
| 部分 VETO | d1 三张 SUPER_LIKE + u4 VETO；d2 全员 PASS | d1 掩码 G=0；d2 mean=48、least=24、G=36；winner=d2 | 一致 |
| 全 VETO | 两菜全员 VETO | winner=None，`has_consensus=false`，两菜 G=0 | 一致 |
| 零分同分（存活集） | d3/d5 同向量、全员 PASS | 两菜同分；按 dish_id 稳定取小 | 一致，winner=d3 |
| 无票 | 无任何票 | 按现有 TIMEOUT=60：R=[76,36,60,68]，mean=60，least=36，G=48 | 一致，有赢家 |

- 全部 VETO 时 `winner_dish_id=None`、`has_consensus=False`、`vetoed_dish_ids` 完整、每道菜 `masked_by_veto=true`；算法结果可解释。
- VETO 成员 `satisfaction=0` 且不进入 mean/least；三张高分票也不能让被否决菜复活。
- **说明**：无票的 `TIMEOUT=60` 是当前实现口径，SSOT 未定义缺席票；房间级语义仍由 S06 验收，本步不宣称已验收 WS/前端揭晓。

## 5. N04 NULL 向量：验收结果

实现（D-S04-01 A）：

- `recommend_single` 候选组装：`feature_vector is None` 直接跳过；后续打分循环不会见到 NULL，不调用 `normalize_vector(None)`。
- `shortlist_candidates`：同样跳过；候选为空返回 `[]`。
- `member_prior_scores`：查询条件加 `feature_vector IS NOT NULL`，不返回 0.5 默认先验。
- `compute_group_consensus`：候选菜中 NULL 不进入 `reports`；全为 NULL 时 `winner=None`、`has_consensus=False`、`dishes=[]`。
- 未改 `models.py/schemas.py`，未新增 API 响应字段；排除数量只写在测试与证据里。

证据：

- 单元：`test_s04_null_vector_excluded_from_single_and_shortlist`、`test_s04_null_vector_excluded_from_priors_and_consensus`、`test_s04_null_only_candidates_keep_existing_empty_semantics`。隔离库中 `feature_vector IS NULL` 计数为 1，单人/初筛/先验/结算均排除；只有 NULL 候选时 `recommendations=[]`、`combo=None`、shortlist `[]`、群组无赢家。
- 真实 HTTP：[`data/live_api_probe.json`](data/live_api_probe.json) 的 `null_vector`：
  - 隔离库 `dishes_and_recipes.feature_vector IS NULL` 前后均为 **1**；
  - NULL 菜 `dish_id=111` 未出现在单人结果、未出现在 shortlist；
  - 只保留 NULL 菜时，API 仍为 **200**，`recommendations=[]`、`combo=null`；
  - 调用前后数据库行数与受控数据不变。
- 数量记录：单元 1 道、隔离探针 1 道；真实 API 与 shortlist 返回 0 道 NULL。

## 6. S04-C3 公式与边界：验收结果

| 项目 | 独立期望 | 证据 |
| --- | --- | --- |
| 衰减同菜当天 | 0.05 | `fixed_samples.json#decay` |
| 精确 3 天 + 同菜系 1 天 | (1−e^−1.5)(1−0.4e^−0.5)=0.588392 | 同上，observed 0.5884 |
| 仅同菜系同日 | 0.6 | 同上 |
| 14 天边界 | 0.999088（仍在窗口） | 同上 |
| 15 天 | 1.0（窗口外） | 同上 |
| λ=1 同样本 | 0.810387 | 同上 |
| R=0.4×prior+0.6×swipe | 120/100/40 刻度；VETO 只掩码 | `#group_consensus`、`test_s04_vote_scale_mapping_matches_ssot` |
| ω 端点/中间值 | 0→least，1→mean，0.5→两者等权 | `#group_consensus` |
| 四权重归一化 | `craving_heavy` 下 α/β/γ/δ=0.4348/0.2174/0.1739/0.1739，和=1 | `#single_formula` |
| 原始分排序、展示封顶 | raw=95.6957，display=95.7；收藏后 raw=110.05、display=100 | 同上 + `test_s04_sort_uses_raw_score_when_display_values_tie` |
| 四人群组均值/最低分 | 81/48（正常样本） | `#group_consensus` |

## 7. S04-C4 套餐：验收结果

`data/fixed_samples.json#combo` 7 组：

- 预算恰好等于总价 → 有解；预算少 0.01 → 无解；
- 平均油腻度恰好 0.65 → 允许；0.6500001 → 拒绝；
- 缺角色 → 无解；Top-20 之外的 SOUP → 无解（证明先取 Top-20 再按角色分组）；
- 高分之选若使平均油腻度超限 → 被跳过，选低分但合规的组合（硬约束不被分数绕过）；
- 采购合并：`build_shopping_list` 主辅料并集去重，过期库存不抵扣，`owned/to_buy` 互斥；
- `lazy_one_pot`：仅按 `appliance_tag` 含 `电饭煲/一锅出` 筛选；`prep_speed=0.4` 的一锅出菜保留，`prep_speed≥0.8` 的免开火凉拌被排除，证明没有重新加回速度门槛；
- 代码/文档措辞：`combo_optimizer.py` 不再称分支限界/背包/动态规划，按 SSOT 称「Top-20 角色分组枚举 + 约束筛选」。

## 8. 验证结果（真实输出）

| 项目 | 结果 | 日志 |
| --- | --- | --- |
| 修复前 F01 红灯 | 1 failed, 3 passed, 16 deselected；exit 1 | `logs/00_red_f01.log` |
| S04 定向（S04 + 五个算法测试） | **70 passed**；exit 0 | `logs/01_s04_target.log` |
| 后端全量 | **360 passed, 1 skipped, 61 warnings**；exit 0 | `logs/10_backend_pytest_full.log` |
| 隔离真实 HTTP 探针 | 2 次 API 均 200；单人/初筛集合一致；NULL 未返回；空候选 0 条；`passed=true` | `logs/21_live_probe.log`、`logs/20_live_server.log`、`data/live_api_probe.json` |
| 固定样本 | 13 忌口 + 6 衰减 + 4 共识 + 7 套餐 + 1 单人公式，`all_match=true` | `logs/23_fixed_samples.log`、`data/fixed_samples.json` |
| 数据库保护 | 三受保护库 SHA 不变；隔离库 schema 与源库一致 | `logs/22_db_protection.log`、`data/db_protection.json` |

## 9. 已知限制与未验证范围

- **未改前端**：未跑 `npm run build`、界面门禁或浏览器；本步不声称视觉或点击验收。
- **未验真实房间 WS**：`CONSENSUS_REVEAL` 广播、断线恢复、真实划卡与前端揭晓留给 S06/S07；本步只验算法与隔离数据。
- **VOTE_SCORES 仍含 `VETO=-999` 作为枚举键**：`group_room.VALID_VOTE_TYPES` 依赖它，属于 F11/S06 的票型口径整改项；本步已删除推荐侧对该键的读取，VETO 不再有任何分值路径。
- **`normalize_vector(None)` 辅助函数仍返回全 0.5**：用于兼容非菜品向量（如历史 base_vector）；本步在四条推荐消费路径调用前显式判 `is None`，未依赖该默认值。Codex 若要求把辅助函数也改为拒绝 None，需先确认对 S02/历史数据的影响。
- **无票 TIMEOUT=60**：SSOT 未定义；本步按现有实现给独立期望，房间级规则留给 S06。
- **单字从严匹配的既有取舍**：`蟹味菇/贝贝南瓜/蚝油` 仍会被海鲜忌口挡掉（过敏口径从严）；本步只修正了明确的「参」词尾误判与「鱼」漏判，未扩大词表语义。
- `campus` 过滤（N02）、`deleted_at` 软删除（N03）、`/admin`、S10–S20、APK 不在本步范围。

## 10. 证据索引

| 文件 | 内容 |
| --- | --- |
| `BASELINE.md` | 源码/工作树/数据库身份/环境/未执行项 |
| `CHECKS.md` | 命令、cwd、起止时间、退出码、日志路径 |
| `SOURCE_MANIFEST.json` | 受审源码/测试/配置/文档/数据库 SHA-256 |
| `validation.json` | 验收矩阵、测试摘要、探针、固定样本、数据库保护 |
| `data/decision_n04.json` | D-S04-01 用户裁决与落地范围 |
| `data/live_api_probe.json` | 隔离库真实 HTTP、单人与 shortlist 对照、NULL 样本、DB 前后状态 |
| `data/fixed_samples.json` | 独立期望值、生产 observed、match |
| `data/db_protection.json` | 三受保护库、隔离库 schema/行数/NULL 计数 |
| `logs/` | 红灯、定向、全量、探针、固定样本、库保护、validation、manifest |
| `data/build_*.py` | 上述数据的可重跑脚本 |

提交后立即停手，等待 Codex 独立复审。
