# SUBMISSION — PC01 / R02：真实仿真与 benchmark 数据替换

## 任务

lgo_configs.benchmark_json 由手写预置曲线改为 ackend/algorithms/simulate_personas.py 的真实仿真输出；
结构按 MASTER_SPEC.md 第 215–234 行锁定；参数与种子随存档 JSON 留存，可复跑。

## 验收条目逐项自测

| 条目 | 自测结果 | 证据 |
|---|---|---|
| 200 personas × 60 天 × 2 餐 = 24,000 条流水 | ✔ 脚本内断言 len(meals) == PERSONAS*DAYS*MEALS_PER_DAY | logs/simulate_seed20261024.log |
| 1,000 房间 × 4 人 × 10 卡 = 40,000 票 | ✔ 脚本内断言 | 同上 |
| duplication_rate_curve.days 固定 14 点、两曲线等长 | ✔ 14 / 14 | data/db_benchmark_check.txt |
| group_satisfaction_bars 三策略、分值 0~100 | ✔ strategies=[mixed,average,random]，两组各 3 个值 | 同上 |
| 结构只有 SSOT 四个键 | ✔ generated_at / sample / duplication_rate_curve / group_satisfaction_bars | 同上 |
| 换种子/换参数可复跑 | ✔ seed=7、λ=0.8、ω=0.6 产出不同曲线并入档 | logs/simulate_seed7.log、data/benchmark_seed7.json |
| 旧手写曲线全仓无残留 | ✔ 搜 xp1_duplication_curve|exp2_group_satisfaction|ebbinghaus_decay_rate|no_decay_rate|cooldown_filter_rate 无命中 | data/no_legacy_curves.txt |
| 库内与文件逐点一致 | ✔ reseed 后读库与 enchmark_snapshot.json 相等 | logs/reseed.log、data/benchmark_snapshot.json |

## 变更路径

- 新增 ackend/algorithms/simulate_personas.py（仿真 + 落库 + 存档）
- 新增 ackend/scripts/benchmark_snapshot.json（seed 20261024 的产出快照，供种子脚本读取）
- 修改 ackend/scripts/init_seed_data.py：删除手写 BENCHMARK_JSON，改 _benchmark_snapshot() 读快照文件（补 import json）
- 修改 ackend/tests/test_api.py：benchmark 断言改为锁定四键结构、长度、取值范围、sample 关键字段
- 新增 ackend/algorithms/time_decay.py 的复用关系不变（仿真与线上同一衰减公式，避免"仿真一套、线上另一套"）

## 接口 / 迁移变化

- 无数据库迁移：lgo_configs.benchmark_json 已是 JSON 列，只换内容。
- 无接口签名变化；GET /api/v1/admin/... 尚未开工，本轮不涉及大屏。

## 已知限制

- **大屏逐点核验留到 S17**：本轮只证明"脚本 → 输出 → 隔离库"三者一致，不声称 /admin 大屏已正确显示（台账同款要求）。
- 仿真为**行为模型**而非真人实验：人格、触发概率、投票分布均为参数化假设，论文中必须表述为「仿真实验」并给出参数表。
- 重样率口径为「与上一餐同菜系」；换成「当日是否出现过同菜系」会得到近乎恒定的高值（第一版即栽在这里，已写进账本 §17.1）。
- rowser/ 不适用：R02 无 UI 变化。

## 未做

- PC02/R01、PC03/F12 的代码已完成并自测（证据在 docs/review/clearance/），**但按台账只开放 PC01，未提交为本轮验收范围**，等待 PC01 放行后再各自按轮次提交。
