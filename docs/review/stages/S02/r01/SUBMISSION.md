# S02 / r01 提交说明

步骤：S02 数值、向量与持久化边界（F08）
轮次：r01
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
前置：S01/r01 由 Codex 独立复审 PASS；台账 S02 = READY

**未签 PASS；未修改 `docs/review/STAGE_STATUS.md`；未创建 REVIEW.md；未开始 S03；未触碰 `/admin`、S10、LLM、统计大屏或 APK。** 本说明不构成独立验收结论。

## 1. 开工决策：八维向量采用方案 A

用户 2026-10-26 明确回复「方案 A」。落地语义：

- `base_vector` 允许只传部分维度，按维度合并到库内旧向量；
- 合并后持久化结果**固定 8 键**；历史缺键用 0.5 中性值补齐；已有有效值原样保留；
- 空对象 `{}` 返回 **422**（不构成有效更新）；
- 未知维度、非数字、布尔、字符串、NaN/Infinity、0–1 之外的值一律 **422**；
- 历史行若已有值越界/非有限，返回 **409** 并要求提交完整八维覆盖，不 clamp、不把坏值写回；超大整数按整数范围判断，不会在 `float()` 处溢出。

该决策不是 SSOT 原文，已单独记录在 `data/boundary_table.json` 的 `USER_DECISION_2026_10_26`。

## 2. 实际修改文件

| 文件 | 改动 | 原因（探针证据见 `BASELINE.md` §4） |
| --- | --- | --- |
| `backend/schemas.py` | 新增 `NonBoolFloat/NonBoolInt`、`BUBBLE_IDS`、数值映射原始值校验；偏好向量非空/非数字/额外键校验；气泡 ID 白名单（推荐+打卡）；冰箱名称与数量描述去空白非空；购物清单/红黑榜/房间/推荐数值字段拒绝布尔 | 布尔被 Pydantic 转成 1.0/0.0；`{}` 与两键向量会清空/丢键；空白食材名入库为空串 |
| `backend/routers/auth_user.py` | 向量写入改为「合并 + 固定八键 + 历史缺键补齐」；新增历史非法值 409 守卫 | 原实现 `dict(payload.base_vector)` 是整段覆盖，违反八键完整存储 |
| `backend/routers/recommend.py` | `/context/weather` 的 `temp` 限定 -30–50、`weather` ≤32，NaN/Inf 422 | `temp=nan` 实际返回 500；1000℃/200 字文本被接受 |
| `backend/routers/fridge.py` | 购物清单任一 `dish_id` 不存在返回 404（列出缺失 ID） | `[有效, 99999]` 原本静默忽略未知项，清单会少算 |
| `backend/main.py` | 新增 `RequestValidationError` 处理器，把非有限浮点转字符串后再返回 422 | FastAPI 默认 422 详情回显 NaN/Infinity，响应序列化再抛错变成 500 |
| `backend/tests/test_s02_numeric_bounds.py`（新增） | 47 条专项回归 | 红灯先行，见 `logs/00_red_baseline.log` |

未改前端、`models.py`、迁移、SSOT、台账。

## 3. 可观察的契约变化

| 入口 | 变化 | 兼容性判断 |
| --- | --- | --- |
| `PUT /users/{id}/preferences` | 向量部分合并；`{}` 422；布尔/字符串/非有限 422；历史非法值 409 | 前端从不发送 `base_vector`（基因只读），零影响；现有 2 键用例仍 200 |
| `POST /recommend/single` | 未知气泡 422；数值字段布尔 422；JSON 体 NaN/Inf 稳定 422 | 前端只发 6 个已知气泡与数字；合法边界不变 |
| `POST /logs/checkin` | 未知气泡 422；`dish_id/cost_amount` 布尔 422 | 前端不发未知气泡 |
| `POST /fridge/{user_id}` | 空白名称/数量描述 422（原为 200 空串） | 前端只发非空名称 |
| `POST /fridge/shopping-list` | 任一未知 ID 404（原先部分未知仍 200） | 前端只发已选菜谱 ID |
| `POST /users/{id}/red-black-list` | 布尔 `target_id` 422 | 前端只发数字 ID |
| `POST /rooms/create` | override 参数布尔 422 | 前端只发数字/不传 |

合法边界（0/1、8/500、0/2000、-30/50、limit 1/100 等）全部接受，前端现有控件取值均在 API 区间内。

## 4. 验收条目自测

| S02 要求 | 结果 | 证据 |
| --- | --- | --- |
| 对照 SSOT 列出八键、存储/展示范围、参数、预算、天气、气泡等边界 | 完成，38 项；SSOT 未定义的 15 项标为待裁决 | `data/boundary_table.json`、`BASELINE.md` §5 |
| 完整/部分更新先锁定 | 已按用户确认方案 A 实现 | 本文件 §1 |
| 缺键/多键/空对象/布尔/NaN/Infinity/越界/无效枚举/超长标签/负金额/不存在引用 | 全部有反例；非法输入 4xx 或契约错误，无 500、无半更新、无脏写 | 专项 47 条 + live 探针 40 步 |
| 入库向量始终八键完整、有限、0–1 | 部分合并、历史缺键补齐、历史非法值 409；收尾实测 8 键有限 | `test_partial_vector_merges_and_keeps_eight_keys`、`data/live_api_probe.json` |
| 合法边界 API 接受 | 向量 0/1、预算 8/500 与 0/2000、天气 -30/50、limit 1/100、override 全边界 | `test_recommend_accepts_legal_boundaries_with_finite_scores` 等 |
| 推荐分数有限且符合 SSOT | radar 0–100；`total_score` 0–100（展示封顶）；decay 0–1；四权重和≈1 | 同上 + live 探针逐条断言 |
| 数据库前后状态断言 | 每条拒绝用例同时断言响应码与库状态；三库哈希前后一致 | 47 条用例 + `data/db_protection.json` |
| 写入只用内存库/隔离库 | pytest 用内存库；真实 HTTP 只用隔离副本；演示/S10/开发源库未变 | `BASELINE.md` §3、`CHECKS.md` §4 |

## 5. 测试与验证

- 红灯：S02 专项 24 failed / 11 passed（exit 1，`logs/00_red_baseline.log`）。
- 绿灯：专项 **47 passed**；后端全量 **257 passed, 1 skipped**，exit 0。
- 真实 HTTP：隔离副本 40 个用例，状态码仅 200/404/422，0 个 500；唯一合法写入为 1 条打卡；收尾向量 8 键。
- 数据库保护：演示库 `775da775…bd3a60b`、S10 库 `315eb3da…6918c28`、开发源库 `b965e73e…706a579` 前后一致。
- 前端无改动，未跑 build/界面门禁/浏览器；理由与只读范围核对见 `BASELINE.md` §6。

## 6. 待裁决与已知缺口（不阻塞本步自测，但需审查方判断）

**SSOT 未定义的代码口径（15 项，本步保持、未新增数值）**：`alpha/beta/gamma/delta` 单值界、`default_budget` 8–500、推荐 `budget` 0–2000、`weather_temp` -30–50、天气文本 32、`max_distance_meters` 0–100000、`limit` 1–100、打卡 `cost_amount` 0–100000、快照 64、忌口/菜系条数与长度、冰箱 `expire_days` 0–365、`quantity_desc`/`ingredient_name` 长度、房间 `budget` 8–500、向量中性值 0.5。完整列表见 `validation.json.pending_adjudications`。

**本步不修的缺口（3 项）**：
1. `group_rooms.campus` 未进入 `RoomCreateRequest`/join（SSOT v2.3.4 §5.5），归 S06 / BRIDGE-10；
2. 房间人数上限 8 为代码值，SSOT 未写，归 S06；
3. `GET /catalog/*` 的非法 `mode_type` 返回空列表而非 4xx，只读接口，归 S05/S08 只读回归。

**范围限制**：未验证多人 WS 投票枚举/结算（S06）、冰箱精确到期边界（S03）、四算法独立期望值（S04）、`/admin`/S10/APK。本步 PASS 不应被解读为这些范围通过。

## 7. 证据索引

| 文件 | 内容 |
| --- | --- |
| `BASELINE.md` | 源码/环境/三库身份/修复前行为/字段边界表 |
| `CHECKS.md` | 命令、cwd、退出码、日志、覆盖说明 |
| `SOURCE_MANIFEST.json` | 145 项受审文件 SHA-256，fingerprint `eb17fe30…f9b03f` |
| `validation.json` | 机器可读验收矩阵、待裁决、缺口、停止原因 |
| `data/boundary_table.json` | 38 项字段边界与依据 |
| `data/db_protection.json` | 三库前后哈希、隔离库 schema/行数 |
| `data/live_api_probe.json` | 40 步真实 HTTP 结果与受保护库哈希 |
| `logs/` | 红灯、各轮全量、最终专项、隔离服务与探针错误日志 |

提交后立即停手，等待 Codex 独立复审。
