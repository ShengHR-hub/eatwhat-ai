# SUBMISSION —— PC01 / R02（防腻曲线改为真仿真）

- 步骤：PC01
- 轮次：r02（针对 `docs/review/clearance-codex-2026-10-24/REPORT.md` 的 CLR-01 / CLR-02 / CLR-03）
- 提交时间：2026-10-24（Asia/Shanghai）
- 状态：**REVIEW_PENDING**（开发方不自签 PASS）

## 一、这轮到底改了什么

| # | 文件 | 改动 | 为什么 |
|---|---|---|---|
| 1 | `backend/algorithms/simulate_personas.py` | 整体重写（692 行） | 第一版自写四维余弦 / 衰减 / 满意度，对生产算法的调用次数为 **0**（CLR-01），投票是纯随机、无票型无共识（CLR-02），三策略采样不同（CLR-03） |
| 2 | `backend/algorithms/single_recommender.py` | `recommend_single(..., now=None)` 新增形参并透传给 `compute_decay_weights` | 仿真要按"历史时刻"重放决策，生产调用不传等价 `utcnow`。**这是最小适配层，算法本身一行未改** |
| 3 | `backend/scripts/benchmark_snapshot.json` | 用新一轮四键结果覆盖（1141 B） | 播种读的是这个快照；不刷新就会把首轮作废曲线写回库（本轮真实踩过并被 `04_db_benchmark_check.log` 抓到） |
| 4 | `backend/tests/test_api.py` | benchmark 断言改为锁定**结构**（四键、14 点、两组等长、三策略、0–100、sample.personas==200） | 曲线数值会随种子变，锁结构才有回归价值 |

## 二、逐条验收自测

| # | 要求（来自返工指令 / REPORT） | 自测结果 | 证据 |
|---|---|---|---|
| 1 | 仿真必须复用生产推荐代码路径 | 生产函数调用 **51,000** 次：`recommend_single` 48,000、`shortlist_candidates` 1,000、`member_prior_scores` 1,000、`compute_group_consensus` 2,000 | `logs/01_simulate_seed20261024.log`、`data/benchmark_seed20261024.json` 的 `params.calls` |
| 2 | 调用计数 > 0 且能指出调用点 | `params.call_sites` 逐条记录调用位置（如 `single_agent:meal_pick`、`group:shortlist`、`group:consensus_mixed`） | 同上 |
| 3 | 真实生成 1000 场 × 4 人 × 10 卡投票 | `rooms 1000`、每房 `members 4` / `cards 10`（min=max）、`votes 37999`、`planned_votes 40000` | `data/db_benchmark_check.txt` |
| 4 | 投票落库可查 | 隔离库 `sim_seed20261024_groups.db`：`group_rooms 1000`、`room_votes 37999`；**演示库 `group_rooms` 仍为 0** | `logs/04_db_benchmark_check.log`、`data/_db_check.py` |
| 5 | 三策略同成员 / 同候选 / 同种子 | 同一房间同一 `member_user_ids`、同一 `candidate_dish_ids`、同一票矩阵；mixed 用 `ω=omega_val`、average 用 `ω=1.0`、random 用**独立随机流** `Random(seed+1)` 在同一候选里抽一张 | `simulate_personas.py` docstring「三策略冻结同一场景」 |
| 6 | 曲线重算并替换入库 | `ours_lambda_0.5` / `baseline_no_decay` 各 14 点已写库，与存档 JSON 逐点一致 | `logs/04_db_benchmark_check.log` |
| 7 | 换种子 / 换参数可复跑 | `--seed 7 --lambda-val 0.8`：`ours d14 0.0098` / `base d14 0.2746`，量级与主跑一致 | `logs/02_simulate_seed7_lambda0.8.log`、`data/benchmark_seed7.json` |
| 8 | 全仓搜不到旧手写曲线 | `exp1_duplication_curve` / `exp2_group_satisfaction` / `cooldown_filter_rate` / `ebbinghaus_decay_rate` / `no_decay_rate` 全部 0 命中 | `data/no_legacy_curves.txt` |

## 三、口径说明（复审最容易质疑的三处）

1. **基线组不是"另一套算法"**：基线 = 同一个 `recommend_single`、同一份数据，只把查询时钟推到 `eaten_at + 15 天`，
   使 14 天窗口内无历史 → `decay_weights` 全 1.0。这在产品语义上就是"新用户冷启动"，不是特例分支。
2. **满意度封顶到 100**：生产侧 `0.4*prior + 0.6*SUPER_LIKE(120)` 最大可到 112。仿真按 `total_score` 同一「展示封顶」口径
   取 `min(100, …)`，**没有改 SUPER_LIKE 权重**。
3. **投票用 rank-based 而不是绝对阈值**：第一版按 `prior/100 + gauss(0,0.12)` 打绝对分，88% 落在 LIKE 以上，
   三策略被天花板压成同一个数（`avg [99.93, 99.95, 96.6]`）。改为"先验扰动后在这 10 张里排序"：
   前 2 名 SUPER_LIKE、3–5 LIKE、6–8 PASS、9–10 各 50% 概率 VETO 否则 PASS。理由是真人面对 10 张卡必然横向比较。

## 四、已知限制

- 人设是**合成**的（200 个随机八维向量 + 预算），票型由先验驱动，属模型假设，不是真人行为测量；论文口径仍写"仿真实验"。
- `votes 37999 < planned 40000` 是 `TIMEOUT_RATE=0.05` 的主动弃权（结算按 `TIMEOUT` 60 分），不是丢票。
- 运行时长约 11 分钟（200 人 × 60 天 × 2 餐 + 1000 场），未做并行化，复跑需要耐心。
