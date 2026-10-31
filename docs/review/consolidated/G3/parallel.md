# G3 并行仿真运行器：开发自测记录

日期：2026-10-29。本文只记录开发自测，不是独立审查结论。

## 实现范围

- `backend/scripts/simulate_g3_parallel.py` 使用 `ProcessPoolExecutor`；默认 200 人按 25 人/片分为 8 片，默认 8 workers。
- 每片 ours/baseline 各有独立 SQLite 与 detail JSONL；子进程通过 SQLite `mode=ro` 只读复制同一 source DB 目录。
- 分片种子为 `seed + zero_based_shard`，同一分片两臂使用相同人设与随机种子；`_seed_personas(..., start_index=1)` 支持跨片全局用户名编号。
- 每日曲线按分片人设数加权合并；各进程 CALLS 以原始计数累加。
- 主群组与 absence 分别在独立全量人设库运行；默认规模为 1000 房和 200 房，不进入单人分片。
- 输出保留原 benchmark JSON 顶层结构，`params` 新增 `parallel`、`shards`、`raw_counts`，`db_files` 列出全部隔离库。
- 不写 source DB、不写 `algo_configs`，未改 G4、frontend、G1/G2/G2_R02 或 `llm_batch_tagger.py`。

## 小规模真实冒烟

执行命令（8 人 × 1 天 × 2 餐，主群组 2 房，absence 2 房，2 片，2 workers）：

```bash
DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_g3_bridge_smoke.db" \
PYTHONIOENCODING=utf-8 py -3.13 -m backend.scripts.simulate_g3_parallel \
  --seed 20261029 --personas 8 --days 1 --rooms 2 --absence-rooms 2 \
  --shard-size 4 --workers 2 \
  --data-dir "d:/EatWhat/docs/review/consolidated/G3/data/parallel_smoke" \
  --out "d:/EatWhat/docs/review/consolidated/G3/data/parallel_benchmark_smoke.json"
```

实测结果：

- 2 个分片、2 个进程；`errors=[]`。
- `recommend_single=32`，即两臂各 `8 × 1 × 2 = 16` 次真实生产调用。
- 两臂 `eating_logs` 各 16、detail JSONL 各 16。
- 主群组：全量 8 人设、2 房、80 planned votes、80 实际合法投票。
- absence：独立全量 8 人设、2 房、80 planned votes、79 实际投票（缺席实验允许不投票）。
- 合计 `shortlist_candidates=4`、`member_prior_scores=4`、`compute_group_consensus=8`，包含主群组与 absence。
- 曲线来自上述真实分片结果加权：ours 第 1 天 0.0，baseline 第 1 天 0.0625；该 1 天结果不得外推为 14/60 天结论。

产物：

- `data/parallel_benchmark_smoke.json`
- `data/parallel_smoke/`（4 个分片 arm 库及 JSONL、独立 groups/absence 库及明细）
- `logs/parallel_smoke.log`

## 定向测试

```bash
PYTHONIOENCODING=utf-8 py -3.13 -m pytest -q \
  backend/tests/test_g3_parallel.py backend/tests/test_simulation_metrics.py
```

结果：`11 passed in 6.91s`。覆盖默认 8 分片、非整除分片、人设数加权、CALLS 累加、`start_index` 兼容与跨片编号、真实小样本两次运行确定性、数据库/JSONL/投票原始计数及源库计数不变。日志见 `logs/parallel_pytest.log`。

## 正式全量运行方法（本次未执行）

S11 尚未完成，本次没有运行正式全量。待 S11 完成并确认源库后，将 `S11_CONFIRMED.db` 替换为实际源库文件名，并使用新的证据目录：

```bash
DATABASE_URL="sqlite:///D:/EatWhat/backend/S11_CONFIRMED.db" \
PYTHONIOENCODING=utf-8 py -3.13 -m backend.scripts.simulate_g3_parallel \
  --seed 20261024 --personas 200 --days 60 --rooms 1000 --absence-rooms 200 \
  --shard-size 25 --workers 8 \
  --data-dir "d:/EatWhat/docs/review/consolidated/G3/data/parallel_full" \
  --out "d:/EatWhat/docs/review/consolidated/G3/data/parallel_benchmark_full.json"
```

正式运行后应据 `params.raw_counts` 和独立库复核，而不是只看 CLI exit 0：

- 8 个分片；`recommend_single=48000`；两臂 eating logs/detail 各 24000。
- 主群组独立库 200 人、1000 房、40000 planned/actual votes。
- absence 独立库 200 人、200 房；缺席票与 planned votes 分开报告。
- 主群组与 absence 合计 `shortlist_candidates=1200`、`member_prior_scores=1200`、`compute_group_consensus=2400`。
- `params.errors`、shortfall/empty/no-consensus/bad rooms 均需纳入后续独立审查。
