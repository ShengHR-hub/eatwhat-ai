# S04 / r02 检查记录（CHECKS）

日期：2026-10-26（Asia/Shanghai）
所有命令在本机执行；cwd、起止时间与退出码逐条保留。日志在 `logs/`，数据在 `data/`。

## 1. 命令总表

| # | 命令 | cwd | 开始 – 结束 | 退出码 | 结果 | 日志 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `python -m pytest tests/test_s04_algorithms.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r02-red -k "specific_tag or category_tags"` | `D:/EatWhat/backend` | 23:23:49 – 23:23:52 | **1（预期红灯）** | 2 failed, 1 passed, 25 deselected；鲜虾误排鲈鱼/螃蟹/扇贝 | `logs/00_red_specific_tag.log` |
| 1 | `python -m pytest tests/test_s04_algorithms.py tests/test_veto_and_consensus.py tests/test_time_decay.py tests/test_single_recommender.py tests/test_group_recommender.py tests/test_combo_optimizer.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r02-f01` | `D:/EatWhat/backend` | 23:27:12 – 23:27:15 | **0** | **73 passed** | `logs/01_s04_target.log` |
| 2 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s04r02-full` | `D:/EatWhat/backend` | 23:27:19 – 23:27:43 | **0** | **363 passed, 1 skipped, 61 warnings** | `logs/10_backend_pytest_full.log` |
| 3 | `python docs/review/stages/S04/r02/data/live_api_probe.py` | `D:/EatWhat` | 23:29:59 – 23:30:03 | **0** | 3 次 API 均 200（类别正常 + 类别仅 NULL + 具体正常）；两路径集合一致；NULL 未返回；空候选 0 条；`passed=true` | `logs/21_live_probe.log`、`logs/20_live_server.log`、`data/live_api_probe.json` |
| 4 | `python docs/review/stages/S04/r02/data/build_fixed_samples.py` | `D:/EatWhat` | 23:30:10 – 23:30:11 | **0** | 35/6/5/7 组样本 + 单人公式，`all_match=true` | `logs/23_fixed_samples.log`、`data/fixed_samples.json` |
| 5 | `python docs/review/stages/S04/r02/data/build_db_protection.py` | `D:/EatWhat` | 23:30:11 – 23:30:12 | **0** | 三受保护库不变；r02 隔离库 schema 与源库一致；NULL 计数 1 | `logs/22_db_protection.log`、`data/db_protection.json` |
| 6 | `python docs/review/stages/S04/r02/data/build_validation.py` | `D:/EatWhat` | 23:30:15 – 23:30:16 | **0** | `state=SUBMITTED_FOR_REVIEW`；C1–C5 self-test PASS | `logs/25_validation.log`、`validation.json` |
| 7 | `python docs/review/stages/S04/r02/data/build_manifest.py` | `D:/EatWhat` | 见 `logs/24_manifest.log` | **0** | 152 项，fingerprint `f23f227014d275dc51171305fa7f635268a6d7d4ba1150f37c754378ba306350` | `logs/24_manifest.log`、`SOURCE_MANIFEST.json` |

> 所有 pytest 使用仓库内独立 `--basetemp=D:/EatWhat/.pytest-tmp-s04r02-*`；这些目录是运行产物，不属于受审源码。
> 红灯日志是**修复前**的真实失败；同一批用例在修复后并入第 1 行 73 passed。

## 2. 红灯覆盖的具体缺口（修复前）

| # | 用例 | 修复前实际 | 期望 |
| --- | --- | --- | --- |
| 1 | `test_s04_specific_tag_does_not_expand_to_category` | `hits(["鲈鱼"], ["鲜虾"]) == True`；`鲜虾` 被反查成海鲜类别 | False |
| 2 | `test_s04_specific_tag_parity_single_and_shortlist` | `veto_tags=["鲜虾"]` 下单人只保留青菜，鲈鱼/螃蟹/扇贝被误杀 | 保留鲈鱼/螃蟹/扇贝，仅排鲜虾/虾仁 |

## 3. 定向覆盖（修复后）

- F01 具体标签：鲜虾/鲈鱼/牛肉三组正反例；五项类别各自展开；35 行固定矩阵；单人与群组 shortlist 一致。
- F01 隔离 HTTP：类别用户保留 3 道；具体用户保留 8 道、只排鲜虾与虾皮；两路径集合一致。
- F02：全 VETO、部分 VETO、无票、存活候选同分（52.8）；说明零分存活候选不可达。
- C3：6 组衰减、4 人 R、120/100/40、ω 0/0.5/1、四权重归一化、raw 排序与 display 封顶。
- C4：Top-20、预算、平均油腻度 0.65、无解、高分但油腻被拒、采购合并、`lazy_one_pot` 无速度门槛。
- N04：单人/初筛/先验/结算排除 NULL；仅 NULL 时单人空结果、初筛空列表、群组无共识。

## 4. 全量回归与警告

- 最终全量：**363 passed, 1 skipped, 61 warnings, exit 0**（20.29s）。
- r01 基线为 360 passed；本步新增 3 条具体标签/类别测试，360 + 3 = 363，条数吻合，未删旧用例。
- skip 为既有 Windows 符号链接权限用例；本步未新增 skip。
- warnings 为既有 `datetime.utcnow()` 弃用与 `requests/urllib3` 版本提示；无新增未处理异常。
- F02 只改测试名/断言文案与固定样本，不删断言、不放宽容差、不改排序逻辑。

## 5. 真实 HTTP 与隔离库

隔离副本：`backend/eatwhat_s04_r02_iso.db`，由 `backend/eatwhat_dev_pre00_r02.db`（`b965e73e…706a579`）复制；schema fingerprint 与源库一致。

| 项目 | 结果 |
| --- | --- |
| 类别用户（海鲜） | API/shortlist 均保留 3 道；排除 7 道海鲜类 |
| 具体用户（鲜虾） | API/shortlist 均保留 8 道；只排除鲜虾、虾皮；鲈鱼/螃蟹/扇贝保留 |
| NULL 样本 | 两用户 API/shortlist 均未返回；NULL 计数前后均 1 |
| 空候选 | API 200、`recommendations=[]`、`combo=null` |
| 数据库前后 | 8 张表行数与两个受控用户偏好完全一致；`db_state_unchanged=true` |
| 受保护库 | 演示库 / S10 库 / 开发源库 SHA-256 前后一致 |
| 服务端 | `127.0.0.1:8016` 已停止，无 LISTEN |

隔离库行数（探针后）：users 6、user_preferences 6、restaurants 20、dishes_and_recipes 111、fridge_inventory 12、eating_logs 9、group_rooms 0、room_votes 0、algo_configs 1；`feature_vector IS NULL` = 1。源库对应 4/4/20/100/12/9/0/0/1、NULL=0。

## 6. r01 保留情况（必须披露）

- r01 的 `SOURCE_MANIFEST.json`（fingerprint `61c163e7…ad6df`）、`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、Codex 的 `REVIEW.md` 与复审报告均未改动。
- r02 准备期间，r02 脚本的 `OUT` 曾误指向 r01，导致 r01 的 `data/{fixed_samples,live_api_probe,db_protection}.json`、`validation.json` 与 `logs/20_live_server.log` 被重写；随后用 **r01 自己的脚本**按 r01 路径重新生成：13 忌口 + 6 衰减 + 4 共识 + 7 套餐、类别用户保留 3/排除 7、NULL 排除，与 r01 提交语义一致；但 `generated_at`、隔离库 SHA 与部分日志时间已不同，**无法恢复逐字节原件**。
- r01 的 manifest 本身不覆盖包内 data/logs，因此该事件不影响 r01 manifest 的 150 项源码清单；但 r01 包内证据的字节身份已改变，特此记录，供 Codex 判断是否要求另立 r01 补证。

## 7. 未执行

- 前端无改动：未跑 `npm run build`、界面门禁、浏览器。
- 真实房间 WebSocket、断线恢复、真实划卡与前端揭晓留 S06/S07。
- `campus` 过滤、`deleted_at` 软删除、`/admin`、S10–S20、APK 不在本步。
