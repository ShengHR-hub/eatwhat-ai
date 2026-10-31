# S03 / r01 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S03 冰箱时效与采购闭环（F09）
轮次：r01
前置：[S02/r02 独立复审 PASS](../../../clearance-codex-s02-r02/REPORT.md)，受审 manifest `2c8cc39d…c9556a`

## 1. 本轮目标

关闭 S00/F09 的残留缺口：

- `round()` 导致 `expire_days=3` 在已过 2.5 天时提前判过期；
- 过期项被计入「临期」；
- 展示 / 推荐 / 采购 / 组合采购没有全部走同一时钟；
- 同名重录不重置 `created_at`；缺少固定时钟边界、时区/DST、跨用户消费与闭环测试。

口径按用户 2026-10-26 裁决 **1A / 2A / 3B** 执行，并同步 `MASTER_SPEC.md`（v2.3.5 补充裁定）。

## 2. 源码与工作树

- 分支：`master`；HEAD 不存在（仓库无 commit）；commit 数 0。
- manifest 生成时状态：staged 280 / unstaged 138 / untracked 61（`git status --porcelain`；测试临时目录已清理）。
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（本步未动 index）。
- 契约：`MASTER_SPEC.md` v2.3.5 + 2026-10-26 S03 补充裁定；版本号未升。
- `SOURCE_MANIFEST.json`：147 项，fingerprint `cd3d7c233fb347913a22e1bf6f67d84b185b40837f903931c2f643a15ec8c8fe`。
- 仓库无 commit，受审版本以 manifest 逐文件 SHA-256 为准。

## 3. 受审改动文件

| 文件 | SHA-256 | 性质 |
| --- | --- | --- |
| `backend/algorithms/fridge_clock.py` | `2fa6329f1663a3acabff667315c53bd647884ef00272346d348e9a33f554f23d` | 重写唯一时钟 |
| `backend/routers/fridge.py` | `f0ec5a8747bbc28ee82e1831beac62aa29688687cae243fe6a0cabe41f796d26` | 列表标记 / 同名重录 / 清单 |
| `backend/algorithms/single_recommender.py` | `1937f9f16a115808cfc49ad3702425de5e1bce3e953734bbd4e7f1e76d3dcb64` | 推荐库存索引共用时钟 |
| `backend/algorithms/combo_optimizer.py` | `a75ca3eb15236d89e6dfd9d034beceee67cceb6a9cbc491f55c9a324e72df5b6` | 组合采购排除过期 |
| `backend/tests/test_s03_fridge_lifecycle.py` | `3ea0eff99b36a1821b36053142474e434762e40c2d665f3461b5f288402f0f2a` | **新增 29 条** |
| `backend/tests/test_identity_bounds_and_stock.py` | `61fb767e3d87e950a7033aa50e4c8842a21c2e5ff6a252748087778a1da324dd` | 改 1 条与新口径冲突的旧断言 |
| `backend/tests/test_query_budget.py` | `fe6c7ef2d579405545b6724c193a6ba2bf9339d587dff573e3094e2541546ecb` | 参考实现改为独立精确公式 |
| `MASTER_SPEC.md` | `1e66d15cd1b6c1a9d0c5aff83b80488e7871f20f1d6b0710cbedba40b8d87867` | 3B 文档同步 |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、台账、`REVIEW.md`、`/admin`、S10。

## 4. 数据库身份与保护

机器可读版本：`data/db_protection.json`。

| 库 | 路径 | 基线 SHA-256 | 收尾 SHA-256 | 是否变化 |
| --- | --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775…bd3a60b` | `775da775…bd3a60b` | 否 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da…6918c28` | `315eb3da…6918c28` | 否 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73e…706a579` | `b965e73e…706a579` | 否 |
| S03 隔离副本 | `backend/eatwhat_s03_r01_iso.db` | 由开发源库复制，初值 `b965e73e…706a579` | `6883112a…5b6168a` | 是（仅本副本） |

- 隔离副本 schema fingerprint 与开发源库一致。
- 隔离副本行数变化：`dishes_and_recipes` 100→102（探针自建 2 道下厨菜）；`fridge_inventory` 12→14（user1 原 3 条被清空后写入 4 条，user2 新增 1 条）；日志 9→9、房间/票 0→0、用户 4→4。
- pytest 隔离：未设置 `DATABASE_URL`；`conftest.py` 用 `sqlite://` + `StaticPool` 内存库并覆盖 `get_db`；`test_room.py` 的 `room_env` 夹具 monkeypatch `group_room.SessionLocal`。
- 真实 HTTP 只连 `127.0.0.1:8015` 的隔离副本；服务由探针脚本自行启动与停止。

## 5. 新旧时效口径对照

| 项目 | 旧实现 | 新实现（1A） |
| --- | --- | --- |
| 到期判定 | `round(expire_days - elapsed) <= 0` | `now >= created_at + expire_days×24h` |
| 剩余天数 | 四舍六入五成双的 `round` | 未过期 `ceil(剩余秒数/86400)`，最小 1 |
| 临期 | `remaining <= 2`（含过期） | 未过期且实际剩余 ≤48h |
| 时区 | 隐含 naive UTC，未显式归一化 | aware → UTC naive；DST 不影响绝对时刻 |
| 同名重录 | 保留旧 `created_at` | 重置为当前时间 |
| 组合采购 | 不看时效 | 与展示/推荐/清单同一 `is_expired` |

已知旧缺陷的实测（实现前）：`expire_days=3`、已过 2.5 天 → `remaining_days=0`、`is_expired=True`；已过 1.5 天 → `remaining_days=2`。红灯日志见 `logs/00_red_baseline.log`。

## 6. 环境

| 项 | 值 |
| --- | --- |
| OS | Windows 10.0.22631 x64 |
| Python | 3.13.9 |
| Node | v24.19.0 |
| npm | 11.17.0 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |

## 7. 未执行 / 不适用

- 前端无改动：未跑 `npm run build`、界面门禁或浏览器；`Fridge.vue` 原本已把 0 天渲染为“已到期”，临期计数由接口字段驱动，但本包不声称视觉验收。
- 多人 WS、S04 四算法、S05–S08、`/admin`、S10–S20、APK 不在本步，未验证也未触碰。
- 未在演示库 / S10 库 / 开发源库执行任何写探针；未清理或恢复用户数据。
