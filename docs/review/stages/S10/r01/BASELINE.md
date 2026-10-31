# S10 / r01 基线

- 日期时区：2026-10-25（Asia/Shanghai）
- 步骤：S10 多源基础数据清洗与导入
- 目标库：`D:/EatWhat/backend/eatwhat_batch4.db`
- 演示库：`D:/EatWhat/backend/eatwhat.db`
- 开发方：Qoder 执行端；审查方：Codex（未签 PASS）

## 1. 版本与工作树

| 项 | 值 |
|---|---|
| Git HEAD | **不存在**（`git rev-parse HEAD` 返回 `ambiguous argument 'HEAD'`；仓库尚无 commit） |
| 工作树状态 | `git status --porcelain` 共 **328** 项；包含此前阶段已存在的 staged/unstaged 变更，不是本轮全部改动 |
| 本轮 S10 代码 | `backend/models.py`（AM）、`backend/scripts/{migrate_s10_data_schema,s10_common,fetch_amap_poi,import_open_recipes,verify_s10_import}.py`（新增）、`backend/tests/test_s10_import.py`（新增） |
| 本轮前端 | **无**；未改 `frontend/`、`package.json`、`vite.config.js` 或颜色/构建文件 |
| 台账/REVIEW | 未改 `docs/review/STAGE_STATUS.md`；未创建/修改任何 `REVIEW.md` |
| `backend/models.py` diff | `logs/31_git_diff_models.log`；其中 `group_rooms.algo_params` 为此前阶段已存在的未暂存变更，非本轮新增 |

## 2. 环境

| 项 | 值 |
|---|---|
| OS | Windows 10.0.22631（x64） |
| Python | 3.13.9 |
| SQLite | 3.50.4 |
| Node | v24.19.0（前端未参与本轮） |
| 目标库 journal_mode | `delete` |
| 目标库 page_size / page_count | 4,096 / 1,542 |

## 3. 数据身份

| 对象 | SHA-256 | 字节 |
|---|---|---:|
| `docs/review/stages/S09/r02/data/amap_pois.jsonl` | `5cdf4953821d5a067aed624fb67b4bfb5f77708a9696f46e7bd28f4869efe478` | 305,023 |
| `docs/review/stages/S09/r02/data/amap_jianda_pois.jsonl` | `ac0a7b2405592ab1ce656b39ca7b3246ac632ea285a61ed94ea05e095a7fb7c7` | 3,568,782 |
| S09/r04 `SOURCE_MANIFEST.json` | `7b1d163dffdad256a82186f7c7e7f9f0d1b3d38692c764e5450499919e694a3a` | — |
| S09/r04 B3 复审报告 | `ea861d8c15b7d978439079447283ecbf1878c7219774db6fa6814c179c04f3e6` | — |
| 目标库 `backend/eatwhat_batch4.db` | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | 6,316,032 |
| 演示库 `backend/eatwhat.db` | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | 217,088 |
| 演示库期望值（S09/r04 `protection.db_sha256`） | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | — |
| `MASTER_SPEC.md` | `5463f88f8cb73c77dd6115adcce93b81382b259092a9da9a39cd68716ef2c8b3` | — |
| `BATCH4_PLAN.md` | `6c95dfe49bbae8bb48eb7a75245167dda057d229b7a3f54ced3fb546d6d14fba` | — |
| `docs/REVIEW_RULES.md` | `f9857dab1f07fe3eaf899f558632de7302267add5017065b9b9eef0f047c9f05` | — |
| `docs/review/STAGE_STATUS.md`（基线） | `1b36d19c34b39c65daf0fd31b2c0a09a9a201e6a2b90cc5adc09c7d074821fe4` | — |

## 4. 目标库与探针库

- 目标库 `backend/eatwhat_batch4.db`：S10 全量结果，重启/重跑后可复核；`restaurants=7,664`、`dishes_and_recipes=6,400`、其余业务表为 0。
- 小样库、拒绝/重试库、种子检查库均为临时隔离库；哈希见 `data/temp_probe_dbs.json`，记录后删除，避免与目标库混淆。
- 演示库只读：`users=4`、`restaurants=20`、`dishes_and_recipes=100`、`eating_logs=9`、`group_rooms=0`、`room_votes=0`；SHA 与 S09/r04 记录一致。

## 5. 变更范围摘要

- 新增可空字段与唯一索引；未删除/改名任何既有字段，未改既有字段语义。
- `feature_vector` 由 `NOT NULL` 放宽为可空（SSOT v2.3.3 允许）；`avg_price/rating/distance_meters/price_or_cost` 去掉旧伪默认，缺失保持 NULL。
- 未改前端、未改 `/admin` 路由、未加 stats/仿真逻辑。
- 未改 `backend/scripts/init_seed_data.py`；隔离库实跑通过。
