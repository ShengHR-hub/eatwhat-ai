# G1-R02 提交说明：Lottie 揭晓整改

- 日期：2026-10-29（Asia/Shanghai）
- 状态：**本轮开发自测完成，等待后续独立复审**。
- 本包只关闭 G1 的 Lottie 揭晓欠项，不签 Codex PASS，不修改 `STAGE_STATUS.md`，不覆盖 G2 原包。
- G1 原包发生一次数据库保护探针误写，原始字节未能恢复；该证据例外见 §5，不以新文件冒充原文件。
- G1 组级状态仍应视为 `CHANGES_REQUIRED`：真机扫码和断线后继续投票尚未闭合；G3 不放行。

## 1. 改动

| 文件 | 改动 |
| --- | --- |
| `frontend/src/views/mobile/Room.vue` | 揭晓内联 SVG 替换为 `LottieIcon name="reveal"`，单次播放；GSAP 时间线和 canvas-confetti 保持不变 |
| `scripts/make_reveal_lottie.py` | 圆点改为静态坐标 + 依次淡入透明度轨道，避免多段位置轨道把图层移到 `-999999` |
| `frontend/src/assets/lottie/reveal.json` | 重新生成，9 个圆点图层，60 帧 / 30fps，停播保持末帧 |
| `docs/LOTTIE_SOURCES.md` | 登记揭晓素材来源、生成方式、字节数和 SHA-256 |
| `docs/AGENT_MEMORY.md` §10.4 | 将历史占位结论更新为已闭环，并记录真实可见性验收口径 |
| `docs/review/consolidated/G1_R02/**` | 新一轮探针、日志、截图、结构化结果和源码清单 |

未改后端、算法、数据库 schema、`/admin` 或其他动效库。

## 2. 根因与修复

旧素材并非简单地“缺少 SVG”：多段位置轨道使图层在 `lottie_light` 中进入 `-999999` 屏外变换，导致 `data-missing=false`、path 存在但视觉为空。仅调整结束关键帧不能解决。

最终版本取消位置轨道，只保留静态坐标与透明度动画。真实房间流程证明：9 条路径全部绘制，9 条路径矩形全部位于 112×112 的 Lottie 组件范围内，前后动画签名不同，最终截图可见中心点和外圈 8 点。

## 3. 验证摘要

- 真实建房→开局→揭晓：通过；Lottie 实际挂载并播放，原内联 SVG 已移除，confetti 保留。
- 前端生产构建：824 modules，exit 0。
- `home-fit` / `refill-fresh` / `sandbox-sync` / `check-colors`：全部 exit 0。
- 7 个受保护库 SHA 与 G1 基线一致；真实房间测试只写既有 G1 隔离库。
- 结构化结果：`validation.json`、`browser/lottie_reveal.json`；完整命令见 `CHECKS.md`。

## 4. 剩余阻塞

1. 真机相机扫码未执行。
2. 断线后在同一交互现场继续投票及结算幂等未证明。
3. S11 仍缺模型、Key、预算与最大调用量；G3 未获独立复审放行。

## 5. 证据封存例外（本轮新增）

本轮首次调用 `G1/data/probe_db_protection.py` 时，探针按自身设计将最新结果写回 `G1/data/db_protection.json`，覆盖了原封存文件。原 manifest 记录 SHA-256 为 `81239287e22757038cacd47e86fbca750e01339ef9fa07a2bd234b3bb1cdcf1f`，当前为 `fb991f17aa596a49a397279e701604cb0de40380856d26cbdf26059673fe38de`。

已尝试按已知内容和时间窗恢复原字节，但未成功，因此**不声称原证据已恢复**。当前旧文件保留为误写后的状态，后续复审需接受该证据例外或按现存原始数据库/日志独立复算。新探针已复制到 `G1_R02/data/`，输出与旧目录隔离；7 个受保护数据库本身始终未变，S09/r04 的 90 项 manifest 和 80 项 snapshot 也只读复核通过。
