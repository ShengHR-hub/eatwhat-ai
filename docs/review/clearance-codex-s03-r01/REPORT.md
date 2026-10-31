# S03 / r01 独立复审报告

审查时间：2026-10-26（Asia/Shanghai）  
审查方：Codex  受审包：`docs/review/stages/S03/r01/`  
受审 manifest：147 项，fingerprint `cd3d7c233fb347913a22e1bf6f67d84b185b40837f903931c2f643a15ec8c8fe`

## 最终结论

**S03/r01：PASS。** 到期语义、统一消费、同名重录、采购清单和跨用户隔离均符合用户裁决与 SSOT；专项和后端全量测试独立复跑通过。允许进入 S04。

## 验收结果

| 条目 | 独立核验与实际结果 | 判定 |
| --- | --- | --- |
| 受审版本 | 147 项 manifest 全部存在；逐项 SHA-256、字节数匹配；无重复路径。按包内生成算法重算 fingerprint 一致 | PASS |
| 到期边界 | 源码以 UTC-naive 数据为存储口径，aware 时间归一到 UTC；到期时刻为 `created_at + expire_days × 24h`；`now >= expires_at` 过期；未过期 `ceil`、过期 0 天 | PASS |
| 临期边界 | `0 < seconds_left <= 48h`；过期不临期；独立测试覆盖 48h、48h+1s、到期前 1s、恰好到期、到期后及区间扫掠 | PASS |
| 夏令时/时区 | 固定时钟测试对照 UTC、Asia/Shanghai 与 DST 偏移表达；相同绝对时刻得到一致结果 | PASS |
| 列表/推荐/采购 | `fridge_clock` 是唯一口径；过期项仍可见/删除但不计临期；下厨状态只用有效库存，临期双倍；API 与组合采购均不以过期库存抵扣 | PASS |
| 同名 ADD | 已有记录覆盖属性并重置 `created_at`；测试覆盖重新入库。历史重复行保留，任一有效匹配即可视为已有；重复库存不会重复提高单个主料权重 | PASS |
| 采购闭环 | 主辅料合并去重，重复 dish ID/菜名不重复 `used_by`，有效库存扣减、过期库存仍需购买、多余库存不进入结果；`quantity_desc` 按 SSOT 保持描述性文本 | PASS |
| 跨用户隔离 | 读/写/删跨用户返回 403；推荐和购物清单按请求头身份，伪造 body `user_id` 无法消费他人库存，快照不变 | PASS |
| 外食不读冰箱 | 独立测试监听 SQL，确认没有 `fridge_inventory` 查询；有无库存的外食推荐结果相同 | PASS |
| 专项回归 | `python -m pytest tests/test_s03_fridge_lifecycle.py tests/test_identity_bounds_and_stock.py tests/test_query_budget.py tests/test_fridge.py tests/test_combo_optimizer.py -q -p no:cacheprovider --basetemp=...`：**63 passed** | PASS |
| 后端全量 | `python -m pytest -q -p no:cacheprovider --basetemp=...`：**335 passed, 1 skipped**，exit 0 | PASS |
| 数据保护 | 演示库 SHA `775da775…bd3a60b`、S10 库 `315eb3da…6918c28`、开发源库 `b965e73e…706a579` 与提交基线一致；独立复核未连接写入它们 | PASS |
| 隔离服务收尾 | 提交包记录 15 步 HTTP `{200,403}`、无 500；独立确认 8015 已关闭 | PASS |
| 前端/浏览器 | 本步仅后端与 SSOT 变化，前端目录未改；按任务范围无需浏览器验收 | N/A |

独立测试执行环境使用仓库内临时 `--basetemp`。默认 Windows pytest 临时根目录权限会导致临时路径创建错误；隔离目录下完整回归通过。唯一 skip 为既有 Windows 符号链接权限用例，本步未新增 skip。回归中 61 条 datetime.utcnow 弃用警告属于既有测试/房间代码，本步无新增运行时失败。

另建临时隔离库并启动 8016 实际 HTTP 服务进行补验：过期食材在列表中为 `0/非临期`，下厨推荐状态为 `0.0`，采购清单转为待买；跨用户读取返回 403；同名 ADD 后单行记录保留、剩余 3 天且属性更新。服务随后停止，临时库已删除。

## 范围与残留

- 未改业务源码、数据库、`/admin` 或 S10；未运行浏览器。
- S04 算法决策红线、S05–S08、多人实时交互、统计后台及 APK 不由本报告验收。
- 本报告登记台账后，`STAGE_STATUS.md` 的工作区哈希会变化；这是受审 manifest 已固定后执行放行登记的预期状态变化，其他 manifest 源文件未改。

## 放行

本轮 S03/r01 必需验收项通过，登记后状态为 `S03=PASS`、`S04=READY`。执行 AI 可在收到新的 S04 任务后开始下一步；不得把本报告扩展解释为其他步骤 PASS。
