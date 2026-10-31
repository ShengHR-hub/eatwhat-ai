# S02 / r01 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S02 数值、向量与持久化边界（F08）
轮次：r01
前置：[S01/r01 独立复审 PASS](../../../clearance-codex-s01-r01/REPORT.md)，受审 manifest `3caa7db07f0516db1ecbda9e58a7cee35c3832ad235dc74f0f4f9c1002c4ad29`

## 1. 源码与工作树

- 分支：`master`；HEAD 不存在（仓库无 commit）；commit 数 0。
- 清单生成时状态：staged 280 / unstaged 137 / untracked 62（`git status --porcelain`）。
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（与 S01 相同，本步未动 index）。
- 契约：`MASTER_SPEC.md` v2.3.5。
- S02/r01 `SOURCE_MANIFEST.json`：145 项，fingerprint `eb17fe30bea0b2c3e530da3465006504944af480f88d65ba4724ce0e17f9b03f`。
- 仓库无 commit，无法从 Git 还原 S01 后的文件内容；受审版本以 manifest 逐文件 SHA-256 为准。
- `docs/review/STAGE_STATUS.md` 与 S01 manifest 中的版本不同：当前文件 mtime `2026-10-26 01:10:22`，早于本步首次代码编辑 `01:31:28`；这是 Codex 在 S01 PASS 后更新台账（S01 PASS / S02 READY）所致，开发方未修改台账。S00/S01 复审报告文件亦由 Codex 在该时点写入。

本步实际改动 6 个文件（哈希取自 manifest）：

| 文件 | SHA-256 | 性质 |
| --- | --- | --- |
| `backend/schemas.py` | `2c11ac5178831dc1983b65e0dd8033fc12370518f7c3b1c316b9ba0b996bfcf7` | 修改 |
| `backend/routers/auth_user.py` | `810659ea39bc64571493823393b20cea541e70c5edbada5cdc540cdff63b3b75` | 修改 |
| `backend/routers/recommend.py` | `63da04f3b90b462a025dfc1a0cf8c4cef96e5ac1d379058dddaa385c110d1864` | 修改 |
| `backend/routers/fridge.py` | `e74a17799b7b230104dedf56e01fa49dc82fda329a500c806e6e314dfcb9e373` | 修改 |
| `backend/main.py` | `50fbe09d2b1908ced770cacb809e32387618853d23256c1369dfd9f48940e35a` | 修改 |
| `backend/tests/test_s02_numeric_bounds.py` | `05613f6c9bd95d431a9d0ca374ab0ecd6f456f732a373f3e83948d11418af216` | 新增（未跟踪） |

未改前端、SSOT、models/表结构、迁移、台账、`/admin`、S10。

## 2. 环境

| 项 | 值 |
| --- | --- |
| OS | Windows 10.0.22631 x64 |
| Python | 3.13.9 |
| Node | v24.19.0 |
| npm | 11.17.0 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |

## 3. 数据库身份与保护

机器可读版本：`data/db_protection.json`。

| 库 | 路径 | 基线 SHA-256 | 收尾 SHA-256 | 是否变化 | 行数摘要 |
| --- | --- | --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775…bd3a60b` | `775da775…bd3a60b` | 否 | 4 用户 / 100 菜 / 9 日志 / 0 房间 / 0 票 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da…6918c28` | `315eb3da…6918c28` | 否 | 7,664 门店 / 6,400 菜谱 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73e…706a579` | `b965e73e…706a579` | 否 | 4 用户 / 100 菜 / 9 日志 |
| 本步隔离副本 | `backend/eatwhat_s02_r01_iso.db` | 从开发源库复制，初值 `b965e73e…706a579` | `469096d8…8bb522` | 是（仅本副本） | 日志 9→10（唯一合法打卡）；房间/票仍 0 |

- 隔离副本 schema fingerprint：`71533fce45b53fbab2bb062171bef68c3e6165d977f46075830c24de81e05fb0`，与源库一致。
- pytest 隔离方式：`DATABASE_URL` 未设置；`backend/tests/conftest.py` 用 `sqlite://` + `StaticPool` 内存库并通过 `dependency_overrides[get_db]` 注入；`test_room.py` 的 `room_env` 夹具 monkeypatch `group_room.SessionLocal`，后台结算任务不会落到演示库。
- 真实 HTTP 探针只连 `127.0.0.1:8013` 的隔离副本；演示库、S10 库、开发源库前后哈希一致。

## 4. 修复前行为基线（内存库探针，已复现）

| # | 输入 | 修复前实际 | 期望 |
| --- | --- | --- | --- |
| 1 | `GET /context/weather?temp=nan` | **500**（响应含 NaN 无法序列化） | 422 |
| 2 | `GET /context/weather?temp=1000` / `weather` 200 字 | 200 | 422 |
| 3 | `PUT /users/1/preferences {"base_vector":{}}` | 200，库内向量变 **0 键** | 422，库不变 |
| 4 | 同上，只传 2 键 | 200，库内向量变 **2 键**（其余丢失） | 200，合并后 8 键 |
| 5 | 向量值 `true` / `"0.5"` | 200，存成 `1.0` / `0.5` | 422 |
| 6 | 向量值 `NaN/Infinity` | 422 详情无法序列化 → 实际 **500** | 422 |
| 7 | 推荐 `bubbles:["bogus"]` | 200，静默忽略 | 422 |
| 8 | 推荐 `budget/limit/weather_temp/exclude_dish_ids` 用布尔 | 200，按 1.0/1 执行 | 422 |
| 9 | 打卡 `dish_id:true` / `cost_amount:true` | 200，写入日志 | 422，日志数不变 |
| 10 | 冰箱 `ingredient_name:"   "` | 200，写入**空字符串** | 422 |
| 11 | 购物清单 `dish_ids:[有效,99999]` | 200，静默忽略未知项 | 404 |
| 12 | 红黑榜 `target_id:true` | 200，把菜品 1 加入红榜 | 422，收藏不变 |
| 13 | 建房 `override_params:{"omega_group":true}` | 200，按 1.0 建房 | 422，不建房 |

红灯日志：`logs/00_red_baseline.log`（24 failed / 11 passed，exit 1）。

## 5. 字段边界表（对照 SSOT）

完整机器可读版本：`data/boundary_table.json`（38 项，含 SSOT/代码/待裁决/越界缺口标注）。摘要：

| 字段 | 规则 | 依据 / 状态 |
| --- | --- | --- |
| 八维键名 | 恰好 8 键，键名逐字锁定 | SSOT 第二章 1、第三章 4 |
| 向量存储值 | 有限数，0.0–1.0 | SSOT 第二章 1、第三章 4 |
| `feature_vector` 可空 | NULL=未完成；成功必须完整 8 键 | SSOT v2.3.3 第三章 4 |
| `base_vector` 更新 | 部分合并；`{}` 422；合并后 8 键；历史缺键 0.5 补齐；历史非法值 409 | **用户 2026-10-26 确认方案 A** |
| `radar_5d` | 5 键，各 0–100 | SSOT 第四章算法 2 |
| `total_score` | 排序用原始分，展示 `min(100, 原始分)` | SSOT v2.3.2 第四章算法 2 注 |
| 四权重 | 归一化后和为 1 | SSOT 第四章算法 2 |
| `lambda_decay` / `omega_group` | 0.1–2.0 / 0.0–1.0 | SSOT 第六章 4 |
| `alpha/beta/gamma/delta` 单值 | 0–1，最终归一化 | 代码 `PARAM_BOUNDS`，待裁决 |
| 气泡 ID | 6 个固定 ID；最多 12 个 | SSOT 第二章 2；上限 12 为代码 |
| 无效气泡 | 422；合法但模式不适用 → 200 + `ignored` | S02 无效枚举要求；模式忽略为既有契约 |
| `default_budget` | 默认 25.0；接受 8–500 | 默认值 SSOT；上下界为代码，待裁决 |
| 推荐 `budget` | 0–2000 | 代码，待裁决；Home 滑块 10–120（120=不限） |
| `weather_temp` / 文本 | -30–50 / ≤32 字 | 代码，待裁决；本轮让 weather 接口同界 |
| `max_distance_meters` | 0–100000 | 代码，待裁决 |
| `limit` | 1–100 | 代码，待裁决 |
| 打卡 `cost_amount` / 快照 | 0–100000 / ≤64 字 | 代码，待裁决 |
| `veto_tags` / `preferred_cuisines` | ≤20 条；忌口单条 ≤16 字非空 / ≤20 条 | 代码，待裁决；SSOT 未定义长度 |
| 冰箱 `category` | 四枚举 | SSOT 第三章 5 |
| `expire_days` | 默认 3；接受 0–365 | 默认值 SSOT；上界为代码 |
| `ingredient_name` / `quantity_desc` | 1–32 非空白 / ≤32 非空白，默认「适量」 | 长度代码；空白漏洞本轮修复 |
| 购物清单 `dish_ids` | 非空；任一不存在 404 | 引用校验，本轮收紧 |
| 红黑榜枚举/引用 | DISH/RESTAURANT、FAV/BLACK、ADD/REMOVE；目标不存在 404 | SSOT 第五章模块 1 |
| 房间枚举 | OUT_DINING/HOME_COOKING；WAITING/SWIPING/FINISHED；四投票枚举 | SSOT 第三章 7/8 |
| 房间 `budget` | 8–500 | 代码，待裁决 |
| 房间 `campus` | 建房必填、join 同校区、跨校区 409 | SSOT v2.3.4 §5.5，**未实现**，登记 S06/BRIDGE-10 |
| 划卡分值 | 120/100/40；VETO 只掩码 | SSOT 第三章 8、第四章算法 3；TIMEOUT=60 非 SSOT 正文 |

待裁决（SSOT 未定义，本步未新增数值，仅记录）：15 项，见 `validation.json.pending_adjudications`。
本步不修的缺口：房间人数上限 8、`group_rooms.campus`、`catalog` 查询枚举（只读）——见 `validation.json.out_of_scope_gaps`。

## 6. 未执行 / 不适用

- 前端无改动，未跑 `npm run build` 与界面门禁；预算/天气控件范围只做只读核对（Profile 8–80、Home 10–120、天气预设 12/26/34 均落在 API 区间内）。
- 无 UI 改动，未启动浏览器；S02 的写入边界全部由后端专项、全量 pytest 与真实 HTTP 探针覆盖。
- 多人 WebSocket 投票枚举/结算、S03 时效、S04 四算法、`/admin`、S10 未在本步验证，未触碰。
