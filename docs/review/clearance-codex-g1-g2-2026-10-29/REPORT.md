# G1/G2 统一独立复审报告

- 复审日期：2026-10-29（Asia/Shanghai）
- 范围：G1（S07 + S08）、G2（BRIDGE-10 + S10 + S11）
- 依据：`docs/review/CONSOLIDATED_REMAINDER_PLAN.md`、`MASTER_SPEC.md`、`docs/REVIEW_RULES.md`、对应提交包及当前源码
- 复审原则：独立复跑命令、核对原始 JSON/日志/源码和隔离数据库；不把开发方自测直接视为 PASS
- 本轮未修改业务代码、受保护数据库、`STAGE_STATUS.md` 或既有证据包

## 1. 独立执行结果

| 检查 | 独立结果 |
| --- | --- |
| 后端全量 | `396 passed, 1 skipped`，exit 0 |
| 前端构建 | Vite `824 modules`，exit 0 |
| S10 官方校验 | `overall_ok=true`，`failed=[]`；SIYUAN 605、JIANDA_YANTA 6659、合成食堂各 200、菜谱 6400、演示库 SHA 未变 |
| G1 manifest | 131 项，0 missing，0 mismatch |
| G2 manifest | 103 项，0 missing，**1 mismatch** |
| G2 失配项 | `docs/review/consolidated/G2/logs/23_runtime_backend_after_fix.log`：manifest 记录 8716 bytes / SHA `53b4...cffe4`，当前 8745 bytes / SHA `bbf6...90d9` |
| 受保护库 | 提交包和独立 S10 校验均显示演示库、S10 原库、开发源库及历史隔离库未被写入 |

G2 manifest 的失配不是业务接口失败，但说明提交后证据包未保持封存，不能把当前 G2 包当作 0 失配的完整证据。

## 2. 逐项裁决

### S07 多人真实交互：`CHANGES_REQUIRED`

已独立核对双身份、四身份、真实 CDP 拖拽四票型、60px 阈值与回弹、超时/全否决、刷新/后台恢复、非成员/非房主/跨校区负例；浏览器 JSON 和截图与这些结果一致。

以下必需项仍未闭合：

1. **真机相机扫码没有执行**。证据只证明二维码载荷是局域网地址、局域网页面可达、第二个 Chrome 打开链接可进房。按 G1 计划，手输/点击链接不能替代手机相机扫码。
2. **Lottie 揭晓没有实现**。[`Room.vue`](/D:/EatWhat/frontend/src/views/mobile/Room.vue:760) 明确注释当前使用内联 SVG，`reveal.json` 在 `lottie-web light` 下不可见；实际揭晓使用 SVG + GSAP + confetti。MASTER_SPEC/动效分工要求揭晓动画使用 Lottie，因此该项不是“截图已见揭晓”可以覆盖的差异。
3. **断线后继续投票证据不完整**。现有证据证明代理重启后的 socket 重连和刷新恢复，但重连过程发生开发期整页重载，未证明断线后在同一交互现场继续投票且不会重复结算。

下一轮要求：在可操作真机上完成扫码并留原始操作/结果证据；替换为实际可见且由 `lottie-web` 播放的揭晓素材并做运行时可见性探针；在不依赖整页重载的断线场景完成一张新票的继续投票、服务端事件和结算幂等核验。三项都完成后重建 G1 manifest，保留本报告和旧包。

### S08 移动端总回归：`PASS`

独立核对了 390×844 与 390×667 一屏布局、元素不重叠、按钮命中、底部导航和返回路径、角色切换后的身份请求头、足迹/冰箱/房间入口、空态/422/500/离线恢复、颜色门禁、玻璃分级及天气/空态 Lottie。G2 校区修复后重新跑过 S08 回归，独立全量测试和构建也通过。

该 PASS 只覆盖 S08 约定的移动端总回归，不替代 S07 的真机扫码和揭晓 Lottie 验收。

### BRIDGE-10 运行时桥接：`PASS（功能范围）`

独立核对并复跑：外食单人请求缺 `campus` 返回 422；SIYUAN/JIANDA_YANTA 结果不跨校区且不包含 NULL 校区；群组跨校区 join 返回 409；下厨单人和群组共享菜谱；桥接库保留运行库用户/日志/库存；受保护库未变。

`/admin/stats/*` 和全局校区切换 UI 在当前 SSOT/提交说明中留给后续 S15/专项，不能作为本项功能失败，也不能在本轮宣称已完成。BRIDGE-10 的功能结论通过，但 G2 组级结论仍受 S11 和证据封存问题约束。

另有一项证据链改进要求：[`bridge_s10_runtime.py`](/D:/EatWhat/backend/scripts/bridge_s10_runtime.py:27) 默认从 `backend/eatwhat_batch4.db` 读取，而本轮新建的全量导入库是 `backend/eatwhat_g2_s10_full.db`。两库数量虽与验证结果一致，但提交包没有给出两者逐行内容等价证明。下一轮应显式以 G2 full DB 作为 `--source` 重建桥接，或提供可复核的逐字段/来源键等价证明。

### S10 基础数据导入：`PASS`

独立重新运行官方 `verify_s10_import.py` 到新的临时输出目录，结果 `overall_ok=true`、`failed=[]`。605/6659 真实 POI、各 200 条明确标记的合成食堂、6400 条唯一合成菜谱、3km/坐标/字段/抽样/完整性/幂等与演示库保护均通过。G2 full DB 的 `tagging_status=PENDING` 和空向量符合 S11 尚未打标的状态，不得把它计成已完成打标。

### S11 LLM 打标与查询扩容：`BLOCKED`

预检如实记录 `LLM_API_KEY` 缺失、模型未确认、预算未确认、`network_calls=0`；6400 道菜仅生成 320 批 dry-run 计划，成功覆盖率为 0。没有密钥、模型、预算和最大调用量的明确授权，不能发起付费调用，也不能把 dry-run 记为 PASS。

查询预算探针显示库存查询恒定为 1、总 SQL 恒定为 6、Top3 与旧实现一致；这些是 S11 的局部通过项，不能解除全量打标阻塞。

## 3. 组级结论与放行

| 组 | 结论 | 原因 |
| --- | --- | --- |
| G1 | `CHANGES_REQUIRED` | S08 已通过，但 S07 有真机扫码、Lottie 揭晓和断线继续投票未闭合 |
| G2 | `BLOCKED` | S10 与 BRIDGE-10 功能范围通过；S11 缺少外部前置，且 G2 manifest 有 1 项失配；桥接默认源还需补全链路证明 |

因此本轮**不签 G1/G2 组级 PASS，不放行 G3，不更新正式台账**。G1 需要先补齐三项交互/动效证据；G2 需要先恢复封存一致性、闭合桥接源链路，并在获得模型、密钥、预算和最大调用量后完成 S11。整改应新建后续轮次证据包，保留本报告及 G1/G2 原包，不覆盖历史文件。

## 4. 复审原始依据

- G1：`docs/review/consolidated/G1/SUBMISSION.md`、`CHECKS.md`、`validation.json`、`browser/`、`SOURCE_MANIFEST.json`
- G2：`docs/review/consolidated/G2/SUBMISSION.md`、`CHECKS.md`、`validation.json`、`data/full_verify/`、`data/bridge_api.json`、`data/s11_preflight.json`、`SOURCE_MANIFEST.json`
- 独立输出：后端 pytest 日志、前端 build 输出、临时目录 `.codex-g2-s10-verify-20261029-a/validation.json`（不属于提交包）
