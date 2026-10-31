# S04 / r03 检查记录（CHECKS）

日期：2026-10-26（Asia/Shanghai）
所有命令在本机执行；cwd、起止时间与退出码逐条保留。日志在 `logs/`，数据在 `data/`。

## 1. 命令总表

| # | 命令 | cwd | 开始 – 结束 | 退出码 | 结果 | 日志 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `python -m pytest tests/test_s04_algorithms.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r03-red -k "unknown_tag"` | `D:/EatWhat/backend` | 23:53:48 – 23:53:52 | **1（预期红灯）** | 2 failed, 28 deselected；核桃误命中核桃仁 | `logs/00_red_unknown_tag.log` |
| 1 | `python -m pytest tests/test_s04_algorithms.py tests/test_veto_and_consensus.py tests/test_time_decay.py tests/test_single_recommender.py tests/test_group_recommender.py tests/test_combo_optimizer.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r03-f01` | `D:/EatWhat/backend` | 23:56:53 – 23:56:58 | **0** | **75 passed** | `logs/01_s04_target.log` |
| 2 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r03-full` | `D:/EatWhat/backend` | 23:57:01 – 23:57:27 | **0** | **365 passed, 1 skipped, 61 warnings** | `logs/10_backend_pytest_full.log` |
| 3 | `python docs/review/stages/S04/r03/data/live_api_probe.py` | `D:/EatWhat` | 23:57:31 – 23:57:34 | **0** | 4 次 API 均 200；类别/具体/未知三用户 API/shortlist 集合一致；NULL 未返回；空候选 0 条 | `logs/21_live_probe.log`、`logs/20_live_server.log`、`data/live_api_probe.json` |
| 4 | `python docs/review/stages/S04/r03/data/build_fixed_samples.py` | `D:/EatWhat` | 23:57:37 – 23:57:38 | **0** | 42/6/5/7 组样本 + 单人公式，`all_match=true` | `logs/23_fixed_samples.log`、`data/fixed_samples.json` |
| 5 | `python docs/review/stages/S04/r03/data/build_db_protection.py` | `D:/EatWhat` | 23:57:39 – 23:57:39 | **0** | 三受保护库不变；r03 隔离库 schema 与源库一致；NULL 计数 1 | `logs/22_db_protection.log`、`data/db_protection.json` |
| 6 | `python docs/review/stages/S04/r03/data/build_validation.py` | `D:/EatWhat` | 23:57:43 – 23:57:43 | **0** | `state=SUBMITTED_FOR_REVIEW`；C1–C5 self-test PASS；r01 证据例外待用户接受 | `logs/25_validation.log`、`validation.json` |
| 7 | `python docs/review/stages/S04/r03/data/build_manifest.py` | `D:/EatWhat` | 见 `logs/24_manifest.log` | **0** | 154 项，fingerprint `9767c3c1af3b96052c80a2ce27b88b0c21159cca8eb93eaeb36f7cf1ca38da02` | `logs/24_manifest.log`、`SOURCE_MANIFEST.json` |

> 所有 pytest 使用仓库内独立 `--basetemp=D:/EatWhat/.pytest-tmp-s04r03-*`；这些目录是运行产物，不属于受审源码。
> 红灯日志是**修复前**的真实失败；同一批用例在修复后并入第 1 行 75 passed。

## 2. 红灯覆盖的具体缺口（修复前）

| # | 用例 | 修复前实际 | 期望 |
| --- | --- | --- | --- |
| 1 | `test_s04_unknown_tag_is_exact_only` | `hits(["核桃仁"], ["核桃"]) == True`；`hits(["秋葵炒蛋"], ["秋葵"]) == True` | False（未知只全等） |
| 2 | `test_s04_unknown_tag_parity_single_and_shortlist` | `veto_tags=["核桃"]` 下单人同时排掉核桃仁 | 只排精确核桃，保留核桃仁/鲜虾/青菜 |

## 3. 定向覆盖（修复后）

- 未知标签：`核桃`/`秋葵` 全等正例、前缀/后缀/子串负例；单人与群组 shortlist 一致；未知不扩到海鲜类别。
- 已登记标签保持：`海鲜` 整类、`鲜虾` 只排虾类、`鲈鱼` 不排草鱼/三文鱼、`牛肉` 不排羊肉/猪肉；五项类别各自展开。
- F02：全 VETO、部分 VETO、无票、存活候选同分（52.8）；零分存活候选不可达。
- C3/C4/N04：与 r02 相同的独立公式、组合约束与 NULL 排除用例全部保留。

## 4. 全量回归与警告

- 最终全量：**365 passed, 1 skipped, 61 warnings, exit 0**（21.13s）。
- r02 基线为 363 passed；本步新增 2 条未知标签测试，363 + 2 = 365，条数吻合，未删旧用例。
- skip 为既有 Windows 符号链接权限用例；本步未新增 skip。
- warnings 为既有 `datetime.utcnow()` 弃用与 `requests/urllib3` 版本提示；无新增未处理异常。
- 未删除或放宽旧断言；未知标签修复只改变未知 token 的匹配策略，已登记标签行为不变。

## 5. 真实 HTTP 与隔离库

隔离副本：`backend/eatwhat_s04_r03_iso.db`，由 `backend/eatwhat_dev_pre00_r02.db`（`b965e73e…706a579`）复制；schema fingerprint 与源库一致。

| 项目 | 结果 |
| --- | --- |
| 类别用户（海鲜） | API/shortlist 均保留 3、排除 7 |
| 具体用户（鲜虾） | API/shortlist 均保留 8、排除 2（鲜虾/虾皮）；鲈鱼/螃蟹/扇贝保留 |
| 未知用户（核桃） | API/shortlist 均保留 11、只排除精确核桃；核桃仁保留；未知不扩到海鲜 |
| NULL 样本 | 三用户 API/shortlist 均未返回；NULL 计数前后均 1 |
| 空候选 | API 200、`recommendations=[]`、`combo=null` |
| 数据库前后 | 8 张表行数与三个受控用户偏好完全一致；`db_state_unchanged=true` |
| 受保护库 | 演示库 / S10 库 / 开发源库 SHA-256 前后一致 |
| 服务端 | `127.0.0.1:8016` 已停止，无 LISTEN |

隔离库行数（探针后）：users 7、user_preferences 7、restaurants 20、dishes_and_recipes 113、fridge_inventory 12、eating_logs 9、group_rooms 0、room_votes 0、algo_configs 1；`feature_vector IS NULL` = 1。源库对应 4/4/20/100/12/9/0/0/1、NULL=0。

## 6. r01 重建件与 r02 保留

- r01 5 个受影响文件（data/fixed_samples、data/live_api_probe、data/db_protection、validation、logs/20）已固定当前 SHA-256，见 `data/r01_reconstructed_manifest.json`；状态 `RECONSTRUCTED_ORIGINAL_BYTES_UNRECOVERABLE`。
- r03 运行前后这 5 个哈希一致；r03 脚本只写 r03 路径与 `eatwhat_s04_r03_iso.db`，未再写 r01/r02。
- r01 `SOURCE_MANIFEST/SUBMISSION/BASELINE/CHECKS/REVIEW` 与 r02 包未改；r02 包 mtime 保持在审查前的时间。
- 最终 PASS 仍需用户接受该历史例外，或提供可验证的原始备份；不得把语义等价表述成字节原件恢复。

## 7. 未执行

- 前端无改动：未跑 `npm run build`、界面门禁、浏览器。
- 真实房间 WebSocket、断线恢复、真实划卡与前端揭晓留 S06/S07。
- `campus` 过滤、`deleted_at` 软删除、`/admin`、S10–S20、APK 不在本步。
