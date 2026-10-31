# AGENTS.md —— 给 AI 助手的入场须知

先读这两份，再动任何代码：

1. **`MASTER_SPEC.md`（根目录）= 唯一事实来源（SSOT）**，当前 v2.3.5。任何设计、契约、算法、视觉的争议，以它为准。
2. **`docs/AGENT_MEMORY.md` = 工程记忆账本**：文档没写但施工要知道的决策与理由、后端与文档的漂移、未决问题、素材缺口、踩过的坑。与文档冲突时以文档为准，并回来修正账本。

历史稿在 `docs/spec_archive/`，只作存档，不作依据。

## 项目一句话

「食刻 EatWhat AI」毕设系统：`backend/` FastAPI + SQLAlchemy + SQLite，`frontend/` Vue 3 + Vite + Tailwind + daisyUI + Pinia + ECharts。移动端 `/m/*` 与 PC 后台 `/admin/*` 同一工程，最终 Capacitor 打 APK。

## 硬性红线（违反即返工）

- **纯 JavaScript**：新文件只许 `.js` / `.vue`，不引入 TypeScript。
- **颜色只有一个出口**：`frontend/tailwind.config.js` 的主题令牌 + `src/styles/` 里的 CSS 变量。组件、页面、图表、动效里**禁止出现裸 hex / 裸 rgb()**；JS 侧（ECharts / confetti / Lottie）统一经 `src/utils/theme.js` 读 CSS 变量。
- **v2.3 单色体系**：黑 `#17171A`、银灰 `#55555E`、白 `#FFFFFF`、浅灰 `#F4F4F5`。双模式靠**图标 + 文案 + 分段开关选中态**区分，不靠颜色。旧的暖橙 / 森林绿 / 奶油白全部作废。
- **三层架构**：L0 背景只做氛围（`Grainient` 全局底 / `LiquidChrome` 仅首页顶部与揭晓页 / `Silk` 仅启动登录页）→ L1 玻璃只给小面积悬浮件（`WEATHERPILL_GLASS.md` 配方）→ L2 内容卡 = **液态玻璃 G 方案**（v2.3.2 定款：折射层 + 112° 对角高光 + 亮边内阴影 + 深投影，四层缺一不可；文字白/浅灰，菜品图全彩不加磨砂）。两套玻璃配方同源不同方，不许混用。
- **玻璃性能分级（硬约束）**：SVG 位移折射只开在一级卡（TOP 1 主卡 / 卡组顶卡 / 主页区块卡），候选索引与列表次卡一律 `.glass-card--matte` 磨砂降级版，禁止整页全开折射。
- **玻璃采样隔离**：玻璃件不要放进套了 `filter: brightness()` 的容器内部（会采到被压暗的像素）。
- **动效库分工锁死**：`@formkit/auto-animate` 列表增删、`@vueuse/motion` 微交互、`gsap` 只管划卡与揭晓时间线、`lottie-web` 只做天气/空状态/插画、`canvas-confetti` 只做揭晓。不要用第二套方案替换其中任何一个。
- **路由前缀** `/api/v1`；本地开发靠 Vite 代理 `/api` → `127.0.0.1:8000`，不要在前端写死后端域名。
- **一屏不滚动**：`/m/home` 在 390×844 与 390×667 上必须一屏装下（问候 + 完整面板 + 顶卡全貌 + 露边 + 候选条 + 操作行），页面自身不滚动；靠 flex 分配高度，禁止写死卡高，单元素 ≤60% 屏高。不达标 Home 不过审。
- **双校区（v2.3.4）**：思源/建大按 `campus` 分开存门店/合成食堂；外食推荐、群组外食必须按校区过滤，跨校区不能拼一桌；下厨菜谱共享；前端校区切换后推荐/POI/统计同步刷新；`1700` 是原规格目标不是实际数，`17` 只是大屏图数量。
- **批次边界**：用户已确认按 `BATCH4_PRE_CLEARANCE.md` 的 R02→R01→F12 顺序，逐项由 Codex PASS 后才进入批次 4（万级数据 + `/admin` 大屏 + APK）。Room 划卡延期，不挡本轮准入，冻结前补验；不追认其他旧问题已通过。S19 冻结后才做展示版，`/admin` 不提前铺。
- **「紧凑呼吸」布局基线**（`MOBILE_VISUAL_SPEC.md` §4.3）：手机首屏必须同屏看到「问候语 + 完整控制面板 + 卡组顶卡全貌 + 下一张露边」，**任何单一元素不得超过 60% 屏高**。393×852 实测：状态行 44、面板 140（分段开关 40 / 气泡 30 单行六列 / 预算+CTA 同排 42）、卡面 374（44%vh，`height: min(47vh, 400px)`）、图区占卡 38%、候选条 30、操作行 44、Tab 52；页面左右边距 20px。卡高由 flex 分配，**禁止写死像素**。数值基线见 `docs/AGENT_MEMORY.md` §10.3 与 §12。

## 工作方式

- **逐步开发、独立放行**（2026-10-24 用户要求）：施工读 `BATCH4_PLAN.md`，审查读 `docs/REVIEW_RULES.md`，当前许可只看 `docs/review/STAGE_STATUS.md`。本规则补充执行顺序，不替代 `MASTER_SPEC.md`。
- **一次只做当前开放步骤**：提交验收包后停手；只有 Codex 明确签发本步 PASS 并登记受审版本后，才可开始下一步。开发方不得自签 PASS、改台账自行放行或提前铺后续代码；旧截图、账本“已完成”和自测通过均不等于独立验收。
- **先对齐，再动手**。范围、素材、契约有缺口时，先把问题摆出来让用户拍板，不要自行开工。
- **改后端要报备**。用户已授权小改后端，但每次改动前须说明改什么、为什么。
- **素材缺失就明说**。拿不到就用明确标注的占位并写 `TODO`，绝不假装完成。

## 验证命令

```powershell
# 后端
cd backend; python -m pytest -q
# 前端
cd frontend; npm run build
# 门禁（失败即 exit 1，必须三条全 PASS 才算界面可用）
node scripts/home-fit.mjs      # 一屏不滚动 + 操作行不与底栏相交 + 按钮命中自身
node scripts/refill-fresh.mjs  # 「换一批」必须给新候选
node scripts/sandbox-sync.mjs  # 沙盒参数与首页卡组同源
node scripts/check-colors.mjs  # 颜色只能从令牌出口取（禁裸 hex / 数字 rgb）
```

**验收口径**：`scrollHeight == innerHeight` **不等于**装得下（卡组曾用 `flex:0 0 auto` 被 `overflow:hidden` 吃掉溢出，按钮沉到底栏下）。必须同时断言元素矩形不相交、按钮中心 `elementFromPoint` 命中自身。

改完东西要跑对应的一侧，把真实输出贴出来再声称完成。

## 已知环境

Node v24.19.0 / npm 11.17.0 / pnpm 11.25.0 / Python 3.13.9。PowerShell 不支持 heredoc；终端默认 cp936，输出中文前需切 UTF-8。
