# S10 / r01 证据映射

- 目标库：`backend/eatwhat_batch4.db`（SHA `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28`）
- 验证脚本：`backend/scripts/verify_s10_import.py`（只读打开目标库）
- 断言来源：`data/validation.json` 的 37 项检查由脚本直接读取目标库与封存输入重算；`data/import_summary.json` 只作运行记录，不作为验证结论。

## 1. 验收条目 → 证据

| 要求 | 证据文件 | 关键字段 / 检查 ID |
|---|---|---|
| 思源 605 / 建大 6,659 真实 POI | `data/validation.json`、`data/dedup_report.json`、`data/input_manifest.json` | `db_real_counts`、`input_counts_match_s09`、`real_poi` 分桶 |
| 两校区合成食堂各 200、与真实分开 | `data/validation.json`、`data/field_quality.json`、`data/import_canteen_*_first.json` | `db_canteen_counts`、`canteen_separated_from_real`、`canteen_all_valid` |
| 菜谱合成标记/来源/行数/唯一名 | `data/field_quality.json`、`data/dedup_report.json`、`data/import_recipes_first.json` | `synthetic_recipes.rows=6400`、`unique_names=6400`、`feature_vector_null=6400` |
| 30 思源 + 30 建大 + 30 菜谱追溯 | `data/sample_poi_mapping.json`、`data/sample_recipe_mapping.json`、`data/sample_mapping_check.json` | `samples[].checks` 全部 true；`input_sha256`/`input_line_no`/`generated_record_sha256` |
| 唯一 ID、campus、GCJ-02、3km | `data/validation.json`、`data/field_quality.json` | `restaurant_id_unique`、`real_poi_coords_equal_input`、`real_poi_within_3km`、`no_unknown_campus` |
| 枚举、外键、NULL、合成标记 | `data/validation.json`、`data/db_inventory.json` | `recipe_rows_all_valid`、`foreign_key_check`、`sqlite_integrity_check`、`demo_*` |
| 同批次重复导入不增行 | `data/idempotency_report.json`、`data/fingerprint_before_second.json`、`data/fingerprint_after_second.json`、`logs/16`–`20` | 三个 delta=0；三组指纹相等；`idempotent_reimport` |
| 拒绝/失败可定位可重试 | `data/reject_retry_probe.json`、`data/reject_probe_source_input.jsonl`、`data/reject_probe_fixed_input.jsonl`、`logs/23`–`25`、`logs/reject_probe_rejects.jsonl` | 首轮 1 拒绝；重试 imported=1 / remaining=0 |
| 演示库不变、房/票为 0 | `data/db_inventory.json`、`data/validation.json`、`logs/28`–`30` | `demo_db.sha256`、`group_rooms_zero`、`room_votes_zero`、`demo_db_sha_unchanged` |
| 只写隔离目标库 | `data/validation.json`、`logs/29`、`logs/30` | `target_db_isolated`；演示库迁移/导入均 exit 1 |
| 后端测试真实运行 | `logs/26_pytest_full.log`、`logs/exit_codes.json` | `168 passed`，exit 0 |
| 断言来自真实导入结果 | `backend/scripts/verify_s10_import.py`、`data/validation.json` | 只读 SQLite + 输入重算；不使用导入汇总作为断言 |

## 2. 输入与输出身份

| 对象 | 路径 | 证据 |
|---|---|---|
| 思源 POI 输入（605） | `docs/review/stages/S09/r02/data/amap_pois.jsonl` | `data/input_manifest.json` SHA `5cdf4953…e478` |
| 建大 POI 输入（6,659） | `docs/review/stages/S09/r02/data/amap_jianda_pois.jsonl` | `data/input_manifest.json` SHA `ac0a7b24…b7c7` |
| 菜谱合成输入 | `backend/scripts/import_open_recipes.py` + seed 20261025 | `data/input_manifest.json` `synthetic_recipe_input.canonical_jsonl_sha256` |
| 目标库 | `backend/eatwhat_batch4.db` | `data/db_inventory.json` SHA/字节/表计数 |
| 演示库（只读） | `backend/eatwhat.db` | `data/db_inventory.json` `demo_db` |
| 临时探针库 | 已删除 | `data/temp_probe_dbs.json` 记录哈希与用途 |

## 3. 失败留痕

| 日志 | 说明 |
|---|---|
| `logs/09a_sample_mapping_check_failed_jsonnull.log` | 发现 JSON `None` 落为文本 `'null'`；修复为 `none_as_null=True` |
| `logs/15a_verify_after_first_failed.log` | 验证脚本食堂名称模式/跨校区 ID 口径错误；修复后重跑通过 |
| `data/sample_mapping_check_failed_jsonnull.json` | 上述失败时的小样核对结果原件 |
| `logs/31_git_diff_models.log` | `models.py` diff；含此前已存在的 `algo_params` 行，非本轮新增 |
