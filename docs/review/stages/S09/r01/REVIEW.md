# S09 / r01 独立复审

审查时间：2026-10-24（Asia/Shanghai）  
审查方：Codex  
受审版本：`docs/review/stages/S09/r01/SOURCE_MANIFEST.json`；工作区无 Git HEAD
审查范围：S09 批次 4 契约、数据来源与指标定稿；未审查 S10 及后续实现。

## 验收结果

| 条目 | 独立检查方法 | 实际结果 | 判定 |
|---|---|---|---|
| 证据包结构与 JSON | 独立运行 `probes/validate_evidence.py` | 48 个证据文件可解析；基线文件、演示库 SHA 和业务文件均未变化 | PASS |
| 只读基线 | 独立运行 `probes/baseline_probe.py` | 20 门店、100 菜、800 特征值、`group_rooms=0`、`room_votes=0`；无 Key/Android 工具/LLM 配置 | PASS |
| 高德来源事实 | 复核 `amap_keyless_check.json`、官方事实证据 | 无 Key 时返回 `INVALID_USER_KEY`；分页、配额、GCJ-02 事实有记录 | PASS |
| 菜谱来源与许可证 | 复核来源评估与许可证日志 | HowToCook 仅 372 道可用；其他规模来源许可证或再分发边界未闭合 | BLOCKED |
| 规模和特征值口径 | 复核 `DATA_PLAN.md` 算术 | 6300×8=50400；若坚持 60000+，成功打标菜品需至少 7500 | BLOCKED |
| stats / 大屏契约 | 复核 13 接口矩阵和 17 图指标 | 12/13 冲突已识别，但 C08/C10/C11/C13/C17 等仍有待决口径；当前实现为 0 个 stats 路由符合 S09 范围 | BLOCKED |
| schema 与历史保护 | 复核 schema 缺口清单 | `allergen_tags`、来源追溯、软删除、打标状态和实验库边界尚未获用户决策 | BLOCKED |
| 实验协议 | 复核 `EXPERIMENT_PROTOCOL.md` | 主要协议已写明；D20、D21、D22 等仍需锁定后才能支撑 S12/S13 | BLOCKED |
| 回归保护 | 独立运行提交包验证脚本；核对提交日志 | S09 未改业务代码，演示库未写入；后端基线日志为 161 passed | PASS（仅基线） |

## 必须由用户裁决的最小集合

以下事项不能由开发方自行决定，必须回复选择并在 SSOT/决策记录中落盘：

1. 实际学校/校区或 GCJ-02 中心坐标；是否提供高德 Key。Key 不要粘贴到文档或聊天，配置到本地环境即可。
2. 菜谱来源：提供有明确许可证且可用于项目的中文数据集，或明确接受某个仅学术/不可再分发来源及其边界；否则降低规模或改为“合成数据并明确标注”。
3. 200 个食堂窗口采用实采还是合成；合成数据必须标注为模拟档口。
4. 特征值口径：坚持 60000+ 并将成功打标菜品目标提高到至少 7500，或改为 `8 × 实际成功打标数` 并同步论文/SSOT。
5. 是否保留 13 个 stats 接口并把 SSOT 的“12 个”改为 13，包含 `quality`。
6. 是否允许为 `allergen_tags`、软删除、来源追溯、打标状态/失败记录增加 schema 或独立表。
7. 仿真数据写入主库并加隔离标记，还是使用独立实验/统计库并让 stats 指向该库。
8. C08 热门菜品、C10 散点、C11 桑基守恒、C13 词云来源、C17 覆盖率的具体数据口径。

## 非当前阻塞项

Android SDK、`adb`、Gradle、Capacitor、真机、LLM Key/预算、95 张菜品图授权属于 S11/S18/后续交付条件，不应通过 S09 私自解决，也不能被写成当前已通过。

## 最终判定

结论：**BLOCKED**。

理由：S09 的文档和小样本证据已基本齐全，但影响数据真实性、规模披露、schema 契约、统计接口和后续实验可复现性的关键决策仍未完成，且尚未同步 `MASTER_SPEC.md`。按 `docs/REVIEW_RULES.md`，不能以“建议方案”代替用户裁决，不能进入 S10。

下一步：用户回复上述裁决后，开发方更新 SSOT、`DECISIONS.md`、`DATA_PLAN.md`、`CONTRACT_MATRIX.md`、`EXPERIMENT_PROTOCOL.md`，生成 S09/r02 新验收包；不得覆盖 r01。Codex 再独立复审，只有 S09 PASS 后才开放 S10。
