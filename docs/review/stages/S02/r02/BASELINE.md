# S02 / r02 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S02 数值、向量与持久化边界（F08）
轮次：r02（整改 S02/r01 FAIL）
前置：[S01/r01 独立复审 PASS](../../../clearance-codex-s01-r01/REPORT.md)；[S02/r01 独立复审 FAIL](../../../clearance-codex-s02-r01/REPORT.md)，受审 manifest `eb17fe30…f9b03f`

## 1. 本轮整改目标

S02/r01 复审阻断项：

- **S02-R01-01**：历史非法向量在只改预算/忌口/菜系时未被校验，200 且预算已写入。
- **S02-R01-02**：历史未知键在向量更新中被静默丢弃。

r02 把历史向量守卫前移到 `PUT /users/{id}/preferences` 的最前面，任何字段更新前先校验；非法/未知历史值统一 409，整行不写；只有“值全部合法、无未知键、仅缺键”才补 0.5 后继续。

r01 证据包原样保留在 `docs/review/stages/S02/r01/`，本轮不覆盖。

## 2. 源码与工作树

- 分支：`master`；HEAD 不存在（仓库无 commit）；commit 数 0。
- 清单生成时状态：staged 280 / unstaged 137 / untracked 59（`git status --porcelain`）。
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（本步未动 index）。
- 契约：`MASTER_SPEC.md` v2.3.5。
- r02 `SOURCE_MANIFEST.json`：146 项，fingerprint `2c8cc39df3a00c8f11c15ecf77d768da47e969447ba6a4fb5140885829c9556a`。
- 仓库无 commit，受审版本以 manifest 逐文件 SHA-256 为准。

本步相对 S01 的代码改动仍为 6 个文件；其中 r02 本轮新改 2 个：

| 文件 | SHA-256 | r02 变化 |
| --- | --- | --- |
| `backend/routers/auth_user.py` | `3adedba4a5ffd9b1a0a91128990b8ca9b55eb0c51f8b9da368a147a7d23fa6f7` | **是**：新增 `_validated_history_vector`，守卫前移到所有更新路径 |
| `backend/tests/test_s02_numeric_bounds.py` | `e776f7364de6d0f5cadbb78ad56d5cc493ceb7b06b4d57a5a65e627b2dcf6f69` | **是**：新增 49 条历史向量路径矩阵与原子失败用例 |
| `backend/schemas.py` | `2c11ac5178831dc1983b65e0dd8033fc12370518f7c3b1c316b9ba0b996bfcf7` | 否（r01 已改） |
| `backend/routers/recommend.py` | `63da04f3b90b462a025dfc1a0cf8c4cef96e5ac1d379058dddaa385c110d1864` | 否 |
| `backend/routers/fridge.py` | `e74a17799b7b230104dedf56e01fa49dc82fda329a500c806e6e314dfcb9e373` | 否 |
| `backend/main.py` | `50fbe09d2b1908ced770cacb809e32387618853d23256c1369dfd9f48940e35a` | 否 |

未改前端、`models.py`、迁移、SSOT、台账、`/admin`、S10。

## 3. 环境

| 项 | 值 |
| --- | --- |
| OS | Windows 10.0.22631 x64 |
| Python | 3.13.9 |
| Node | v24.19.0 |
| npm | 11.17.0 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |

## 4. 数据库身份与保护

机器可读版本：`data/db_protection.json`。

| 库 | 路径 | 基线 SHA-256 | 收尾 SHA-256 | 是否变化 | 行数摘要 |
| --- | --- | --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775…bd3a60b` | `775da775…bd3a60b` | 否 | 4 用户 / 100 菜 / 9 日志 / 0 房间 / 0 票 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da…6918c28` | `315eb3da…6918c28` | 否 | 7,664 门店 / 6,400 菜谱 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73e…706a579` | `b965e73e…706a579` | 否 | 4 用户 / 100 菜 / 9 日志 |
| r02 隔离副本 | `backend/eatwhat_s02_r02_iso.db` | 从开发源库复制，初值 `b965e73e…706a579` | `c9b1a59e…778278` | 是（仅本副本） | 日志 9→10；user2 历史向量用例后已还原 |

- 隔离副本 schema fingerprint：`71533fce45b53fbab2bb062171bef68c3e6165d977f46075830c24de81e05fb0`，与源库一致。
- pytest 隔离：`DATABASE_URL` 未设置；`conftest.py` 用 `sqlite://` + `StaticPool` 内存库并覆盖 `get_db`；`test_room.py` 的 `room_env` 夹具 monkeypatch `group_room.SessionLocal`。
- 真实 HTTP 探针只连 `127.0.0.1:8014` 的 r02 隔离副本；三库前后哈希一致。

## 5. 修复前行为基线（r02 红灯，已复现）

| # | 历史向量 + 请求 | r01 实际 | r02 期望 |
| --- | --- | --- | --- |
| 1 | `{"spicy_level":95,"oily_level":0.8}` + `{"default_budget":31}` | 200，预算写入 31，坏向量保留 | 409，整行不变 |
| 2 | `{"spicy_level":0.5,"umami_level":0.5}` + `{"base_vector":{"soup_level":0.7}}` | 200，未知键被删除 | 409，未知键保留、整行不变 |
| 3 | 同上 + 预算/忌口/菜系/组合更新 | 200，部分字段已写 | 409，全部字段不变 |
| 4 | 历史含 NaN/Infinity/布尔/字符串/null/超大整数/非对象 + 任意更新 | 部分 200 | 409，整行不变 |
| 5 | 历史仅缺键且值合法 + 预算更新 | 200，但向量仍缺键 | 200，补齐 8 键后写预算 |

红灯日志：`logs/00_red_baseline.log`（**42 failed / 54 passed**，exit 1）。

## 6. 字段边界表（r02 更新）

完整机器可读版本：`data/boundary_table.json`（38 项）。r02 只改写“`base_vector` 更新语义”一项：

| 字段 | 规则 | 依据 / 状态 |
| --- | --- | --- |
| `base_vector` 更新 | 每次偏好更新（预算/忌口/菜系/向量/组合）先校验历史向量；未知键、非数字、布尔、NaN/Infinity、越界值 → 409，整行不写；全部合法但缺键 → 补 0.5；完整八维覆盖也不能绕过非法历史值 | 用户 2026-10-26 方案 A + S02/r01 复审 S02-R01-01/02 |
| 八维键名 / 存储范围 | 恰好 8 键；有限数 0.0–1.0 | SSOT 第二章 1、第三章 4 |
| `radar_5d` / `total_score` | 0–100 / 展示 `min(100, 原始分)` | SSOT 第四章算法 2 |
| 四权重 | 归一化后和为 1 | SSOT 第四章算法 2 |
| `lambda_decay` / `omega_group` | 0.1–2.0 / 0.0–1.0 | SSOT 第六章 4 |
| 气泡 | 6 个固定 ID；无效 422；模式不适用仍 200 + `ignored` | SSOT 第二章 2 + S02 无效枚举要求 |
| 预算/天气/距离/limit/打卡金额/标签长度等 | 15 项代码口径，SSOT 未定义 | 待裁决，见 `validation.json.pending_adjudications` |
| `default_budget` 默认值 / 冰箱枚举 / 房间枚举 / 划卡分值 | SSOT 明文 | SSOT 第三、四章 |
| 房间 `campus`、人数上限、`catalog` 查询枚举 | 未实现/只读缺口 | `validation.json.out_of_scope_gaps` |

## 7. 未执行 / 不适用

- 前端无改动，未跑 `npm run build`、界面门禁或浏览器；预算/天气控件范围只做只读核对（Profile 8–80、Home 10–120、天气预设 12/26/34 均在 API 区间内）。
- 多人 WS、S03 时效、S04 四算法、S10/`/admin`、APK 不在本步，未验证也未触碰。
