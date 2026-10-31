# 审查与验收证据索引

**当前步骤与许可**见 [STAGE_STATUS.md](STAGE_STATUS.md)，独立审查规则见 [REVIEW_RULES.md](../REVIEW_RULES.md)，任务见根目录 [BATCH4_PLAN.md](../../BATCH4_PLAN.md)。只有 Codex 明确签发 PASS 后才能进行下一步。

> **2026-10-31 提醒**：台账的许可状态已落后于实际代码（S10–S20 对应功能多数已实现但未审查）。差距与逐项对照见 [STAGE_STATUS.md](STAGE_STATUS.md) 文末「2026-10-31 实际施工快照」。**该快照不构成 PASS**。

## 分步审查证据

- `stages/Sxx/rNN/`：每步每轮的提交、基线、日志、浏览器证据和 Codex 的 `REVIEW.md`；实际执行时按具体编号创建。**截至 2026-10-31，已有 PASS 的步骤为**：PC01/R02、PC02/R01、PC03/F12、S00、S01、S02、S03、S04、S05、S06、S09；S07/S08 为 READY，S10–S20 仍 LOCKED（明细见 [STAGE_STATUS.md](STAGE_STATUS.md)）。
- `audit-2026-10-24/REPORT.md`：首轮设计/代码审查，保留当时结论。
- `recheck-2026-10-24/REPORT.md`：导航故障修复与真实点击复查；结论不覆盖其后新增补丁。

不同轮次的截图工具、视口、数据版本可能不同，以各包记录为准。截图存在不能单独证明当前版本通过。

## 历史页面截图

下表历史素材主要由 **headless Chrome + CDP**（`scripts/shot.mjs`）采集；`recheck-2026-10-24/` 使用真实浏览器操作工具。按页面分子目录，文件名中的数字是当轮实测值，不是统一设计值。

| 目录 | 证明什么 | 重拍命令 |
|---|---|---|
| `home/` | 首页一屏装下（含 667 矮屏）、带真实菜品图、天气胶囊展开、空态插画、打卡 toast | `node scripts/shot.mjs http://127.0.0.1:5173/m/home 393 852 docs/review/home/home-393x852.png` |
| `deck-gesture/` | 卡组九个动作帧：左划印章 → 出牌 → 右划确认面板 → 确认 → 返回；雷达弹层；触摸 tap 开层；耗尽/换一批/重置与 `refill-evidence.json` | `node scripts/record.mjs`、`node scripts/exhaust.mjs`、`node scripts/tap-probe.mjs` |
| `footprint/` | 打卡后足迹：本周次数/花费、冷却看板、菜系环形图 | `node scripts/shot.mjs .../m/footprint 390 844 ...` |
| `profile/` | 四区块（人设卡、基因条、忌口、红黑榜）与切换室友名单、冰箱入口 | `node scripts/shot.mjs .../m/profile 390 844 ...` |
| `fridge/` | 冰箱一屏（临期徽章、四分类）+ 买菜清单结果 | `node scripts/shot.mjs .../m/fridge 393 852 ...` |
| `room/` | 多人房间：B 端加入的 lobby、划卡投票、两端各自见到的揭晓页 | `node scripts/room-demo.mjs` |
| `dishes/` | 82 张菜品图的接触印样（每张 24 图），人工挑错用 | `python scripts/contact_sheet.py` |
| `final/` | **2026-10-30～31 后台与移动端迭代的最终态截图**（见下表） | `node scripts/shot.mjs ...` |

### `final/` 关键截图索引（2026-10-31）

| 文件 | 证明什么 |
|---|---|
| `v12-wall-final.png` | 大屏改抽屉式后的概览主题（KPI 三行完整、底部三卡不裁切） |
| `v11-wall-quality.png` | 数据质量主题：热力与词云已替换，5 卡填满 3×2 |
| `v10-datamanage-needstag.png` | 「待补标签（缺过敏原）」筛选生效，843 条全部带琥珀状态带 |
| `v13-users.png` / `v13-settings.png` / `v13-import.png` | 用户管理 / 算法参数 / 数据导入三页 |
| `v19-user-profile.png` | 单用户画像：偏好雷达、菜系分布、满意度、最近决策 |
| `v14-home-talk.png` | 首页八维分数已替换为三行自然语言描述 |
| `v14-login-demo.png` | 登录页五个演示账号快捷填充（只填不提交） |
| `v17-checkin-result.png` | 打卡结果面板：本周餐数 / 花费 / 预算剩余 + 去哪吃 |
| `v18-footprint-rate.png` | 足迹页每条记录的评价入口（未评价 / 已评价 + 改） |
| `v16-avatar-profile.png` / `v16-avatar-edit.png` | 头像图片渲染与上传弹层 |
| `v12-swap-60ms.png` | 后台路由切页 80ms 帧不再露深色底 |

## 已知的截图工具伪影

- `captureBeyondViewport`（整页长图）时，视口外的玻璃件与背景会渲染成白色 —— 是截图伪影，不是页面 bug。
- `--window-size` 启动参数截图不可信（Chrome 有最小窗口宽度，右侧会被裁），一律用 CDP `Emulation.setDeviceMetricsOverride`，`shot.mjs` 已经这么做了。
