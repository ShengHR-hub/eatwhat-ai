# S10 / r01 送审说明

- 日期：2026-10-25（Asia/Shanghai）
- 步骤：**S10 多源基础数据清洗与导入**
- 前置：S09 `PASS`（`docs/review/STAGE_STATUS.md` 已登记 S09/r04 B3 PASS、S10 READY）
- 性质：开发方提交验收包，**不签 PASS、不改台账、不创建 REVIEW.md、不进入 S11**
- 目标库：`backend/eatwhat_batch4.db`（独立批次 4 导入库）
- 演示库：`backend/eatwhat.db` 只读保护，SHA-256 未变

## 1. 本轮做了什么

1. 新增幂等迁移 `backend/scripts/migrate_s10_data_schema.py`：
   - `restaurants` 增加可空 `source_dataset/source_record_id/source_url/data_version/is_synthetic/deleted_at/campus`；
   - `dishes_and_recipes` 放宽 `feature_vector` 为可空，并增加 `allergen_tags/tagging_status/tagging_error/llm_meta/source_dataset/source_record_id/source_url/data_version/is_synthetic/deleted_at`；
   - `group_rooms` 增加可空 `campus`；
   - 增加 `ux_restaurants_source` 与 `ux_dishes_source` 唯一索引，支撑同批次重复导入不增行；
   - 不改变既有字段语义，重复执行无副作用。
2. 新增 `backend/scripts/fetch_amap_poi.py`：
   - 从 S09 封存 JSONL 导入真实 POI，不重新联网、不合成补足、不跨校区挪用；
   - 按校区生成合成食堂窗口，显式 `is_synthetic=1`；
   - 拒绝记录写入 JSONL，支持 `retry` 子命令重试。
3. 新增 `backend/scripts/import_open_recipes.py`：
   - 使用 D 类确定性合成模板生成 6,400 行共享下厨菜谱，显式 `is_synthetic=1`；
   - 菜名、`(name, ingredients_main)` 均唯一；
   - `feature_vector`/`allergen_tags`/`llm_meta` 保持 SQL NULL，`tagging_status=PENDING`，留给 S11。
4. 新增 `backend/scripts/verify_s10_import.py`：
   - SQLite 只读打开目标库，直接对封存输入与库内行重算，不采信导入脚本汇总；
   - 生成 `data/validation.json`、抽样映射、缺失字段、去重、幂等与 DB 清单。
5. 新增 `backend/tests/test_s10_import.py`（7 条），覆盖迁移幂等、POI 幂等、拒绝/重试、食堂隔离、菜谱唯一性与幂等。
6. `backend/models.py` 对齐 v2.3.3/v2.3.4 可空字段；`JSON(none_as_null=True)` 确保未打标字段落为 SQL NULL，而不是 JSON 文本 `null`。
7. 既有 `backend/scripts/init_seed_data.py` 未改语义，在隔离库实跑通过（4 用户/20 门店/100 菜/9 日志/0 房/0 票）。

## 2. 导入结果（库内重算）

| 校区 | 真实 POI（`AMAP_POI`，`is_synthetic=0`） | 合成食堂（`CANTEEN`，`is_synthetic=1`） | 合计 |
|---|---:|---:|---:|
| `SIYUAN` | **605** | **200** | **805** |
| `JIANDA_YANTA` | **6,659** | **200** | **6,859** |
| 合计 | 7,264 | 400 | 7,664 |

| 菜谱指标 | 值 |
|---|---:|
| `dishes_and_recipes` 行数 | **6,400** |
| 唯一菜名数 | **6,400** |
| 唯一 `(name, ingredients_main)` 数 | **6,400** |
| 模式 | `HOME_COOKING` 6,400 |
| 角色分桶 | `MEAT` 2,535 / `VEG` 2,605 / `SOUP` 644 / `ONE_MEAL` 616 |
| `feature_vector IS NULL` | 6,400 |
| `allergen_tags IS NULL` | 6,400 |
| `tagging_status` | `PENDING` 6,400 |

- 真实 POI 的两个输入文件行数、唯一 ID、3km 距离、campus、`is_synthetic=0`、来源字段与库内逐条一致；0 条越界、0 条重复、0 条拒绝。
- 思源缺失：rating 1、cost 178、tag 296；建大缺失：rating 7、cost 1,248、tag 2,788。缺失值在库内保持 NULL，未填 0/4.5/500。
- 合成食堂每校区 4 栋 × 5 层 × 10 窗口 = 200；rating/price 为 NULL，campus 明确，address 标注“演示占位，非真实采集”。

## 3. 逐项验收对照

| # | 验收要求 | 自测结果 | 证据 |
|---|---|---|---|
| 1 | 思源真实 POI 605、建大雁塔 6,659 | 通过；库内按 campus + source_type + is_synthetic 重算 | `data/validation.json` `db_real_counts` |
| 2 | 两校区合成食堂各 200，与真实 POI 分开 | 通过；400 条 `CANTEEN`，不计入真实 POI | `data/validation.json` `db_canteen_counts`、`canteen_separated_from_real` |
| 3 | 菜谱合成标记、来源说明、行数/唯一菜名数 | 通过；6,400 行 / 6,400 唯一名；`source_dataset=synthetic_recipe_v1` | `data/field_quality.json`、`data/dedup_report.json` |
| 4 | 30 思源 + 30 建大 + 30 菜谱可追溯 | 通过；30/30/30 条逐字段与输入/生成器比对 | `data/sample_poi_mapping.json`、`data/sample_recipe_mapping.json` |
| 5 | 所有真实 POI 唯一 ID、campus 正确、GCJ-02、3km 内 | 通过；ID 唯一、坐标与封存输入一致、最大距离 2,999m、0 越界 | `data/validation.json` `restaurant_id_unique`、`real_poi_coords_equal_input`、`real_poi_within_3km` |
| 6 | 字段枚举、外键、NULL、合成标记符合 SSOT | 通过；role/appliance 合法；`PRAGMA foreign_key_check` 空；rating/cost/feature_vector 缺失保持 NULL | `data/validation.json`、`data/db_inventory.json` |
| 7 | 同批次重复导入不增行 | 通过；五条重复导入 `inserted=0`，库 SHA 不变，逻辑指纹一致 | `data/idempotency_report.json`、`logs/16`–`20` |
| 8 | 拒绝/失败可定位、可重试 | 通过；隔离探针 1 条缺名拒绝→修正→重试成功，0 残留 | `data/reject_retry_probe.json`、`logs/23`–`25` |
| 9 | 演示库 SHA 不变，`group_rooms=0`、`room_votes=0` | 通过；SHA `775da7…60b`，房/票均 0 | `data/validation.json`、`data/db_inventory.json` |
| 10 | 只写隔离目标库 | 通过；目标库独立命名；迁移/导入对演示库均 exit 1 拒绝 | `logs/29`、`logs/30` |
| 11 | 后端测试真实运行 | 通过；`168 passed`；前端未改动，不适用 build | `logs/26_pytest_full.log` |
| 12 | 断言来自真实导入结果 | 通过；验证脚本只读目标库并重算输入，不使用导入汇总代替 | `backend/scripts/verify_s10_import.py`、`data/validation.json` |

## 4. 幂等与拒绝

- 批次号：`s10-full-20261025`；五类数据首轮共插入 605 + 6,659 + 200 + 200 + 6,400。
- 同批次第二轮：五类均 `inserted=0`，`existing` 分别 605 / 6,659 / 200 / 200 / 6,400；目标库 SHA 两轮前后均为 `315eb3da…18c28`。
- 指纹：餐厅行、菜品行、关联关系（当前 HOME 菜无门店关联）三组指纹均一致。
- 拒绝探针：`missing_name` 1 条被写入 `logs/reject_probe_rejects.jsonl`，修正后重试导入 1 条，残留 0；探针库随后删除并记录 SHA。

## 5. 保护与边界

- 未修改演示库、台账、`REVIEW.md`、`/admin`、stats、仿真逻辑；未进入 S11。
- 目标库只含 S10 基础数据：`users=0`、`algo_configs=0`、`eating_logs=0`、`group_rooms=0`、`room_votes=0`；演示用户/配置未复制进目标库。
- 未改前端或构建文件，未运行前端 build。
- 既有 `init_seed_data.py` 在隔离库实跑通过；未对演示库执行 `--force` 或任何清空。

## 6. 已知限制 / 待审查判断

1. **合成食堂坐标**：S09 `DATA_PLAN.md` §3 要求“用户确认校园边界后，把窗口坐标落在校园多边形内”。本轮任务未提供校园边界；为避免伪造真实位置，采用每校区 4 个确定性合成锚点（每栋 5 层 × 10 窗口共用锚点），锚点距该校区所有真实 POI 最近 102.6m、距中心 102–445m、均 <3km，`address` 明确“演示占位，非真实采集”。如审查要求严格满足“校园多边形”，需用户提供边界后重算坐标；本轮不声称已满足多边形约束。
2. **POI `tag` 字段**：SSOT §3 的 `restaurants` 没有 `tag` 列；原始 tag 保留在 S09 封存 JSONL，可按 `source_record_id` 追溯。缺失计数按输入统计，未在库内填默认值。S09 数据方案将 tag 定位为外食菜品候选，不在 S10 导入范围。
3. **菜谱打标**：6,400 行全部 `PENDING`、`feature_vector=NULL`，未实现 LLM 打标（S11）；未写占位向量。
4. **外食菜品**：S10 未导入外食菜单；本轮范围只含真实 POI、合成食堂、共享下厨菜谱。
5. **目标库用户/配置**：为保持独立导入库语义，未复制演示用户与 `algo_configs`；后续步骤如需要，应按批准流程另行处理。

## 7. 停手声明

本包只请求 Codex 独立审查 S10/r01。开发方不签 PASS、不修改 `docs/review/STAGE_STATUS.md`、不创建 `REVIEW.md`、不开始 S11/S12/S13 或 `/admin`。S10 审查结论与下一步许可由 Codex/用户按流程决定。
