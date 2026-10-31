# R02 第三轮：指标口径与候选约束（R2-02）

## 1. 三种策略共同的口径

三个策略（`mixed_omega_0.5` / `average_omega_1.0` / `random`）**在同一批房间、
同一批成员、同一份合法候选上**评测；候选来自生产函数
`shortlist_candidates(db, members, mode_type, top_n=10)`，不做二次采样。

满意度按**全体四人**计算：

| 项 | 定义 |
|---|---|
| 单人 satisfaction | `min(100, 0.4*prior + 0.6*swipe)`，与生产同式；VETO 记 **0**；未表态（TIMEOUT）按 `TIMEOUT_SWIPE_SCORE = 60` |
| `avg_scores` | 四人 satisfaction 的算术平均，保留两位 |
| `least_misery_scores` | 四人 satisfaction 的最小值，保留两位 |

返工前错误：直接取生产报告里的 `mean_satisfaction / least_misery`，而生产共识把
VETO 成员的 0 分排除在 `satisfaction_values` 之外（它用 mask 把 group_score 置 0，
本不需要那个均值）。柱图问的是"这桌人吃得有多满意"，被否决者恰恰是最不满意的那位，
把他排除会同时抬高平均值、抬走最低值。

## 2. random 策略的候选约束（明确选择）

`random` 允许抽到**被否决的菜**，且**不排除否决成员的 0 分**——这是刻意的：
随机基线代表"完全不动脑、随手点一张"，它当然可能点到有人忌口的菜。若把它限制到
可行性集合，就等于偷偷替它做了 veto 过滤，柱图差异会被人为抹平。

两种设计不能混写。本轮采用「允许抽到否决菜 + 四人全算」，因此 random 的柱值会
明显低于 mixed/average——这正是要展示的差距。

## 3. 固定样本（可独立复算）

`fixed_samples.json` 五个场景的 `got` 与被测函数无关地由
`0.4*prior + 0.6*swipe` 逐人重算，见 `backend/tests/test_simulation_metrics.py`。
差异只在 0.01（生产把单人分存成两位小数）。

## 4. 主规模投票（R2-03）

主规模 `TIMEOUT_RATE = 0.0`：要求 1,000 房间 × 4 人 × 10 卡 = **40,000 张真实合法票**，
逐房校验 `len(votes) == 40` 且 `(user_id, dish_id)` 不重复，`rooms_full_votes` 必须 1000、
`bad_rooms` 为空。

缺席（超时）另列独立实验：`ABSENCE_RATE = 0.05`、200 房间，结果写
`docs/review/simulation/absence_seed<seed>.json`，只进存档 JSON 的 `params.absence`，
**不进 SSOT 四键**——大屏读的是四键，多塞字段就是契约漂移。
