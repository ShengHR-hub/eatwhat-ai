# PRE-00 / r01 提交说明

步骤：PRE-00 运行基线与数据库兼容层
轮次：r01
状态：**已提交待审（SUBMITTED_FOR_REVIEW）**——开发方未签 PASS，未修改台账，未开始 S00 及后续步骤
日期：2026-10-25（Asia/Shanghai）
依据：[PRE_S10_REMEDIATION_PLAN.md](../../../PRE_S10_REMEDIATION_PLAN.md) §3「PRE-00」、[AGENTS.md](../../../../AGENTS.md)、[MASTER_SPEC.md](../../../../MASTER_SPEC.md) v2.3.5、[REVIEW_RULES.md](../../../REVIEW_RULES.md)

## 1. 本轮任务与边界

只执行 PRE-00：

1. 固定演示库 `backend/eatwhat.db`、S10 独立导入库 `backend/eatwhat_batch4.db`、源码与依赖基线；
2. 复现当前推荐与足迹接口 500；
3. 创建明确命名的开发运行库副本；
4. 用幂等迁移补齐当前代码需要的可空 schema；
5. 验证两个原库 SHA 不变；
6. 验证 `/health`、`/api/v1/recommend/single`、`/api/v1/logs/stats/1`；
7. 记录迁移前后 schema、数据库 SHA、命令退出码和失败反例。

未做：未改台账；未清空/迁移演示库；未直接迁移 S10 导入库；未修改 `/admin`；未实现 S10/批次 4 业务；未跑前端 build（本轮无前端改动）。

## 2. 变更路径

| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `backend/scripts/migrate_pre00_runtime_schema.py` | 新增（未跟踪） | 幂等兼容迁移；拒绝演示库与 S10 库；单事务、失败回滚 |
| `backend/tests/test_pre00_runtime_migration.py` | 新增（未跟踪） | 5 条最小回归：补列/放宽/幂等/拒绝原库/失败回滚 |
| `backend/eatwhat_dev_pre00.db` | 新增运行产物（`*.db` 已被 .gitignore 忽略） | 开发运行库副本；来源 = 演示库，迁移后 SHA 见下 |
| `docs/review/stages/PRE-00/r01/**` | 新增证据 | 本包 |

既有业务源码、`/admin`、S10 导入脚本与两个原库均未编辑。基线采集时工作区已有 staged 280 / unstaged 130 / untracked 49 项历史变更，本包没有清理或覆盖它们。

## 3. 关键身份

| 对象 | 身份 |
| --- | --- |
| 演示库 `backend/eatwhat.db` | SHA-256 `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b`（217,088 B；4 用户 / 20 门店 / 100 菜 / 9 日志 / 0 房间 / 0 投票） |
| S10 导入库 `backend/eatwhat_batch4.db` | SHA-256 `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28`（6,316,032 B；7,664 门店 / 6,400 菜品 / 0 用户） |
| 开发运行库 `backend/eatwhat_dev_pre00.db` | 迁移前 = 演示库 SHA；迁移后 `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579`；二次迁移后字节不变 |
| 迁移脚本 | `migrate_pre00_runtime_schema.py` SHA-256 `0fa78f009fc7b21bf0df271c853b53dfdf810fbbce04640ac767ae53f13eead4` |
| 回归测试 | `test_pre00_runtime_migration.py` SHA-256 `5bafdb494a3c1fa56a30368fb50222e24a857ea552014f6351f67fc27939350f` |
| 源码清单 | `SOURCE_MANIFEST.json` fingerprint `81dbdda089340a3e3292ee435356868955e80123a3378eb3d66cf7ccc7a5fc63` |

完整 SHA 与逐文件哈希见 `SOURCE_MANIFEST.json`、`data/baseline.json`、`data/final_protection.json`。

## 4. 复现与修复摘要

### 4.1 迁移前 500（开发运行库副本，端口 8031）

`GET /health` → 200 `{"status":"ok","version":"2.3.2"}`。

`POST /api/v1/recommend/single`（`X-User-Id: 1`，`OUT_DINING`）→ **500**。
`GET /api/v1/logs/stats/1` → **500**。

服务端根因一致：

```text
sqlite3.OperationalError: no such column: dishes_and_recipes.allergen_tags
```

完整堆栈：`logs/02_server_pre_migration.log`；客户端原始响应：`logs/04_http_recommend_pre.txt`、`logs/05_http_stats_pre.txt`。

### 4.2 迁移内容（仅开发运行库副本）

首次执行补齐 **18 个可空列**：

- `restaurants`（7）：`source_dataset`、`source_record_id`、`source_url`、`data_version`、`is_synthetic`、`deleted_at`、`campus`
- `dishes_and_recipes`（10）：`allergen_tags`、`tagging_status`、`tagging_error`、`llm_meta`、`source_dataset`、`source_record_id`、`source_url`、`data_version`、`is_synthetic`、`deleted_at`
- `group_rooms`（1）：`campus`

同时按当前 `models.py` 重建 `dishes_and_recipes`，把 `feature_vector` 从 `NOT NULL` 放宽为可空，并把 `appliance_tag` 对齐为 `JSON`；100 行数据、3 个索引与主外键全部保留，`PRAGMA foreign_key_check` 为空。

不回填：历史行的 `is_synthetic`、`campus` 保持 NULL，不冒充真实/合成或某校区。

迁移前后 schema 指纹：`b708e1d2…e5228f` → `82f1b327…ccaeb7`；逐列快照见 `data/pre_schema.json`、`data/post_schema.json`。

### 4.3 迁移后（同一开发运行库，端口 8032）

| 请求 | 结果 |
| --- | --- |
| `GET /health` | 200，`status=ok` |
| `POST /api/v1/recommend/single`（外食，user 1） | 200，5 条；Top `dish_id=24`、`total_score=86.7`；契约键齐全、分数有限且 ≤100、五维雷达键正确 |
| `POST /api/v1/recommend/single`（下厨，user 2 + `lazy_one_pot`） | 200，5 条；分数有限且 ≤100 |
| `GET /api/v1/logs/stats/1` | 200；`cooling_dishes=3`、`weekly_expense=72.0`、`meals_this_week=3`、`cuisine_pie_data=2` |

原始响应：`logs/10_http_health_post.json`、`logs/11_http_recommend_out_post.json`、`logs/12_http_recommend_home_post.json`、`logs/13_http_stats_post.json`。

### 4.4 幂等

第二次执行 `added_columns=[]`、`rebuilt_tables=[]`、`idempotent=true`，schema 指纹与文件 SHA 均与第一次执行后相同：

`b965e73e…706a579`（run1 after = run2 before = run2 after）。

### 4.5 原库保护

最终复核（`logs/19_final_protection.log`、`data/final_protection.json`）：

- 演示库 SHA 与基线相同：`775da775…bd3a60b`，`unchanged=true`；
- S10 导入库 SHA 与基线相同：`315eb3da…6918c28`，`unchanged=true`；
- 两库均无 `-wal` / `-journal` / `-shm` 旁文件；
- 开发运行库行数与演示库一致（4/20/100/12/9/0/0），证明没有把 7,664 门店的 S10 大库接进演示流程。

### 4.6 失败反例

| 反例 | 退出码 | 结果 |
| --- | --- | --- |
| 直接指定演示库 | 1 | 拒绝，提示只允许开发运行库副本；演示库 SHA 不变 |
| 直接指定 S10 库 | 1 | 拒绝；S10 库 SHA 不变 |
| 预检缺表（`group_rooms` 被换成视图） | 1 | schema 与文件 SHA 均不变 |
| 事务中途失败（dishes 出现未知列 `zzz_unexpected`） | 1 | 已执行的 `restaurants` 补列全部回滚；`campus` 不存在、`feature_vector` 仍为 `NOT NULL`；schema 与文件 SHA 均不变 |

证据：`logs/15_guard_refusal.log`、`logs/16_failure_rollback.log`、`data/failure_rollback.json`。

## 5. 自测结果（不等同于独立验收）

| 检查 | 退出码 | 结果 | 证据 |
| --- | --- | --- | --- |
| PRE-00 回归测试 | 0 | `5 passed in 0.43s` | `logs/06_pytest_pre00.log` |
| 后端全量（隔离 `DATABASE_URL`） | 0 | `173 passed, 505 warnings in 21.28s`；隔离库未生成 | `logs/17_pytest_full_isolated.log` |
| 迁移第 1 次 | 0 | 补 18 列 + 重建 1 表；行数不变 | `logs/07_migration_run1.log` |
| 迁移第 2 次 | 0 | 幂等，字节不变 | `logs/08_migration_run2.log` |
| ORM 列/可空性对齐 | 0 | 3 张表 0 缺失、0 可空性不一致 | `logs/18_model_schema_parity.log` |
| 原库保护 | 0 | 两库 SHA 均不变 | `logs/19_final_protection.log` |

全量测试中的 505 条 warning 为既有 `datetime.utcnow()` 弃用与 `requests` 依赖版本提示，没有 failure/error；未把 warning 计入通过条件。

## 6. 已知限制与残留风险

1. **未跑前端**：PRE-00 未改前端，`npm run build` 与三条界面门禁留到 S05/S08。
2. **未实现 campus**：当前 `POST /recommend/single` 不接受 `campus`，外食校区过滤属于后续 S05/BRIDGE-10；本包不把「迁移后可用」写成「双校区契约已验收」。
3. **开发运行库只是演示库副本**：不含 S10 的 7,664 门店 / 6,400 菜品；BRIDGE-10 才验证只读或导入边界。
4. **SQLite 表重建**：`feature_vector` 放宽只能靠重建；迁移已校验未知列、行数、外键与索引，但仍是本包风险最高的动作，请重点复验 `data/migration_run1.json` 与 `data/post_schema.json`。
5. **后端版本号未改**：`/health` 仍返回 `2.3.2`；本轮只做运行库兼容，不顺手改版本/路由。
6. **工作区无 commit**：源码版本由 `SOURCE_MANIFEST.json` + staged diff SHA 固定；新脚本/测试是未跟踪文件，未执行 `git add`。

## 7. 停机声明

本包提交后即停止。未签 PASS、未改 `docs/review/STAGE_STATUS.md`、未开放 S00 及后续步骤；等待 Codex 独立审查。
