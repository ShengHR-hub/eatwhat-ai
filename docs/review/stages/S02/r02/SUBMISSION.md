# S02 / r02 提交说明

步骤：S02 数值、向量与持久化边界（F08）
轮次：r02（整改 S02/r01 复审 FAIL）
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
前置：S01/r01 PASS；[S02/r01 独立复审 FAIL](../../../clearance-codex-s02-r01/REPORT.md)，受审 manifest `eb17fe30…f9b03f`

**未签 PASS；未修改台账；未开始 S03；未触碰 `/admin`、S10。** r01 证据包原样保留，不覆盖。

## 1. 对复审阻断项的整改

### S02-R01-01：非向量偏好更新绕过历史向量守卫

- **根因**：`_valid_stored_value` 校验写在 `if payload.base_vector is not None:` 分支内；只提交 `default_budget`/`veto_tags`/`preferred_cuisines` 时直接进入字段赋值与 `commit()`。
- **修复**：新增 `_validated_history_vector(raw)`，在 `update_preferences` 读取偏好后、任何字段赋值之前执行。只要历史向量存在未知键、非数字、布尔、NaN/Infinity、越界值或不是对象，立即 **409**；预算/忌口/菜系/向量/组合请求全部不写。
- **验证**：9 种历史状态 × 4 条更新路径 + 组合请求，均断言 409 与整行快照一致；真实 HTTP 复现复审场景 1（95 + 预算 31 → 409，预算与向量均未变）。

### S02-R01-02：历史未知键被静默丢弃

- **根因**：`completed = {key: merged.get(key, DEFAULT_FEATURE_VECTOR[key]) for key in GENE_KEYS}` 只遍历合法八键，历史未知键在规范化时被无声删除。
- **修复**：守卫先比较 `set(raw) - set(GENE_KEYS)`；未知键直接 409，不进入补齐/合并。完整八维覆盖也不能绕过（显式覆盖不等于允许丢弃）。
- **验证**：`umami_level` 历史行 + 合法部分向量 → 409，未知键仍在、整行不变；真实 HTTP 复现复审场景 2。

### 合法缺键的补齐

只有“键都在八维内且值全部合法”的历史向量才进入补齐：按方案 A 用 0.5 补齐缺失键；补齐发生在**任何**偏好更新路径（包括只改预算/忌口/菜系），保证更新后库内向量始终八键完整。历史非法值不会被 clamp、覆盖或丢弃。

## 2. 实际修改文件（r02 增量）

| 文件 | 改动 | 原因 |
| --- | --- | --- |
| `backend/routers/auth_user.py` | 新增 `_validated_history_vector`；守卫前移到所有偏好更新路径；去掉“仅向量分支校验”；补齐在字段赋值前完成 | 复审 S02-R01-01/02 |
| `backend/tests/test_s02_numeric_bounds.py` | 新增 51 条历史向量矩阵/原子失败/补齐用例；删除 2 条已不成立的旧断言 | 红灯先行，覆盖复审要求 |

r01 已修改且本轮未再改动的文件：`backend/schemas.py`、`backend/routers/recommend.py`、`backend/routers/fridge.py`、`backend/main.py`。

未改前端、`models.py`、迁移、SSOT、台账。

## 3. 行为矩阵

| 历史向量状态 | 预算/忌口/菜系更新 | 部分向量更新 | 完整八维覆盖 | 合法缺键补齐 |
| --- | --- | --- | --- | --- |
| 8 键合法 | 200；向量不变 | 200；按维度合并 | 200 | 不适用 |
| 合法但缺键 | 200；补 0.5 后更新字段 | 200；合并并补齐 | 200 | 是 |
| 未知键 | **409**，整行不变 | **409** | **409** | 否 |
| 越界 / 非有限 / 布尔 / 字符串 / null / 超大整数 / 非对象 | **409**，整行不变 | **409** | **409** | 否 |

409 响应 detail 只列出未知键名/非法键名，不回显原始值（避免 NaN/Infinity 序列化问题）。

## 4. 验收要求对照

| 复审要求 | 落实 | 证据 |
| --- | --- | --- |
| 1. 所有 PUT 路径先统一守卫；未知键/非数字/布尔/NaN/Inf/越界 → 409，任何字段不提交 | `_validated_history_vector` 在赋值前调用 | 36 条路径矩阵 + 组合 1 条 + live 3 条 |
| 2. 合法缺键补 0.5；仅当历史值全部合法且无未知键 | 先校验后补齐；非法/未知直接 409 | 4 条补齐用例 + live 预算补齐 |
| 3. 仅预算/仅忌口/仅菜系/合法向量；覆盖缺键/未知/越界/非有限；断言状态码与前后快照 | 9 状态 × 4 路径；快照含向量/预算/忌口/菜系/红黑榜 | 专项 96 条 |
| 4. 重新生成 r02 manifest、完整日志、隔离 HTTP 证据 | 146 项 manifest、red/green/全量日志、8014 隔离探针 | 本目录 |

## 5. 验证结果

- 红灯：专项 **42 failed / 54 passed**（exit 1，`logs/00_red_baseline.log`），包含复审两条复现。
- 绿灯：专项 **96 passed**；后端全量 **306 passed, 1 skipped**，exit 0。
- 真实 HTTP：隔离副本 45 个用例，状态 `{200,404,409,422}`，0 个 500；复审两场景均 409 且整行不变；合法缺键预算更新 200 并补齐 8 键；唯一合法写入为 1 条打卡。
- 数据库保护：演示库 `775da775…bd3a60b`、S10 库 `315eb3da…6918c28`、开发源库 `b965e73e…706a579` 前后一致。
- 前端无改动，未跑 build/界面门禁/浏览器（理由见 `BASELINE.md` §7）。

## 6. 待裁决与范围外缺口

- SSOT 未定义的 15 项代码口径保持原值并列入待裁决，见 `validation.json.pending_adjudications`。
- 范围外缺口 3 项：`group_rooms.campus`、房间人数上限、`catalog` 只读枚举，见 `validation.json.out_of_scope_gaps`。
- 本步未验证多人 WS、S03/S04、`/admin`、S10、APK。

## 7. 证据索引

| 文件 | 内容 |
| --- | --- |
| `BASELINE.md` | r02 源码/环境/三库身份/红灯行为/边界表 |
| `CHECKS.md` | 命令、cwd、退出码、日志与覆盖说明 |
| `SOURCE_MANIFEST.json` | 146 项受审文件 SHA-256，fingerprint `2c8cc39d…c9556a` |
| `validation.json` | 验收矩阵、复审发现、待裁决、缺口、停止原因 |
| `data/boundary_table.json` | 38 项字段边界（r02 已更新向量语义） |
| `data/db_protection.json` | 三库前后哈希、r02 隔离库 schema/行数 |
| `data/live_api_probe.json` | 45 步真实 HTTP 结果（含 409 历史守卫） |
| `logs/` | 红灯、专项、全量、隔离服务与探针日志 |

提交后立即停手，等待 Codex 独立复审。
