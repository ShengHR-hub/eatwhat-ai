# S04 / r01 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S04 四算法与决策红线（F01 / F02 / N04）
轮次：r01
前置：[S03/r01 独立复审 PASS](../../../clearance-codex-s03-r01/REPORT.md)，受审 manifest 147 项、fingerprint `cd3d7c233fb347913a22e1bf6f67d84b185b40837f903931c2f643a15ec8c8fe`

## 1. 本轮目标

- F01：忌口、菜品黑榜、门店黑榜在单人推荐与群组初筛中同口径；海鲜别名覆盖主辅料；鱼香肉丝/豆腐/党参不误判。
- F02：全部候选被 VETO 时无赢家、可解释；部分 VETO 只能从存活集选；VETO 不能靠零分/平分复活。
- N04：按用户 2026-10-26 裁决 **D-S04-01 方案 A**，`feature_vector IS NULL` 的菜品不进入单人候选、群组初筛、先验与结算；不回退 0.5；API/前端不变。
- S04-C1～C5：独立期望值覆盖公式、边界、全否决和套餐约束。

## 2. 源码与工作树

- 分支：`master`；HEAD 不存在（仓库无 commit）；commit 数 0。
- manifest 生成时状态：staged 280 / unstaged 140 / untracked 68（`git status --porcelain`）。
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（本步未动 index）。
- 契约：`MASTER_SPEC.md` v2.3.5（含 2026-10-26 S03 冰箱时效补充裁定）；本步未改 SSOT。
- 工作树包含 S03 及更早的未提交改动；本步的 S04 增量见 §3。manifest 固定的是整个受审工作树，不是只含 S04 diff。
- `SOURCE_MANIFEST.json`：150 项，fingerprint `61c163e74d8a1cef08ab3a35e2778459b28afb62d67f501db04f4e4d185ad6df`（最终包只改证据文档，不改源码时 fingerprint 不变）。

## 3. 受审改动文件

| 文件 | SHA-256 | 性质 |
| --- | --- | --- |
| `backend/algorithms/veto_rules.py` | `fb8fb27674821d30f862b7d658e90c845fb09cffcab9ccaa4c52d8f249df8621` | F01：补「鱼」精确别名、去掉「参」词尾误判、补「刺参」；`_search` 统一 `find_hit/explain` |
| `backend/algorithms/single_recommender.py` | `a8d81069caf92dc38eb650e279a68d9d0320aaebe51fb9d1903db7a2d6f68e0f` | N04：候选组装跳过 NULL 向量 |
| `backend/algorithms/group_recommender.py` | `4825b015f4a0845ca4e9b4cc8b4954b743defc2967e0596d63c4693cad343a4c` | N04：初筛/先验/结算跳过 NULL；删除 VETO 死分值读取 |
| `backend/algorithms/combo_optimizer.py` | `941e3aa68ee68278d13211ff0b1f14740f497d9f96b59b32d718e1e6620480cc` | 仅按 SSOT 改「Top-20 角色分组枚举 + 约束筛选」措辞；枚举/剪枝逻辑未改 |
| `backend/tests/test_s04_algorithms.py` | `b28a1fe73ff1f3350ea452a88b6eb56468792ec98925401d2fd16ae40a15ba9e` | **新增 25 条** S04 独立期望测试 |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、`docs/review/STAGE_STATUS.md`、任何 `REVIEW.md`、`/admin`、S05–S20。

## 4. 数据库身份与保护

机器可读版本：`data/db_protection.json`；真实 HTTP 前后状态：`data/live_api_probe.json`。

| 库 | 路径 | 基线/收尾 SHA-256 | 是否变化 |
| --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | 否 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | 否 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | 否 |
| S04 隔离副本 | `backend/eatwhat_s04_r01_iso.db` | 由开发源库复制；含 11 道受控菜 + 1 个受控用户 | 是（仅本副本） |

隔离副本身份：

- schema fingerprint 与开发源库一致（`data/db_protection.json` 的 `schema_matches_source=true`）。
- 行数：users 5（源 4，+1 受控）、user_preferences 5（+1）、restaurants 20（不变）、dishes_and_recipes 111（源 100，+10 受控 +1 NULL）、fridge_inventory 12、eating_logs 9、group_rooms 0、room_votes 0、algo_configs 1。
- `feature_vector IS NULL` 计数：源库 0，隔离库 1（N04 受控样本）。
- `deleted_at` 非空：dishes 0、restaurants 0。

pytest 隔离：未设置 `DATABASE_URL`；`conftest.py` 使用 `sqlite://` + `StaticPool` 内存库并覆盖 `get_db`。真实 HTTP 只连 `127.0.0.1:8016` 的隔离副本；服务由探针脚本自行启动/停止。

## 5. 新旧行为对照

| 场景 | S04 前 | S04 后 |
| --- | --- | --- |
| 忌口「海鲜」+ 食材「鱼」 | 漏判（不排除） | 排除（单字精确别名） |
| 忌口「海鲜」+ 食材「党参」 | 误判（词尾「参」） | 保留 |
| 忌口「海鲜」+ 食材「草鱼」 | 排除（词尾） | 排除（不变） |
| `explain(["草鱼"], ["海鲜"])` | 与 `hits` 不一致（返回未命中） | 与 `hits` 同源（返回命中） |
| `feature_vector=NULL` 菜品 | `normalize_vector(None)` 补 0.5 后参与推荐 | 单人/群组候选、先验、结算均排除；不回退 |
| 全部候选 NULL | 仍以 0.5 分参与排序 | 单人 `recommendations=[]`、群组无赢家/无共识；不反向补菜 |
| `compute_group_consensus` 的 VETO 分支 | 读取 `VOTE_SCORES["VETO"]` 的死变量 | 不读取任何 VETO 分值，仅掩码 |

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

- 前端无改动：未跑 `npm run build`、界面门禁或浏览器；本包不声称视觉验收。
- 真实房间 WebSocket 广播、断线恢复、真实划卡与前端揭晓留给 S06/S07；本步只验算法与隔离数据。
- `campus` 过滤（N02）、`deleted_at` 软删除（N03）、`/admin`、S10–S20、APK 不在本步，未验证也未触碰。
- 未在演示库 / S10 库 / 开发源库执行写探针；未清理或恢复用户数据。
