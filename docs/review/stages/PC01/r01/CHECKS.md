# CHECKS — PC01 / R02

cwd 一律为仓库根 D:\EatWhat，Shell 为 PowerShell 7。2026-10-24（Asia/Shanghai）。

| # | 命令 | 开始 | 结束 | 退出码 | 日志 |
|---|---|---|---|---|---|
| 1 | python -m backend.algorithms.simulate_personas --seed 20261024 --lambda-val 0.5 --omega-val 0.5 | 16:20 | 16:21 | 0 | logs/simulate_seed20261024.log |
| 2 | python -m backend.algorithms.simulate_personas --seed 7 --lambda-val 0.8 --omega-val 0.6 | 16:21 | 16:21 | 0 | logs/simulate_seed7.log |
| 3 | python -m backend.scripts.init_seed_data --force | 16:21 | 16:21 | 0 | logs/reseed.log |
| 4 | python -m pytest -q | 16:22 | 16:22 | 0 | logs/pytest.log（128 passed） |
| 5 | 读库脚本：解析 lgo_configs.benchmark_json 并打印键/长度/末点 | 16:22 | 16:22 | 0 | data/db_benchmark_check.txt |
| 6 | Select-String 全仓搜旧手写键名 | 16:22 | 16:22 | 0（无命中） | data/no_legacy_curves.txt |

## 未执行

- 未跑前端构建：R02 不改前端（
pm run build 的状态记录在上一轮批次 ②③④ 的收口里，但**不作为本轮证据**）。
- 未做浏览器核验：见 SUBMISSION.md「已知限制」。
- 未跑 /admin 大屏：未开工，属 S17。

## 备注

- 第 1、2 条只在 --write 时写库；本轮第 1 条写库、第 2 条只入档，用于证明"换种子可复跑且不污染生产数据"。
- 日志为完整输出（含头部参数与尾部汇总），未截断。
## 关于 0 字节的日志

`data/no_legacy_curves.txt` 是 0 字节，因为排除 node_modules/ dist/ docs/spec_archive/ 后没有任何命中——「什么都没有」本身就是这条证据。复现：

    Select-String -Path backend\*.py,backend\**\*.py -Pattern "exp1_duplication_curve|exp2_group_satisfaction|ebbinghaus_decay_rate|no_decay_rate|cooldown_filter_rate"
