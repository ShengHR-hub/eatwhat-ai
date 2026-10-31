# PRE-00 / r02 命令与检查记录

工作目录：`D:\EatWhat`
时间：2026-10-25（Asia/Shanghai）；表中时间为日志文件 mtime
环境：Windows Git Bash、Python 3.13.9；中文日志使用 `PYTHONIOENCODING=utf-8`

## 1. 命令清单

| # | 时间 | 命令 | 退出码 | 结果 / 日志 |
| --- | --- | --- | --- | --- |
| 1 | 13:22:40 | `python -m pytest backend/tests/test_pre00_runtime_migration.py -q -rs` | **0** | `7 passed, 1 skipped`；`logs/01_pytest_pre00_r02.log` |
| 2 | 13:23:06 | `python docs/review/stages/PRE-00/r02/data/guard_probe.py` | **0** | 真实硬链接拒绝；原库不变；`logs/02_guard_probe.log`、`data/guard_probe.json` |
| 3 | 13:23:12 | `cp backend/eatwhat.db backend/eatwhat_dev_pre00_r02.db` + SHA 比对 | 0 | 副本与演示库字节一致；`logs/03_dev_copy_provenance.log` |
| 4 | 13:23:15 | `python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_pre00_r02.db --json-out …/migration_run1.json` | **0** | 18 列 + 重建 dishes；`logs/04_migration_run1.log` |
| 5 | 13:23:18 | 同 #4，输出 `migration_run2.json` | **0** | `idempotent=true`，SHA 不变；`logs/05_migration_run2.log` |
| 6 | 13:23:30（日志落盘） | `DATABASE_URL=...eatwhat_dev_pre00_r02.db ... --port 8034` | n/a（后台，已停止） | `logs/06_server_post_migration.log` |
| 7 | 13:23:27–30 | httpx：health / 外食推荐 / 下厨推荐 / 足迹 / 冰箱 | 0（客户端） | 全部 200；`logs/07_…` … `logs/12_post_summary.json` |
| 8 | 13:23:50 | `DATABASE_URL="sqlite:///D:/EatWhat/backend/_pytest_pre00_r02.db" python -m pytest -q` | **0** | `175 passed, 1 skipped`；隔离库未生成；`logs/13_pytest_full_isolated.log` |
| 9 | 13:23:52 | ORM 列与 r02 开发库 PRAGMA 对齐 | 0 | 0 缺失、0 可空性不一致；`logs/14_schema_parity.log` |
| 10 | 13:24:01 | 迁移脚本 `--db backend/eatwhat.db` 与 `--db backend/eatwhat_batch4.db` | **1 / 1（预期拒绝）** | `logs/15_direct_guard.log` |
| 11 | 13:24:02 | 失败反例：预检缺表 + 事务中途未知列 | **1 / 1（预期失败）** | `logs/16_failure_rollback.log`、`data/failure_rollback.json` |
| 12 | 13:24:15 | 最终 SHA/schema/行数/旁文件保护 | 0 | 两原库不变；无残留探针文件；`logs/17_final_protection.log` |
| 13 | 13:24:38 | 大小写别名 + 8.3 短路径探针 | 0 | 大小写别名被拒绝；短路径未启用；`logs/18_path_alias_probe.log` |
| 14 | 13:25:02 | `python docs/review/stages/PRE-00/r02/data/generate_evidence.py` | **0** | 生成 manifest 与 validation；`logs/19_manifest_validation_gen.log` |
| 15 | 13:24:27 | 内联 Python：环境、git 状态、三个数据库 SHA/行数、依赖文件 SHA | 0 | `logs/00_baseline.txt`、`data/baseline.json`（采集晚于上面的验证命令，表中按执行顺序排在最后） |

## 2. 关键断言

### 2.1 FAIL-01 文件身份守卫

| 断言 | 实际 |
| --- | --- |
| 硬链接别名与演示库 samefile | true；`resolved_paths_equal=false` |
| 守卫拒绝该别名 | 抛出 `SystemExit`，信息“拒绝迁移演示库 …” |
| 硬链接别名与 S10 库 samefile | true；`resolved_paths_equal=false` |
| 守卫拒绝该别名 | 抛出 `SystemExit`，信息“拒绝迁移S10 独立导入库 …” |
| 原库 SHA/schema/行数 | 探针前后完全相同 |
| CLI 硬链接（演示库副本） | 退出码 1；副本 SHA/schema/行数不变 |
| CLI 硬链接（S10 副本） | 退出码 1；副本 SHA/schema/行数不变 |
| 大小写路径别名 | 守卫拒绝 |
| 符号链接 | 本机 `WinError 1314` 无法创建；专项测试 skip，未伪装通过 |
| 8.3 短路径 | 未启用（`GetShortPathNameW` 返回原路径），无法构造 |

### 2.2 迁移

| 断言 | 实际 |
| --- | --- |
| 新副本迁移前身份 | SHA = 演示库 `775da775…` |
| 首次迁移 | 18 可空列 + `feature_vector` 放宽；20 门店 / 100 菜；`foreign_key_check=[]` |
| 二次迁移 | `idempotent=true`，`added_columns=[]`，SHA `b965e73e…` 不变 |
| ORM 对齐 | restaurants 17/17、dishes 24/24、group_rooms 15/15；0 不一致 |
| 失败回滚 | 预检与事务中途失败均退出 1，schema/file SHA 不变；`campus` 未加入、`feature_vector` 仍 NOT NULL |

### 2.3 接口

| 请求 | 实际 |
| --- | --- |
| `GET /health` | 200，`status=ok` |
| `POST /recommend/single`（外食） | 200，5 条，Top 24 / 86.7；契约键、五维雷达键齐全；分数有限且 0–100 |
| `POST /recommend/single`（下厨） | 200，5 条；分数有限且 0–100 |
| `GET /logs/stats/1` | 200；3 / 72.0 / 3 / 2 |
| `GET /fridge/1` | 200，3 条 |

### 2.4 原库保护

| 断言 | 实际 |
| --- | --- |
| 演示库 SHA | `775da775…bd3a60b`，与基线一致 |
| S10 库 SHA | `315eb3da…6918c28`，与基线一致 |
| schema / 行数 | 与探针前一致 |
| 旁文件 | 无 `-wal/-journal/-shm`；无 `backend/_pre00_r02_*` 残留 |
| 演示流程未接 S10 大库 | r02 开发库 4 用户 / 100 菜；S10 库 7,664 门店 / 6,400 菜且 SHA 不变 |

## 3. 独立复跑方法

```bash
# 1) 文件身份反例（会创建并删除临时硬链接/副本，不写原库）
python docs/review/stages/PRE-00/r02/data/guard_probe.py

# 2) 专项与全量
python -m pytest backend/tests/test_pre00_runtime_migration.py -q -rs
DATABASE_URL="sqlite:///D:/EatWhat/backend/_pytest_pre00_recheck.db" python -m pytest -q

# 3) 新副本迁移两次
cp backend/eatwhat.db backend/eatwhat_dev_recheck.db
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_recheck.db
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_dev_recheck.db

# 4) 接口
DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_recheck.db" \
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8035
# GET /health、POST /api/v1/recommend/single、GET /api/v1/logs/stats/1

# 5) 直接路径拒绝（预期退出码 1）
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat.db
python -m backend.scripts.migrate_pre00_runtime_schema --db backend/eatwhat_batch4.db
```

符号链接测试需要 Windows 开发者模式/管理员权限；当前账户没有，测试会明确 skip，而不是伪造通过。

## 4. 未执行项

| 项 | 原因 |
| --- | --- |
| `cd frontend; npm run build` | PRE-00 未改前端 |
| 三条首页门禁 / 颜色门禁 | 属 S05/S08，需要前端与浏览器 |
| `/admin`、S10 导入、LLM 打标 | 批次边界禁止提前实现 |
| 真实符号链接迁移反例 | 本机无创建权限（WinError 1314） |
