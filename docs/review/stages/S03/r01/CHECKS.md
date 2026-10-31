# S03 / r01 检查记录（CHECKS）

日期：2026-10-26（Asia/Shanghai）
所有命令在本机执行；cwd 与退出码逐条保留。日志在 `logs/`，数据在 `data/`。

## 1. 命令总表

| # | 命令 | cwd | 退出码 | 结果 | 日志 / 证据 |
| --- | --- | --- | --- | --- | --- |
| 1 | `python -m pytest tests/test_s03_fridge_lifecycle.py tests/test_identity_bounds_and_stock.py tests/test_query_budget.py tests/test_fridge.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s03r01-red` | `D:/EatWhat/backend` | **1（预期红灯）** | 16 failed, 30 passed, 12 errors | `logs/00_red_baseline.log` |
| 2 | `python -m pytest tests/test_s03_fridge_lifecycle.py tests/test_identity_bounds_and_stock.py tests/test_query_budget.py tests/test_fridge.py tests/test_combo_optimizer.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s03r01-target3` | `D:/EatWhat/backend` | **0** | **63 passed** | `logs/12_backend_pytest_s03_final.log` |
| 3 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s03r01-full` | `D:/EatWhat/backend` | **0** | **335 passed, 1 skipped** | `logs/10_backend_pytest_full.log` |
| 4 | `python docs/review/stages/S03/r01/data/live_api_probe.py` | `D:/EatWhat` | **0** | 15 步真实 HTTP；状态 `{200,403}`；0 个 500；服务自动停止 | `data/live_api_probe.json`、`logs/20_live_server.log`、`logs/21_live_probe.log` |
| 5 | `python docs/review/stages/S03/r01/data/build_db_protection.py` | `D:/EatWhat` | **0** | 三库未变；隔离库 schema 与源库一致 | `data/db_protection.json`、`logs/22_db_protection.log` |
| 6 | `python docs/review/stages/S03/r01/data/build_boundary_table.py` | `D:/EatWhat` | **0** | 13 组边界 + 6 组时区/DST | `data/clock_boundary.json`、`logs/23_boundary_table.log` |
| 7 | `python docs/review/stages/S03/r01/data/build_validation.py` | `D:/EatWhat` | **0** | 机器可读验收摘要 | `validation.json`、`logs/25_validation.log` |
| 8 | `python docs/review/stages/S03/r01/data/build_manifest.py` | `D:/EatWhat` | **0** | 147 项，fingerprint `cd3d7c23…8c8fe` | `SOURCE_MANIFEST.json`、`logs/24_manifest.log` |

> 所有 pytest 使用仓库内独立 `--basetemp=D:/EatWhat/.pytest-tmp-s03r01-*`，未触发本机 Windows 临时目录权限问题；这些目录是本次运行产物，已在收尾清理。
> 红灯日志是**实现前**的真实失败（含 `fridge_clock.now_utc` 尚不存在导致的 12 个 setup error）；同一批用例在实现后 63 条全过。
> 收尾审查时补了“推荐索引每个请求只解析一次当前时间”，随后重跑了专项、全量与真实 HTTP 探针（本表第 2/3/4 行均为最终代码的结果）。

## 2. 红灯覆盖的具体缺口

| # | 用例 | 实现前实际 | 期望 |
| --- | --- | --- | --- |
| 1 | `test_clock_boundary_matrix[3-216000-…]`（已过 2.5 天） | `remaining=0`、`is_expired=True` | `remaining=1`、未过期 |
| 2 | `test_clock_boundary_matrix[3-51840-…]`（剩余 2.4 天） | `remaining=2`（round） | `remaining=3`（ceil） |
| 3 | `test_clock_boundary_matrix[3-86400-…]`（剩余 48h） | 临期判定依赖旧取整 | `remaining=2`、临期 |
| 4 | `test_clock_invariants_hold_across_sweep` | 取整后等价关系不成立 | `0 天 ⇔ 过期`、`≤2 ⇔ ≤48h` |
| 5 | `test_expired_item_is_reported_as_zero_days_and_not_expiring` | `is_expiring_soon=True` | `False` |
| 6 | 12 条 API/闭环用例 | `fridge_clock.now_utc` 不存在（setup error） | 固定时钟可注入 |

## 3. 实现后定向覆盖

- **纯时钟**：13 组参数边界 + 全区间 30 分钟步长扫掠 + 6 组时区/DST（美东回拨/春进、+08:00、naive UTC）。
- **四处一致**：同一库存行同时经 `GET /fridge`、`POST /recommend/single`、`POST /fridge/shopping-list`、`build_shopping_list(now=…)`，断言 0 天/非临期、status=25、清单切分完全一致。
- **临期双倍**：48h 整 → 双倍；48h+1s → 不双倍；0.5 天 → 双倍；过期 → 0。
- **排序**：临期第一组按剩余天数升序；过期项（0 天、非临期）排在临期之后、新鲜项之前。
- **清单**：合并去重、`used_by` 不重复、`owned`/`to_buy` 互斥、多余库存不出现、同名过期/有效并存仍算已有、重复 `dish_id` 不重复。
- **闭环**：ADD→GET→推荐→清单→同名重录（`created_at` 重置、单行）→REMOVE→推荐回落/清单转待买。
- **跨用户**：GET/ADD/REMOVE 403 且对方库存快照不变；推荐与清单的 body `user_id` 被请求头覆盖，拿不到对方库存。
- **外食**：加库存前后推荐结果（ID + status）一致，且 SQL 监听确认不查 `fridge_inventory`。

## 4. 全量回归与警告

- 最终全量：**335 passed, 1 skipped, 61 warnings, exit 0**（16.09s）。
- S02 基线为 306 passed；本步新增 29 条专项用例，306 + 29 = 335，条数吻合，未删旧用例。
- skip 为既有 Windows 符号链接权限用例；本步未新增 skip。
- warnings 为既有 `datetime.utcnow()` 弃用（主要集中在 `test_room.py` 与旧测试）与 `requests/urllib3` 版本提示；无新增未处理异常。
- 唯一改写的旧断言是“过期 ⇒ 临期”（S03 新口径冲突），其余旧断言保留。

## 5. 真实 HTTP 与隔离库

隔离副本：`backend/eatwhat_s03_r01_iso.db`，由 `backend/eatwhat_dev_pre00_r02.db`（`b965e73e…706a579`）复制；schema fingerprint 与源库一致。

| 项目 | 结果 |
| --- | --- |
| 用例步数 | 15 |
| 状态码集合 | `{200, 403}`；**0 个 500** |
| 过期/新鲜列表 | 过期 `0` 天且非临期；新鲜 `5` 天 |
| 推荐 status | 新鲜 25 / 临期 50 / 过期 0 |
| 同名重录 | 行数 1、`expire_days=3`、`created_at` 在请求后 30s 内 |
| 跨用户 | GET/ADD/REMOVE 均 403；body `user_id=2` 被请求头覆盖；对方库存快照不变 |
| 外食 | 加库存前后推荐（ID + status）一致 |
| 受保护库 | 演示库 / S10 库 / 开发源库 SHA-256 前后一致 |
| 服务端 | `127.0.0.1:8015` 已停止，无 LISTEN |

服务端日志 `logs/20_live_server.log` 可见 3 次 `path_header_mismatch … status=403` 与 2 次 `identity_conflict … resolution=header`。

## 6. 未执行

- 前端无改动：未跑 `npm run build`、界面门禁、浏览器（理由见 `BASELINE.md` §7）。
- S04、S05–S08、`/admin`、S10–S20、APK 不在本步，未验证也未触碰。
