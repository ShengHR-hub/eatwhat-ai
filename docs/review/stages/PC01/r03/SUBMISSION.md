# PC01 / r03 提交说明（R02 第三轮）

- 提交日期：2026-10-24（Asia/Shanghai）
- 对应审查项：**R2-01**（播种前快照守卫）、**R2-02**（柱图满意度口径）、**R2-03**（主规模满票 + 缺席实验）
- 上一轮：`docs/review/stages/PC01/r02/`（判定 FAIL），本包不覆盖 r01/r02。

## 一、改了什么

| # | 路径 | 改动 |
|---|---|---|
| 1 | `backend/algorithms/simulate_personas.py` | 删掉 `_satisfaction_of()`，改 `_four_member_metrics(report, dish_id)`：从生产报告的逐人 `satisfaction` 取值，**VETO 的 0 分照算**，`min(100, ·)` 展示封顶。mixed / average / random 三处统一用它。<br>`TIMEOUT_RATE = 0.0`（主规模必须满票），新增 `ABSENCE_RATE = 0.05` 与 `run_absence_experiment()`（200 房，独立库/独立明细）。<br>`_run_group_phase` 逐房校验 40 张票不重不漏，输出 `rooms_full_votes` / `bad_rooms`。 |
| 2 | `backend/scripts/init_seed_data.py` | 删除模块级 `BENCHMARK_JSON = _benchmark_snapshot()`（原来导入即读盘）；新增 `BenchmarkSnapshotError`、`validate_benchmark`、`load_benchmark`、`_db_benchmark_generated_at`、`ensure_benchmark_ready`；`seed_all(..., benchmark=...)`；`main()` 新增 `--benchmark-from`、`--allow-stale-benchmark`，并且**先守卫、再清库、后播种**。 |
| 3 | `backend/scripts/benchmark_snapshot.json` | 用本轮仿真结果刷新（四键，1140 字节），不含 `params`。 |
| 4 | `backend/tests/test_seed_guard.py`（新） | 四类反例：陈旧快照 + 较新库、缺快照、刷新失败（新快照点数不足）、连续刷新幂等。 |
| 5 | `backend/tests/test_simulation_metrics.py`（新） | 五类固定样本：无否决 / 单人否决 / 多人否决 / 全否决 / 缺席。期望值由测试自己按 `0.4*prior + 0.6*swipe` 重算，不复用被测函数。 |

## 二、口径（对应 R2-02）

- 三人策略共用同一批房间、同一批成员、同一批生产候选（`shortlist_candidates(..., top_n=10)`）。
- 满意度：`min(100, 0.4*prior + 0.6*swipe)`；VETO 记 **0**；未表态按 `TIMEOUT_SWIPE_SCORE = 60`。
- `avg_scores` = 四人算术平均；`least_misery_scores` = 四人最小值。**0 分不得排除。**
- `random` 策略**允许抽到被否决的菜，且不排除否决成员的 0 分**——随机基线代表"随手点一张"，若替它做 veto 过滤就等于人为抹平差异。两种设计不混写，本包只采用这一种。
- 详见 `data/method_notes.md`。

## 三、验收逐项

| 项 | 要求 | 证据 |
|---|---|---|
| R2-02 指标口径 | 否决成员 0 分计入平均与最低 | `data/fixed_samples.json`（5 场景，got 与独立期望逐项一致）＋ `logs/07_r2_01_r2_02_tests.log`（9 passed） |
| R2-02 重生成 | 原始数据 / 柱图 / 快照 / 隔离库全部重跑，禁止手改 | `logs/01_simulate_seed20261024.log`、`data/benchmark_seed20261024.json`、`data/detail_seed20261024.jsonl`、`data/rooms_seed20261024.jsonl` |
| R2-01 守卫位置 | 清库**前**刷新 + 校验 | `backend/scripts/init_seed_data.py` 的 `main()`；`logs/06_stale_snapshot_blocked.log`（真实库：exit 1，4 个用户未被动） |
| R2-01 四类反例 | 陈旧快照+较新库 / 缺快照 / 刷新失败 / 连续执行 | `backend/tests/test_seed_guard.py` 4 条 + `logs/07_r2_01_r2_02_tests.log` |
| R2-03 满票 | 40,000 张真实合法票、逐房 40 张不重不漏 | `logs/04_db_benchmark_check.log`：`votes: 40000`、`votes_per_room min/max: (40, 40)`、`rooms_full_votes` 见 `01` 日志 |
| R2-03 缺席另列 | 不混进主规模 | `data/absence_seed20261024.json`（200 房 / 8,000 计划 / 7,614 实投），只进存档 `params.absence` |
| 库内一致 | 大屏数据与存档逐点一致、四键 | `logs/04_db_benchmark_check.log`：`db_benchmark_keys` 四键、`db_curve_matches_archive: True` |
| 不污染演示库 | 仿真不写 `backend/eatwhat.db` 的房间/票 | 同上：`demo_db_group_rooms: 0` |

## 四、本轮数字

```
ours_lambda_0.5 d14 = 0.0091      baseline_no_decay d14 = 0.2927
avg_scores  = [92.0, 92.05, 71.39]      (mixed / average / random)
least_misery= [75.37, 74.77, 38.82]
votes = 40000 / planned 40000, rooms_full_votes = 1000 / 1000, bad_rooms = []
absence(200 房, 5%) avg [92.38, 92.45, 69.71] / least [77.49, 76.85, 36.31]
calls = {recommend_single: 48000, shortlist_candidates: 1200, member_prior_scores: 1200, compute_group_consensus: 2400}
```

> 与审查报告推算的 73.43 / 40.37 不同，原因是**同时执行了 R2-03**：主规模不再丢弃 5% 缺席票，
> 而 rank 票型是"横向排序"——全员都投票后，末两名拿到 VETO 的机会变多（本轮 VETO 4,093 张，
> 上轮 3,820），整体满意度随之下移。审查报告的推算基于"其余输入不变"，属预期差异，不是口径回退。
> 固定样本（`data/fixed_samples.json`）可独立验证 0 分确实进入了平均数与最低值。

## 五、已知限制

1. 人设、票型仍是合成行为假设，论文须写明模型/噪声/超时参数，S13 补敏感性分析。
2. `rank` 票型只用"同一房间内 10 张卡的相对排序"，不代表真人绝对偏好强度。
3. 基线组是「保持其余输入一致的无历史衰减基线」，**不是**产品意义上的全新用户。
4. 单次全量约 12 分钟（48,000 次 `recommend_single`）。
