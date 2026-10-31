# S03 / r01 提交说明

步骤：S03 冰箱时效与采购闭环（F09）
轮次：r01
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-26（Asia/Shanghai）
前置：[S02/r02 独立复审 PASS](../../../clearance-codex-s02-r02/REPORT.md)，受审 manifest `2c8cc39d…c9556a`

**未签 PASS；未修改 `docs/review/STAGE_STATUS.md`；未创建/修改任何 `REVIEW.md`；未开始 S04；未触碰 `/admin`、S10–S20。** 本步只改后端与 SSOT 说明，未改前端。

## 1. 用户裁决与落地

| 裁决 | 内容 | 落地 |
| --- | --- | --- |
| **1A** | `expires_at = created_at + expire_days × 24h`，UTC 绝对时间；`now >= expires_at` 即过期；过期返回 0 天；未过期按剩余秒数**向上取整**；临期 = 未过期且实际剩余 ≤48h | `backend/algorithms/fridge_clock.py` 重写；列表/推荐/清单/组合采购全部改读它 |
| **2A** | 同名再次 `ADD` 视为重新入库：覆盖属性并把 `created_at` 重置为当前时间；历史重复行不合并/删除，任一条有效即算已有 | `backend/routers/fridge.py` 的 ADD 分支 |
| **3B** | 后端实现 + 证据包记录裁决 + 同步 `MASTER_SPEC.md`；不改前端 | `MASTER_SPEC.md` 增加 v2.3.5 补充裁定，并改字段/路由/算法 2 三处措辞 |

边界等价关系（已写成测试）：

- `is_expired ⇔ now >= expires_at ⇔ remaining_days == 0`
- `is_expiring_soon ⇔ 0 < 剩余秒数 <= 48h ⇔ (not expired) and remaining_days <= 2`
- 未过期最小显示 1 天；实际剩余 2.4 天显示 3 天；剩余 0.5 天显示 1 天

## 2. 实际修改文件

| 文件 | 改动 | 原因 |
| --- | --- | --- |
| `backend/algorithms/fridge_clock.py` | 重写：`now_utc()`、`expires_at()`、精确 `is_expired`、`ceil` 语义的 `remaining_days`、独立 `is_expiring_soon`；aware 时间归一化到 UTC naive | 1A / F09 提前过期 |
| `backend/routers/fridge.py` | 列表统一单次请求时钟；`is_expiring_soon` 不再包含过期项；ADD 同名重置 `created_at`；清单用同一 `is_expired` | 1A / 2A / 过期不算临期 |
| `backend/algorithms/single_recommender.py` | `_fridge_index` / `_fridge_status_score` 接受 `now`，与衰减共用时点；`now=None` 时每个请求只解析一次当前时间；过期跳过、临期双倍改走 `fridge_clock` | 四处同口径 |
| `backend/algorithms/combo_optimizer.py` | `build_shopping_list` 增加 `now` 并排除过期库存 | 采购消费端同口径 |
| `backend/tests/test_s03_fridge_lifecycle.py` | **新增 29 条**：固定时钟边界/等价关系/DST、四处一致、临期双倍、排序、无主料/缺料/多余库存、合并去重、同名重复行、CRUD 闭环、同名重录、跨用户五类负向、外食不读库存 | 最小回归先行（红灯 16 failed / 30 passed / 12 errors） |
| `backend/tests/test_identity_bounds_and_stock.py` | 把“过期 ⇒ 临期”旧断言改为“过期 ⇒ 0 天且非临期”（1 行断言 + 测试名） | 与新口径冲突的唯一旧断言 |
| `backend/tests/test_query_budget.py` | 独立参考实现改为按 1A 规格自行计算到期秒数，不再调用被测 `fridge_clock` | 保持“独立期望值”，不删断言、不改等价测试结构 |
| `MASTER_SPEC.md` | v2.3.5 补充裁定（到期边界、剩余天数、临期定义、统一消费、同名重录）；字段/路由/算法 2 措辞同步 | 3B |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、台账、`REVIEW.md`、`/admin`、S10。

## 3. 行为变化矩阵

| 场景 | 旧行为 | 新行为 |
| --- | --- | --- |
| `expire_days=3`，已过 2.5 天 | `remaining=0`、`is_expired=True`（提前半天过期） | `remaining=1`、未过期、临期 |
| 实际剩余 2.4 天 | `round(2.4)=2` | `ceil(2.4)=3` |
| 实际剩余恰好 48h | 2（临期） | 2（临期，含边界） |
| 实际剩余 48h+1s | 2（临期，错误） | 3（不临期） |
| 已过期项在 `GET /fridge` | `expire_days=0`、`is_expiring_soon=True` | `expire_days=0`、`is_expiring_soon=False`，仍返回可删除 |
| 同名食材再次 `ADD` | 保留旧 `created_at`，改保质期可能立即过期 | `created_at` 重置为当前时间 |
| `build_shopping_list`（算法侧） | 过期库存仍算「已有」 | 过期不抵扣 |
| 外食推荐 | 不读冰箱 | 不变（已加 SQL 与结果不变断言） |

## 4. 验收要求对照

| 验收项 | 落实 | 证据 |
| --- | --- | --- |
| 固定时间覆盖到期前/到期时/到期后，边界等价关系明确 | 13 组边界参数 + 全区间扫掠断言 + 6 组时区/DST 对照 | `test_clock_boundary_matrix`、`test_clock_invariants_hold_across_sweep`、`data/clock_boundary.json` |
| 时区/DST | 统一 UTC 绝对时间；aware 输入归一化；美东回拨/春进日与 +08:00 对照 | `test_clock_uses_absolute_utc_instants_across_dst_offsets`、`data/clock_boundary.json` |
| 四处一致 | 同一库存记录同时经列表、推荐 status、API 清单、组合采购断言 | `test_expired_stock_consistent_across_all_consumers` |
| 过期不计可用/不加分/不抵扣 | 过期 status=0、清单转 to_buy、列表 0 天非临期 | 同上 + `test_status_score_uses_exact_clock_and_double_weight` |
| 临期提权严格符合 SSOT | 48h 整双倍、48h+1s 不双倍；0.5 天仍双倍 | 同上 |
| 余料反推只用有效库存 | 推荐库存命中只读有效行；无主料/全缺料为 0 | `test_home_cooking_without_mains_or_stock_scores_zero` |
| 数量/单位/菜谱需求/重复菜品合并 | `quantity_desc` 按 SSOT 为自由文本、不做算术；合并去重与 `used_by` 独立断言；重复 `dish_id` 不重复 | `test_shopping_list_merges_dedupes_and_subtracts_valid_stock`、`test_shopping_list_quantity_desc_is_descriptive_not_deducted` |
| 增删改查→推荐→清单闭环 | ADD→GET→推荐→清单→同名重录→REMOVE→推荐回落/清单转待买 | `test_fridge_crud_loop_and_readd_resets_created_at`、`live_api_probe.json` |
| 跨用户读/写/删/推荐/清单消费 | 403、body 身份按头解析、对方库存快照不变 | `test_cross_user_cannot_read_update_delete_or_consume_fridge`、`live_api_probe.json` |
| 内存库/隔离副本 | pytest 内存库 `sqlite://`；HTTP 只写 `eatwhat_s03_r01_iso.db` | `BASELINE.md` §4、`data/db_protection.json` |
| 专项 + 后端全量 | 专项 63 passed；全量 335 passed, 1 skipped | `logs/12_*`、`logs/10_*` |
| 无新增 500；受保护库不变 | HTTP 状态集合 `{200,403}`；三库 SHA 前后一致 | `data/live_api_probe.json`、`data/db_protection.json` |
| 前端 build/门禁/浏览器 | **未执行**：本步未改 `frontend/**`；按任务“纯后端改动无需为形式补做浏览器验收” | `BASELINE.md` §6 |

## 5. 验证结果（真实输出）

- 红灯（实现前）：**16 failed, 30 passed, 12 errors**，exit 1（`logs/00_red_baseline.log`）。
- 专项（实现后）：**63 passed**，exit 0（`logs/12_backend_pytest_s03_final.log`）。
- 后端全量：**335 passed, 1 skipped**，exit 0（`logs/10_backend_pytest_full.log`）。S02 基线 306 passed，本步新增 29 条，条数吻合。
- 隔离 HTTP：**15 步，状态集合 `{200, 403}`，0 个 500**；跨用户 3 次 403、body 身份冲突日志可见；服务已停止（`logs/20_live_server.log`、`data/live_api_probe.json`）。
- 受保护库：演示库 `775da7…3a60b`、S10 库 `315eb3…6918c28`、开发源库 `b965e7…706a579` 前后一致；隔离副本 schema 与源库一致（`data/db_protection.json`）。
- manifest：147 项，fingerprint `cd3d7c233fb347913a22e1bf6f67d84b185b40837f903931c2f643a15ec8c8fe`。

## 6. 已知限制与未验证范围

- 前端代码未改，**未跑 `npm run build`、界面门禁或浏览器**。`Fridge.vue` 原本就把 `expire_days=0` 显示为“已到期”，临期计数/提示由接口的 `is_expiring_soon` 驱动，本次语义修正后会自动排除过期项；但本包不声称做过视觉验收。
- 真实 HTTP 探针使用真实系统时钟与相对时间样本（如“剩余 0.5 天”“恰好过期 1 秒前”），精确到秒的边界由固定时钟单测覆盖。
- `quantity_desc` 是自由文本，本步不新增数量/单位扣减规则；有有效库存即视为已有。
- 外食推荐不消费冰箱；本步只验证其不受库存影响。
- 同名历史重复行保留展示，不自动合并/删除；推荐与清单一律只认有效行，不叠加权重。
- SSOT 版本号保持 **v2.3.5**，以“补充裁定”形式精确化既有字段语义；如 Codex 认为需要正式升版，请按审查意见处理。
- S04、S05–S08、`/admin`、S10–S20、APK 均未验证、未触碰。

## 7. 证据索引

| 文件 | 内容 |
| --- | --- |
| `BASELINE.md` | 源码/环境/三库身份/新旧口径/未执行项 |
| `CHECKS.md` | 命令、cwd、退出码、日志与测试隔离 |
| `SOURCE_MANIFEST.json` | 147 项受审文件 SHA-256，fingerprint `cd3d7c23…8c8fe` |
| `validation.json` | 验收矩阵、裁决、测试摘要、数据库保护、范围外 |
| `data/clock_boundary.json` | 13 组边界 + 6 组时区/DST 固定时钟结果 |
| `data/live_api_probe.json` | 15 步真实 HTTP、状态码、隔离库与受保护库指纹 |
| `data/db_protection.json` | 三库前后哈希/schema/行数、隔离副本身份 |
| `data/build_*.py` | 边界表、库保护、validation、manifest 的可重跑脚本 |
| `logs/` | 红灯、专项、全量、隔离服务与探针、库保护、边界表、validation、manifest |

提交后立即停手，等待 Codex 独立复审。
