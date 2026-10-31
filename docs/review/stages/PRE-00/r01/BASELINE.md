# PRE-00 / r01 基线

日期：2026-10-25（Asia/Shanghai）
工作目录：`D:\EatWhat`
基线采集：2026-10-25T03:50:11+08:00（`logs/01_baseline.txt`、`data/baseline.json`）
源码清单：`SOURCE_MANIFEST.json`，fingerprint `81dbdda089340a3e3292ee435356868955e80123a3378eb3d66cf7ccc7a5fc63`（66 项）

## 1. 源码版本

| 项 | 值 |
| --- | --- |
| 分支 | `master` |
| HEAD | **不存在**（`git rev-parse HEAD` 退出码 128，仓库 0 commit） |
| 工作区 | 基线采集时即非干净：staged 280 / unstaged 130 / untracked 49；生成 manifest 时为 51（新增 2 个未跟踪源文件，证据目录另计）；本包未清理或覆盖历史变更 |
| staged diff SHA-256 | `cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（`git diff --cached --binary`） |
| 契约版本 | `MASTER_SPEC.md` v2.3.5 |
| 新文件 | `backend/scripts/migrate_pre00_runtime_schema.py`、`backend/tests/test_pre00_runtime_migration.py`（未跟踪，按 SHA 固定） |

说明：仓库无 commit，因此不能给出 commit id；版本以逐文件 SHA-256 + staged diff SHA 固定。`SOURCE_MANIFEST.json` 覆盖全部 `backend/**/*.py`、`requirements.txt`、`pytest.ini`、前端依赖锁、契约文档与三个数据库文件。

## 2. 运行环境

| 组件 | 版本/取值 |
| --- | --- |
| OS / Shell | Windows 10.0.22631 x64 / Git Bash |
| Python | 3.13.9 |
| FastAPI / Starlette | 0.115.0 / 随 FastAPI |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |
| HTTPX | 0.28.1 |
| Uvicorn | 0.30.0 |
| pytest | 9.0.3 |
| Node / npm | v24.19.0 / 11.17.0 |
| SQLite journal | 两库均为 `delete`（不是 WAL） |

依赖声明仍是 `requirements.txt` 的区间（`fastapi>=0.115,<1.0`、`SQLAlchemy>=2.0,<3.0`、`pydantic>=2.8,<3.0`、`httpx>=0.28`、`pytest>=8.0`）；上表是本次实际安装版本。前端本轮未构建，仅固定 `frontend/package.json`（`66e99826…48c49b`）与 `frontend/package-lock.json`（`adc87fc7…20c297`）。

## 3. 数据库身份

### 3.1 演示库 `backend/eatwhat.db`

| 项 | 值 |
| --- | --- |
| 大小 | 217,088 B |
| SHA-256 | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` |
| 行数 | users 4 / restaurants 20 / dishes_and_recipes 100 / user_preferences 4 / fridge_inventory 12 / eating_logs 9 / group_rooms 0 / room_votes 0 / algo_configs 1 |
| 用途 | 演示数据只读基线；**不迁移、不清空** |

迁移前缺列（相对 `backend/models.py`）：

- `restaurants`：`source_dataset`、`source_record_id`、`source_url`、`data_version`、`is_synthetic`、`deleted_at`、`campus`
- `dishes_and_recipes`：`allergen_tags`、`tagging_status`、`tagging_error`、`llm_meta`、`source_dataset`、`source_record_id`、`source_url`、`data_version`、`is_synthetic`、`deleted_at`
- `group_rooms`：`campus`
- `dishes_and_recipes.feature_vector` 为 `NOT NULL`（模型为可空）

逐列快照：`data/pre_schema.json`（开发副本迁移前，schema 与演示库一致）。

### 3.2 S10 独立导入库 `backend/eatwhat_batch4.db`

| 项 | 值 |
| --- | --- |
| 大小 | 6,316,032 B |
| SHA-256 | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` |
| 行数 | restaurants 7,664 / dishes_and_recipes 6,400 / 其余 0 |
| schema | 已含 v2.3.3/v2.3.4 可空列与 `ux_dishes_source`；`feature_vector` 可空 |
| 用途 | S10 独立导入库；**本轮只读，不迁移、不接线** |

### 3.3 开发运行库 `backend/eatwhat_dev_pre00.db`

| 项 | 值 |
| --- | --- |
| 创建命令 | `cp backend/eatwhat.db backend/eatwhat_dev_pre00.db` |
| 创建时间 | 2026-10-25T03:50:20+08:00（见 `logs/00_dev_copy_provenance.log`） |
| 来源 SHA | `775da775…bd3a60b`（与演示库字节一致） |
| 迁移前 SHA | 同上 |
| 迁移后 SHA | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` |
| 二次迁移后 SHA | 同迁移后，字节不变 |
| 迁移后行数 | 与演示库一致：4 / 20 / 100 / 12 / 9 / 0 / 0 |
| 迁移后 schema 指纹 | `82f1b327dcd220dacf055cf57354454f03b2cfe7fa1809336bc3b4c036ccaeb7` |
| 用途 | PRE-00 及后续 S00–S08 的开发运行库；`*.db` 已被 `.gitignore` 忽略，Codex 可按上表复算 |

迁移脚本：`backend/scripts/migrate_pre00_runtime_schema.py`（`pre00_runtime_v1`，SHA `0fa78f00…3eead4`）。它显式拒绝 `backend/eatwhat.db` 与 `backend/eatwhat_batch4.db`，单事务执行，失败回滚。

## 4. 服务基线

| 用途 | 地址 | 数据库 |
| --- | --- | --- |
| 迁移前复现 | `http://127.0.0.1:8031` | `sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00.db` |
| 迁移后验证 | `http://127.0.0.1:8032` | 同一开发运行库 |

启动命令（仓库根目录）：

```bash
DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00.db" \
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 803x
```

两次服务都在验证后停止；没有连接 `backend/eatwhat_batch4.db`。

## 5. 范围声明

- 本轮只固定基线、复现 500、迁移开发副本、验证三个接口；
- 未做 S00 的缺陷清单冻结，未进入 S01–S08，未修改台账；
- 未把 S10 大库接入演示用户流程，未验证 BRIDGE-10 的只读/导入边界。
