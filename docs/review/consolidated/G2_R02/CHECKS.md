# G2-R02 执行记录

1. Key 与模型只读验证：备用域名可用，gemini-3.7-flash 在账户模型列表中。
2. 20 道试标：首次发现校验器字段缺陷，修复后 20/20 成功。
3. 串行续跑：确认真实调用稳定，但估算全量需约 3 小时；停止时已成功部分保留，未重复收费。
4. 主键取模 4 路分片：互斥/完整性测试通过，四路均完成 74 批、1,480 道，failed=0。
5. 最终验收：`verify_s11.py` 的 9 项检查全部 true，见 `logs/41_s11_verification_final.log`。
6. 扩容查询：limit 5/10/24 均 6 SQL，Top3 与旧实现一致，见 `logs/42_query_budget_expanded.log`。
7. 数据保护：受保护库和 S09 均未变，见 `logs/43_db_protection_post.log`。
8. 正式 G3 来源桥接：`../G3/logs/10_bridge_s11_to_g3.log`。

详细命令与输出均保存在 `logs/`；原始 JSONL、汇总、抽检和保护文件均保存在 `data/`。
