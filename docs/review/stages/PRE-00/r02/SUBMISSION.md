# PRE-00 / r02 提交说明

步骤：PRE-00 运行基线与数据库兼容层
轮次：r02（针对 r01 FAIL-01 整改）
状态：**已提交待审（SUBMITTED_FOR_REVIEW）**——开发方未签 PASS，未修改台账，未开放 S00
日期：2026-10-25（Asia/Shanghai）
上一轮结论：[PRE-00/r01 独立复审](../../../clearance-codex-pre00-r01/REPORT.md) —— **FAIL（FAIL-01 / P1）**

## 1. 本轮只改一件事

r01 的迁移、幂等、回滚、接口恢复均被复审认可；唯一 P1 是保护守卫只比较路径字符串，Windows 硬链接可用不同路径指向同一文件并绕过。

r02 的改动：

1. `backend/scripts/migrate_pre00_runtime_schema.py` 的 `_guard_path()` 改为**文件身份**判断：
   - 目标必须是普通文件；
   - 对演示库与 S10 库使用 `os.path.samefile()` 比较，不再比较路径字符串；
   - 硬链接、符号链接、大小写/短路径别名都归一到同一文件身份；
2. 脚本版本升为 `pre00_runtime_v2`；
3. `backend/tests/test_pre00_runtime_migration.py` 新增三条反例：
   - `test_refuses_hardlink_alias`（真实硬链接，NTFS）；
   - `test_refuses_symlink_alias`（可用时；本机无权限则明确 skip）；
   - `test_refuses_case_alias`（Windows 大小写别名）。

未改迁移的补列/重建/回滚逻辑，未改业务接口、`/admin`、S10 业务或台账。r01 证据原样保留，未覆盖。

## 2. 变更路径与身份

| 路径 | 身份 |
| --- | --- |
| `backend/scripts/migrate_pre00_runtime_schema.py` | SHA-256 `4554358c8f0a458c8e334f1ffd2ec3eb380a1ff1570dbeab4950b8c97e624369`；`pre00_runtime_v2` |
| `backend/tests/test_pre00_runtime_migration.py` | SHA-256 `2c097b4f7166e895d0eed7d7078ef07fa36acc84c6097685fab1d5345026d09b` |
| `backend/eatwhat_dev_pre00_r02.db` | 新建开发运行库副本；迁移后 SHA `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` |
| `SOURCE_MANIFEST.json` | fingerprint `4d2187b64aced13445049807ec9f5b580da34e3d139dcb1dcadd267974a16361`（66 项） |

原库：

- 演示库 `backend/eatwhat.db`：`775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b`；
- S10 库 `backend/eatwhat_batch4.db`：`315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28`。

## 3. FAIL-01 复验

### 3.1 真实硬链接别名（只读守卫探针）

在 `backend/` 下分别创建演示库、S10 库的 NTFS 硬链接，确认 `samefile=true` 且 `resolved_paths_equal=false`，再调用 `_guard_path()`（只读，不执行迁移）：

| 目标 | samefile | 路径相等 | 守卫 | 原库 SHA/schema/行数 |
| --- | --- | --- | --- | --- |
| 演示库别名 | true | **false** | 抛出 `SystemExit`，拒绝 | 不变 |
| S10 库别名 | true | **false** | 抛出 `SystemExit`，拒绝 | 不变 |

探针结束后删除别名；最终复核两个原库 SHA、schema 指纹、行数全部与探针前相同。证据：`logs/02_guard_probe.log`、`data/guard_probe.json`。

### 3.2 真实 CLI 硬链接反例（写操作只落在副本）

对演示库副本、S10 库副本分别创建硬链接，把守卫常量指向副本，再通过 `m.main()` 走完整 CLI：

| 场景 | samefile | 路径相等 | 退出码 | 副本 SHA/schema/行数 |
| --- | --- | --- | --- | --- |
| 演示库副本 + 硬链接别名 | true | **false** | **1** | 不变 |
| S10 副本 + 硬链接别名 | true | **false** | **1** | 不变 |

标准错误均为明确的拒绝信息；没有进入迁移事务。证据同上。

### 3.3 其他别名

- **大小写别名**：`D:\EATWHAT\BACKEND\EATWHAT.DB` 能被 Windows 定位到演示库；`_guard_path()` 抛出 `SystemExit`。证据：`logs/18_path_alias_probe.log`。
- **符号链接**：当前 Windows 账户创建文件符号链接返回 `WinError 1314`（没有所需特权），专项测试 skip、真实探针标记 `supported=false`。守卫使用同一 `samefile` 身份判断；该限制已写入 `validation.json.known_limits`，不伪装成已实测。
- **8.3 短路径**：当前卷未启用 8.3（`GetShortPathNameW` 返回原路径），无法构造短路径实测；身份比较不依赖路径字符串。

### 3.4 直接路径

`--db backend/eatwhat.db` 与 `--db backend/eatwhat_batch4.db` 均退出码 1，原库不变。证据：`logs/15_direct_guard.log`。

## 4. 迁移与接口回归（新副本）

从演示库新建 `backend/eatwhat_dev_pre00_r02.db`（迁移前 SHA 与演示库相同），用 v2 脚本执行两次：

- 首次：补 18 个可空列，重建 `dishes_and_recipes` 放宽 `feature_vector`；20 门店 / 100 菜 / 0 房间保留；`foreign_key_check=[]`；schema 指纹 `b708e1d2…e5228f` → `82f1b327…ccaeb7`。
- 第二次：`added_columns=[]`、`rebuilt_tables=[]`、`idempotent=true`；SHA `b965e73e…706a579` 前后不变。

服务（端口 8034，`DATABASE_URL` 指向 r02 开发库）验证：

| 请求 | 结果 |
| --- | --- |
| `GET /health` | 200 |
| `POST /recommend/single`（外食） | 200，5 条，Top 24 / 86.7，契约键与雷达键齐全 |
| `POST /recommend/single`（下厨 + `lazy_one_pot`） | 200，5 条 |
| `GET /logs/stats/1` | 200，3 条冷却 / 72.0 元 / 3 餐 / 2 类 |
| `GET /fridge/1` | 200，3 条 |

证据：`logs/06_server_post_migration.log`、`logs/07_http_health.json` … `logs/12_post_summary.json`。

## 5. 自测结果（不等同于独立验收）

| 检查 | 退出码 | 结果 | 证据 |
| --- | --- | --- | --- |
| 迁移专项 | 0 | `7 passed, 1 skipped`（符号链接权限） | `logs/01_pytest_pre00_r02.log` |
| 后端全量（隔离库） | 0 | `175 passed, 1 skipped, 505 warnings`；隔离库未生成 | `logs/13_pytest_full_isolated.log` |
| 文件身份探针 | 0 | 真实硬链接拒绝；原库不变 | `logs/02_guard_probe.log` |
| 迁移第 1 次 / 第 2 次 | 0 / 0 | 18 列 + 重建；二次幂等且字节不变 | `logs/04_…`、`logs/05_…` |
| ORM 对齐 | 0 | 0 缺失、0 可空性不一致 | `logs/14_schema_parity.log` |
| 失败回滚 | 1 / 1（预期） | 预检缺表、事务中途失败均不改库 | `logs/16_failure_rollback.log` |
| 原库保护 | 0 | 两库 SHA/schema/行数不变；无旁文件 | `logs/17_final_protection.log` |

## 6. 已知限制

1. 符号链接因本机权限无法实测；`samefile` 与硬链接/大小写别名已覆盖同类身份问题。
2. 8.3 短路径未启用，无实测样本；守卫不依赖路径字符串。
3. 未跑前端 build / 浏览器门禁；未实现 campus 过滤（留 S05/BRIDGE-10）。
4. 工作区无 commit，源码由逐文件 SHA + staged diff SHA 固定；新脚本/测试仍为未跟踪文件。

## 7. 停机声明

本包提交后立即停手：未签 PASS、未改 `docs/review/STAGE_STATUS.md`、未开放 S00–S05；等待 Codex 独立复审。
