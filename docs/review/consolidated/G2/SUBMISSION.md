# G2 提交说明（BRIDGE-10 + S10 + S11）

- 日期：2026-10-28（Asia/Shanghai）
- 状态：**已封存，等待统一独立复审**。开发方未签 PASS、未改台账、未创建 `REVIEW.md`。
- 结论摘要：S10 导入与幂等自测通过；S11 在缺少 Key/模型/预算时按规则 BLOCKED（0 付费调用）；BRIDGE-10 首轮发现单人推荐未接校区（P1），**已修复并复验**，`self_test_ok=true`。仍不宣称 Codex PASS。

## 1. 改动与新增

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `backend/scripts/llm_batch_tagger.py` | 新增 | S11 打标器：每批 20、附录 C 提示词、整批重试 3 次、失败清单、断点/不覆盖成功、dry-run 预检、只写 G2 库 |
| `backend/scripts/bridge_s10_runtime.py` | 新增 | BRIDGE-10 显式导入边界：运行时副本 ← S10 导入库，按唯一来源键幂等 |
| `backend/schemas.py` | 修改 | `SingleRecommendRequest` 新增 `campus`，外食缺失返回 422 |
| `backend/routers/recommend.py` | 修改 | 把 `campus` 传入单人算法 |
| `backend/algorithms/single_recommender.py` | 修改 | 外食按 `restaurant.campus` 过滤，NULL/跨校区排除；下厨不受影响 |
| `frontend/src/stores/algo.js` | 修改 | 推荐请求带 `mode.campus` |
| `backend/tests/test_g2_single_campus.py` | 新增 | 5 条校区契约回归；受影响的旧 API 测试请求体已补 campus |
| `docs/review/consolidated/G2/**` | 证据 | 本轮全部数据、日志与复验脚本 |

未改应用 API/算法/schema/`/admin`；未写演示库、S10 库、G1 库或 S09 证据。

## 2. BRIDGE-10

| 验收条目 | 方法 | 结果 | 证据 |
| --- | --- | --- | --- |
| 运行库与 S10 库边界 | 运行时 API（8000）指向 G1 运行库；桥接副本（8010）由显式脚本生成 | 运行库无任何 S10 数据集；S10 大库未被当作演示库；演示用户/日志/库存保持来自运行库 | `data/bridge_api.json`、`data/bridge_provenance.json` |
| 双校区数据归属 | 桥接库 SQL | SIYUAN 真实 605 + 合成食堂 200；JIANDA_YANTA 6,659 + 200；NULL 校区仅 20 条历史种子，未归属任何校区 | 同上 |
| 群组外食按校区过滤 | `POST /rooms/create` + 候选门店反查 | SIYUAN/JIANDA 候选全部落在本校区；跨校区 join → 409 | `bridge_api.json.group_out` |
| 下厨菜谱共享 | 同一用户分别建两校区下厨房 + 单人下厨推荐 | 候选/推荐 dish_id 完全一致 | `bridge_api.json.home_shared/group_home_shared` |
| 合成食堂按校区单列 | SQL 分组 | 每校区 `synthetic_canteen_v1` 200，未与真实 POI 混计 | `bridge_provenance.json.campus_stats` |
| NULL campus 不误归属（群组） | 候选门店反查 | 通过 | `group_out` |
| 外食单人推荐按校区过滤 / 缺 campus 422 / NULL 不误归属 | `POST /recommend/single`（修复后重跑） | 通过：缺 campus → 422；SIYUAN/JIANDA 结果全部落在本校区；NULL 不出现 | `bridge_api.json.recommend_out` |
| 统计请求随校区变化 | `/admin/stats/overview` | 404（统计接口属 S15，未实现） | `admin_stats` |
| 前端校区切换 UI | — | SSOT v2.3.6 明确留后续专项，本轮只验 API 层 | — |

### BRIDGE-10-P1（已按用户裁决修复并复验）

- 原缺陷：单人推荐未接校区，缺 `campus` 仍 200，且可返回 NULL / 另一校区门店。
- 修复：schema 加校区必填校验；路由透传；算法按 `restaurant.campus` 过滤；前端请求带 `mode.campus`；新增 5 条回归并迁移受影响 API 测试（测试库种子店标为 SIYUAN，生产种子不变）。
- 复验：桥接探针全部通过；`pytest` **396 passed / 1 skipped**；`home-fit`/`refill`/`sandbox`/build/colors 全部 exit 0；S08 在修复后重跑并更新证据（见 `G1/RECHECK_AFTER_G2_CAMPUS_FIX.md`）。

## 3. S10 基础数据导入

| 条目 | 结果 | 证据 |
| --- | --- | --- |
| 小样先行 | 40 POI + 20 食堂 + 60 菜谱；40/40 与 60/60 映射逐字段通过 | `data/smoke_mapping.json` |
| 全量 POI | SIYUAN 605、JIANDA 6,659；rejected 0、failures 0；保留 GCJ-02；分页/限流/失败字段见汇总 | `data/import_counts.json`、`data/full/poi_*.json` |
| 合成食堂 | 每校区 200，`is_synthetic=1`、`source_type=CANTEEN`、rating/价格 NULL、地址标注合成 | `data/full/canteen_*.json` |
| 共享菜谱 | 6,400 行、6,400 唯一菜名；`is_synthetic=1`、`tagging_status=PENDING`、fvector/allergen NULL | `data/full/recipes.json`、`coverage.json` |
| 抽样 | POI 60 条（≥30）+ 菜谱 30 条 | `data/sample_mapping.json` |
| 官方验证 | 36/36 checks，`overall_ok=true`；demo 库 SHA 未变 | `data/full_verify/validation.json` |
| 幂等 | 复跑后行数与三类指纹完全一致（delta 0） | `data/idempotency.json` |
| 断点/失败/拒绝 | 导入器自带 existing/skipped/duplicate/rejected/failures；重复批次不新增；无 destructive seed | 汇总 JSON |
| 原始/去重/有效/拒绝 | 见 `import_counts.json.count_chain`，按校区与来源分桶 | 同上 |

## 4. S11 LLM 打标

| 条目 | 结果 |
| --- | --- |
| 前置确认 | **BLOCKED**：`LLM_API_KEY` 缺失，模型/单价/预算未确认；`network_calls=0` |
| 批次计划 | 6,400 道 → 320 批；含重试上限 3 → 最多 960 次调用；输入约 53.4 万 tokens、输出约 57.6 万 tokens |
| 预算 | 未给单价与上限，拒绝发起付费调用 |
| 覆盖 | 成功覆盖 0（未调用），不伪造；向量异常 0 |
| 查询预算 | 下厨库存查询恒为 1 条（旧实现 32 条），limit 5/10/24 总 SQL 恒为 6；top3 与旧实现一致 |
| 回归 | `pytest` 396 passed / 1 skipped；前端 build 与四条门禁 exit 0 |
| 断点/不覆盖成功/失败清单 | 已在脚本实现（`--retry-failed`、SUCCESS 跳过、失败 JSONL）；本轮无真实调用，未产生批次日志 |

证据：`data/s11_preflight.json`、`data/s11_dryrun_full.json`、`data/coverage.json`、`data/query_budget.json`、`logs/16_s11_preflight.log`。

## 5. 数据库与保护

| 库 | 用途 |
| --- | --- |
| `backend/eatwhat_g2_s10_smoke.db` | 小样导入（60 门店 / 60 菜） |
| `backend/eatwhat_g2_s10_full.db` | 全量导入（7,664 门店 / 6,400 菜） |
| `backend/eatwhat_g2_bridge_iso.db` | 运行库副本 + S10 数据桥接（仅验证，不替代演示库） |

受保护库（演示、batch4、dev、S05/S06、G1）SHA 全部未变；S09 r04 manifest 哈希未变（`data/db_protection.json`、`logs/21–22`）。回滚：删除 `eatwhat_g2_*.db` 即可。

## 6. 交付物

`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、`SOURCE_MANIFEST.json`、`validation.json`、`logs/`、`data/`、`source_manifest/`。
