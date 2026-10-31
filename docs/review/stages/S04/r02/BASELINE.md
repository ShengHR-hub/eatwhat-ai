# S04 / r02 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S04 四算法与决策红线（F01 / F02 / N04）
轮次：r02
前置：S03/r01 独立复审 PASS；S04/r01 由 Codex 判 **BLOCKED**（[r01 REVIEW](../r01/REVIEW.md)、[复审报告](../../../clearance-codex-s04-r01/REPORT.md)）；用户 2026-10-26 确认 **D-S04-02 方案 A**。

## 1. 本轮目标

- 关闭 S04-F01-SEM-01：`鲜虾` 这类具体食材标签不得扩成整个海鲜类别；只有五项类别标签（海鲜/海味/内脏/牛奶/辣）各自展开。
- 修正 S04-F02-EVIDENCE-01：把“零分同分”改称“存活候选同分稳定性”，固定样本补 `survivor_tie=52.8`，说明合法输入下零分存活候选不可达；排序逻辑不改。
- 保持 S04/r01 已通过的 F02 核心行为与 N04 NULL 排除实现。
- 保留 r01 原件，不覆盖、不删除。

## 2. 源码与工作树

- 分支：`master`；HEAD 不存在（仓库无 commit）；commit 数 0。
- manifest 生成时状态：staged 280 / unstaged 140 / untracked 70（`git status --porcelain`；r02 包为新增未跟踪目录）。
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（本步未动 index）。
- 契约：`MASTER_SPEC.md` v2.3.5；**未改 SSOT/AGENT_MEMORY**。D-S04-02 决策记录在包内 `data/decision_f01.json`。
- r01 包的功能性证据（manifest/SUBMISSION/BASELINE/CHECKS/REVIEW）原样保留；r01 manifest 对应的是被 BLOCKED 的旧版本，不再匹配当前源码；本包 manifest 固定 r02 版本。
- **披露**：r02 准备期间 r02 脚本 `OUT` 曾误指向 r01，r01 的 `data/*.json`、`validation.json` 与 `logs/20_live_server.log` 被重写；已用 r01 自己的脚本按 r01 路径重建，语义等价但时间/隔离库 SHA 不同，无法逐字节恢复。详见 `CHECKS.md` §6。
- r02 `SOURCE_MANIFEST.json`：152 项，fingerprint `f23f227014d275dc51171305fa7f635268a6d7d4ba1150f37c754378ba306350`。

## 3. 受审改动文件

| 文件 | SHA-256 | 性质 |
| --- | --- | --- |
| `backend/algorithms/veto_rules.py` | `2312fbc25c6b16a59f01b238ba4506026b0ae768071c647e0f1e319075ac44ad` | D-S04-02：`CATEGORY_TAGS` 五项类别、`SPECIFIC_SYNONYMS` 具体同义词组、`expand_tags` 不再反向扩类 |
| `backend/algorithms/single_recommender.py` | `a8d81069caf92dc38eb650e279a68d9d0320aaebe51fb9d1903db7a2d6f68e0f` | N04 候选跳过 NULL（r01 已通过，未改） |
| `backend/algorithms/group_recommender.py` | `4825b015f4a0845ca4e9b4cc8b4954b743defc2967e0596d63c4693cad343a4c` | N04 初筛/先验/结算跳过 NULL（r01 已通过，未改） |
| `backend/algorithms/combo_optimizer.py` | `941e3aa68ee68278d13211ff0b1f14740f497d9f96b59b32d718e1e6620480cc` | SSOT 措辞（r01 已提交，未改） |
| `backend/tests/test_s04_algorithms.py` | `a928ad9b0ce9ff61b23e386e32f96b9cb8d04b0f397ae746033d23041a235f99` | 新增具体标签/类别测试 3 条；F02 同分测试改名并断言 52.8；共 28 条 |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、`docs/review/STAGE_STATUS.md`、任何 `REVIEW.md`、`/admin`、S05–S20。

## 4. 数据库身份与保护

机器可读版本：`data/db_protection.json`；真实 HTTP 前后状态：`data/live_api_probe.json`。

| 库 | 路径 | 基线/收尾 SHA-256 | 是否变化 |
| --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | 否 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | 否 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | 否 |
| S04/r02 隔离副本 | `backend/eatwhat_s04_r02_iso.db` | 由开发源库复制；含 11 道受控菜 + 2 个受控用户 | 是（仅本副本） |

隔离副本身份：

- schema fingerprint 与开发源库一致（`schema_matches_source=true`）。
- 行数：users 6（源 4，+2 受控）、user_preferences 6（+2）、restaurants 20、dishes_and_recipes 111（源 100，+10 受控 +1 NULL）、fridge_inventory 12、eating_logs 9、group_rooms 0、room_votes 0、algo_configs 1。
- `feature_vector IS NULL`：源库 0，隔离库 1（N04 受控样本）。
- 两个受控用户：`s04_probe_user`（忌口 海鲜）、`s04_probe_specific_user`（忌口 鲜虾）。

pytest 隔离：未设置 `DATABASE_URL`；`conftest.py` 使用 `sqlite://` + `StaticPool` 内存库并覆盖 `get_db`。真实 HTTP 只连 `127.0.0.1:8016` 的 r02 隔离副本；服务由探针脚本自行启动/停止。

## 5. 新旧语义对照

| 场景 | r01（BLOCKED） | r02（D-S04-02 A） |
| --- | --- | --- |
| `veto_tags=["鲜虾"]` + 鲈鱼/螃蟹/扇贝 | 整个海鲜类别被排，鲈鱼/螃蟹/扇贝误杀 | 只排虾类；鲈鱼/螃蟹/扇贝保留 |
| `veto_tags=["鲈鱼"]` + 草鱼/三文鱼 | 别名反查成海鲜，全部误杀 | 只匹配鲈鱼；草鱼/三文鱼保留 |
| `veto_tags=["牛肉"]` + 羊肉/猪肉 | 牛肉是具体组，本来不跨类 | 保持：只排牛肉组，不排羊肉/猪肉 |
| `veto_tags=["海鲜"]` | 展开整类 | 保持：展开整类 |
| `veto_tags=["海味"/"内脏"/"牛奶"/"辣"]` | 各自展开 | 保持：各自展开，不跨类 |
| 未知文本 | 原样保留 | 保持：只做精确/包含匹配 |
| 存活候选同分测试名 | “零分同分”，实际 52.8 | 改名“存活候选同分稳定性”，固定样本 52.8 |
| NULL 向量 | 已排除（r01 PASS） | 保持排除 |

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
- 真实房间 WebSocket、断线恢复、真实划卡与前端揭晓留给 S06/S07。
- `campus` 过滤（N02）、`deleted_at` 软删除（N03）、`/admin`、S10–S20、APK 不在本步。
- 未在演示库 / S10 库 / 开发源库执行写探针；未清理或恢复用户数据。
