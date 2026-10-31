# docs/ 目录地图

先读根目录的 `MASTER_SPEC.md`（SSOT，当前 v2.3.5），再看这里。

## 谁会读这些文件

| 读者 | 该读什么 |
|---|---|
| 第一次接手的 AI / 新人 | `AGENTS.md`（红线与工作方式）→ `docs/AGENT_MEMORY.md`（施工决策与踩坑）→ 本文件 |
| 执行下一步开发 | 根目录 `BATCH4_PLAN.md`（逐步任务）→ `docs/REVIEW_RULES.md`（审查标准）→ `docs/review/STAGE_STATUS.md`（当前开工许可） |
| 只想验收页面 | `docs/review/README.md`（每张截图证明什么） |
| 要改菜品图 | `docs/DISH_IMAGES_PLAN.md`（口径，已执行）→ `docs/DISH_IMAGES_LEDGER.md`（每张的来源）→ `docs/DISH_IMAGES_MISSING.md`（当前无缺失） |
| 要换 Lottie 素材 | `docs/LOTTIE_SOURCES.md` |
| 要复核 Vue Bits 是否被改过 | `docs/vuebits-diff.md` |
| 查历史规格 | `docs/spec_archive/`（只存档，不作依据） |

## 根目录的四份规格

| 文件 | 作用 |
|---|---|
| `MASTER_SPEC.md` | 唯一事实来源（v2.3.5）：架构、契约、算法口径、批次路线图 |
| `MOBILE_VISUAL_SPEC.md` | 移动端视觉细则：单色总纲、背景分工、三层架构、§4.1 内容卡 G 方案基准值、§4.3 首页尺寸基线 + 单屏硬约束 |
| `WEATHERPILL_GLASS.md` | 悬浮小件（WeatherPill / Tab / 沙盒钮）玻璃配方，数值唯一来源 |
| `DASHBOARD_EXPANSION.md` | 后台大屏扩容方案（批次 4 用，图表清单待勾选） |

`DASHBOARD_EXPANSION.md` 的“待勾选”为历史措辞；现行 SSOT 已锁定 17 项。根目录新增 `BATCH4_PLAN.md` 为执行细则，含整改复核、批次 4、批次 5；不另设设计 SSOT。统计接口已确认 **13 个**（含 `quality`），SSOT v2.3.5 已同步；不能私删路由。

## 当前执行门禁

2026-10-25 当前状态（以 `review/STAGE_STATUS.md` 最终台账为准）：

- **PC01** = R02 真实仿真与 benchmark；**PC02** = R01 消除 N+1 与性能重测；**PC03** = F12 颜色清理与脚本门禁。三者是批次 4 的前置清账项。
- **r03** 是第三轮独立复审：R02 FAIL、F12 FAIL、R01 PASS（历史结论，保留不覆盖）。
- **r04** 是第四轮独立复审：PC01/R02 PASS、PC02/R01 PASS、PC03/F12 PASS；这是当前有效结果，只绑定 r04 manifest。README 中的“PC01/02/03 PASS”指 r04，不是 r03。
- **S09/r02**：提交时曾记 `REVIEW_PENDING`；Codex 独立复审后，台账最新修订与步骤表为 **BLOCKED**（双校区超出 r02 范围、r02 manifest 失配；D03 已于 2026-10-25 由用户裁决并落入 `DECISIONS.md`）。README 按最终台账写 BLOCKED；台账解封由 Codex/用户按流程处理，开发方不自改。
- **S10–S20、`/admin`：LOCKED**。建大雁塔已试抓：中心 `108.967153,34.236991`、真实 POI **6,659**、合成食堂 200、合计 **6,859**；思源 605+200=805。D03 已裁决：思源 605=样本 A、建大 6,659=样本 B，分校区报，不把 1700 当实际数，不得建大补思源或跨校区混算。Key 不写入文档/聊天。Room 划卡延期，冻结前补验；其他旧问题未自动通过。

## 目录约定

```
docs/
├── AGENT_MEMORY.md          工程记忆账本（决策、漂移、坑、未决问题）
├── README.md                本文件
├── REVIEW_RULES.md          独立审查规则、验收包与放行标准
├── 选题方向.md               毕设选题与背景（开题材料）
├── DISH_IMAGES_PLAN.md      菜品图口径与清单（人工维护）
├── DISH_IMAGES_LEDGER.md    逐张来源/校验值（自动生成，勿手改）
├── DISH_IMAGES_MISSING.md   缺失清单（自动生成，勿手改）
├── DISH_IMAGES_TODO.md      历史交办清单（已收口，保留防死链）
├── DISH_IMAGES_SOURCES_RAW.md 用户提供的原始来源清单（人工维护）
├── LOTTIE_SOURCES.md        四个 Lottie 文件的来源与校验
├── vuebits-diff.md          Vue Bits 三组件与原件的 diff 对照
├── _data/                   脚本读写的中间数据（机器文件，不是给人看的）
├── review/                  历史证据与分步审查，含 STAGE_STATUS.md；见 review/README.md
├── spec_archive/            历史规格存档（含 v2.1 初稿、v2.1.1、v2.3.1）
└── vuebits-originals/       Vue Bits 上游原件，用于 diff 复核
```

**`_data/` 里的文件由脚本生成**，改了会被覆盖；要改口径请改 `DISH_IMAGES_PLAN.md` 或脚本里的 `PICKS` / `DROP`。

## 一条纪律

文档里的数字（图片张数、测试条数、尺寸基线）必须能被命令复现。复现不了就说明数字过期了，改文档，不要改记忆。
