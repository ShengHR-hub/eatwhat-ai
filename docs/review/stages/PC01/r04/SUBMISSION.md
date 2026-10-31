# PC01 / r04 提交说明（R02 第四轮）

- 提交日期：2026-10-24（Asia/Shanghai）
- 对应审查项：**R3-01**（播种守卫仍可放行非法/更旧数据）、**R3-03**（满意度指标口径未闭环），并更正 R02 证据身份说明。
- 上一轮：`docs/review/stages/PC01/r03/`（判定 FAIL），本包不覆盖 r01/r02/r03。
- 后端改动已按 AGENTS.md 先报备：`init_seed_data.py` 的守卫/CLI、`simulate_personas.py` 的柱图指标与 `--data-dir`。

## 一、改了什么

| # | 路径 | 改动 |
|---|---|---|
| 1 | `backend/scripts/init_seed_data.py` | `generated_at` 用 `datetime.fromisoformat` 真正解析；无时区按本地时区解释，带偏移/`Z` 归一到 UTC 后比较。`sample` 五字段正整数（bool 拒绝）、`curve.days` 必须 `1..14` 连续、两条曲线 14 个有限值且 `0~1`、策略身份/长度、柱值 `0~100`；JSON `NaN/Infinity/重复键` 拒绝。incoming 与当前快照、库内时间的**全部检查通过后才写目标快照**；`--benchmark-from` 接受完整仿真输出（四键 + params），落盘只存四键；新增 `--snapshot` 供隔离复验。`--allow-stale-benchmark` 只跳过库内新旧比较，不跳过结构与时间校验。 |
| 2 | `backend/algorithms/simulate_personas.py` | `_four_member_metrics` 恢复 r02 口径：**个体 R 用原始值（不逐人封顶）**，VETO 的 0 分与缺席 TIMEOUT 分进入四人分母；柱图作为展示统计，四人聚合后统一 `min(100, ·)`。新增 `--data-dir`，隔离库/明细/缺席文件写到指定目录，避免覆盖历史证据。 |
| 3 | `backend/tests/test_seed_guard.py` | 23 条：旧快照、缺快照、刷新失败、连续执行、非法/缺失库内时间、跨时区旧时间、非法 sample/curve/策略/柱值、bool 冒充整数、NaN、incoming 拒绝不覆盖、`allow_stale` 只跳过库内比较、完整输出带 params 导入。 |
| 4 | `backend/tests/test_simulation_metrics.py` | 五类成员样本 + 两条 R>100 固定样本，锁定“原始 R、聚合后封顶”。 |
| 5 | `backend/scripts/benchmark_snapshot.json` | 用 r04 默认 seed 的全量输出刷新（四键）。 |
| 6 | `docs/AGENT_MEMORY.md` | 更正 §19.3/19.4/19.5 的错误口径说明；补 §19.6 的 `--data-dir` 纪律。 |

## 二、R3-01 逐项对照

真实 CLI 探针只重定向数据库/快照路径，不替换守卫/清库/播种函数；完整结果在
`data/seed-results.json`，日志在 `logs/04_seed_probe.log`。每个拒绝用例都记录运行前后
数据库逻辑摘要与快照 SHA。

| 反例/正例 | 实际退出 | DB 未变 | 快照未变 | 结果 |
|---|---:|---|---|---|
| `generated_at="zz-not-a-date"` | 1 | 是 | 是 | 解析失败，清库前中止 |
| DB `16:00+00:00` vs 快照 `23:00+08:00`（实际更旧 1h） | 1 | 是 | 是 | 归一化后拒绝 |
| personas=0、rooms=-1、days=`[14]*14`、ours=非数值 | 1 | 是 | 是 | 类型/规模/日序/范围校验失败 |
| 普通旧快照 + 较新库（无 incoming） | 1 | 是 | 是 | 拒绝 |
| 缺快照 | 1 | 是 | — | 缺文件中止 |
| 目标 00:00 / incoming 12:00 / DB 20:00 | 1 | 是 | **是** | 拒绝且不先覆盖快照（r03 旧问题） |
| 完整仿真输出（四键 + params）导入 | 0 | 重播 | 刷新为四键 | params 被剥离 |
| 同一目标快照连续执行 | 0 | benchmark 不变 | 不变 | 不被自己判成旧快照 |
| `--allow-stale-benchmark` 刷新 | 0 | 重播 | 刷新 | 显式例外；结构非法仍会拒绝（单测覆盖） |

文档化导入流程（已写进 `--benchmark-from` 帮助）：

```bash
python -m backend.algorithms.simulate_personas --seed 20261024 --out <benchmark.json>
python -m backend.scripts.init_seed_data --force --benchmark-from <benchmark.json>
```

## 三、R3-03 逐项对照

### 3.1 锁定的定义

| 项 | 定义 |
|---|---|
| 个体 R | `0.4*prior + 0.6*swipe`，**原始值，不逐人封顶**；VETO=0；缺席按 TIMEOUT=60 换算 |
| 四人聚合 | 先算四人均值/最小值，再按展示口径统一 `min(100, ·)` |
| 三种策略 | 同一批房间/成员/生产候选；`random` 允许抽到被否决菜，且 0 分照常进入四人集合 |

r03 的“逐人先封顶再聚合”已撤销；它与聚合后封顶不可交换。固定样本
`[0, 67.58, 97.82, 107.70]`：当前实现 **68.28 / 0**；逐人封顶会得到 **66.35 / 0**。
R>100 的全员样本 `[107,108,109,110]` 得到 **100 / 100**，证明封顶发生在聚合之后。
五类常规样本里，`no_veto` 也从 r03 的 76.57 变为 79.45（该样本本身含 R>100 成员），
这是口径恢复的结果，不是票数据变化。证据：`data/fixed_samples.json`、`logs/03_metric_probe.log`。

### 3.2 同策略、同口径对照（默认 seed）

| 数据与统计定义 | random 平均 / 最低 | mixed 平均 / 最低 |
|---|---|---|
| r02 归档柱值（旧 bug：VETO 被排除） | 81.13 / 61.76 | 93.81 / 74.68 |
| r02 原票，VETO=0，聚合后封顶（r03 报告复算） | 73.43 / 40.37 | 93.81 / 74.68 |
| r03 满票，VETO=0，逐人封顶（已撤销） | 71.39 / 38.82 | 92.00 / 75.37 |
| **r04 满票，VETO=0，聚合后封顶（本轮）** | **72.83 / 38.82** | **94.23 / 75.37** |

- r04 的 random/mixed 与 r03 报告对“满票 + 聚合后封顶”的独立推算**逐点相同**。
- 同一口径下从 r02 原票到 r04 满票：random 略降、mixed 升高，不能写“两项都下移”。
  差异来自满票（R2-03）与 RNG 消费，不归因给指标定义。
- VETO 概率仍是 0.5；默认 4,093 张是**数量**，不是概率上升。seed7 为 4,034 张。
- 不再使用 r03 的“mixed 92.0 vs r02 random 73.43”跨策略比较。

### 3.3 全量重跑与柱值

两组完整仿真（默认 seed=20261024、λ=.5、ω=.5；第二组 seed=7、λ=.8、ω=.6）均：
200 人 ×60 天 ×2 餐 ×2 arms、1,000 主房 + 200 缺席房；`recommend_single=48,000`、
`shortlist_candidates=1,200`、`member_prior_scores=1,200`（外层）、
`compute_group_consensus=2,400`；主规模每房 40 张唯一合法票，`rooms_full_votes=1000`、`bad_rooms=[]`。

| seed | avg_scores（mixed/average/random） | least（mixed/average/random） | d14 ours/base |
|---|---|---|---|
| 20261024 | 94.23 / 94.49 / 72.83 | 75.37 / 74.77 / 38.82 | 0.0091 / 0.2927 |
| 7 | 93.94 / 94.06 / 72.57 | 73.62 / 73.02 / 38.46 | 0.0098 / 0.2746 |

`data/bars_recomputed.json` 用 r03 归档的 40,000 票 + 新 helper 独立复算，两 seed 与全量输出逐点一致。
曲线未受 R3-03 影响（改动只在群组柱图 helper），d14 与 r03 相同；本轮仍用全量重跑重新生成快照，
不是手工改柱图。

## 四、R02 证据身份更正

- `docs/review/simulation/sim_seed20261024_ours.db` 只有 **8,000 条日志 / 20 天**，是首轮 stdout
  缺失后补跑覆盖的**截断旧库**；`data/db_inventory.json` 已标为 `truncated/deprecated`，
  它**不是**本次 60 天 benchmark 的来源，也没有被覆盖或删除。
- 完整 60 天来源有两条独立证据：
  1. r03 归档 `PC01/r03/data/detail_seed20261024.jsonl` 48,000 行，SHA 与审查方独立生成文件一致；
  2. r04 新目录 `data/sim_seed20261024/` 两臂各 24,000 行/60 天，DB 行数、日数、SHA 在
     `data/db_inventory.json` 列清。
- 演示库 `backend/eatwhat.db` 重新播种后：4 用户 / 20 门店 / 100 菜 / 9 条演示日志 /
  `group_rooms=0` / `room_votes=0`；`algo_configs.benchmark_json` 与快照、存档四键逐点一致
  （`data/db_benchmark_check.json`、`logs/09_db_check.log`）。

## 五、回归

- `cd backend; python -m pytest -q` → **161 passed**（`logs/05_pytest.log`）。
- `cd frontend; npm run build` → exit 0（PC03/r04 `logs/20_build.log`）。
- `node scripts/check-colors.mjs` → 38 文件 exit 0（PC03/r04 `logs/20_check_colors_real.log`）。
- R01 共享推荐实现/时钟/fixture 本轮未改，维持 r02 PASS；本包不重新声称 R01 全量对照。

## 六、已知限制

1. 人设、票型仍是合成行为假设；论文须写明模型、噪声、超时与票型分布，S13 补敏感性分析。
2. 基线组是「保持其余输入一致的无历史衰减基线」，不是产品意义的全新用户。
3. 单次全量约 12–16 分钟（48,000 次 `recommend_single`）；本轮两 seed 实际耗时见日志。
4. 本轮未跑多人 WS、APK、`/admin`；S09 与批次 4 仍 LOCKED。

**不签 PASS**；等待 Codex 独立复审本包。
