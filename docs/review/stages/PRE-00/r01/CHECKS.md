# PRE-00 / r01 命令与检查记录

工作目录：`D:\EatWhat`（以下所有命令均在此目录执行）
时间：2026-10-25（Asia/Shanghai）；表中时间为日志文件 mtime，不是人工估计
说明：Windows Git Bash；中文日志统一用 `PYTHONIOENCODING=utf-8` 输出。退出码来自命令本身；后台服务启动记为 `n/a`，验证后已停止。

## 1. 命令清单

| # | 时间 | 命令 | 退出码 | 结果 / 日志 |
| --- | --- | --- | --- | --- |
| 1 | 03:50:11 | 内联 Python：采集 Python/Node/依赖版本、git 状态、两库 SHA 与 schema、依赖锁 SHA | 0 | `logs/01_baseline.txt`、`data/baseline.json` |
| 2 | ~03:50:20 | `cp backend/eatwhat.db backend/eatwhat_dev_pre00.db` + SHA 比对 | 0 | 来源 SHA = 演示库 `775da775…`；`logs/00_dev_copy_provenance.log` |
| 3 | 03:50:24 | `DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00.db" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8031 --log-level info` | n/a（后台） | `logs/02_server_pre_migration.log`（含两次 500 堆栈） |
| 4 | 03:50:30 | httpx：`GET /health`、`POST /api/v1/recommend/single`、`GET /api/v1/logs/stats/1` | 0（客户端） | health 200；另两条 500；`logs/03_http_health_pre.json`、`04_http_recommend_pre.txt`、`05_http_stats_pre.txt` |
| 5 | 03:51:11 | `python -m pytest backend/tests/test_pre00_runtime_migration.py -q` | **0** | `5 passed in 0.43s`；`logs/06_pytest_pre00.log` |
| 6 | 03:51:16 | `python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_pre00.db --json-out docs/review/stages/PRE-00/r01/data/migration_run1.json` | **0** | 18 列 + 重建 dishes；`logs/07_migration_run1.log`、`data/migration_run1.json` |
| 7 | 03:51:19 | 同 #6，输出 `migration_run2.json` | **0** | `idempotent=true`，SHA 与 schema 不变；`logs/08_migration_run2.log`、`data/migration_run2.json` |
| 8 | 03:51:31 | `DATABASE_URL=...eatwhat_dev_pre00.db ... --port 8032` | n/a（后台） | `logs/09_server_post_migration.log` |
| 9 | 03:51:33–36 | httpx：health / 外食推荐 / 下厨推荐 / 足迹统计 | 0（客户端） | 全部 200；`logs/10_http_health_post.json` … `13_http_stats_post.json`、`14_post_summary.json` |
| 10 | 03:51:48 | 迁移脚本 `--db backend/eatwhat.db` 与 `--db backend/eatwhat_batch4.db` | **1 / 1（预期拒绝）** | `logs/15_guard_refusal.log` |
| 11 | 03:52:03 | 失败反例：预检缺表 + 事务中途未知列 | **1 / 1（预期失败）** | `logs/16_failure_rollback.log`、`data/failure_rollback.json` |
| 12 | 03:52:36 | `DATABASE_URL="sqlite:///D:/EatWhat/backend/_pytest_pre00.db" python -m pytest -q` | **0** | `173 passed, 505 warnings in 21.28s`；隔离库未生成；`logs/17_pytest_full_isolated.log` |
| 13 | 03:52:39 | 内联 Python：ORM 模型列与开发库 PRAGMA 对齐 | 0 | 0 缺失、0 可空性不一致；`logs/18_model_schema_parity.log` |
| 14 | 03:52:46 | 内联 Python：最终 SHA/行数/旁文件保护 | 0 | 两原库 `unchanged=true`；`logs/19_final_protection.log`、`data/final_protection.json` |
| 15 | 03:53:44 | `python docs/review/stages/PRE-00/r01/data/generate_evidence.py` | **0** | 生成 `SOURCE_MANIFEST.json` 与 `validation.json`；`logs/20_manifest_validation_gen.log` |

## 2. 关键断言与结果

### 2.1 迁移前（复现）

| 断言 | 实际 |
| --- | --- |
| 服务指向开发副本而不是原库 | `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00.db` |
| `/health` 可用 | 200 `{"status":"ok","version":"2.3.2"}` |
| `POST /api/v1/recommend/single` 复现 500 | 500；服务端 `no such column: dishes_and_recipes.allergen_tags` |
| `GET /api/v1/logs/stats/1` 复现 500 | 500；同一根因 |
| 演示库 / S10 库未被写入 | 本轮结束时 SHA 与基线一致 |

### 2.2 迁移

| 断言 | 实际 |
| --- | --- |
| 只补可空列 | 18 列，全部无 `NOT NULL` / 无默认值 |
| `feature_vector` 放宽 | `PRAGMA table_info` `notnull` 1 → 0 |
| 数据不丢 | 100 菜品行数不变；`foreign_key_check` 空 |
| 索引保留 | `ix_dishes_and_recipes_name` / `_mode_type` / `_cuisine_type` 均在 |
| 幂等 | 第二次 `added_columns=[]`、`rebuilt_tables=[]`，SHA `b965e73e…` 不变 |
| 不回填 | `is_synthetic`、`campus` 历史行为 NULL |

### 2.3 迁移后（契约成功响应）

| 请求 | 断言 | 实际 |
| --- | --- | --- |
| `GET /health` | 200 + `status=ok` | 通过 |
| `POST /recommend/single`（OUT_DINING） | 200；`recommendations` 非空；含 `mode_type`/`combo`/`params_used`/`bubble_effects`；分数有限且 0–100；`radar_5d` 五键 | 5 条，Top dish 24 / 86.7 |
| `POST /recommend/single`（HOME_COOKING + `lazy_one_pot`） | 200；分数有限且 0–100 | 5 条，Top dish 89 |
| `GET /logs/stats/1` | 200；四键 `cooling_dishes`/`weekly_expense`/`meals_this_week`/`cuisine_pie_data` | 3 / 72.0 / 3 / 2 |

### 2.4 失败反例

| 场景 | 期望 | 实际 |
| --- | --- | --- |
| 指定演示库 | 拒绝，非零退出，原库不变 | 退出 1；提示拒绝；SHA 不变 |
| 指定 S10 库 | 拒绝，非零退出，原库不变 | 退出 1；提示拒绝；SHA 不变 |
| `group_rooms` 被替换成视图（预检缺表） | 事务前中止；schema/file SHA 不变 | 退出 1；两者均不变 |
| 事务中途未知列（dishes 有 `zzz_unexpected`） | 回滚已执行的所有 ALTER；schema/file SHA 不变 | 退出 1；`restaurants.campus` 不存在、`feature_vector` 仍 NOT NULL、SHA 不变 |

### 2.5 保护

| 断言 | 实际 |
| --- | --- |
| 演示库 SHA 不变 | `775da775…bd3a60b` = 基线 |
| S10 库 SHA 不变 | `315eb3da…6918c28` = 基线 |
| 无 WAL/journal/shm 旁文件 | 两库均为空列表 |
| 演示流程未接 S10 大库 | 开发库 4 用户 / 100 菜；S10 库 7,664 门店 / 6,400 菜且 SHA 不变 |

## 3. 独立复跑方法

```bash
# 1) 从一个新的演示库副本开始（不要覆盖已迁移的 dev 库）
cp backend/eatwhat.db backend/eatwhat_dev_recheck.db

# 2) 迁移前：把 DATABASE_URL 指向该副本并启动 803x，调用三个接口
DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_recheck.db" \
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8033

# 3) 迁移两次，核对第二次幂等
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_recheck.db
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_recheck.db

# 4) 重新启动服务，验证 /health、/recommend/single、/logs/stats/1

# 5) 反例（预期退出码 1，且文件 SHA 不变）
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat.db
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_batch4.db

# 6) 回归
python -m pytest backend/tests/test_pre00_runtime_migration.py -q
```

注意：`backend/eatwhat_dev_pre00.db` 已是迁移后状态；复跑请用新的副本名，避免把「迁移前复现」建立在已迁移库上。

## 4. 未执行项

| 项 | 原因 |
| --- | --- |
| `cd frontend; npm run build` | PRE-00 未改前端 |
| `scripts/home-fit.mjs` / `refill-fresh.mjs` / `sandbox-sync.mjs` / `check-colors.mjs` | 需要前端与浏览器，属 S05/S08 |
| `/admin`、S10 导入、LLM 打标 | 批次边界禁止提前实现 |
