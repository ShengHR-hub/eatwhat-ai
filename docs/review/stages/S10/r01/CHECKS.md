# S10 / r01 检查记录

- cwd：`D:/EatWhat`
- 时区：Asia/Shanghai
- 运行日期：2026-10-25
- 每条命令的完整日志、日志创建/修改时间与退出码见 `logs/exit_codes.json`；本文件给出摘要。
- `09a`、`15a` 是保留的历史失败日志；修复后已重跑并保留两条链路。

## 1. 命令与结果

| 序号 | 命令（摘要） | 退出码 | 结果 | 日志 |
|---|---|---:|---|---|
| 01 | 目标库首次迁移 | 0 | 建表 + 两个唯一索引 | `logs/01_migrate_target.log` |
| 02 | 目标库重复迁移 | 0 | `idempotent=true` | `logs/02_migrate_target_again.log` |
| 03 | 小样库迁移 | 0 | 隔离库 | `logs/03_migrate_sample.log` |
| 04 | 思源 POI 小样 30 条 | 0 | inserted=30 | `logs/04_sample_poi_siyuan.log` |
| 05 | 建大 POI 小样 30 条 | 0 | inserted=30 | `logs/05_sample_poi_jianda.log` |
| 06 | 思源食堂小样 10 条 | 0 | inserted=10 | `logs/06_sample_canteen_siyuan.log` |
| 07 | 建大食堂小样 10 条 | 0 | inserted=10 | `logs/07_sample_canteen_jianda.log` |
| 08 | 菜谱小样 30 条 | 0 | inserted=30，唯一名 30 | `logs/08_sample_recipes.log` |
| 09 | 小样字段映射核对 | 0 | 20 POI + 10 食堂 + 10 菜谱全通过 | `logs/09_sample_mapping_check.log` |
| 09a | 小样字段映射核对（历史） | 1 | 发现 JSON None→文本 `null`；已修复 | `logs/09a_sample_mapping_check_failed_jsonnull.log` |
| 10 | 思源真实 POI 全量 | 0 | inserted=605，rejected=0 | `logs/10_full_poi_siyuan_first.log` |
| 11 | 建大真实 POI 全量 | 0 | inserted=6,659，rejected=0 | `logs/11_full_poi_jianda_first.log` |
| 12 | 思源合成食堂全量 | 0 | inserted=200 | `logs/12_full_canteen_siyuan_first.log` |
| 13 | 建大合成食堂全量 | 0 | inserted=200 | `logs/13_full_canteen_jianda_first.log` |
| 14 | 合成菜谱全量 | 0 | inserted=6,400，唯一名 6,400 | `logs/14_full_recipes_first.log` |
| 15 | 首次全量库内验证 | 0 | 37 项全 PASS | `logs/15_verify_after_first.log` |
| 15a | 首次全量库内验证（历史） | 1 | 食堂名称模式/跨校区 ID 检查口径错误；修复后重跑 | `logs/15a_verify_after_first_failed.log` |
| 16 | 思源 POI 同批次复导入 | 0 | inserted=0，existing=605 | `logs/16_reimport_poi_siyuan.log` |
| 17 | 建大 POI 同批次复导入 | 0 | inserted=0，existing=6,659 | `logs/17_reimport_poi_jianda.log` |
| 18 | 思源食堂同批次复导入 | 0 | inserted=0，existing=200 | `logs/18_reimport_canteen_siyuan.log` |
| 19 | 建大食堂同批次复导入 | 0 | inserted=0，existing=200 | `logs/19_reimport_canteen_jianda.log` |
| 20 | 菜谱同批次复导入 | 0 | inserted=0，existing=6,400 | `logs/20_reimport_recipes.log` |
| 21 | 最终验证 + 幂等对比 | 0 | 37 项全 PASS；三组指纹一致 | `logs/21_verify_final.log` |
| 22 | 拒绝探针库迁移 | 0 | 隔离库 | `logs/22_reject_probe_migrate.log` |
| 23 | 拒绝探针导入 | 0（`--allow-rejects`） | 1 入库 + 1 条 `missing_name` 拒绝 | `logs/23_reject_probe_first.log` |
| 24 | 修正后重试 | 0 | imported=1，remaining=0 | `logs/24_reject_probe_retry.log` |
| 25 | 拒绝探针汇总 | 0 | 终态 2 行、0 残留拒绝 | `logs/25_reject_probe_summary.log` |
| 26 | `python -m pytest -q` | 0 | **168 passed**，505 warnings | `logs/26_pytest_full.log` |
| 27 | 既有种子脚本（隔离库） | 0 | 4 用户/20 门店/100 菜/9 日志 | `logs/27_seed_isolated.log` |
| 28 | 种子库计数与保护 | 0 | 4/20/100/9/0/0；演示库 SHA 未变 | `logs/28_seed_isolated_counts.log` |
| 29 | 演示库迁移保护 | 1（预期） | 拒绝迁移演示库 | `logs/29_demo_db_guard_migrate.log` |
| 30 | 演示库导入保护 | 1（预期） | 拒绝写入演示库 | `logs/30_demo_db_guard_import.log` |
| 31 | `git diff -- backend/models.py` | 0 | S10 schema diff | `logs/31_git_diff_models.log` |
| 32 | 生成 `SOURCE_MANIFEST.json`（临时脚本） | 0 | manifest 最后生成、自排除 | `logs/32_manifest_generation.log` |

## 2. 关键断言

- 真实 POI：思源 605、建大 6,659；唯一 `id`、唯一 `(source_type,campus,source_dataset,source_record_id)`；坐标与封存输入逐条一致；最大距离 2,999m；0 越界；0 跨校区挪用。
- 合成食堂：每校区 200；`source_type=CANTEEN`、`is_synthetic=1`、rating/price NULL；锚点距真实 POI 最近 102.6m；未混入真实 POI 计数。
- 菜谱：6,400 行 / 6,400 唯一名 / 6,400 唯一 `(name, ingredients_main)`；全部 `HOME_COOKING`、`is_synthetic=1`、`tagging_status=PENDING`、`feature_vector` 为 SQL NULL。
- 约束：`PRAGMA integrity_check=ok`；`PRAGMA foreign_key_check` 空；`ux_restaurants_source`、`ux_dishes_source` 存在。
- 演示库：SHA `775da775…3a60b` 与 S09/r04 记录一致；`group_rooms=0`、`room_votes=0`。
- 目标库：SHA `315eb3da…18c28`；第二批复导入前后完全一致。

## 3. 失败与修复留痕

1. **JSON NULL 口径**：首次小样核对发现 `feature_vector`/`allergen_tags`/`llm_meta` 的 Python `None` 被 SQLAlchemy JSON 写成文本 `'null'`，不是 SQL NULL。改为 `JSON(none_as_null=True)` 后重建小样库并重跑；失败日志 `09a` 保留。
2. **验证脚本口径**：首次全量验证把 `建大·` 基础名重复拼接了 `·`，且跨校区 ID 检查把按校区重复的食堂 `canteen-001` 视为冲突。修正验证脚本后重跑；失败日志 `15a` 保留。
3. 上述修复只涉及导入/验证实现，不涉及台账、演示库、`/admin` 或前端。

## 4. 未执行项与说明

- 前端 `npm run build`：**不适用**。本轮未修改 `frontend/`、构建配置、颜色/主题文件。
- 未执行 LLM 打标、stats、仿真、`/admin` 或 APK 相关命令；这些属于后续步骤。
- `pytest` 输出中的 `requests/urllib3` 版本提示与 `datetime.utcnow()` 弃用警告为既有环境/代码警告，不是本轮失败；168 条测试全部通过。
- 4 份日志曾因 Windows 控制台 cp936 为非 UTF-8，已在不改内容的前提下转码为 UTF-8；转码命令未单独留日志，原始内容见对应日志。
