# S04 / r03 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S04 四算法与决策红线（F01 / F02 / N04）
轮次：r03
前置：S04/r02 由 Codex 判 **FAIL**（[r02 REVIEW](../r02/REVIEW.md)、[复审报告](../../../clearance-codex-s04-r02/REPORT.md)）；用户确认 D-S04-02 方案 A；r03 只整改 S04-F01-UNK-01 与证据口径，不改变用户语义。

## 1. 本轮目标

- 关闭 S04-F01-UNK-01：未知忌口文本必须规范化后全等，不能因候选食材包含该子串而命中（`核桃` 不得命中 `核桃仁`，`秋葵` 不得命中 `秋葵炒蛋`）。
- 修正 r02 `decision_f01.json` 中 `semantics.unknown` 的“精确/包含匹配”矛盾，改为只全等。
- 保持已登记的类别/具体标签、F02、N04 行为不变。
- 将 r01 受影响文件固定为重建件并冻结现状哈希；r03 不再写入 r01 或已提交的 r02。
- 不开始 S05；最终 PASS 仍需用户接受 S04-EVID-01 历史证据例外或提供原始备份。

## 2. 源码与工作树

- 分支：`master`；HEAD 不存在（仓库无 commit）；commit 数 0。
- manifest 生成时状态：staged 280 / unstaged 140 / untracked 72（`git status --porcelain`；r03 包为新增未跟踪目录）。
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`（本步未动 index）。
- 契约：`MASTER_SPEC.md` v2.3.5；**未改 SSOT/AGENT_MEMORY**。D-S04-02 修正后的决策记录在 `data/decision_f01.json`。
- r01/r02 包均保留；r03 脚本只写 `docs/review/stages/S04/r03/` 与 `backend/eatwhat_s04_r03_iso.db`。
- r03 `SOURCE_MANIFEST.json`：154 项，fingerprint `9767c3c1af3b96052c80a2ce27b88b0c21159cca8eb93eaeb36f7cf1ca38da02`。

## 3. 受审改动文件

| 文件 | SHA-256 | 性质 |
| --- | --- | --- |
| `backend/algorithms/veto_rules.py` | `5fd8993a01a19a7fd6c633e5c9972e1549a0aa74d8d9df497e41a4f7965f43ba` | S04-F01-UNK-01：`_expand` 拆出精确未知 token；`_search` 未知 token 全等；已知类别/同义词才做包含 |
| `backend/tests/test_s04_algorithms.py` | `864ca33b9bfbedd072642845cdfe22a3827f1834078c40c0c5120509a0e50302` | 新增未知标签全等/包含反例与单/群组 parity；共 30 条 |
| `backend/algorithms/single_recommender.py` | `a8d81069caf92dc38eb650e279a68d9d0320aaebe51fb9d1903db7a2d6f68e0f` | N04（r01 已通过，未改） |
| `backend/algorithms/group_recommender.py` | `4825b015f4a0845ca4e9b4cc8b4954b743defc2967e0596d63c4693cad343a4c` | N04（r01 已通过，未改） |
| `backend/algorithms/combo_optimizer.py` | `941e3aa68ee68278d13211ff0b1f14740f497d9f96b59b32d718e1e6620480cc` | SSOT 措辞（r01 已提交，未改） |

未改：`backend/models.py`、`backend/schemas.py`、数据库 schema/迁移、`frontend/**`、`docs/review/STAGE_STATUS.md`、任何 `REVIEW.md`、`/admin`、S05–S20。

## 4. 数据库身份与保护

机器可读版本：`data/db_protection.json`；真实 HTTP 前后状态：`data/live_api_probe.json`。

| 库 | 路径 | 基线/收尾 SHA-256 | 是否变化 |
| --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | 否 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | 否 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | 否 |
| S04/r03 隔离副本 | `backend/eatwhat_s04_r03_iso.db` | 由开发源库复制；含 12 道受控菜 + 3 个受控用户 + 1 道 NULL | 是（仅本副本） |

隔离副本身份：

- schema fingerprint 与开发源库一致（`schema_matches_source=true`）。
- 行数：users 7（源 4，+3 受控）、user_preferences 7（+3）、restaurants 20、dishes_and_recipes 113（源 100，+12 受控 +1 NULL）、fridge_inventory 12、eating_logs 9、group_rooms 0、room_votes 0、algo_configs 1。
- `feature_vector IS NULL`：源库 0，隔离库 1（N04 受控样本）。
- 三个受控用户：`s04_probe_user`（海鲜）、`s04_probe_specific_user`（鲜虾）、`s04_probe_unknown_user`（核桃）。

## 5. r01 重建件（S04-EVID-01）

r02 准备期间 `OUT` 路径误指 r01，导致 r01 的 `data/fixed_samples.json`、`data/live_api_probe.json`、`data/db_protection.json`、`validation.json`、`logs/20_live_server.log` 被重写；已用 r01 自己的脚本按 r01 路径重建。**原始字节不可恢复**。当前哈希固定在 [`data/r01_reconstructed_manifest.json`](data/r01_reconstructed_manifest.json)：

| 文件 | 当前 SHA-256 | 状态 |
| --- | --- | --- |
| `docs/review/stages/S04/r01/data/fixed_samples.json` | `1c3693f27397d3bd2020d1d865579e160df9e46d0a8ffdac4542a59d0ca0b799` | 重建件 |
| `docs/review/stages/S04/r01/data/live_api_probe.json` | `88bc2cecc3f2da3632a052b0dbb0614f5df6f36918f95a658689b5014cf153c8` | 重建件 |
| `docs/review/stages/S04/r01/data/db_protection.json` | `b18ea35f6c1a282c9a7ed7d2a949ca4767e8869eac97ccda6c857727649f3656` | 重建件 |
| `docs/review/stages/S04/r01/validation.json` | `8a378bf8187ed066a65b820eabf740b1c5bebde4aeaab39409ef323d55262e72` | 重建件 |
| `docs/review/stages/S04/r01/logs/20_live_server.log` | `5e6929d4a8fc2de4a5b0278a28b380b0aea60b6be517db0e7ca78e29b7ce7f4f` | 重建件 |

- r01 `SOURCE_MANIFEST.json`、`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、Codex `REVIEW.md` 与复审报告未改。
- r03 运行前后上述 5 个重建件哈希一致；r03 未写入 r01/r02。
- 最终 PASS 仍需用户明确接受该历史例外，或提供可验证的原始备份；r03 不把语义等价表述成字节原件。

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
