# G2-R02 提交说明：S11 真实全量打标

- 日期：2026-10-29（Asia/Shanghai）
- 状态：开发方全量执行与自测完成，不签 Codex PASS。
- 模型：`gemini-3.7-flash`；接口：`https://api.buzzgw.com/v1`；提示词：`prompt_v1_appendix_c`。

## 结果

- 6,400 道 HOME_COOKING 菜谱全部 `SUCCESS`，无 PENDING/FAILED。
- 320 次有效 API 响应、320 个成功批次、6,400 个唯一菜品 ID；全部一次校验通过，无付费重试。
- 八维向量完整率 100%，异常 0；6,313 种不同向量，全 0.5 向量 0；50 条跨菜系分层抽样已保存。
- 实际 usage：输入 556,458 tokens、输出 1,746,027 tokens；按保守 Gemini-Ultra 单价估算 **$0.69649441**，低于授权的 $1。
- 首次试标曾因校验器 `name`/`dish_name` 缺陷崩溃一次，未写入菜品且该次 usage 未入账；修复后 6 条校验/预算回归通过。该次可能产生极少量额外费用，未伪称精确总扣款。

## 工程改动

- `llm_batch_tagger.py`：修复输出字段校验；新增真实 usage 预算熔断、输入/输出单价、累计费用；支持稳定主键取模的 4 路分片与 SQLite 30 秒写入等待。
- `test_llm_budget.py`：7 条预算、字段、分片回归全部通过。
- `bridge_s10_runtime.py`：新增显式 `--out`，允许明确命名的 G3 桥接库；G3 正式库由 `eatwhat_g2_s10_full.db` 作为唯一来源生成，闭合来源链。
- 扩容后查询：OUT/HOME 在 limit 5/10/24 下均恒为 6 条 SQL；库存查询 HOME=1、OUT=0；Top3 与旧实现一致。旧实现 HOME 库存查询 4,898 条。

## 证据

- 覆盖与抽样：`data/s11_verification.json`
- 费用与用量：同文件 `ledger` 段及 `s11_*_summary.json`
- 原始账本：`data/s11_ledger.jsonl`、`data/s11_shard[0-3].jsonl`
- 查询复验：`logs/42_query_budget_expanded.log`
- 数据保护：`logs/43_db_protection_post.log`，全部受保护库与 S09 manifest 未变
- G3 来源链：`../G3/data/bridge_provenance.json`

## 备注

后端全量曾取得 402 passed / 1 failed；失败为既有 Windows 符号链接环境用例 `test_refuses_symlink_alias`，与 S11 改动无关。S11 定向测试独立全部通过。
