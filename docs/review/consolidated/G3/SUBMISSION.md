# G3 提交说明：全规模仿真与对照实验

- 状态：开发方执行与独立原始流水复算完成，不签 Codex PASS。
- 输入：`eatwhat_g3_bridge_iso.db`，由 S11 完成后的 `eatwhat_g2_s10_full.db` 显式桥接；桥接后源库 SHA 未变。
- 运行：8 个人设分片并行，只并行人设，不改变生产推荐/群组算法或规模。

## 规模

- 200 人 × 60 天 × 2 餐；`recommend_single=48,000`。
- ours/baseline 各 24,000 条 detail、24,000 条 eating log。
- 1,000 个四人房间，每房 10 候选、40 票；共 40,000 票，每房均恰好 40。
- 独立缺席实验 200 房：计划 8,000 票，实际 7,582 票。
- `shortlist=1,200`、`member_prior=1,200`、`consensus=2,400`；`errors=[]`。

## 实验结果（如实保留）

- 14 天重样率：ours 各天均 0；baseline 从 0.0775 到 0.1843。
- 独立从 detail JSONL 复算：ours 前 14 天 0/5,600 重样；baseline 1,032/5,600，曲线与汇总完全一致。
- 群组满意度（mixed/average/random）：95.36 / 95.46 / 73.84。
- Least Misery：77.07 / 76.72 / 40.34。

## 证据

- `data/parallel_benchmark_full.json`
- `data/parallel_full/` 原始分片库与 JSONL
- `data/g3_verification.json`：9 项复算检查全部 true
- `logs/31_independent_recompute_final.log`
- `data/bridge_provenance.json`：S11 full → G3 的来源、SHA、行数与只读边界
