# 食刻 EatWhat —— 工程记忆（Agent Memory）

> **定位**：跨会话的工程状态与决策账本。**唯一事实来源永远是 [`MASTER_SPEC.md`](../MASTER_SPEC.md)（当前 v2.3.7）**；本文件只记录三类东西：
> ① 文档没写、但施工必须知道的工程决策与理由；② 文档写了但代码还没跟上的漂移；③ 阻塞项与教训。
> 与文档冲突时**以文档为准**，并回来改本文件。
>
> 最后更新：2026-10-25 ｜ 更新原因：D03 正式裁决（思源 605=样本 A、建大 6,659=样本 B，分校区报，不是 1700 合计）；补 rating/cost/tag 有值/缺失数与建大抽查；思源用同版递归脚本复跑仍 605。S09 台账当前 BLOCKED（r02 复审），S10 仍 LOCKED；详见 §24。任务见根目录 `BATCH4_PLAN.md`，规则见 `docs/REVIEW_RULES.md`，当前许可见 `docs/review/STAGE_STATUS.md`。
> §13–§16 为历史施工/复查记录，“已完成”“123 passed”等不能替代新流程 PASS；旧的一次改完再统一审查授权已被本次逐步门禁替代。

---

## 1. 项目是什么

- 毕设：《基于多维上下文感知与群组偏好博弈的智能饮食决策系统设计与实现》= 产品名「食刻 EatWhat AI」。
- 仓库：`D:\EatWhat`。后端 `backend/`（FastAPI + SQLAlchemy + SQLite），前端 `frontend/`（Vue 3 + Vite），PC 管理后台与移动端**同一个工程**，路由分流 `/m/*` 与 `/admin/*`。
- 交付形态：移动端 APK（Capacitor 打包）+ PC 管理后台/实验大屏 + 批次 5 的网页展示版（答辩投屏用）。

## 2. 文档版本与来源

| 文件 | 状态 |
| --- | --- |
| `MASTER_SPEC.md`（根目录，780 行） | **SSOT，v2.3.7**，2026-10-24 00:0x 从 `D:\谷歌\MASTER_SPEC_v2.3.2.md` 拷入 |
| `docs/spec_archive/MASTER_SPEC_v2.3.1.md` | 上一版 SSOT 归档（59548 字节，540 行） |
| `docs/spec_archive/MASTER_SPEC_v2.1_初稿.md` | 最初被 @ 的历史稿（2026-10-24 从根目录归档），仅存档不再引用 |
| `MOBILE_VISUAL_SPEC.md` / `WEATHERPILL_GLASS.md` / `DASHBOARD_EXPANSION.md` | ✅ 均在仓库根目录。`MOBILE_VISUAL_SPEC.md` 已于 2026-10-24 13:4x 用 `D:\谷歌` 的 **12353 字节新版覆盖**（含 §4.1 G 方案与 §4.3 单屏硬约束），旧版 8285 字节归档为 `docs/spec_archive/MOBILE_VISUAL_SPEC_v1_旧版_8285B.md` |
| `BATCH4_PLAN.md` / `BATCH4_PRE_CLEARANCE.md`（根目录） | 当前路线 PC01/R02→PC02/R01→PC03/F12→S09–S19→S20；旧 S00–S08 为未验收专项，Room 延期，冻结前补验 |

## 3. v2.1.1 → v2.3.1 的实质变化（只记影响施工的）

### 3.1 视觉体系整体推翻（v2.3）

- **配色**：暖橙 / 森林绿 / 奶油白 **全部作废**。改黑、灰、银、白单色：近黑 `#17171A`、银灰 `#55555E`、白 `#FFFFFF`、浅灰 `#F4F4F5`。0.5 第 1 条「双模式主色」废止。
- **双模式区分方式**：不再靠颜色 → 靠 **图标 + 文案标签 + 分段开关选中态（深灰实底白字）**；两模式共用同一套单色令牌。
- **背景构造法**：v2.1 的「backgrounds.supply 纹理 PNG + 70%~85% 奶油白罩色」**作废**，素材不再使用（其 $49 授权争议随之消失）。改 **Vue Bits 三背景分工**：
  1. `Grainient`（谷物）银灰版 → 移动端**全局底**，三色 `#3A3A40 / #17171A / #55555E`，`timeSpeed ≈ 0.2` 近静止，禁用默认蓝紫配色；内容密集页允许冻帧或降帧。
  2. `Liquid Chrome` → **仅**首页顶部与共识揭晓页；底色 `#1A1A1A`（最亮不超 `#222226`）；**文字严禁直接压铬面**，必须落在玻璃或实底组件上。
  3. `Silk` → **仅**启动/登录页，银灰，Speed 5 → 1~2；**不得作全局底**（墨池已用 Silk 作全局底，两作品须区分）。
- **三层架构（当前 v2.3.7）**：L0 背景氛围 → L1 小面积悬浮件使用 WeatherPill 配方 → L2 内容卡使用液态玻璃 G 方案。旧“内容一律实底”已废止；一级卡折射、次卡 matte 降级，按 `MOBILE_VISUAL_SPEC.md` 执行。
- **daisyUI 令牌**：`primary` = `#17171A`、`secondary` = `#55555E`、`base` = `#FFFFFF` / `#F4F4F5`。「颜色只许引用主题令牌、严禁写死」的硬约束不变。
- **WeatherPill 玻璃**：不再「打开 Figma 抄 CSS」，参数已实测提取，**唯一数值来源是 `WEATHERPILL_GLASS.md`**（Apple「macOS 27」Materials 页 Liquid Glass - Small（Light）两层填充 + 3 内阴影 + 4 外阴影 + 折射参数）。该文件缺失 → 当前阻塞。
- **其他**：状态气泡选中态 = 深灰实底白字（无模式色）；卡片仍是 `rounded-3xl` + `shadow-[0_8px_30px_rgb(0,0,0,0.04)]`，但图标改**单色**（不再双色图标）。
- **未废止**：5 个动效库分工、Lottie（天气/空状态/揭晓）、confetti、gsap 专用于划卡与揭晓编排、daisyUI 控件来源、Inspira Shimmer Button 主 CTA、`auto-animate` 用法 —— 全部继续有效。

### 3.2 接口契约变化（直接影响批次 2）

- **红黑榜分对象**：`POST /users/{id}/red-black-list` 入参改为 `target_type`（`DISH` | `RESTAURANT`）+ `target_id` + `list_type`（`FAV` | `BLACK`）+ `action`；**`FAV` 只允许 `DISH`**；响应新增 `blacklist_restaurant_ids`。
- `user_preferences` 新增 `blacklist_restaurant_ids`（JSON，默认 `[]`）：外食模式下该门店全部菜品剔除；群组取全体成员**两类黑榜的并集**。
- Profile 文案口径：红榜只对菜品；黑榜分「菜品」与「门店」两类分别提示，**严禁**再把黑榜笼统写成「黑榜店铺」。
- `POST /auth/login` 已从第五章路由总表**移除**（演示身份只走 `X-User-Id`）；后端目前仍挂载。
- `GET /context/weather` 表格不再列 `temp/weather` 覆盖参数（仍支持，后端离线兜底）,数据源锁定高德天气 API；**天气覆盖参数现在只算后端兜底，不是契约**。
- `appliance_tag` 改 **JSON 数组**，默认 `["炒锅"]`，多值如 `["电饭煲","一锅出"]`；气泡规则按「数组含任一」判定。
- `room_votes` **只存枚举不存分值**；百分制分值唯一出处是算法 3（`SUPER_LIKE=120 / LIKE=100 / PASS=40`，`VETO` 不计分只掩码，超时 `60`）。
- `POST /rooms/{room_code}/join` 是成员落库**唯一入口**；WebSocket 只订阅不落库，未落库连接直接 403。
- **模块 8：大屏统计** `GET /admin/stats/*`：已确认 **13 个**（overview / geo / calendar / heatmap / cuisine / cuisine-trend / personas / scatter / flow / keywords / race / cooccurrence / quality），`quality` 保留；双校区 `campus` 过滤与合计规则见 SSOT v2.3.4 §5.5。
- `benchmark_json` 结构换新：`generated_at`、`sample`、`duplication_rate_curve`（`days` 14 点等长）、`group_satisfaction_bars`（`strategies/avg_scores/least_misery_scores` 等长）。

### 3.3 算法口径

- 算法 2 已在 v2.3.2 正文锁定：原始分排序，展示 `min(100, raw_score)`，四权重归一化到和 1；不是待裁决事项，见 §8。
- 算法 4 从「分支限界」措辞**降级**为「Top-20 候选内的角色分组三元组枚举 + 约束筛选」，论文/答辩**不得**再称「改进背包」或动态规划；代码若仍是 branch-and-bound 实现，行为等价、可不动。

### 3.4 路线图（4 批次 → 5 批次）

- 批次 1–3 已有实现，当前先按用户确认的 R02→R01→F12 准入清账，三项 Codex PASS 后进入 S09；旧专项未追认通过，Room 延期且冻结前补验。S19 冻结后进入展示版/真机录屏；17 项大屏已锁定（含导出能力项）。

## 4. 已定的工程决策（含理由，勿重复讨论）

| 决策 | 理由 |
| --- | --- |
| Tailwind **3.4** + daisyUI **4** | daisyUI 5 是 CSS-first、没有 `tailwind.config.js`，与「一套主题令牌、只改一处」的硬约束冲突 |
| 纯 JavaScript，不引入 TS | 文档锁定 `.js` / `.vue` |
| Vite 代理 `/api` → `127.0.0.1:8000`，前端统一前缀 `/api/v1` | 后端 `main.py:31-33` 就是 `/api/v1` |
| Pinia 三个 store：`persona` / `mode` / `algo` | 人设切换、双模式与气泡、沙盒参数互不耦合 |
| 颜色唯一出口 = `tailwind.config.js` 主题 + CSS 变量 `--color-*`；ECharts/confetti/lottie 通过 `utils/theme.js` 读 CSS 变量 | 满足「组件里禁裸 hex」，同时让 JS 侧图表也能拿到令牌 |
| Shimmer 主 CTA：抄 Inspira UI **单组件源码**到 `components/ui/` | 文档禁手写流光，但不引整库 |
| 批次 2 只交付 Home / Footprint / Profile / AlgoSandboxDrawer + 4 组件；Fridge / Room 放占位页防死链；`/admin` 留批次 4 | 用户已确认该范围 |
| 允许小改后端，**必须先报备** | 用户 2026-10-23 明确授权 |

## 5. 当前状态（2026-10-24，分步门禁初始化）

- **实现范围**：后端已挂载 auth_user/recommend/eating_log/catalog/fridge/group_room REST 与 WS；移动端 Home/Footprint/Profile/Fridge/Room 已有实现，不再是冰箱/房间占位阶段。admin_sandbox 与完整批次 4 尚未挂载。
- **最近独立复查证据**：`docs/review/recheck-2026-10-24/REPORT.md` 记录导航修复、7 项真实点击、两档首页尺寸和单人沙盒联动；当时后端 106 passed、前端 build 成功。仅证明该时点与所测范围，不覆盖后续补丁。
- **其后新增补丁**：§16 记录 F07/F08/F09 新实现和开发方报告的 123 passed；尚未按新流程获得 Codex 独立 PASS。全入口身份、部分向量覆盖、精确到期边界分别在 S01/S02/S03 复核。
- **未闭环范围**：F10 群组参数链、Room 完整划卡/扫码/多端恢复、主题/素材全量验收分别进入 S06/S07/S08；不因单测数量上涨整体关单。
- **当前许可（2026-10-24 r02独立复审更新）**：用户已允许三项同轮提交；Codex现签PC01/R02 FAIL、PC02/R01 PASS、PC03/F12 FAIL，详见§19。仅允许失败项整改，S09/批次4仍LOCKED。批次4准入不再要求旧S00–S08全部先过，Room延期，未验收专项在冻结前补验；展示壳仍等S19。状态唯一入口为 `docs/review/STAGE_STATUS.md`。
- **初始化记录范围**：建立分步流程时仅改文档，没有为上述所有补丁签PASS；后续r01/r02审查的实际执行和许可分别见§18/§19。不要用历史初始化说明覆盖当前审查记录。

## 6. 后端 ↔ 文档对齐状态（v2.3.2，2026-10-24 00:20 完成）

用户已裁决「同意现在同步，列为批次 2 第 1 步的前置对齐项」。以下**已完成并通过 `pytest`（47 passed）**：

| 项 | 处理结果 |
| --- | --- |
| `appliance_tag` | `backend/models.py:75` 改 `Column(JSON, nullable=False, default=lambda: ["炒锅"])`；种子统一数组化，`一锅出番茄牛腩` 存 `["炒锅","一锅出"]` 验证多值 |
| `blacklist_restaurant_ids` | `backend/models.py:47` 新增 `Column(JSON, nullable=False, default=list)`；`ProfileResponse` / `RedBlackListResponse` 均返回 |
| 红黑榜入参 | `backend/schemas.py:53-58` 改 `target_type`(`DISH`\|`RESTAURANT`) + `target_id` + `list_type` + `action`；`FAV` + `RESTAURANT` 返回 **400** |
| 红黑榜出参 | 三个数组齐回 |
| 门店黑榜过滤 | `single_recommender.py` 外食模式按 `blacklist_restaurant_ids` 整店剔除；`group_recommender.py` 取全员两类黑榜并集 |
| `POST /auth/login` | **已删除**（`auth_user.py` 不再注册），`schemas.py` 同步删 `LoginRequest/LoginResponse`；测试改为断言 404 |
| `lazy_one_pot` 白名单 | `vector_spec.py:76` 改 `("电饭煲", "一锅出")`；菜品侧按「数组含任一」判定（`_appliance_set` 兼容历史单值） |
| 单测 | 移除 login 用例；新增 4 条：login 已下架、FAV 只收菜品、门店黑榜整店剔除 API+算法、未知 target 404 |
| 开发库迁移 | `backend/scripts/migrate_v231.py`（幂等）：加列 + 100 条 `appliance_tag` 转数组；随后 `init_seed_data.py --force` 重播 |

本节其余表格为此前对齐记录；当前 fridge/group_room 已挂载（见 §5），admin_sandbox 与模块 8 stats 仍待批次 4；整改是否通过以新台账为准。

**已知数据张力（v2.3.2 已裁决，不再是问题）**：`一锅出` 三道菜 `prep_speed` 0.40/0.45/0.45 曾与 `prep_speed>=0.7` 门槛冲突，导致 `lazy_one_pot` 只召回 3 道电饭煲菜。v2.3.2 正文删除该门槛（厨具可用性与做菜速度正交，不许改数据迁就规则）→ 后端 `single_recommender.py:192-197` 只保留厨具判定，`vector_spec.py:71-77` 去掉 `prep_speed_min`，单测补 `assert "一锅出" in seen`。

## 7. 素材与外部依赖

| 素材 | 状态 |
| --- | --- |
| `MOBILE_VISUAL_SPEC.md` / `WEATHERPILL_GLASS.md` / `DASHBOARD_EXPANSION.md` | 均在根目录；现行视觉遵循 v2.3.2 G 方案与单屏硬约束。`BATCH4_PLAN.md` 已起草，逐步任务与验收见该文件 |
| backgrounds.supply 三张纹理 PNG | **作废，不再需要** |
| Vue Bits `Grainient` / `LiquidChrome` / `Silk` | 用户已授权（2026-10-23）：「自行去 vue-bits.dev 取源文件原件接入，只改 props（颜色、speed），不许改 shader 与内部实现；验收时交与原文件的 diff 对照」。许可 MIT + Commons Clause，毕设自用合规 |
| WeatherPill 玻璃参数 | ✅ 唯一来源 = `WEATHERPILL_GLASS.md` §4「Web 生产组合版」，**整段照抄、不许自调**；见下方 §9.1 |
| Lottie JSON（晴/雨/雪、空状态、揭晓） | 仍需要；v2.3.1 未废止 Lottie |
| 高德 Key | 未配置 → `/context/weather` 永远 `offline` 22℃/晴 |

### 7.1 当前批次门禁

- 用户 2026-10-24 确认：按清账文件 R02→R01→F12，完成一项停手，由 Codex 充分检查代码、独立测试和真实运行，PASS 才进入下一项；Room 划卡延期，不挡本轮批次 4。v1.0 的 S00–S08 前置串行安排已修订，不追认其验收。
- 施工读根目录 `BATCH4_PLAN.md`，验收读 `docs/REVIEW_RULES.md`，当前许可只看 `docs/review/STAGE_STATUS.md`。开发方不得自行放行或提前铺下一步；设计 SSOT 仍是 MASTER_SPEC。

## 8. 已裁决事项（2026-10-23 用户答复，勿再议）

1. 三份附属文档已到手；`BATCH4_PLAN` 按临近批次逐份出，大屏契约以 v2.3.1 第五章模块 8 + 第六章 §5 为准。
2. **`total_score` 封顶 100 保留**，后端现状正确。口径写死：**排序用未封顶 `raw_score`，展示用封顶值** —— `total_score_display = min(100, W_decay × (α·taste + β·weather + γ·budget + δ·status) × boost_fav)`；四权重归一化（和为 1）不变。雷达图画 `radar_5d` 五个分项（各 0–100），与总分封顶无关，轴不会失效。论文按此表述。
3. **`POST /auth/login` 删除**，身份口径锁定为演示级 `X-User-Id`。
4. **`lazy_one_pot` 白名单只有 电饭煲 / 一锅出**；`免开火凉拌` 是 `appliance_tag` 合法枚举，但不进该白名单。~~`prep_speed>=0.7`~~ 已于 v2.3.2 删除（见 §10.1）。
5. 后端同步已获授权并已完成（见 §6）。
6. 三步走法获同意：①重做三个样式文件换单色令牌、去纹理层 ②`glass-tokens.css` 数值必须取自 `WEATHERPILL_GLASS.md` ③一屏 Home 先行验收。

## 9. 术语与常量备忘（施工常用）

- **8 维风味向量**（顺序即 `FEATURE_KEYS`）：`spicy_level` 辣度 / `oily_level` 油腻度 / `soup_level` 汤水感 / `temp_fit` 适宜温度 / `satiety_level` 饱腹度 / `prep_speed` 出餐速度 / `social_fit` 社交属性 / `comfort_level` 抚慰指数。
- **五维雷达**（`radar_5d` 键，0~100）：`taste` / `weather` / `budget` / `freshness` / `status`。
- **6 个状态气泡**（id → 文案 → 适用模式 → 关键参数）：`exhausted` 😫 刚加完班累瘫 / 双模式 / `delta_status=0.45`；`broke_end_month` 💸 月底吃土模式 / **仅外食** / `gamma_budget=0.55` + 预算硬过滤；`craving_heavy` 🌶️ 嘴馋想吃重口 / 双模式 / `alpha_taste=0.50`；`light_healthy` 🥗 肠胃负担重想清淡 / 双模式 / `oily>0.5 或 spicy>0.3` 得分 ×0.2；`need_hot_soup` 🍲 手脚冰凉想喝热汤 / 双模式 / `beta_weather=0.45` + `soup_level>=0.7`；`lazy_one_pot` 🍚 只有电饭煲/不想洗碗 / **仅下厨** / 厨具白名单（v2.3.2 起不再限速度）。
- **枚举**：模式 `OUT_DINING` / `HOME_COOKING`；菜品角色 `MEAT` / `VEG` / `SOUP` / `ONE_MEAL`；房间状态 `WAITING` / `SWIPING` / `FINISHED`；冷却状态 `COOLING` / `WARMING` / `READY`（阈值 `<0.3` / `<0.8` / 其余）。
- **默认算法参数**：`lambda_decay=0.5`、`omega_group=0.5`、`alpha_taste=0.35`、`beta_weather=0.25`、`gamma_budget=0.20`、`delta_status=0.20`。
- **环境**：Node v24.19.0、npm 11.17.0、pnpm 11.25.0、Python 3.13.9。

### 9.1 玻璃令牌（`WEATHERPILL_GLASS.md` §4 Web 生产组合版，整段照抄、禁止自调）

```css
.weather-pill {
  border-radius: 999px;
  background: rgba(246, 246, 246, 0.48); /* Thin 档；Ultrathin 0.36 / Medium 0.60 */
  backdrop-filter: blur(60px);
  -webkit-backdrop-filter: blur(60px);
  box-shadow:
    inset 0 40px 10px -40px rgba(40, 40, 40, 1),
    inset 0 -40px 10px -40px rgba(40, 40, 40, 1),
    inset 0 40px 30px -40px rgba(230, 230, 230, 1),
    1.25px 0 0 -0.75px rgba(208, 208, 208, 1),
    -1.25px 0 0 -0.75px rgba(208, 208, 208, 1),
    0 0 0 0.5px rgba(232, 232, 232, 1),
    0 8px 15px rgba(0, 0, 0, 0.02);
}
```

- 降级（`backdrop-filter` 不支持）：`background: rgba(246,246,246,0.85)` 实底。
- 只用于小面积悬浮件；深色底（Grainient 深灰 / Liquid Chrome）下仍可读；Dark 变体本次未提取。
- Figma 未给 `saturate`；若加，必须在注释注明「自选参数、非 Apple 原值」。
- 原值出处：下层 4 层填充 `#F8F8F8·20% / #444444·60% / #FFFFFF·25% / #000000·25%`；外阴影 4 个、内阴影 3 个，逐项见文档 §1 表 A/B。

## 10. 教训（踩过的坑，别踩第二次）

- **Hindsight 写接口 401**（`Authentication failed: API key required`，未配 `apiToken`）→ 记忆只能落本地文件；`hindsight_capture_initiative` / `hindsight_ingest_document` 不要反复重试。
- **PowerShell 不支持 heredoc**（`<<'PY'` 直接报错），多行脚本改用 here-string 或写临时文件。
- **默认控制台 cp936** 会把中文打成乱码，输出中文前需设 UTF-8。
- `git diff --no-index` 在 Windows 下把中文路径显示成八进制转义（`\350\260\267`），属正常现象。
- 仓库尚无 commit：改 `MASTER_SPEC.md` 前先归档（已在 `docs/spec_archive/` 留档）。
- **`@vueuse/motion@2.2.6` 两个 API 陷阱**（模式滑块三天里两次翻车都因它）：
  1. `v-motion` 指令**没有 `:animate` 变体**，合法变体只有 `initial / enter / leave / visible / visible-once / hovered / tapped / focused`。写 `:animate="{ x: 8 }"` 是死代码，永远不会动。
  2. `useSpring(values, spring)` 返回 `{ values, stop, set }`，**不是 Ref**；当 `ref.value` 读会得到 NaN，浏览器随即丢弃 `translate3d(NaNpx,…)`（`style` 属性变 null），看起来像"没生效"。
  3. 正确写法：`const { apply } = useMotion(elRef, { initial: { x: 0 } })`，然后 `apply({ x: 多少像素, transition: { type: 'spring', stiffness: 300, damping: 20 } })`。像素必须自己量（`clientWidth / 2 - 4`），传 `'100%'` 会按元素自身宽度算，对不上轨道。
- **daisyUI v4 的 `.range` 不能直接用在深色底**：它的 thumb 是 1.5rem 方块 + 超大 `box-shadow` 填充条，父级 `overflow: hidden` 会把填充裁成一块浅色方片。已统一改用 `.slider-ink`（见 `main.css` 末尾）：16px 白圆点、4px 细轨、`overflow: visible`。
- **非 Tailwind 入口的 CSS 不能用 `@layer components`**：`glass-card.css` 被 `main.js` 直接 import，构建会报 `@layer components is used but no matching @tailwind components directive is present`。只有 `main.css`（含 `@tailwind` 指令）才能用。
- **截图别信 `--window-size`**：Chrome 窗口有最小宽度，`--window-size=390` 会被钳到约 500 并裁掉右侧，误判成"页面溢出"。用 `scripts/shot.mjs`（CDP `Emulation.setDeviceMetricsOverride`），它会同时打印 `clientWidth / scrollWidth / overflow`。`FULL=1` 的整页长图里，视口外的玻璃件与背景会渲染成白色，属 CDP `captureBeyondViewport` 伪影，不是 bug。
- **`job_kill` 只杀 shell，不杀 uvicorn 子进程**：端口被占时报 `[WinError 10013]`，先用 `Get-NetTCPConnection -LocalPort 8000` 找 PID，再 `Stop-Process -Id <PID> -Force`。
- **`uvicorn` 必须在仓库根启动**：`python -m uvicorn backend.main:app`。在 `backend/` 里跑 `uvicorn main:app` 会 `ImportError: attempted relative import with no known parent package`。
- **编辑器原子写会打死 Vite watcher**：`EBUSY ... .tmpdir/xxx.tmp`；`vite.config.js` 的 `server.watch.ignored` 已加 `['**/*.tmp','**/.*.tmpdir/**','**/.*.tmpdir']`。
- **别用 `Substring` 做整段替换**：一次"从注释处截断"直接砍掉了 `main.css` 的后半段（`prefers-reduced-motion` 块被腰斩），排查了半小时。改 CSS 用 `edit` 精确替换，或先备份。
- **GSAP `Draggable` 的 `zIndexBoost` 会吃掉确认面板**：它默认在按下时把被拖元素 `z-index` 抬到 1000，且松手不还原；于是 `.confirm`（`z-index: 6`）被压在顶卡下面，透视玻璃把面板糊成一团白斑 —— 看起来像"backdrop-filter 渲染 bug"，其实是层级。创建时必须 `zIndexBoost: false`。
- **卡组停位别给大位移 + 大旋转**：`x: 24 / rotation: 5°` 会把 390 视口撑成 `scrollWidth 406`；确认态停位改成 `x: 10 / y: -8 / rotation: 1.5` 后页宽恢复 390。
- **卡面隐藏 ghost 正文**：露边卡是半透明玻璃，正文会被顶卡透出来叠字；`DishCard` 在 `variant="ghost"` 下用 `v-if="!isGhost"` 整块不渲染 body。

### 10.2 「紧凑呼吸」布局基线（2026-10-24 用户口径，已落地）

- 面板：`ModeSwitcher` 总高 44px（轨道 padding 3 + item 38，图标 15 / 标题 13 / 描述 9.5 横排）；气泡**单行六列**、`height: 30px / font-size: 11.5px / gap: 5px`；面板 `gap: 10px`、`margin-bottom: 24px`；实测面板高 **246px（29% 屏高）**。
- CTA：`ShimmerButton` `min-height: 48px`；预算行 `gap: 3px`、标签 `margin-bottom: 4px`。
- 卡组：`.deck` 高 **300px（36% 屏高）**；图区 `92px`（≈25% 卡高）；菜名 20px、匹配度 30px、归因 2 行截断；露边 `--offset: depth×22px`、`--shrink: 1 - depth×0.06`（缩放 0.94 / 0.88，露出约 12px / 26px）。
- 页面：`MobileShell` 左右 `px-5`（20px）、`pt = safe + 14px`；问候语 16.5px、`margin: 28px 0 22px`；区块间距 20px。
- 实测（390×844）：pill 12/34、问候语 68/21、面板 119/246、卡组 389/300、按钮 733/43、Tab 栏 788/44，`scrollWidth == clientWidth == 390`，无横向溢出；单一元素最大 246px，远低于 506px（60% 屏高）。

### 10.1 v2.3.2 定款要点（2026-10-24，用户答复原文摘录）

- 内容卡 = **液态玻璃 G 方案**，四层缺一不可：①折射层（`rgba(255,255,255,0.16)` + `backdrop-filter: blur(4px) saturate(170%)` + SVG 位移滤镜）②112° 对角高光 ③亮边 `rgba(255,255,255,0.45)` + 内阴影高光 ④深投影。文字白/浅灰，**菜品图全彩原样不加磨砂**。
- **性能分级是硬约束**：折射只开一级卡（TOP 1 主卡 / 卡组顶卡 / 主页区块卡），候选索引与列表次卡用 `.glass-card--matte`，整页全开折射中端机必卡，"没得商量"。
- 悬浮小件（WeatherPill / Tab 栏 / 沙盒钮）继续走 `WEATHERPILL_GLASS.md` 配方，**两套同源不同方，不许混用**。
- 「玻璃采样隔离」继续有效：玻璃件不许放进套了 `brightness` 的容器内（`.home__chrome` 的 `filter: brightness(0.13)` 只能罩 LiquidChrome 本身，玻璃卡必须是它的兄弟节点）。
- `lazy_one_pot` **删掉 `prep_speed>=0.7`**：语义是"厨具可用性"，与做菜速度正交；一锅出的 0.40–0.45 是真实值，不许改数据迁就规则。
- `total_score` 封顶口径入正文：**排序用未封顶原始分，展示 `min(100, 原始分)`**，与雷达五维无关。

## 10.3 一屏硬约束（v2.3.2 §4.3）落地基线

**目标**：390×844 一屏装下全部主元素、页面不滚动；矮屏（667）同样成立；单元素 ≤60% 屏高。

**结构（Home.vue，自上而下）**
- `.home__head` 44px：问候（14px，单行 ellipsis）+ 沙盒图标钮 32px + WeatherPill（`flex:0 0 auto`，文字全部 `nowrap`，整颗约 130px 宽）。
- `.panel` 140px：ModeSwitcher 40px（只留模式名，desc 降级为 `title`）+ StatusBubbles 30px（单行六列）+ `.runrow` 42px（预算滑块 flex + CTA 固定 128px）。
- `.deck-host` flex:1（844 下 470px）：卡组吃满，卡面 = host − 26px 露边预留 → 444px（53% 屏高）。
- `.candidates` 30px：一行横滑，无标题，`aria-label`/`title` 说明用途。
- `.deck-actions` 44px：换一个 / 就吃这个。
- 底部预留 60px 给 `.tabbar`（栏体 52 + 8 呼吸）。

**实现要点（改之前先看这几条）**
- 一屏靠 flex 分配，不写死卡高：`SwipeCardDeck` 的 `.deck` 是 `flex:1 1 auto; min-height:0`，卡层 `inset: 0 0 26px`；露边偏移 24/48、缩放 0.05/层，露出 13px 与 26px。
- `DishCard` 图区是 `flex: 0 0 32%`（不是固定 px），卡变矮自动缩，`min-height: 96px` 兜底；正文用 `.dishcard__info { justify-content: center }` 垂直居中，footer 贴底。
- 玻璃采样隔离仍在：LiquidChrome 容器 `filter: brightness(0.13)` 只管背景层，所有玻璃件都是它的兄弟节点。
- 验证据 `docs/review/home/onescreen-390.png`、`docs/review/home/onescreen-390x667.png`；探针数据（390×844）：head 44 / panel 140（17%vh）/ chips 30 / actions 44 / tab 44，`scrollHeight == innerHeight`，`scrollWidth == clientWidth == 390`。卡面最终 374（44%vh，`height: min(47vh, 400px)` 后的实测值）。

## 11. 菜品图（v2.3.2 批次 2，已完成）

- 口径：只爬现有 100 条种子菜（外食 60 / 下厨 40，含 5 组同名重复 → 95 张唯一图），来源限 Wikimedia Commons；`image_url` 存**相对路径** `/dishes/xxx.jpg`，文件落 `frontend/public/dishes/`（Vite public，构建时原样拷贝；后端只给路径不给字节）。
- **2026-10-24 收口**：用户按清单自搜后整包给来 95 张（`D:\谷歌\dish-images-all-95.zip`，含 `SOURCES.md`），已全部落盘。现在 **95 张唯一图 / 100 条记录全部带图 / 缺失 0**（5 组同名菜共用一张）。
- 与自动流水线时期的差异：来源从 Commons/Unsplash/Pexels 换成**小红书笔记实拍截图**；规格从 800×450 横图换成**672×890 竖版原图不裁切**（卡片端 `object-fit: cover` 取中间带，保留后续改取景的余地）；映射从「按菜名读清单表」改成**按文件名里的三位 id**（`scripts/build_dish_image_map.py`），因为「番茄炒蛋 / 西红柿炒蛋」这种近名菜按名字匹配会错。
- 台账改为逐张登记笔记标题/作者/链接/尺寸/sha256（`docs/DISH_IMAGES_LEDGER.md`），原始清单存 `docs/DISH_IMAGES_SOURCES_RAW.md`；`docs/DISH_IMAGES_TODO.md` 标记为已收口语料。
- 缺失 13：酸辣土豆丝、凉拌折耳根、青椒土豆丝、韭菜炒鸡蛋、洋葱炒蛋、酸辣白菜、玉米排骨汤、腊肠煲仔饭、凉拌木耳、一锅出番茄牛腩、一锅出土豆炖鸡、番茄麻辣烫、骨汤麻辣烫（后两个可与「麻辣烫套餐」复用同一张，待裁决）。
- 规格：800×450（16:9 居中裁）、JPEG q82 progressive、单张 ≤120KB，全量 5.9MB。
- 脚本链路（都在 `scripts/`，可重跑；中间数据统一放 `docs/_data/`）：
  `fetch_dish_images.py`（Commons 检索 + 打分 + 下载 + 裁切；ALIASES 别名、1.2s 节流、429 退避）→ `contact_sheet.py`（人工挑错用的接触印样，出 `docs/review/dishes/dishes-sheet-N.png`）→ `apply_picks.py`（`PICKS` 精确取件 / `DROP` 退回缺失）→ `recover_missing.py`（对缺失菜换叫法再试，`ok_title()` 强制标题含核心词）→ `build_dish_image_map.py`（按 id 生成 `backend/scripts/dish_images.py`）→ `render_image_ledger_from_sources.py`（从 `SOURCES_RAW` 生成台账与缺失清单）。旧脚本 `gen_dish_image_map.py` / `render_image_docs.py` 保留但已被上面两个取代。
- 网络坑（本机特有）：`curl.exe` 一律 http=000；`requests` 必须保留 `trust_env=True`（读 Windows 注册表代理）才通，直连会 reset。
- 纪律：`DROP`（退回缺失）与恢复必须**维护同一份清单**，不能两套叠加——曾因为旧 `DROP` 把刚恢复的好图又删了一遍。
- 卡片图区占整卡 **38%**（`flex: 0 0 38%`，约屏高 21%），`object-fit: cover`；露边卡 `v-if="!isGhost"` 连图一起不渲染（否则后卡图会透过玻璃糊上来）。

## 12. 一屏硬约束（复核口径）

- 390×844：head 44 / panel 140 / card 444 / chips 30 / actions 44 / tab 44，scrollHeight == innerHeight。
- 390×667：card 279、图区 112，同样无滚动；@media (max-height: 700px) 再收紧间距。

## 10.4 自绘揭晓 Lottie 不可见（2026-10-29 已闭环）

- 历史现象：`reveal.json` 多版出现空白或灰块；当时暂用内联 SVG，并误判为 `lottie_light` 对所有自绘结构不兼容。
- 本轮定位：克隆圆点的多段位置轨道会让图层 `transform` 变成 `matrix(1,0,0,1,-999999,-999999)`；只把结束关键帧从 60 改到 59 仍无效。`data-missing=false`、SVG/path 存在甚至非零矩形都不能证明可见，矩形还必须落在组件可视区域内。
- 修复：`scripts/make_reveal_lottie.py` 改为静态圆点坐标 + 依次淡入透明度轨道，停播保持末帧；`Room.vue` 正式接入 `LottieIcon name="reveal"`，GSAP 时间线与 confetti 分工不变。
- 验证：`docs/review/consolidated/G1_R02/` 真实房间揭晓证据为 9/9 路径绘制且位于组件矩形内、动画签名随时间变化、无 console/exception；前端 build、三条首页门禁、颜色门禁均通过。
- 后续做 Lottie 素材：必须跑真实渲染与可视区域探针，不再只数 SVG 节点，也不再把尚未接入的占位称为完成。

## 13. 审查报告整改（2026-10-24）

审查报告 `docs/review/audit-2026-10-24/REPORT.md` 提出 6 项 P1 / 7 项 P2 / 2 项批次 4 风险。
用户裁决：按 ①决策红线 → ②房间状态机 → ③首页可用性 → ④数据边界 的顺序修，
房间「划卡交互」留到下一轮，记忆账本跟着整改一起更新。

### 批次① 已完成（F01 / F02）

- **F01 忌口漏判**：新增 `backend/algorithms/veto_rules.py` 作为**唯一出口**，
  单人推荐与群组初筛都调它，不再各写一份（旧的两份实现就是漂移根源）。
  - 词表 `VETO_SYNONYMS`：类别 → 别名，「海鲜」自动展开成 虾/蟹/贝/鱼/蚝油…
  - 匹配只做「别名出现在食材名里」这一个方向。**反向包含会造假阳性**：
    别名池里有「鱼豆腐」，食材「豆腐」反过来包含于「鱼豆腐」，
    于是麻婆豆腐被判成海鲜 —— 第一版就踩了这个坑。
  - 单字别名必须进 `STRONG_SINGLE`，否则「鱼」会命中「鱼香肉丝」。
  - 词尾规则 `SUFFIX_RULES`：草鱼/黑鱼/鲳鱼列不完，用「词尾是鱼/虾/蟹/贝/蛤/螺/鱿/鲍/参」
    兜底；只认词尾，所以「鱼香肉丝」（尾缀「丝」）不会被误判。
  - 已知取舍：`蒜蓉生菜` 因含 `蚝油` 会被海鲜忌口挡掉，这是有意的（过敏口径从严）。
- **F02 全否决仍出赢家**：`backend/algorithms/group_recommender.py` 的胜出集合改为
  `eligible = [r for r in reports if not r["masked_by_veto"]]`，全被否决时
  `winner_dish_id = None`、`has_consensus = False`，并返回 `vetoed_dish_ids`；
  `backend/routers/group_room.py` 的 `CONSENSUS_REVEAL` 带上 `has_consensus` 与
  `message`（「所有候选都被否决了，这局没有共识」），前端不许把 0 分当推荐结果。
- 回归：新增 `backend/tests/test_veto_and_consensus.py`（20 条），全量 `pytest -q` → **87 passed**。
- 实测：`X-User-Id: 3`（忌口 海鲜）`limit=100` 返回 51 道，`水煮鱼/白灼虾/虾饺皇/
  云吞面/三文鱼沙拉/清蒸鲈鱼/鳗鱼饭/蒜蓉生菜` 全部被挡；`麻婆豆腐/鱼香肉丝` 不受影响。

### 复现笔记（下次复查直接用）

```python
# F02 全否决
compute_group_consensus(db, [1,2], [23,24], [V(1,23,"VETO"),V(2,23,"VETO"),V(1,24,"VETO"),V(2,24,"VETO")])
# 修复前 winner_dish_id=23；修复后 None + has_consensus=False
```

```powershell
# F06 短屏重叠：用 scripts/shot.mjs 的 preShot 量，别只看 scrollHeight
node scripts/shot.mjs 'http://127.0.0.1:5173/m/home' 390 667 'out.png' `
  "JSON.stringify({a:document.querySelector('.deck-actions').getBoundingClientRect(),t:document.querySelector('.tabbar').getBoundingClientRect()})"
# 修复前：actions 607–651、tab 615–659、重叠 36px
```

**验收口径教训**：`scrollHeight == innerHeight` 不等于"装得下"。卡组是
`flex:0 0 auto`，矮屏不收缩时溢出会被 `overflow:hidden` 吃掉，按钮就沉到底栏下面。
以后一律加「元素矩形不相交 + 按钮中心 `elementFromPoint` 命中自身」两条断言。

## 14 审查整改批次 ②③④（2026-10-24 下午）

用户裁决：按 ①→④ 顺序一次改完再统一审查；房间先只对齐契约、划卡交互下轮；账本跟着整改更新。

### 14.1 批次 ② 房间状态机（F03/F04/F05/F11）

- 契约以 `MASTER_SPEC.md` 为准，四处偏离已改：`POST /rooms/create`（带 `budget`，返回 10 个候选）、6 位**数字**码、状态枚举 `WAITING|SWIPING|FINISHED`、未 join 的 WS 握手直接 **HTTP 403**。
- 三列新增（`backend/scripts/migrate_room_contract.py` 幂等迁移，实跑 `added_columns=[budget, deadline_at, settled_at]`、`status_migrated=12`）：
  - `deadline_at`：15 秒倒计时是**服务端**的时间事实，前端只拿 `deadline_at/remaining_ms` 显示，不各自倒数（F03/F05）。
  - `settled_at`：结算幂等标记——`_settle()` 见到它就返回 `None`，重复调用不会二次结算（F03）。
- `_settle_if_due()` 让 `GET /rooms/{code}` 具备**惰性结算**能力：即使所有人都断线、进程重启，只要过了 `deadline_at`，读一次就结清（F03）。
- WS 连上先发 `ROOM_STATE` 全量快照（成员、候选、`my_votes`、`deadline_at`、`remaining_ms`、赢家与报告），SWIPING 时补发 `START_SWIPING` 并重挂定时器（F05）。
- 投票三道闸（F04）：`FINISHED` 拒改票、非 `SWIPING` 拒投、`remaining_ms <= 0` 拒投。
- 最后一人断开不再取消定时器，而是 `hub.schedule_settle(code, remaining)`（F03）。
- 测试 11 条，含 `test_settlement_survives_all_disconnects`（`SWIPE_SECONDS=1`，断开后 `sleep(1.4)` 再 GET 必须 FINISHED）与 `test_snapshot_exposes_deadline_for_recovery`。

### 14.2 批次 ③ 首页可用性（F06/F10/F13）

- **F06**：卡组从 `flex: 0 0 auto; height: min(47vh,400px)` 改为 `flex: 1 1 auto; max-height: min(47vh,400px); min-height: 0`，矮屏先压卡面而不是把按钮顶到底栏下面。
- **F06 的验收方式也换了**：新增 `scripts/home-fit.mjs`，两条硬断言 —— `scrollHeight <= innerHeight + 1`（不滚动）**只是第一层**，还必须 ①操作行与 `.tabbar` 矩形不相交 ②两个 `.act` 按钮中心 `elementFromPoint` 命中自身。教训见 §13。
- **F10**：`_settle` 里写死的 `omega_group=0.5` 改为读 `AlgoConfig.default_production`（无配置回退 `DEFAULT_ALGO_PARAMS`）；沙盒滑块不再自己发请求，改为 `algo.reloadTick` + Home 侧 320ms 防抖 `loadBatch`，首页卡组与多人房吃同一份参数。
- **F13**：`SingleRecommendRequest.exclude_dish_ids` + `recommend_single(exclude_dish_ids=...)`，「换一批」把已看过的 24 个 id 排掉，不再重复请求同一批 Top 24。
- 三个门禁脚本（都可被 CI 直接调用，失败 `exit 1`）：`scripts/home-fit.mjs`、`scripts/sandbox-sync.mjs`、`scripts/refill-fresh.mjs`。

### 14.3 批次 ④ 数据边界（F07/F08/F09）

- **F07 身份口径翻转**：`backend/deps.py` 新增 `resolve_user_id(header, body)` —— **`X-User-Id` 请求头优先**，body 的 `user_id` 只在没有头部时回退，最后才回退 1。四处调用点（`recommend.py` / `eating_log.py` / `fridge.py` / `group_room.py`）全部改用它。
  - 副作用是 6 个测试失败——它们编码的是旧口径（body 压过 header）。已按新口径重写：`test_checkin_header_wins_over_body`（并补 body 回退用例 `test_checkin_body_user_id_used_only_without_header`）、`test_missing_user_returns_404`、`test_shopping_list_splits_owned_and_to_buy`、`test_room.py` 三处「第二个人」的 join 改成带 `X-User-Id: 2`。
- **F08**：`SingleRecommendRequest` 收 `limit 1..100` / `budget 0..2000` / `weather_temp -30..50` / `weather_text ≤32` / `max_distance_meters 0..100000` / `bubbles ≤12` / `exclude_dish_ids ≤500`；`CheckinRequest` 收 `dish_id ≥1` / `cost_amount 0..100000` / `weather_snapshot ≤64`；新增 `PARAM_BOUNDS` + `field_validator` 校验 `override_params`：未知键、非有限数、越界值一律 422。
- **F09**：`fridge._remaining_days()` 用 `created_at` 与当前时间的差把已过去的天数扣掉（`max(0, round(total - elapsed))`），库存不再「放三天还是 5 天后到期」。实跑：种子里「2 天」的牛肉现在返回 1 天。
- 测试新增 14 条（7 个越界入参 + 5 个坏 override + 1 个合法 override + 1 个负花费）。

### 14.4 矮屏卡片正文溢出（F06 的连带问题）

- 现象：390×667 下卡面被压到 261px，图区 40% 之后正文放不下，`footer` 被卡片圆角裁掉半行——`scrollHeight` 完全正常，肉眼却能看见「防腻权重 1.00」被切。
- 修法：`DishCard.vue` 末尾加 `@media (max-height: 720px)` —— 图区 40%→32%、菜名 19px、匹配度 24px、归因 `-webkit-line-clamp: 1`、footer 隐藏。
- **踩坑两次**：①媒体查询一开始写在 `<style>` 顶部，被后面的同名规则覆盖（同优先级后者胜），必须放到样式块末尾；②`scripts/home-fit.mjs` 的探针里用 `for (const el of ...)` 遮蔽了外层的 `el`，导致「按钮命中自身」永远为真——重写探针时把变量改名成 `hitEl` / `node`。
- 门禁新增第三条断言：卡片内所有可见元素的 `bottom` 不得超过卡面 `bottom`（`contentOverflow <= 0`），否则直接 FAIL。

### 14.5 卡面占屏比例

- 目标「结果占一半以上」：`.deck` 的 `max-height` 调到 `min(53vh, 440px)`、`.deck__top` 的下边距 `inset: 0 0 18px` → 393×852 实测卡面 **422px（50%）**；390×667 由 flex 压到 261px（39%），不再溢出。

### 14.6 本轮验证结果

- `cd backend; python -m pytest -q` → **106 passed in 5.65s**
- `cd frontend; npm run build` → `✓ built in 5.59s`
- `node scripts/home-fit.mjs` → 390×844 卡面 422px(50%) / 390×667 卡面 261px(39%)，两档 overlap 全 0、contentOverflow 全 0
- `node scripts/refill-fresh.mjs` → refill 排除 24 个、返回 24 个新候选
- `node scripts/sandbox-sync.mjs` → 拖 λ 触发第二次请求、批次仍 24
- 真实 API 复核：`limit=0` → 422、`X-User-Id: 999` → 404、`GET /fridge/1` 的牛肉 `expire_days=1`

## 15 真实点击复查：底部导航卸载异常（2026-10-24）

- 用户实测底部“足迹/我的”进不去；真实浏览器复现为 URL/title 已变化但 Home 留在页面，控制台 `ReferenceError: timer is not defined`，栈指向 `AlgoSandboxDrawer` 的 `beforeUnmount`。
- F10 重构时防抖已迁到 Home，抽屉删掉 `timer` 声明却残留 `clearTimeout(timer)`。即使从未打开沙盒，Home 卸载也会抛错阻断导航。本轮仅移除该失效调用，保留 body overflow 恢复；没有修改后端业务代码。
- 真实点击回归 7 项通过：Home→足迹、Home→我的、我的→冰箱、我的→房间入口、667 短屏沙盒关闭后→足迹→我的，以及换卡后继续导航。新增控制台 error 0。必须等待目标内容可见后判定，不能把 fade/AutoAnimate 的离场节点或数字中间态当成最终结果。
- 390×667 / 390×844：卡面 261 / 422px；操作行 bottom 607 / 784，底栏 top 615 / 792；重叠 0，两按钮中心均命中自身。沙盒 β=1 后抽屉和首页 Top5 同源，主卡稳定为 87.6%；已恢复默认。
- **上一轮整改还不能全关单**：临时库复现 F07 路径型偏好接口仍可 header=1 改 user=2；F08 偏好向量 999/预算 -100 仍 200 入库；F09 过期剩余天数显示已修，但鲜虾仍被采购清单视为已有、推荐仍使用原始库存天数。F10 群组 ω 的请求 override 与 DB config 仍非同一链路，未验收通过。
- 最新验证：后端 **106 passed, 73 warnings in 6.24s**；前端 **built in 8.59s**。真实库未用于非法输入/跨角色写入测试，临时库探针前后原库哈希一致。
- 证据与范围：`docs/review/recheck-2026-10-24/REPORT.md`、`browser-results.json`、`backend-recheck.json`、真实点击前后截图及验证日志。旧审查报告保留历史，不将“测试全过”写成“原 13 项全部修复”。

## 16 复核报告第二轮：F07 / F08 / F09 收口（2026-10-24 晚）

复核方指出上一轮只修了「表面对面」（body 身份、展示天数、单侧边界），写入口与消费端仍有洞。逐条补齐：

- **F07 路径身份**：`backend/deps.py` 新增 `raw_user_id`（区分「没带请求头」与「带了 1」）与 `ensure_self(path_user_id, header_user_id)`——不一致直接 **403**，detail 写明「请求头 X-User-Id=x，路径 user_id=y」。接到 `GET /users/{id}/profile`、`PUT /users/{id}/preferences`、`POST /users/{id}/red-black-list` 三个路径型接口。没带请求头时按演示约定放行（curl / 上屏脚本）。
- **F08 偏好边界**：`PreferenceUpdate` 收紧——`default_budget` `ge=8 le=500`；`base_vector` 只收 8 个 `GENE_KEYS`，值必须 **0~1**（存储口径就是 0~1，`normalize_vector` 用 `clamp01`，前端展示才 ×100），未知维度 / NaN / inf / 越界一律 422；`veto_tags` 上限 20 条、单条 ≤16 字、不许空白标签。
- **F09 消费端**：新建 `backend/algorithms/fridge_clock.py` 作为**唯一时效口径**（`remaining_days` / `is_expired` / `EXPIRING_SOON_DAYS=2`）；`routers/fridge.py` 删掉自己那份 `_remaining_days` 改引用它；`POST /fridge/shopping-list` 匹配「已有」时加 `and not is_expired(row)`；`algorithms/single_recommender._fridge_status_score` 跳过过期项、临期双倍权重改用同一 `remaining_days`。

教训（这一轮最重要的一条）：**「改了一半」比没改更危险**。F07 只堵 body、F09 只改展示，功能看起来都对，但写入口和消费端各留一个洞。以后号称修完一个「口径类」问题，必须同时回答三个问题：谁是唯一实现？所有写入口都过它吗？所有消费方都读它吗？

验证：新增 `backend/tests/test_identity_bounds_and_stock.py` 17 条（403 三类 + 不写他人偏好 + 边界 422 六类 + 过期不计「已有」/不加分 + 未过期仍计入），全量 **123 passed in 8.20s**；真实库只做只读与「插入→验证→删除」的受控探针，前后行数一致。

**F10 仍未验收**：请求里的 `override_params.omega_group` 与 DB `algo_configs.omega_group` 还没合并到同一条链路，等下一轮。

## 17. 批次 4 准入清账（2026-10-24，R02 / R01 / F12）

依据用户下发的 `BATCH4_PRE_CLEARANCE.md`，顺序 R02 → R01 → F12 一次做完。证据包在 `docs/review/clearance/`，**开发方不自签 PASS**。

### 17.1 R02：benchmark_json 改成真跑仿真

> **本节为开发方提交时的自报记录，已被 §18 独立审查否定关键验收结论。** 下面的 40,000 票与“混合策略换取收益”不可作为已证实事实；仿真与生产算法不同、三组场景不配对，当前曲线不得用于生产算法效果论证。

- 脚本 `backend/algorithms/simulate_personas.py`：200 personas × 60 天 × 2 餐 = 24,000 条流水；1,000 房间 × 4 人 × 10 张卡 = 40,000 票。
- 落库结构严格按 SSOT 四键：`generated_at / sample / duplication_rate_curve / group_satisfaction_bars`。参数（seed、λ、ω、权重、note）**只写存档 JSON**，不进库——多一个键就是契约漂移。
- 重样率口径：**「与上一餐同菜系」**，不是「该菜系今天出现过」。第一版写成后者，加上当天 gap=0 不衰减，跑出 ours == baseline == 0.5 的假结果。这条口径必须写进论文。
- 抽样：`score**3` 加权随机（温度过高会退化成纯贪心，曲线会被压平）。
- 结果（seed 20261024，λ=0.5，ω=0.5）：ours d14 `0.1696` vs baseline d14 `0.2441`；满意度 `[85.92, 86.37, 73.40]`、Least Misery `[77.07, 75.85, 57.15]`——混合策略以 −0.45 平均分换 +1.22 最差分。

### 17.2 R01：下厨推荐 N+1

- 新增 `_fridge_index(db, user_id)`：**一次**查出该用户全部库存并预计算权重（过期跳过、临期 2.0），循环内只做纯内存 `_fridge_status_from_index()`。
- 基准（同一条命令 `measure_recommend_sql.py`，limit 40，user 2）：`HOME_COOKING` **37 → 6 条 SQL**（`fridge_inventory` 32 → 1），top3 与返回条数完全一致；`OUT_DINING` 6 → 6（本来就不查库存）。
- 回归：`backend/tests/test_query_budget.py` 三条（库存查询 ≤1 且总语句 ≤10 / 批量实现与逐菜实现等价 / 外食不查库存）。

### 17.3 F12：颜色只有一个出口

> **“157→0”仅为原脚本有限扫描范围内结果，不能代表全系统清零。** §18 实测还有 CSS 业务声明与门禁漏检；整目录白名单不可继续当作合格依据。

- `frontend/src/styles/main.css` 加 RGB 通道令牌（`--rgb-white/black/ink/steel/mist/silver/grain-a/grain-c/chrome/chrome-max/panel/sheet`）与 `--color-black/panel/sheet`。
- 机械搬移用 `scripts/normalize_colors.py`（`--write` 才写盘），令牌出口白名单：`styles/`、`utils/theme.js`、`components/bits/`（Vue Bits 是上游原件，不算违规）。
- 门禁 `scripts/check-colors.mjs`：禁裸 `#hex` / 数字 `rgb()` / `hsl()`，放行 `rgb(var(--rgb-x) / a)`。
- 结果：**157 处 / 21 文件 → 0**；`Home.vue` 的暖色 `.toast--warn` 改为反白底 + ink 字（靠明度反差，不引入色相）。
- 两个必须记住的坑：
  1. **ECharts 不解析 CSS 变量**。`itemStyle.borderColor: 'rgb(var(--rgb-ink) / .55)'` 在 canvas 上是非法颜色，必须走 `alpha(tokens().ink, .55)`。
  2. **`@media` 块的位置会影响优先级**。同优先级下后写的规则胜出，媒体查询写在样式块顶部时会被后面的基础规则覆盖——矮屏适配那次就是这么失效的。
- 门禁正则必须是 `rgb\((?!\s*var\()` ：第一次写成 `rgb\(` 会把 `rgb(var(--rgb-white) / .06)` 误报 117 处——「令牌 + 透明度」是正确写法。

### 17.4 门禁清单（改完必跑）

```powershell
python -m pytest -q          # 128 passed
cd frontend; npm run build   # ✓ built
node scripts/check-colors.mjs    # 颜色出口
node scripts/home-fit.mjs        # 一屏不滚动 + 按钮命中自身
node scripts/refill-fresh.mjs    # 换一批给新候选
node scripts/sandbox-sync.mjs    # 沙盒与卡组同源
```

### 17.5 验收包与"不自签"

- 正式证据包按 `REVIEW_RULES.md` §5 落在 `docs/review/stages/PC0x/r01/`，`docs/review/clearance/` 只作过程留痕。
- 台账 `STAGE_STATUS.md` 只记"已提交待审"，**PASS 只由 Codex 签**；开发方不写 `REVIEW.md`。

## 18 三项准入独立审查 r01（2026-10-24）

- 审查结果：**PC01/R02 FAIL、PC02/R01 FAIL、PC03/F12 FAIL**；台账改 CHANGES_REQUIRED，S09 不开放。完整证据与下一轮验收标准在 `docs/review/clearance-codex-2026-10-24/REPORT.md`，三份 `stages/PC0x/r01/REVIEW.md` 已签发。
- **CLR-01/02/03（P1）**：仿真生产算法调用为 0；四维与自写预算/天气/衰减替代真实算法；未生成合法群组投票/真实共识，外食和下厨混抽；三策略使用不同房间输入。昨天同菜的衰减生产 0.3935、仿真 0.2980088529；两个相同 ω=1 策略因重新抽样也有不同结果。不能凭会出数、可复现、写库一致就称算法验收通过。
- 独立三轮仿真确有每臂 24,000 内存餐次，复算曲线与写库一致；原 CLI exit 0。默认脚本丢弃餐次明细，库中没有新房间/投票；“40,000 张票已产出”的自报不成立。现有数值只描述未通过的简化模型。
- **R01 业务优化有效**：真实 API 40/400 候选均 6 SELECT / 1 库存，独立逐菜对照 36/315 SELECT，API 响应相等；普通/临期/过期独立期望通过。400 候选为隔离库结构探针，不计入正式数据规模。开发方 `--legacy` 仍保留一次预取，多算一次查询，不能等同真实旧版。
- **CLR-04（P2）**：`test_query_budget.py` 直接连全局库而不使用 fixture；全新隔离库 3 failed。等价测试两次调用同一实现，不能独立防回归；`<=10` 也不符合个位数要求。应修测试，不重做已有效优化。
- **CLR-05（P2）**：原颜色门禁仍 exit 0；PostCSS 排除自定义属性定义后找到 10 个业务 CSS 声明裸色。新 CSS、styles 下 JS、bits 下非上游 Vue、普通 Vue 的大写 RGB 均实测漏拦，普通 hex/rgb 反例能拦。违规样例已移除。
- 本轮新鲜执行：隔离预置库下后端 **128 passed, 133 warnings in 7.40s**；前端 **built in 9.45s**；不能据此忽略上述缺陷。业务源码 123 文件审查前后哈希一致。
- 真实浏览器：5174→8011→隔离库；两档首页、外食/下厨布局量测成立；“足迹/我的”真实导航成功，打开沙盒后再导航亦成功；角色切换、冰箱添加与房间入口测试；λ=2 后回传标签及 Top5 与首页同步。Room 划卡、完整耗尽换批、大屏/APK 不在本次已验收范围。
- 浏览器末轮因自动审批服务 **403 / Insufficient balance** 未执行，非安全性拒绝；667 确认按钮最后复测、最终 console 导出、tab 4 关闭及 viewport reset 未完成，最后 390×667。不得把本轮记成完整 UI 总验收，也不得绕过审批补做。
- 演示库只读逻辑摘要前后一致，journal_mode=delete，SHA-256 为 `3a7fa3f4487c29f3e1f43c09014c1d7a8f4f6261e1ad0dddc06c408cdf5e092f`。本轮测试只写隔离库，没有清空/恢复/修改用户演示库。

## 18. 第二轮返工（CLR-01～CLR-05，2026-10-24）

Codex 对 r01 三包判 FAIL 后，按 `D:\谷歌\BATCH4_REWORK_ROUND2.md` 整改，三项交 r02。包在 `docs/review/stages/PC0x/r02/`，**未签 PASS**。

### 18.1 R02：仿真必须调生产算法（CLR-01/02/03）

- **根因**：第一版 `simulate_personas.py` 自写四维余弦、衰减与满意度，对 `recommend_single / compute_decay_weights / shortlist_candidates / compute_group_consensus` 的调用次数是 **0**。隔离库实测同一场景：线上衰减 `0.3935`，仿真 `0.2980088529`——差在「同菜是否叠加 similar 惩罚」和「14 天窗口」，这类偏差靠肉眼永远发现不了。
- **改法**：只加最小适配层（`recommend_single(..., now=None)` 透传给 `compute_decay_weights`），其余全部走真函数。调用计数用模块级 `CALLS` / `CALL_SITES` 记，写进存档 JSON 的 `params`（不写库，避免契约漂移）。
- **基线组不是另一套算法**：同一函数、同一份数据，只把查询时钟推到 `eaten_at + 15 天`，14 天窗口内无历史 → 权重全 1.0。这是"新用户冷启动"的真实语义。
- **投票必须落库**：1000 场 × 4 人 × 10 卡，`planned_votes 40000 / votes 37999`（5% 主动超时按 TIMEOUT 计），`sim_seed<seed>_groups.db` 可查；演示库 `group_rooms` 保持 0。
- **三策略同场景**：同一房间同一成员、同一 `candidate_dish_ids`、同一票矩阵；mixed 用 `ω=omega_val`、average 用 `ω=1.0`、random 用**独立随机流** `Random(seed+1)`。上一版三策略各自重抽样本，差异来自样本不是权重——那样的数字不能做因果结论。
- **票型模型**：绝对阈值（`prior/100 + gauss(0,0.12)`）会让 88% 落在 LIKE 以上，三策略被天花板压成同一个数（`avg [99.93, 99.95, 96.6]`）。改成 rank-based：先验扰动后在这 10 张里排序，前 2 SUPER_LIKE / 3–5 LIKE / 6–8 PASS / 9–10 各 50% VETO。理由：真人面对 10 张卡就是横向比较。
- **满意度封顶到 100**：生产侧 `0.4*prior + 0.6*SUPER_LIKE(120)` 最大 112，按 `total_score` 同一「展示封顶」口径取 `min(100, …)`，**没有改 SUPER_LIKE 权重**。
- **快照刷新纪律**：`init_seed_data --force` 读的是 `backend/scripts/benchmark_snapshot.json`。仿真重跑后**必须先刷新这个快照**再播种，否则库里的曲线会被旧快照覆盖（本轮真踩过，靠 `04_db_benchmark_check.log` 抓到）。
- 结果：`ours d14 0.0091` vs `base d14 0.2927`；`avg [93.81, 94.12, 81.13]`、`least [74.68, 73.47, 61.76]`（mixed 用 −0.31 平均分换 **+1.21** 最差分）。

### 18.2 R01：实现不动，只改测试（CLR-04）

- **根因**：测试直接 import 全局 `SessionLocal/engine`，`DATABASE_URL` 指向新库时三条全 `no such table`；等价测试把同一个函数调两遍比第一道菜——自己跟自己比。
- **改法**：全部走 `conftest.py` 的 `session_factory` fixture，SQL 监听绑该 fixture 的 engine；新增**独立参考实现** `_reference_fridge_status()`（逐菜、只用 `ingredients_main`）；等价测试用 monkeypatch 把批量函数换成"每道菜单查一次"的旧写法，比完整 top-40 的 `(dish_id, total_score)`。
- 数字：`HOME_COOKING 37 → 6`（库存 `32 → 1`），`top3` 与条数完全一致；`OUT_DINING 6 → 6`。断言收紧到 `总 ≤9 / 库存 ≤1`。
- 干净库跑法：`$env:DATABASE_URL='sqlite:///D:/EatWhat/backend/tmp-clean-r02.db'` → `6 passed`，且跑完该文件未生成。

### 18.3 F12：门禁的漏检比残留更严重（CLR-05）

- **根因**：门禁只看 `.vue/.js`，整目录豁免 `styles/` 与 `components/bits/`，正则还不认大小写。于是 `src/styles/*.css` 里 10 处直接写色全部漏过。
- **改法**：扫 `.vue/.js/.css`；`rbga?`/`hsla?` 加 `i`；白名单改成**精确文件**（三个上游 bits 文件 + `utils/theme.js`）；只允许「令牌声明行 / 跨多行声明体 / 注释」例外。
- **10 处归并**：新增玻璃调色板通道令牌 `--rgb-glass-fill/-shade/-highlight/-edge/-ring`，把 `main.css` 7 处、`glass-card.css:117`、`glass-tokens.css:36,39` 改成 `rgb(var(--rgb-…) / a)`。**只改"怎么写"，不改"写多少"**——已锁定的玻璃数值逐项保留。
- 反例必须能拦：临时 CSS 写 `#ff0000`/`RGB(...)`/`hsla(...)` → exit 1；在 `components/bits/` 放非上游业务文件写 `#00ff00` → 也被拦（证明不再整目录豁免）。

### 18.4 教训

1. **"调了生产代码"要用计数证明**，不是靠读代码相信。`CALLS` 计数器是这类争议的唯一硬证据。
2. **对照实验的两组必须真的不同**：同一函数跑两遍、或两轮各自重抽样本，得到的差异不能归因。
3. **门禁的价值在拦截率，不在绿灯**：只报"0 处违规"没用，必须同时给出"塞一处违规会被拦"的证据。
4. **凡是"播种/初始化读某个中间文件"的链路，就有一个静默回退点**：改了上游产出却忘了刷新中间文件，库里的数据会安静地回到旧值。

## 19. 清账第二轮 r02 独立复审（2026-10-24）

本节覆盖§18.1～18.4中开发方自报的“待复审”状态，不覆盖或删除历史证据。报告：`docs/review/clearance-codex-r02-2026-10-24/REPORT.md`；各r02包新增Codex签署的`REVIEW.md`。

- **许可**：PC01/R02 FAIL，PC02/R01 PASS（只绑定本次manifest），PC03/F12 FAIL。S09与批次4仍LOCKED；`/admin`未操作。下一轮失败项交r03，不覆盖r01/r02。
- **R02已核实**：完整200人×60天×2餐、两臂各24000真实流水独立重跑；seed7/λ.8独立覆盖全部14点与1000房间；两seed原库全60天只读复算。生产推荐48000、衰减48000、shortlist1000、prior3000、consensus2000，脚本外层计数合计52000，旧“51000”自报错误。1000对同场景输入哈希全相同；新曲线.0091/.2927可复现，存档/快照/演示库一致。
- **R2-01/P2未闭环**：`init_seed_data.py:249–268,469–471`没有刷新保障；同SHA副本在隔离库把较新benchmark覆盖成旧快照，exit0。§18“先刷新快照纪律”只约束人，没有锁进代码。必须在破坏旧库前刷新/验证并保证失败中止。
- **R2-02/P1新增**：random从全cards抽到VETO菜后，消费共识内部排除了否决者的mean/least。默认331/1000房受影响，81.13/61.76不是全四人成员指标；纳入0分成员的独立诊断值73.43/40.37。先统一可行集合与全成员指标，再重跑柱图，不能只手改数据。
- **R2-03/P2**：37999是真实票，但40000只是计划格数；2001格TIMEOUT缺席并未落成票，不满足SSOT40000+真实投票。主规模补完整合法40000票，5%超时场景另列；不造TIMEOUT枚举，不污染演示库。
- **方法判断**：时钟+15天与只关闭衰减的16个固定历史完整响应相同，当前是可接受的无历史衰减基线；不是无用户画像的完整冷启动。排名票型可作透明合成假设，不得声称真人必然遵守；新旧.1696→.0091来自不同模型/行为假设，不是同实验的算法提升，群组票型不影响单人曲线。
- **R01/CLR-04关闭**：不存在全局库条件6 passed且文件未生成；真实API40/400目录均6 SELECT/库存1，独立逐菜完整响应相等。原优化只增加R02时钟适配，反向去适配后精确匹配r01源码SHA。legacy确有逐菜查询但多保留一次预取，37/32是工具口径；独立逐菜40目录实测36/31。正式扩容仍需S11复验。
- **F12部分修复成立**：原10条业务CSS残留清零，五玻璃通道新增正确，10/10声明展开后数值不变；原脚本34文件绿、普通大写/RGB/HSLA/非上游bits反例能拦。
- **R2-04/05/P2未闭环**：门禁整行跳过通配选择器、注释后业务、令牌后业务；任意组件`--local-red:#ff0000`也放行。独立13探针4个违规错exit0。要识别语法范围并限定合法主题定义位置；禁止重新扩大目录白名单。
- **实际回归**：后端131 passed；前端build exit0（775模块、6.69s）。存在requests依赖提示、utcnow弃用与pytest缓存权限警告，均保留日志，不当作核心验证失败。原报告落盘时未获浏览器余额确认，故当时未执行；用户随后明确确认，已按下一条补验，不再记为当前未验证。F12仍由实测漏检判FAIL，新版本修后仍需对应回归。
- **浏览器补验（20:36–20:54）**：新增`clearance-codex-r02-2026-10-24/browser-supplement/REPORT.md`。独立库8022、前端5182；390×844/667足迹/我的真实点击正常、无页面滚动，顶卡50.0%/39.1%，操作行与底栏间隔8px，外食两屏6/6中心命中。冰箱列表/返回、房间入口、角色切换、下厨决策、换卡、五维/沙盒开关正常；确认洋葱炒蛋7元后user2足迹2次/31元→3次/38元，隔离日志9→10。123响应全200，0请求失败/未捕获异常/console error，保留5条ECharts alignTicks刻度warning。未做多人WS/完整划卡、APK或/admin。viewport reset、tab5关闭、自有服务停止/端口关闭；源码与演示库摘要不变。本范围PASS不关闭R2-01～05，不替S05/S07/S08签完整PASS，S09/批次4继续LOCKED。
- **保护**：审查未改业务源码；演示库只读逻辑摘要前后相同，房间/票仍0，完整证据在`final-protection.json`。

## §19 第三轮返工 r03（R2-01～R2-05，2026-10-24）

### 19.1 R2-02 四人满意度口径

`simulate_personas._four_member_metrics(report, dish_id)` 遍历 `report["dishes"][i]["members"]`
逐个取 `satisfaction`，**VETO 成员的 0 分照常进入均值与最低值**，不做过滤。

原因：`group_recommender.compute_group_consensus` 内部把 VETO 记 `satisfaction=0` 但不放进
`satisfaction_values`（那是"参与打分的人"的集合），仿真若直接拿报告的
`mean_satisfaction/least_misery` 当四人值，random 策略抽到被否决菜时就会虚高。
审查给出的可复现差异：房间 000001 抽 dish 52，四人 `[0, 67.58, 97.82, 107.70]`，
报告 91.03/67.58，正确应为 **约 68.275 / 0**。

固定样本测试在 `backend/tests/test_simulation_metrics.py`（无否决 / 单人否决 / 多人否决 /
全否决 / 缺席 五类），期望值由测试按 `0.4*prior + 0.6*swipe`（VETO=0、缺席=TIMEOUT 60）
独立重算，不复用被测函数。

**r04 修正（R3-03）**：r03 曾在个体层面先 `min(100, R)` 再聚合，得到 66.35/0；这不是
r02 的口径。r04 恢复为「个体 R 保留原始值，四人聚合后再 `min(100, ·)`」，
固定样本 `[0, 67.58, 97.82, 107.70]` 为 **68.28/0**。新增含 R>100 的两条固定样本，
把“原始 R vs 展示统计”的边界钉死。

### 19.2 R2-03 满票与缺席另列

主规模 `TIMEOUT_RATE = 0.0`，必须产出 1,000×4×10 = **40,000 张真实合法票**；
每房用 `{(user_id, dish_id)}` 去重后校验条数，记 `rooms_full_votes` / `bad_rooms`。
超时缺席作为**独立实验** `run_absence_experiment(...)`（`ABSENCE_RATE = 0.05`，200 房），
落独立库 `sim_seed<seed>_absence.db` 与 `absence_seed<seed>.json`，
摘要只进 `params.absence`，**不写进 SSOT 的四键结构**。

### 19.3 R2-01 播种守卫

`backend/scripts/init_seed_data.py` 的根因是模块导入时就把快照读进 `BENCHMARK_JSON`，
`--force` 直接清表 → 旧快照可以覆盖较新的库内曲线。r03 已有守卫，但只判
`generated_at` 非空并用字符串比较。**r04（R3-01）**补全为：

1. `generated_at` 用 `datetime.fromisoformat` 真正解析；无时区按运行环境本地时区解释，
   带 `Z`/偏移的归一到 UTC 后比较，禁止字典序；
2. `sample` 五个字段必须是正整数（bool 拒绝），`curve.days` 必须是 `1..14` 连续整数，
   两条曲线 14 个有限数值且落在 `0~1`，策略身份/长度、柱值 `0~100` 全部校验；
   JSON 的 `NaN`/`Infinity` 与重复键直接拒绝；
3. incoming 与当前快照、库内时间的**所有检查通过之后**才写目标快照；拒绝路径
   数据库与快照都不变（r03 的“先覆盖再报错”已消除）；
4. `--benchmark-from` 接受完整仿真输出（四键 + `params`），落盘仍只保留四键；
   新增 `--snapshot` 便于隔离复验；`--allow-stale-benchmark` 只跳过库内新旧比较，
   不跳过结构/时间校验。
5. 反例：`backend/tests/test_seed_guard.py` 23 条；真实 CLI 证据在
   `docs/review/stages/PC01/r04/data/seed-results.json`（9 例）。

### 19.4 R2-04/R2-05 门禁词法化

`scripts/check-colors.mjs` 不再"整行跳过"：

- r04（R3-02）按语言分别剔除注释：`maskJsComments()` 识别字符串/模板字符串/正则字面量
  与行块注释，`maskCssComments()` 识别字符串与 `url(...)`，`maskHtmlComments()` 只吃
  `<!-- -->`，`maskVue()` 把 `<script>`/`<style>` 分段交给前两者。r03 的共用状态机把
  `/[/*]/` 当块注释、把 `url(https://…//…)` 当行注释，已修复。
- 注释替换成等长空格，行列不变；注释之后的同行业务代码照查。
- `maskTokenDeclarations()` **只对主题出口文件**（`styles/{main,glass-card,glass-tokens}.css`）涂掉 `--x: <value>;`。
- 非主题出口文件里出现「带裸色的自定义属性」记 `token-literal` 违规——这是 R2-05 的绕过点：组件自己定 `--local-red:#f00` 再 `var()` 用。
- `UPSTREAM` 是精确的三个 Vue Bits 文件，不是整个 `components/bits/` 目录。
- 探针：`scripts/gate_probes.py` 在隔离 sandbox 跑 24 例；证据在
  `docs/review/stages/PC03/r04/`。

### 19.5 教训：数字变了要先问"是不是口径也跟着变了"

r03 的这段解释有实质性错误，r04 已更正：

- r03 mixed 92.0/75.37 与 r02 random 73.43/40.37 **不是同一策略**，不能拿来解释修复前后差异。
- r03 同时改了满票（R2-03）与逐人封顶（额外的口径变化），不能把差值归因给其中一项；
  mixed 在同一新口径下反而升高，更不能写“两项都让满意度下移”。
- VETO 概率仍是 0.5；4,093 是**数量**，不是概率上升。取消缺席抽样还会改变后续 RNG 消费。
- 只允许同策略、同口径对照。r04 恢复聚合后封顶，固定样本 `[0,67.58,97.82,107.70]`
  锁定 **68.28/0**；r03 逐人封顶的 **66.35/0** 是被退回的旧口径。

### 19.6 取证教训：长任务先接管道，再点击运行

主规模仿真（200 人设 × 60 天 × 1,000 房）跑了十几分钟，但 stdout 没有重定向到证据目录，
只能事后补跑；而补跑会**覆盖按 seed 命名的同名明细文件**（`detail_seed<seed>.jsonl`），
把已经归档好的 48,000 行冲成几千行。恢复办法是从证据包里已经拷走的那份 11.2 MB 明细复制回来。

两条纪律：
1. 任何超过一分钟的任务，**先**把 stdout/stderr 重定向到 `docs/review/stages/<包>/logs/`，再启动。
2. 明细文件名里带上 run 标识（时间戳或 `--out` 前缀），不要让两次运行抢同一个路径。

r04 起 `simulate_personas` 支持 `--data-dir`：隔离库、明细、缺席文件都落到指定目录，
benchmark JSON 默认也跟随该目录。复验一律指向新目录，不再覆盖 `docs/review/simulation/`
里的历史证据。

## 20. Codex r03 独立复审（2026-10-24，覆盖 §19 中未经核验的结论）

独立报告：`docs/review/clearance-codex-r03-2026-10-24/REPORT.md`。PC01 FAIL / PC02维持PASS / PC03 FAIL；S09、批次4继续LOCKED，不碰 `/admin`。本节由审查方追加，不抹去开发方历史自报；受审账本原文另存该目录 `AGENT_MEMORY-before-review.md`。

- **R2-01未关闭 / R3-01 P2**：普通旧快照阻断成立，但 `generated_at` 只判非空且用字符串比较；真实隔离CLI证明非法日期、跨时区更旧日期、非法样本/曲线仍会exit0并清库重播。incoming还会在库内比较失败前先替换快照。须解析/归一化日期、补齐类型/范围/日序与策略校验，所有检查先于持久化；拒绝必须同时保留DB与快照。正常含params的仿真输出也需明确四键提取导入流程。
- **VETO零分修复成立，但§19.1/19.5须更正 / R3-03 P2**：r03新增逐人先封顶再聚合，不等于r02聚合后封顶。四人 `[0,67.58,97.82,107.70]` 当前helper为 **66.35/0**，原始四人均值才是68.275/0。r03 mixed92.0/75.37不能与r02 random73.43/40.37作同策略比较。须与SSOT明确原始R/展示统计边界，并以含R>100样本锁口径。
- 同一r02原票重算random：聚合后封顶73.43/40.37，逐人封顶72.08/40.37；r03新票逐人封顶71.39/38.82。mixed在同新口径下r02=91.58/74.68、r03=92.0/75.37，实际升高。VETO概率仍0.5，4,093是数量而非概率提高；取消缺席抽样还改变后续RNG消费，不能继续写“两个改动都使满意度下移”。
- **R2-03 PASS**：两seed独立完整重跑均1,000房/40,000唯一合法真票；缺席200房另库另params。每组recommend_single48,000次、decay48,000次、shortlist1,200次、prior含内部3,600次、consensus2,400次；1,200对输入哈希一致。曲线/柱值/主群组与缺席摘要全部复现。
- 默认归档48,000行明细与独立生成文件逐字节SHA一致，原空stdout由新独立全量日志补证。但原 `docs/review/simulation/sim_seed20261024_ours.db` 仍仅8,000行/20天，不能标为完整60天原库；新审查输出两臂各24,000行/60天，须标清证据身份而非覆盖旧包。
- **R2-04未关闭 / R3-02 P2；R2-05 PASS**：22独立探针19符合；合法JS `/[/*]/`会被当块注释，合法CSS `url(https://example.com//a.png)`会被当行注释，均可隐藏后续裸色并exit0。语法已独立验证。HTML注释另有误报。组件自造裸色token旧洞已堵，精确文件白名单成立。真实38文件与原10处/五玻璃令牌检查通过，不能混淆“门禁仍可绕过”和“当前业务已出现裸色”。
- 全回归140 passed（工作区basetemp/cache），R01干净环境6 passed且不存在的DATABASE_URL文件未生成，build7.04s。首次4个tmp_path权限错误原日志保留。R01共享实现/时钟/fixture未变，保留r02 PASS。
- 新鲜真实浏览器：隔离库/8023/5183；390×844卡422px、390×667卡261px，无页面滚动，操作行与Tab相隔8px、6中心命中；足迹/我的能进，沙盒开关及卸载后导航、下厨切换成立。两次输入工具超时后以可见DOM确认结果；CDP网络缓冲截断，不宣称全程网络零异常。控制台读取为空，后端观察到API均200。截图/动作证据在新报告目录，未补验完整多人WS或S08。
- 审查不改业务代码，演示库逻辑SHA保持 `4bf4233faa8bdf42c0257c0f67a6d307e86256511ae1a1cb42bbd12a5d8eea27`，group_rooms/room_votes仍0。仅准当前清账返工，下一轮提交r04由Codex独立复审，不自行签PASS。

## 21. r04 整改（R3-01 / R3-02 / R3-03，2026-10-24）

提交包：`docs/review/stages/PC01/r04/`、`docs/review/stages/PC03/r04/`。开发方未签 PASS，
等待 Codex 独立复审；S09 与批次 4 仍 LOCKED。

### 21.1 R3-01 播种守卫

- `generated_at` 真正解析并归一化到 UTC；无时区按本地时区解释。非法时间、跨时区旧时间、
  非法 sample/curve/策略/柱值、bool 冒充整数、NaN/Infinity/重复键全部拒绝。
- incoming 与当前快照、库内时间的全部检查通过后才写 tmp；tmp 回读校验通过后才替换目标，
  拒绝路径数据库与快照都不变。`--benchmark-from` 接受完整仿真输出（四键 + params），
  落盘仍只存四键；`--snapshot` 供隔离复验；`--allow-stale-benchmark` 只跳过库内新旧比较。
- 23 条单测 + 9 个真实 CLI 用例：`backend/tests/test_seed_guard.py`、
  `PC01/r04/data/seed-results.json`。

### 21.2 R3-03 指标口径

- 恢复「个体 R 原始值、四人聚合后 `min(100, ·)`」；VETO=0、缺席 TIMEOUT=60 都进分母。
  r03 的逐人封顶已撤销。
- 固定样本 `[0,67.58,97.82,107.70]` → **68.28/0**；逐人封顶为 66.35/0（被退回）。
  五类样本的 `no_veto` 从 76.57 → 79.45，也是同一原因。
- 两组全量重跑（seed 20261024 / seed 7）与归档 40,000 票复算逐点一致：
  - seed20261024：avg `[94.23, 94.49, 72.83]`，least `[75.37, 74.77, 38.82]`；
  - seed7：avg `[93.94, 94.06, 72.57]`，least `[73.62, 73.02, 38.46]`。
- 同策略同口径：r02 原票 aggregate cap random 73.43/40.37、mixed 93.81/74.68；
  r04 满票 aggregate cap random 72.83/38.82、mixed 94.23/75.37。random 略降、mixed 升高，
  不能写“两项都下移”；VETO 概率仍 0.5，4,093 是数量。
- 证据：`PC01/r04/data/fixed_samples.json`、`bars_recomputed.json`、
  `benchmark_seed20261024.json`、`benchmark_seed7.json`、`db_benchmark_check.json`。

### 21.3 R3-02 颜色门禁

- `check-colors.mjs` 按语言剔除注释：JS 正则/字符串/模板字符串、CSS `url(...)`/字符串、
  HTML `<!-- -->`、Vue SFC 分段。`/[/*]/` 与 `url(https://…//…)` 不再吞掉后续裸色。
- 23 个隔离 sandbox 探针 + 基线全 PASS；真实目录 38 文件 exit 0；build 通过。
- 证据：`PC03/r04/logs/gate_probes.json`、`20_check_colors_real.log`、`20_build.log`。

### 21.4 证据身份

- `docs/review/simulation/sim_seed20261024_ours.db` 是 8,000 行/20 天的截断旧库，
  在 `PC01/r04/data/db_inventory.json` 标为 `truncated/deprecated`；不覆盖、不删除。
- r04 新目录两臂各 24,000 行/60 天；演示库 reseed 后 benchmark 与快照/存档四键逐点一致，
  `group_rooms=0`、`room_votes=0`。

## 22. S09/r02 契约修订（2026-10-24/25，待 Codex 独立复审）

用户已确认批次 4 的数据/统计/实验口径，SSOT 已升到 **v2.3.3**。r01 保留，不覆盖；r02 在 `docs/review/stages/S09/r02/`，开发方未签 PASS。

### 22.1 已确认并写入 SSOT

- **中心点**：西安思源学院主校区；高德地名搜索实际返回 GCJ-02 `109.078487,34.234818`（2026-10-25T00:24:28+08:00）；固定 3km。
- **真实 POI**：`types=050000` 直接 count=600，网格去重后 **605**（扣除 2 个非餐饮）；原目标约 1500+ 未达成。**D03 已裁决接受 605 为样本 A**（建大 6,659 为样本 B），不再要求补足；禁止合成补足、建大补思源或跨校区混算。
- **合成食堂**：200 个，`source_type=CANTEEN`、`is_synthetic=1`、`source_dataset=synthetic_canteen_v1`，不计入真实 POI；605+200=805，不是 1700。
- **合成菜谱**：6,300–8,000 行目标，`is_synthetic=1`；行数与唯一菜名数分别报告；不得重复行凑数。
- **特征值**：`8 × 成功打标菜品数`；不再固定 60,000+；要写 60,000+，成功数须 ≥7,500。
- **stats**：13 个（含 quality）；SSOT 旧计数已改 13；不删 quality。
- **schema**：新增字段全部可空；`allergen_tags`、`deleted_at` 软删除、`source_dataset/source_record_id/source_url/data_version`、`tagging_status/tagging_error/llm_meta`、`is_synthetic`；`feature_vector` 可空表示未完成。旧字段语义不变。
- **大屏**：C08 Top10 由 logs+votes 聚合、VETO 不计；C10 为 restaurants+dishes 全量，HOME_COOKING 无真实 rating → `rating=NULL`，评分轴只绘非空并报 `meta.not_plotted_no_rating`（整数），**不返回 `applicable=false`**；C11 桑基单位=票；C13=allergen_tags+菜名分词；C17 分母=snapshot dishes 总数、分子=完整成功 8 维。
- **默认口径**：N/A 统一 `200 {applicable:false, reason, items:[], meta:{}}`；random R=30；重复率=相邻同菜系/累计餐次；7×4 时段、Asia/Shanghai、全库；共现≥3、top_n=30/上限100、过滤通用调味；C07 dishes 行数、C12 logs 决策量；overview 返回 `meta.scope`；`distance_meters`=直线距离。
- **仿真数据**：写独立统计库，不写演示库；S09 不实现。

### 22.2 证据与保护

- 高德 Key 只在命令环境变量中注入；证据 `data/amap_geocode.json`、`data/amap_collection.json`、`data/amap_pois.jsonl`、`data/amap_pagination_probe.json` 均不含 Key；`amap_collect.py` 从 `AMAP_API_KEY` 读取。
- 真实 POI 与合成食堂分列：`real_poi_count=605`、`synthetic_canteen_count=200`、`total=805`；`data/canteen_plan.json` 明确 `PLAN_ONLY_NOT_IMPORTED`。
- 演示库保持 4 用户/20 门店/100 菜/9 日志、`group_rooms=0`、`room_votes=0`；S09 只读。
- 仍阻塞：LLM Key/模型/预算（S11）、Android SDK/adb/Gradle/Capacitor/真机（S18）；图片仅本地演示，不公开发布；真实 POI 目标差额需用户裁决。

## 23. v2.3.4 双校区与口径纠错（2026-10-25，文档同步）

本轮**只同步文档**，不改代码/数据库/`/admin`，不签 PASS，不开 S10。SSOT 升到 v2.3.4，v2.3.3 历史数字保留不改写。

- **校区 A 思源**：中心 GCJ-02 `109.078487,34.234818`；3km；真实餐饮 POI **605**（直接 count 600、网格去重 605），合成食堂 **200**，合计 **805**；不是 1700。
- **校区 B 建大雁塔**：中心 `108.967153,34.236991`；真实餐饮 POI **6,659**（3km/050000/递归网格/去重，0 未完成），合成食堂 200 单列，合计 **6,859**；未返回草堂。
- **口径纠错**：`1700` 是原规格总数目标（约 1500+ 真实门店 + 200 食堂窗口），不是实际数；`17` 只是大屏图数量；“2km 内不足 1700 再扩 3km”规则作废。
- **双校区数据**：`restaurants.campus`、`group_rooms.campus` 新增可空字段；外食推荐/群组外食按校区过滤，跨校区不能拼桌；下厨菜谱共享，不按校区复制；前端校区切换后推荐/POI/统计同步，默认思源。
- **统计**：13 个（含 quality）；`overview` 返回 `by_campus` + `total`；适用 stats 加 `campus`；固定 C05/C06/C09 为 `scope=GLOBAL`，campus 筛选 `applicable:false`；C10 改为 restaurants+dishes 全量，HOME 无真实 rating 时 NULL，评分轴只绘非空并报 `not_plotted_no_rating`；C08/C11/C13/C17 增加校区作用域。
- **合成/图片**：菜谱为共享合成数据；食堂按校区分别合成并标注；图片仅本地演示，不进入公开发布/APK 公开分发/论文公开素材。
- **状态**：S09/r02 台账为 `BLOCKED`（提交时曾为 REVIEW_PENDING），S10 仍 LOCKED；r03 历史结论保留（R02 FAIL、F12 FAIL、R01 PASS），r04 后续 PASS 记录不变。D03 已裁决（见 §24）。

## 24. v2.3.5 建大雁塔试抓结果（2026-10-25，文档同步）

- 地名搜索：西安建筑科技大学雁塔校区 → GCJ-02 `108.967153,34.236991`（碑林区，雁塔校区，adcode 610103；未返回草堂）。
- 真实餐饮 POI：3km、`types=050000`、45 个初始 800m 网格 + 递归细分；425 个网格、1,206 次调用、0 错误/0 未完成；原始 25,857、`poi.id` 去重 12,990、3km 内 6,730、剔除 71 条非餐饮后 **6,659**；字段有值/缺失：rating 6,652/7、cost 5,411/1,248、tag 3,871/2,788。
- 合成食堂：建大单独 200 目标，`is_synthetic=1`、`campus=JIANDA_YANTA`，不与思源混用；建大合计 **6,859**，原目标 1500+ 已满足。
- 思源：同版递归脚本复跑（61 个处理格、133 次调用）仍为 605+200=805；字段有值/缺失：rating 604/1、cost 427/178、tag 309/296。**D03 已裁决接受 605 为样本 A、建大 6,659 为样本 B**，分校区报，不是 1700 合计；不得用建大数据补思源、不得跨校区混算。
- 建大抽查：0 条 >3km（最远 2,999.5m）；同名同址重复 0 组；同名 ≤50m 4 对、≤100m 5 对为疑似同店多 ID，S10 导入前人工裁决；同坐标 116 组多为商场/楼宇不同店。
- 状态：S09/r02 台账 **BLOCKED**（r02 复审），S10–S20 仍 LOCKED；D03 解封由 Codex/用户处理；未改代码/DB/`/admin`，未签 PASS。

## 25. V5 极简前端设计决策（2026-10-29，设计基线）

用户已确认“V5 极简 + 青黛水彩 + Apple 玻璃”方向。完整决策见 `docs/V5_DESIGN_DECISIONS.md`，这里只记会影响施工的硬结论。

- 视觉：浅色燕麦版为默认，深色青黛版保留；纸感颗粒 `assets/paper-grain.png` + 水彩 `assets/watercolor-ink.png`；抽屉/导航真实 `backdrop-filter`。
- 首页：决策台，不是大图卡；菜品卡统一用八维风味雷达，无图也成立；背景图可上传，按平均亮度自动切浅/深文字，遮罩可调；主按钮为毛玻璃高对比。
- 足迹：主视图是时间线，周报移到右上角抽屉；不得再把周报当足迹首页。
- 冰箱：临期优先 → 全部库存 → 能做什么 → 买菜清单；拍照入库走“云端识别 → 用户确认 → 入库”，低置信度默认不勾，不能自动写库；离线 YOLO 暂缓。
- 房间：等待、15 秒划卡、揭晓三态；划卡单图双线雷达（深色菜品八维 + 橙色个人五维，橙线独立缩放并注释）；文案随外食/下厨模式变化。
- 我的：饮食基因、成就、红黑榜、演示角色切换、外观设置。
- 静态设计页在 `design/v5-minimal/`，调色台在 `design/color-lab/`；已复制到 `frontend/public/design/`，主项目可通过 `/design/index.html` 预览。主项目 Vue 迁移尚未完成，不得把静态页当正式功能。
- 迁移顺序：全局令牌与 Dock → 首页 → 足迹 → 冰箱 → 房间 → 我的 → 回归/APK。

## 26. 全量目录导入正常库（2026-10-29）

- 用户决定正常库直接使用全量目录，不再以独立库作为日常入口。
- 来源 `backend/eatwhat_g2_s10_full.db`（SHA `37eb6b0e…8dcb`）导入 `backend/eatwhat.db`；导入前备份 `eatwhat_backup_before_catalog_20261029_202033.db`。
- 结果：门店 **7,684**（20 原有 + 7,664 全量）、菜谱 **6,500**（100 原有 + 6,400 全量）；4 用户、9 流水、0 房间保持不变。
- 校区门店：思源 825、建大雁塔 6,859；菜谱共享 6,440、思源外食 60。
- 证据：`docs/review/final/FULL_CATALOG_IMPORT.json`、`FULL_CATALOG_IMPORT.log`；脚本 `backend/scripts/import_full_catalog_to_runtime.py` 可重复执行并按 `source_dataset` 跳过已导入目录。
- 真实门店仍无菜单，外食仍使用 60 道 fixture；下厨菜谱已全量可用。V5 设计页已复制到 `frontend/public/design/`，主项目 Vue 迁移仍未开始。


## 27. 后台部署重规划（2026-10-30）

- APK 暂缓：用户未部署服务器，先做后台可部署性与功能重规划。
- 新增 `docs/BACKEND_DEPLOYMENT_PLAN.md`、`backend/.env.example`。
- CORS 改为 `CORS_ORIGINS` 环境变量，`allow_credentials=False`；生产必须白名单。
- 当前仍是演示身份 `X-User-Id`；上线前必须换 JWT/微信/学校登录。
- 目标架构：FastAPI + PostgreSQL + Redis + 对象存储 + 视觉模型；Alembic 迁移、管理后台鉴权、限流、可观测性。
- 数据边界：7,704 门店、6,560 菜谱；真实 7,664 门店无菜单，外食推荐仅思源/建大各 60 道 fixture。菜单需真实来源或明确标记的合成菜单。
- 测试房间/投票已清理：10 房/21 票 → 0；备份 `eatwhat_backup_before_room_cleanup_20261030_010059.db`。
- 房间逐用户五维匹配已接入：后端快照 `my_match`，前端五维条；天气维度暂按 20°C。

## 28. 真实门店菜单策略（2026-10-30）

- 决策：分层策略。仅 40 家带菜单 fixture 门店（思源 20 + 建大 20，各 60 道）进入外食推荐；7,664 家真实/合成 POI 无菜单，只做地图、统计和大屏。
- 不批量生成假菜单；后续补菜单必须标记 real/curated/synthetic。
- 证据：`docs/MENU_STRATEGY.md`、`docs/review/final/MENU_COVERAGE.json`。

## 29. 阶段 A 单机部署准备（2026-10-30）

- 健康检查升级为 `/health` 存活 + `SELECT 1` 数据库探测，正常返回 `db=ok`，数据库异常返回 503 `db=error`。
- 新增 `backend/scripts/backup_db.py`，使用 SQLite backup API 在线备份并保留最近 N 份；已验证 `backend/backups/eatwhat_20261030_013522.db`。
- 新增 `docs/DEPLOYMENT_PHASE_A.md`：环境变量、CORS、单 worker 启动、Caddy/Nginx WebSocket、备份 cron、日志、上线检查、回滚。
- 当前仍为 SQLite + 单 worker；多 worker/多实例前必须 Redis + PostgreSQL。APK 仍暂缓。

## 30. 后台地基：Alembic + PostgreSQL 迁移（2026-10-30）

- 用户选定顺序：① 结构重做（PG + Alembic）→ ② 角色表 + 管理接口鉴权 → ③ 管理后台页面重设计。理由：管理后台要加的角色表、审计日志都落在数据库层，地基不换先画页面必返工。
- Alembic 落地：`backend/alembic.ini` + `backend/migrations/`，连接串唯一来源 `backend/config.py`，支持 `-x db_url=` 与环境变量覆盖。
- 基线迁移 `022b1382298a`（11 张表）+ `5974c7e57e83`（users.role）。旧库用 `alembic stamp head` 认账，不重建。
- 迁移可回滚：SQLite 上 11 表 → downgrade base → 0 → upgrade head → 11，`alembic check` 空库升级后无差异。
- `create_all` 收口：新增 `AUTO_CREATE_SCHEMA`，SQLite 默认开、PostgreSQL 默认关，生产只认 `alembic upgrade head`。
- 数据搬家脚本 `backend/scripts/sqlite_to_postgres.py`：保留主键、按 metadata 拓扑序插入、搬完 setval 重置序列、`--dry-run/--verify/--truncate`。JSON 列做了字符串→数组转换（旧库 appliance_tag 是 VARCHAR 存 JSON 文本）。
- 发现 3 处旧库与模型漂移：appliance_tag 类型、feature_vector 可空性、room_votes 唯一索引 vs 约束。基线以模型为准，旧库不回头改。
- 管理接口鉴权：`deps.require_admin` 只认 Bearer token + `users.role=ADMIN`，**故意不认 X-User-Id**（那个头无秘密，认它等于把改菜删店挂在明文头上）。三个 admin router 统一挂 router 级依赖。实测：无 token 401 / 伪造 X-User-Id 401 / 普通用户 403 / 管理员 200。
- 管理员授予：`python -m backend.scripts.grant_admin --username xxx`（--revoke / --list）。注册接口不允许自选角色。
- 新增 `docker-compose.dev.yml`（PG 16，端口 5433 避让本机 5432）与 `docs/MIGRATION_SQLITE_TO_PG.md` 手册。
- **未完成**：真 PG 上跑搬家。Docker Desktop 的 WSL 引擎崩溃（0xc00000fd），本机 wsl.exe 被安全策略禁用，无法自动恢复；恢复后按手册 §4 执行并留 `--verify` 输出。
- 坑：`alembic.ini` 必须纯 ASCII，configparser 按系统 locale(GBK) 读文件，中文注释会让 alembic 起不来。

## 31. 管理后台审计日志（2026-10-30）

- 新增表 `admin_audit_logs`（迁移 `0a755691cec1`）：user_id / action / resource_type / resource_id / summary / detail(JSON) / ip / created_at。
- 只记写操作，不记查询：查询不改数据，逐条记录只会把表撑大。
- 埋点 7 处：restaurant.create/update/delete、dish.create/update/dish.delete、dish.llm_tag。全部在业务 commit 之后写，保证"改成功才留痕"。
- 查询接口 `GET /admin/audit-logs`：分页 + action/resource_type/user_id 过滤，仅 ADMIN。
- 实测：建店→改价→删店三条记录齐全（含 operator、ip、detail 改前改后），普通用户 403；测试数据已清理（门店回到 7,704，审计表清空）。
- 运行库切换 PG 暂缓：Docker 引擎当天崩了三次（WSL 内存不足），切过去后端会卡在 startup。`backend/.env` 里保留了切换/回滚两行注释。
- 新增 `connect_timeout=5` 到 PG 引擎：数据库不可达时 5 秒报错，不再无限挂死（之前 PG 容器一挂，`/health` 全部超时）。
- PG 实例尚未包含 `admin_audit_logs`（数据在加表前搬的），Docker 恢复后需补 `alembic upgrade head`。

## 32. 运行库切到原生 PostgreSQL（2026-10-30）

- Docker 当天崩四次（WSL2 内存不足 + ecommerce 六个服务 `restart: unless-stopped` 自动拉起），放弃容器方案。
- 官方 EDB 安装程序在本机必然失败：解压到 `C:\Users\<用户名>\AppData\Local\Temp\`，中文路径让 PowerShell 以 GBK 执行 `getlocales.ps1` 报编码错；提权后不继承 `set TEMP`。
- 改用免安装包：`postgresql-16.15-5-windows-x64-binaries.zip`（直链 get.enterprisedb.com，356MB），解压到 `D:\PostgreSQL\16`。
- initdb：`-D D:\PGData\16 -U postgres -E UTF8 --locale=C --pwfile`；pg_hba 本机连接 trust → scram-sha-256；postgresql.conf `port=5433`、`listen_addresses=127.0.0.1`。
- 建 role/database `eatwhat`（UTF8），跑三个迁移（13 表），搬家 14,311 行，逐表核对一致。
- `.env` 已切 `postgresql+psycopg://eatwhat:eatwhat_dev@127.0.0.1:5433/eatwhat` + `AUTO_CREATE_SCHEMA=0`。
- 验证：health `db=ok`、外食推荐 200（砂锅豆腐 83.8，与 SQLite 一致）、登录 200。
- 启停脚本 `D:\PGData\start-pg.bat` / `stop-pg.bat`；注册服务命令见 `docs/MIGRATION_SQLITE_TO_PG.md` §8（需管理员，尚未执行）。
- `docker-compose.dev.yml` 降级为备用方案，文件头已标注。
- 机器上 MySQL 装了 5.7/8.0/8.4/9.5 四个版本（8.4 在跑），SQL Server 也在；本项目不用它们。

## 33. 后台大屏 v8 冷色三屏（2026-10-30，设计稿，未复刻）

- 用户决策：后台配色走**独立冷色令牌**（与移动端 V5 燕麦/青黛解耦）；先在 `design/admin-v7/` 静态页定稿，**定稿后再复刻到主项目 Vue**，本轮不动 `frontend/`。
- 背景：`admin-v7` 已有 8 个稿。管理端 `app.css`（冷灰 `#f4f5f7` + 蓝 `#2f6bff`，看板/表格/质检三视图）结构已可用；大屏有 `dashboard` / `kiosk` / `editorial` / `hero` / `full` 五个方向，共同问题是 17 项塞一屏后单图约 200px 高、最小字号 8.5px（3 米外投影不可读），且 kiosk/full 同时出现青绿+紫+琥珀+玫红四色。
- 产出：`design/admin-v7/dashboard-v8.html`，1920×1080，三屏轮播（总览 / 数据质量 / 算法实验），17 项拆为每屏 5–6 项。
- 令牌：底 `#0b0e14`，唯一强调色冷蓝 `#5b8cff`（`app.css` 的 `#2f6bff` 在深底提亮一档），状态色只保留 ok/warn/bad 三档，取消紫/青绿。裸 hex 仅 11 处且全部在 `:root`。
- 字号基线（1920 画布）：KPI 30px、卡片标题 12.5px、正文 12px、轴标签 10–11px、热力格 12px。
- 数据全部取自真实运行库与 G3/G4 证据：7,704 门店、6,560 菜谱、52,352 特征值、1,284 流水、40 家带菜单、打标 99.3%；重样率 λ=0.5 为 0 vs λ=0 为 18.43%，满意度 95.36/95.46/73.84，Least Misery 77.07/76.72/40.34。
- 截图：`docs/review/final/v8-screen1.png` – `v8-screen3.png`（1920×1080@2x，`overflow: []`）。
- 已知取舍：地图用点阵模拟分布，真实版接高德 JS API（`maptest.png` 已验证能渲染，`full-1920` 里空白属加载时序）；图表为手写 SVG，复刻换 ECharts；**JS 内约 40 处 `rgba()` 数字是静态稿的临时写法，复刻时必须经 `src/utils/theme.js` 读 CSS 变量**，否则违反颜色单一出口。
- 踩坑：`.bar__track/.bar__fill` 用 `<span>` 且未设 `display:block` 时高度不生效，条形只剩空轨道；热力表用单一 grid 且 `align-content:center` 会在高卡片里缩成中间一条，须拆成「固定表头 + `grid-auto-rows:1fr` 数据行」。

## 34. 大屏 v8 复刻到主项目（2026-10-30）

- 范围：`/admin/dashboard` 由旧 17 项长页面改为三屏轮播（总览 / 数据质量 / 算法实验），设计源 `design/admin-v7/dashboard-v8.html`。数据仍是同一组 13 个 stats 接口 + `/admin/experiments`，未新增后端接口。
- 颜色出口：`main.css` 新增 `--wall-*` 与 `--rgb-wall-*` 令牌（后台独立冷色，与移动端 V5 燕麦/青黛解耦）；`utils/theme.js` 新增 `wallTokens()` / `isWall()` / `chartTokens()`；`dashboardOptions.js` 的 import 改为 `chartTokens as tokens`，因此同一套 option 生成器同时服务 DataManage 小图（单色）与大屏（冷色），图表代码零改动。
- 大屏作用域用 `document.documentElement.dataset.surface = 'wall'` 标记，`ExperimentDashboard` 挂载时置位、卸载时删除；ECharts 取色因此能跟随页面切换。
- 新增 `styles/admin-wall.css`（只引用令牌，无裸色值）；`EChartPanel` 加 `bare` prop（不自带卡片壳，供大屏嵌入）；`PoiMap` 在大屏下把热力渐变换成冷蓝。
- 踩坑（都已在代码注释里留痕）：
  1. grid 的 `1fr` 默认 `min-height:auto`，ECharts canvas 会把行撑高并顶出屏幕，必须写 `minmax(0,1fr)`；屏 3 六个图若有一个跨行，最后一个会被挤到隐式行并溢出。
  2. 地图在 grid/fr 布局下初始化时容器可能还是 0×0，AMap 会得到一张永不请求瓦片的空白地图；`PoiMap` 已加 `waitForSize()` + `ResizeObserver` 兜底。
  3. 高德热力 gradient 的 key 必须从 0 起，且低值要落到背景色，否则热力层把整张底图刷白。
  4. ECharts `wordCloud` 在 ~600×250 卡片里布局失败（gridSize 3/7/8/10、多档 sizeRange 均叠字），C13 改为 HTML 文字云，与设计稿一致。
  5. 日历热力在只有 7 天真实数据时会被拉成整年横条，C03 改为「按日决策量」柱状图，数据源仍是 `/admin/stats/calendar`。
  6. 散点价格长尾到 ¥1485（p99 仅 ¥127），轴截断到 ¥200 并在 note 注明超出点数。
- `vite.config.js` 的代理目标改为 `VITE_API_TARGET` 可覆盖，默认仍是 8000（8000 被占用时用 8010 验证）。
- 验证：`npm run build` 通过；三屏在 1920×1080 下 `overflow: []`；接口为真实 PG 运行库（7,704 门店 / 6,560 菜谱 / 52,480 特征值 / 打标 100% / G3 曲线 D14 0% vs 18.4%）。
- 门禁现状：`check-colors` 仍有 262 处 `[literal]`，全部是 V5 迁移遗留（`Room.vue`、`main.css` 的暖色令牌），**本次改动的 6 个文件均未出现在报告中**。修 V5 那批不在本轮范围。
- 未做：DataManage 页面未按 v8 冷色重做（仍用旧 admin.css）；真机/投屏未验；高德配额与暗色样式在长时间运行下的稳定性未压测。

## 35. DataManage 冷色收口（2026-10-30 晚）

- `admin.css` 的 `.admin-shell` 内做了**变量别名映射**（`--color-ink` → `--wall-bg`、`--rgb-silver` → `--rgb-wall-muted` 等），文件里几百处 `rgb(var(--rgb-silver)/x)` 自动落到冷灰，不必逐条改色值；这是本轮最省改动量的做法。
- 三处强调态改冷蓝：`.admin-nav a.is-active`、`.admin-tabs button.is-active`、`.admin-button--primary`（含 hover）。
- `qualityOption` 的 gauge `progress.itemStyle.color` 原本硬编码 `tokens().white`，改为 `tokens().accent || tokens().white`；否则环形图在冷色页里仍是白色。
- `DataManage.vue` 在 **setup 同步阶段**置 `document.documentElement.dataset.surface = 'wall'`，`onBeforeUnmount` 删除。不能放 `onMounted`：`qualityChart` 是 computed，首次渲染早于 mounted，会取到旧的单色组。
- 验证：菜品/菜谱与门店/食堂两个 Tab 均正常（7,704 门店、6,560 菜谱），筛选、分页、编辑/下架按钮在位；build 通过；`check-colors` 对本轮改动的 `admin.css` / `DataManage.vue` / `dashboardOptions.js` 无告警。
- 遗留：表格里的 `SUCCESS` 标签仍是白底黑字（状态标签对比度高，暂留）；后台顶部副标题 10px 偏小；`/login` 登录成功后跳 `/m/home`，进后台还需手动点「实验大屏/数据管理」，未改成按角色跳转。

## 36. 登录按角色分流（2026-10-30 深夜）

- 问题：`/login` 登录成功固定 `window.location.assign('/m/home')`，而移动端没有任何通往 `/admin/*` 的入口——管理员登录后等于进不去后台，只能手改 URL。
- 后端（小改，已报备）：`schemas.AuthUser` 增加 `role: str = "USER"`，`auth_local._auth_user()` 返回 `user.role or "USER"`。`/auth/login` 与 `/auth/me` 因此都带角色。**权限判定没有放宽**，仍由 `deps.require_admin` 用 Bearer + `role=ADMIN` 把关。
- 前端 `Login.vue`：登录成功按 `role === 'ADMIN'` 跳 `/admin/data`，否则 `/m/home`；「你已经登录」卡片改为调 `/auth/me` 取角色，管理员显示「你已经以管理员身份登录」+「进入管理后台」。
- 验证：`/auth/me` 与 `/auth/login` 均返回 `role: "ADMIN"`；登录页卡片文案与按钮随角色变化。端到端「点按钮后落到 /admin/data」的截图受无头浏览器时序影响未捕获，路由与接口分别验证过，未声称完整通过。
- 改后端后必须重启 uvicorn（未开 `--reload`），否则 `/auth/me` 仍返回旧结构。
- 验证用临时账号 `verify_tmp` 已连同 credential/preference/token 一并删除，用户表回到 7 个账号。

## 37. 移动端补管理后台入口 + 管理员密码重置（2026-10-30 深夜）

- `Profile.vue` 账号区加「管理后台」入口，**仅 `role=ADMIN` 显示**：`onMounted` 调 `/auth/me` 取角色，未登录或普通用户不渲染。账号文案同步区分「已登录 · 管理员」与「已登录」。
- CSS 坑：`.account-block div`（特异性 0,1,1）会把新加的 `.account-block__ops`（0,1,0）压回 `flex-direction: column`，必须写成 `.account-block .account-block__ops`（0,2,0）。
- **2026-10-31 更新**：全部 7 个账号口令已统一重置为 `〔演示口令已脱敏，见本地答辩材料〕`（PBKDF2-SHA256 / 120k 轮 / 16 字节随机盐，与注册同算法，逐个回验通过）。改密走 `_hash_password()` 直接写 `auth_credentials`，**目前没有对外改密接口**。
- 同日移除前端硬编码口令：`Login.vue` 的 `DEMO_PASSWORD` 常量已删除，快捷账号按钮只填用户名、密码留空由使用者输入（独立审查 P0：口令曾随 `dist/assets/Login-*.js` 分发）。
- 验证：管理员登录态下账号区显示「已登录 · 管理员 / 管理后台 / 退出登录」且三元素并排不挤压；`localStorage.clear()` 后显示「演示身份 / 登录 / 注册」，无后台入口。
- 未验证：「点入口后落到 /admin/data」的端到端截图没抓到（无头浏览器 click 与截图存在时序竞争，试了 1.5s 与 3.5s 两档延时均未捕获）。链接本身是 `router-link`，目标路由与权限都已分别验证，但不把这条记作通过。

## 38. admin-v7 设计稿定位与 hash 直达（2026-10-30 深夜）

- 用户以为「数据管理质检视图的静态页没保存」。实际 `design/admin-v7/index.html`（22.8 KB，10-30 04:11）一直在，只是**默认打开是「看板」视图**，质检视图藏在第三个切换按钮后面，打开时看不到，容易误判为丢失。
- 该文件含三视图：`#view-board`（三列看板）、`#view-table`（表格）、`#view-grid`（四列雷达质检卡），配套 `app.css` 的冷灰蓝令牌。
- 新增 hash 直达：`index.html#grid` / `#table` / `#board`；切换时 `scrollRestoration = 'manual'`，并在 rAF 后再压一次 `scrollTop`。
- 已知伪影：无头浏览器在「初始直达 + Emulation 改视口」组合下，会把 `.page` 的 scrollTop 补偿到约 133px，标题与筛选条被顶出视口。真实浏览器（用户原图 1080×675 有标题）与「布局完成后点击切换」均正常，判定为截图工具的视口模拟副作用，不是页面缺陷。诊断值：`scrollTop=0`（页面自身）、`pageScrollHeight=1006 / clientHeight=621`。
- 交付证据：`docs/review/final/v7-grid-tall.png`（1080×1000，标题+筛选+三行卡片完整）。
- 注意：`admin-v7` 的**管理端三视图尚未落到主项目**，`/admin/data` 仍是旧表格形态（只做了冷色收口，见 §35）。

## 39. 管理端三视图复刻（2026-10-31 凌晨）

- 目标：把 `design/admin-v7/index.html` 的质检视图落到 `/admin/data`。同时把后台从深色翻成设计稿的**浅色**——大屏是投屏场景用深色，后台是长时阅读场景用浅色，两套令牌并存。
- 令牌：`main.css` 新增 `--admin-*` / `--rgb-admin-*`（口径取自设计稿 `app.css`：bg `#f4f5f7`、ink `#171a1f`、accent `#2f6bff`）。`theme.js` 新增 `adminTokens()` 与 `isAdminLight()`，`chartTokens()` 按 `dataset.surface` 三路分流：`wall` → 深色、`admin` → 浅色、其他 → v2.3 单色。
- `AdminShell.vue` 重写为 **220px 左侧栏 + 顶栏面包屑 + 页面标题**，导航分「数据 / 分析」两组；审计日志入口置灰标注「待建」（后端 `/admin/audit-logs` 已存在，前端页面尚未实现）。新增 `#search` 与 `#actions` 两个具名插槽。
- `DataManage.vue` 增加三视图：看板（按打标状态三列）/ 表格（原实现）/ 质检（四列雷达卡），默认落在质检。门店 Tab 自动切回表格——门店没有 `feature_vector` 与 `tagging_status`。
- 新增 `DishRadar.vue`：132×132 手写 SVG，8 轴 + 3 圈网格 + 渐变填充 + 缺失维度红点。
- **设计稿与数据契约的偏差**：设计稿雷达轴写的是「酸/甜/苦/辣/咸/鲜/油/烫」，但库里 `feature_vector` 的真实 8 键是 `spicy_level / oily_level / soup_level / temp_fit / satiety_level / prep_speed / social_fit / comfort_level`（辣/油/汤/温/饱/速/社/抚）。复刻按真实字段画，轴标签随之调整；设计稿那套是视觉占位，不能照抄。
- 踩坑：`--color-ink` 在旧 `admin.css` 里同时充当「背景」和「文字」。翻浅色后它指向深墨，导致 ① 弹窗 `.admin-modal` 变黑底、表单标签看不见 ② 表格 `.admin-status[SUCCESS]` 变黑块。两处都已显式改用 `--admin-surface` / 状态浅底。
- 验证：质检、看板、表格、新增弹窗四张实拍（`docs/review/final/v10-datamanage-*.png`）；`npm run build` 通过；`check-colors` 对本次改动文件无新增告警（`main.css` 剩余 262 处仍是 V5 暖色遗留）。
- 未做：页面级「导出 PNG」按钮（设计稿有，当前只有质量图自带导出）；审计日志页面；看板按状态全量分组（现在只对当前页分组，避免三次额外请求）。

## 40. 质量区重做、审计日志页与大屏浅色化（2026-10-31 凌晨）

- **质量区合并**：原来「大环 + 松散清单」两栏占掉半屏、信息量只有一个 100%，改为一条 `admin-qbar`（72px 环 + 4 个数字 + 缺口条形 Top3），高度从约 300px 压到 120px，一屏质检卡从 1 行变 2 行。
- **100% 打标无法造差异**：S11 已把 6,560 道全部打标成功，库里没有 PENDING/FAILED 样本。**不造假数据**，改为让 SUCCESS 之间有可见差异——质检卡状态带右侧加「缺图 / 缺标签」角标（真实缺口：缺 image_url 6,400、缺 allergen_tags 843）。若答辩需要状态对比，得先有真实未打标数据。
- **审计日志页** `views/admin/AuditLog.vue` + `/admin/audit` 路由，侧栏「待建」改为真实入口。只读、无编辑入口；动作/资源/操作人三筛选 + limit-offset 分页；空态说明「只记写操作，查询不记录」。接口 `GET /admin/audit-logs`。
- **页面级导出**：`DataManage` 头部加「导出」，用 `exportElementPng` 截 `.admin-main` 整块。
- **大屏浅色化**：`ExperimentDashboard` 改由 `AdminShell` 包裹（新增 `flush` 模式：无页面标题区、主区不滚动），去掉自有品牌块，`dataset.surface` 由 `wall` 改 `admin`，`admin-wall.css` 全部令牌从 `--wall-*` 切到 `--admin-*`，卡片改白底。
- 踩坑：
  1. `AdminShell` 的 `flush` 主区若用 `overflow: hidden`，视口偏矮时底部三卡会被直接裁掉；改 `overflow: auto` 兜底。
  2. 大屏容器从 grid 改 flex（`flex:1 + min-height:0`），并显式 `height: calc(100dvh - 54px)`，否则底部卡片高度算不准。
  3. 菜系卡在三卡并排时只放得下 4 行，`slice(0,6)` 会与标题重叠。
- **未达标（如实记录）**：高德底图瓦片在本机反复加载失败（`amap://styles/dark` 时好时坏，浅色默认样式直接白屏），只剩热力层。已加 4 秒超时探测 + 明确降级文案（`admin-map-fallback`），但不等于地图可用。排查过：`pg`/网络正常、瓦片 URL curl 200、`waitForSize` 与 `ResizeObserver` 均生效，怀疑是高德 JS API 的样式服务在该 Key 下不稳定，需换 Key 或改用静态瓦片方案验证。

## 41. 质量指标口径修正 + 大屏地图换点阵（2026-10-31 凌晨）

- **「缺图片」不是缺陷**（用户裁定）：菜品图不是必需资产，MASTER_SPEC 也允许无图。已从三处移除——质检卡角标、数据管理质量统计、大屏缺口卡。质检卡只保留「缺标签」（`allergen_tags` 缺失会影响词云与 C13 统计）。
- **质量区最终形态**：不用大环、不列非缺陷项，改为一行 `admin-qstats`（在库 / 八维齐全 / 向量异常 / 缺过敏原 + 一句口径说明），高度约 44px。之前的 300px 大环卡信息量只有一个 100%，已被否掉两次。
- **大屏地图换方案**：新增 `PoiScatter.vue`，把真实 GCJ-02 坐标直接投影成点阵（纯本地渲染，零外部依赖）。均匀采样到 1,400 点避免 DOM 过载，按 campus 求质心标注「思源校区 825 / 建大雁塔 6,879」，底部显示图例与经纬度范围。`PoiMap`（高德）仍保留在组件库，但大屏不再使用。
- 踩坑：
  1. `PoiScatter` 放在 `.wall-map`（`position: relative`）里，`flex: 1` 拿不到高度 → 整块空白；必须显式 `height: 100%`。
  2. 大屏底部三卡高度 158px 装不下「标题 + 4 行条形」，标题会压在第一条上；172px + 条形 gap 6px 才够。
  3. 大屏 KPI 行 78px、底部 172px 是 1080 视口下的实测下限，再压就会溢出。

## 42. 大屏改抽屉式分析台（2026-10-31 凌晨）

- 结构：`三屏轮播 + 底部圆点` 改为 `左侧主题抽屉 + 右侧内容区`，去掉 12s 自动轮播与 hover 暂停。主题三项：数据概览 / 数据质量 / 算法实验，键盘 ↑↓ 可切换。
- 卡片：`completeness()` 从「缺 2 维」改为指名道姓「缺 油 烫」（对齐 v7 设计稿的状态带写法）。
- **删掉两张无信息量的图**：星期×时段热力（9 条流水全在夜宵，7×4 网格全是 0）、词云（占一整格只有两行字，且 ECharts wordCloud 在小卡片里始终叠字）。词云改为「标签频次 Top 9 条形」，数据同源。
- 质量环再改一次：大屏与数据管理页的 100% 环都改成大数字 + 图例（满环等于没信息）。
- 后端小改：`/admin/dishes` 新增 `needs_tag` 参数（`allergen_tags IS NULL OR cast(...) = '[]'`），前端下拉新增「待补标签（缺过敏原）」，实测 843 条与质量统计一致。**PG 的 json 类型没有 `=` 运算符**（jsonb 才有），必须 cast 成文本比较。
- 用户数据同步口径（回答提问）：移动端注册写 `users` / `auth_credentials` / `user_preferences`，与后台同一个 PostgreSQL 库，所有统计接口都查这张库，所以数据天然同步。**缺口是后台没有用户管理页**，看不到「有哪些用户、各自多少数据」——`admin.py` 里也没有 users 相关接口。
- 未做（用户提出但本轮未动）：功能增删（打标队列 / 数据导入 / 算法参数配置 / 用户管理）、按需生成补充数据。这两项需要单独一轮。

## 43. 抽屉并入侧栏 + 缺标签换色（2026-10-31 凌晨）

- 用户要的「抽屉」不是页面内独立一列，而是**侧栏里「实验大屏」下面的子项**。`AdminShell` 新增 `#subnav` 插槽，大屏把三个主题（数据概览 / 数据质量 / 算法实验）渲染成缩进子项，页面内的 `.wall-drawer` 整列删除。
- 缺过敏原标签的质检卡：不只是右侧小角标，**整条状态带换成琥珀**（`data-tone="tag"`），与「完全合格（绿）」「打标失败（红）」区分。
- 行为数据现状（回答用户提问）：`eatwhat.db` / `g4_runtime_iso` / `g3_bridge_iso` 三个库的 `eating_logs` **都只有 9 条**，`room_votes` 只有隔离库有 392 条。**演示库同样没有规模化的行为数据**。
- 但 G3 仿真已经产出过 48,000 条流水与 40,000 票，存在 `docs/review/consolidated/G3/data/parallel_full/` 的 JSONL 里，**没有入库**。若要让热力/趋势/桑基有数据，正确做法是写导入脚本把它灌进独立演示库并打 `is_synthetic` 标记，而不是重新造数据。

## 44. 后台路由切页露深色底（2026-10-31 凌晨，已修）

- 现象：在 `/admin/*` 之间点导航，过渡帧会闪一下近黑底色。
- 三个叠加原因：
  1. `App.vue` 的 `AppBackdrop`（Grainient 深色氛围底）条件是 `!isMobile`，**`/admin` 也命中了**；
  2. `body` 的底色是 `--color-grain-b`（#17171a 近黑），是首帧与降级底色；
  3. 路由切换用了 `transition name="fade" mode="out-in"`，旧组件淡出到新组件淡入之间存在空档。
- 修法：
  1. `AppBackdrop` 改为 `!isMobile && !isAdmin`，后台不挂深色氛围底；
  2. `App.vue` 根节点加 `.admin-stage`（`--admin-bg`），后台内部切页用 `admin-swap`（`transition: none`），不做淡入淡出；
  3. 表面色改由 **`router.afterEach` 统一设置** `documentElement.dataset.surface`，并加 `html[data-surface="admin"] body { background: var(--admin-bg) }`。**不能靠页面组件自己设**——组件的 `onBeforeUnmount` 发生在导航之后，会把刚设好的值删掉，首帧照样露黑。两个 admin 页里原来的 `delete dataset.surface` 已移除。
- 实测：点击「实验大屏」后 80ms 与 2.8s 两帧均为浅色，无黑底。
- 顺带修：抽屉并入侧栏后内容区变宽，KPI 行 78px 装不下「标签+数字+说明」三行（说明被裁），改 88px，底部 168px。

## 45. 后台四功能：用户 / 参数 / 打标队列 / 导入（2026-10-31 凌晨）

- 新增 `backend/routers/admin_ext.py`（与 admin.py 分开，避免继续堆），挂同一套 `require_admin`。
- 新表：`system_settings`（key/value JSON）、`tagging_jobs`；迁移 `b7f1c2d3e4a5`，已在 PG 上 upgrade。
- **用户管理** `GET /admin/users` + `PATCH /admin/users/{id}/role`：列表带流水/投票计数（子查询，避免 N+1）；不能取消自己的管理员权限（防自锁）。
- **算法参数** `GET/PUT /admin/settings/algo`：保存后写 `system_settings` 并 `reload_algo_params()` **热加载**，推荐接口下一次请求就用新参数。为此把 `single_recommender` / `group_room` / `eating_log` 三处的 `DEFAULT_ALGO_PARAMS` 改为 `current_algo_params()`；`lifespan` 启动时从库加载一次，否则重启回落默认值。**这是「配置真的生效」与「只是存着」的分界**。
- **打标队列** `POST/GET /admin/tag-jobs`：接口立刻返回 job_id，`threading.Thread` 逐批（20 道）推进并更新 done/failed，前端 2s 轮询。线程内必须用独立 `SessionLocal`（请求 session 在响应后已关闭）。未配置 LLM 时任务落 `FAILED` 并写明原因，实测通过。
- **数据导入** `POST /admin/import/preview` + `/commit`：CSV/XLSX 解析 → 列名与字段映射 → 预览前 8 行 → 确认写库。导入行标记 `is_synthetic=1`、`source_dataset=admin_import`、`tagging_status=PENDING`。只支持菜品，门店导入（校区归属 + 坐标校验）未做。
- 踩坑：preview 原本只返回前 8 行，commit 拿这份数据会导致**大文件只导入 8 条**；改为 `rows` 返回全量（上限 2000 行）+ `preview_rows` 供展示。
- 前端：`Users.vue` / `Settings.vue` / `Import.vue` 三个新页面 + 侧栏「系统」分组；`client.js` 补 `patch` 与 `postForm`（`request` 已支持 FormData，不设 Content-Type 让浏览器带 boundary）。
- 测试现状：本节施工时 `pytest -q` 为 **405 passed / 25 failed / 1 skipped**，25 个失败全部是 `401 missing_token` 与 `login` 路由断言，属 §30 加鉴权、§35 恢复 login 后**测试未同步的既有债**，与这四个功能无关。**该债已在 §46 全部关闭，现基线为 430 passed / 1 skipped**，本节数字仅作历史记录，勿再引用。

## 46. 补齐 25 个失败测试（2026-10-31 凌晨）

- 结果：`pytest -q` → **430 passed / 1 skipped / 0 failed**（修复前 405 passed / 25 failed）。
- 主体修法：`conftest.py` 新增 `admin_client` 夹具——建一个 `role=ADMIN` 用户 + `AuthCredential`，用 `_issue_token()` 签发真实 token 挂在 `TestClient(headers=...)` 上，让测试走与生产完全一致的 `require_admin` 链路（而不是绕过鉴权）。`test_admin.py` / `test_admin_stats.py` 的测试签名与请求调用统一改为 `admin_client`。
- 两条过时断言单独修：
  1. `test_login_route_removed` → 改名 `test_login_validates_payload`：login 路由在 §30 已恢复，断言从「404/405」改为「缺密码 422、未知账号 401」。
  2. `test_weather_offline_fallback` → 改名 `test_weather_fallback_never_500`：天气降级链已扩展为 高德 → open-meteo → 离线常量，写死 `source == "offline"` 会误报，改为断言来源属于已知降级集合。
- 经验：给管理接口加鉴权后，必须同步给测试注入 token；否则整批 401 会被误读成「功能坏了」。测试夹具应尽量复用生产鉴权函数（`_issue_token`），而不是直接改 `dependency_overrides` 放行。

## 47. 产品层修补第一批：人话解释 / 身份锁定 / 组合方案（2026-10-31 凌晨）

用户反馈「功能只是推荐、没有实质产出」「算法分数看不懂」「登录和演示切换冲突」。本轮先做收益最高的三条。

- **八维翻译成人话**（`utils/dishTalk.js`）：把 `feature_vector` 拼成三句——口味（辣/油/汤）、场景（温度/饱腹/抚慰，结合天气）、做法（主料 + 用时，外食/下厨措辞不同）。**不用 LLM**：描述必须与向量严格对应，规则拼装才不会加戏，也方便答辩解释。首页 `explain_reason`（「口味契合 96.5；天气适配 84.0…」）换成三行自然语言。
- 后端配合：`RecommendationItem` 增加 `ingredients_main` 与 `cook_minutes`，否则「怎么做的」那句没有原料。
- **身份锁定**：登录后 `Profile` 隐藏「切换室友」（`v-if="!token"`）。此前登录成 A 还能切到 B 看 B 的数据，与账号体系冲突。演示改由登录页的**快捷账号**承担：5 个按钮（管理员 + 4 个演示人设），**点击只填用户名、不填密码**（2026-10-31 起，口令不再出现在源码与产物中）。全部账号口令统一为 `〔演示口令已脱敏，见本地答辩材料〕`。
- **组合方案接通**：后端一直支持 `combo_mode`，但前端 `algo.js` 写死 `false`，等于功能没接。现在 `mode.comboMode` 可切换，首页按钮在下厨模式 + 已设预算时生效，并展示「一荤一素一汤」套餐卡（角色/菜名/单价/总价/平均油腻）。实测预算 40 时产出：凉拌鹌鹑蛋豆芽 10 + 麻婆豆腐 9 + 冬瓜排骨汤 18 = 37 元，平均油腻 0.417。
- 组合方案的硬前置：`optimize_combo` 在 `budget<=0` 或三个角色缺任一时返回 `None`，所以 UI 必须先提示设预算，否则用户点了没反应。

## 48. 待办：产品层第二批（**已于 §49–§53 全部完成，保留原始需求备查**）

按优先级排列，均来自用户 2026-10-31 的反馈：

1. **打卡闭环**：点「就吃这个」后只有一闪而过的提示，没有结果页、没有满意度反馈、用户感知不到「这顿影响了明天推荐」。
2. **用户画像页**：后台只能看聚合统计，看不到「某个用户喜欢什么、选了什么、预算执行如何」。
3. **个人资料编辑**：昵称/头像/预算/忌口无保存入口（缺 `PATCH /users/{id}/profile`）。
4. **背景图全局**：`eatwhat.v5.background` 只有首页实际应用，其余 `/m/*` 页面不生效。
5. **外卖/地图跳转**：选完菜后「去哪吃」——跳平台搜索页（`meituan.com/s/菜名` 等）与高德搜索附近店铺，导航跳系统地图 App（**不做 App 内导航**）。**不做跨平台比价**：美团/饿了么无公开商品查询 API。入口只在「点外卖」路径出现，不干扰「去食堂」路径。

## 49. 产品层第二批：组合入口收敛 / 背景全局 / 资料编辑（2026-10-31 凌晨）

- **组合入口收敛**：抽屉里的模式分段原是三段（外食/下厨/组合），但组合只在下厨成立，外食点了必然无效。已删掉第三段，模式只剩外食/下厨（`.segmented--two` 让两个按钮各占一半，不再留白）；首页「组合方案」按钮也加了 `v-if="mode.modeType === 'HOME_COOKING'"`。
- **背景图全局**：`MobileShell` 原来只在挂载时读一次 `eatwhat.v5.background`，所以在「我的」里换完背景，除首页外都不更新。改为 `loadBackground()` + `watch(route.fullPath)` + 监听自定义事件 `eatwhat:background-changed`，`Profile.saveBackground()` 保存后派发该事件。
- **资料编辑**：新增 `PATCH /users/{id}/profile`（只改昵称与头像，与管偏好的 `preferences` 分开）；前端人设卡加「编辑」入口 + 弹层（昵称/头像，头像限 1–4 字符）。保存后 `persona.loadProfile()` 刷新。
- 数据口径（回答提问）：外食 120 道 **100% 有 restaurant_id**（40 家门店 × 3 道，店名精确到窗口）；下厨 6,440 道 **0% 有门店**（共享菜谱）。所以「跳高德搜店名」只对外食菜成立，下厨菜没有店可搜。

## 50. 头像支持上传图片（2026-10-31 凌晨）

- 后端：`POST /users/{id}/avatar`（multipart），用 Pillow 居中裁成 256×256 JPEG（quality 86），存 `backend/uploads/avatars/{user_id}_{ts}.jpg`，`users.avatar` 存相对路径；`main.py` 挂 `StaticFiles("/uploads")`。
- 文件名带时间戳：同名覆盖会被浏览器缓存，换了头像看不到变化。
- 前端：编辑弹层加「上传图片」（`<input type=file>` 隐藏，label 触发）+ 圆形预览；头像是图片时隐藏文本输入框，改为「移除图片，改回文字头像」——之前直接把 `/uploads/...` 路径摊在输入框里，用户看不懂。
- 渲染兼容：`isImageAvatar()` 判断以 `/uploads/` 或 `http` 开头则用 `<img>`，否则按 emoji/首字渲染。
- **踩坑**：Vite 只代理了 `/api` 与 `/ws`，`/uploads` 被 SPA 回退成 `index.html`（返回 200 但 `Content-Type: text/html`），`<img>` 加载失败。已在 `vite.config.js` 补 `/uploads` 代理。
- 另一个坑：`main.py` 加 `from fastapi.staticfiles import StaticFiles` 时把原本的 `from fastapi import FastAPI, Request` 拆坏了，`Request` 被带进 staticfiles 那一行；补 `from pathlib import Path` 也一度漏掉导致启动 `NameError`。

## 51. 打卡结果页 + 满意度反馈 + 去哪吃跳转（2026-10-31 凌晨）

一次性做完用户清单的第 4、5、7 项——它们共用同一个落点（打卡后的结果面板）。

- **结果面板**（`HomeV5Exact` 的 `.rsheet`）：点「就吃这个」不再只弹一句 toast，而是给出这顿的上下文——菜名/门店/价格、**本周第几顿 / 本周已花 / 预算剩余**（数据来自 `GET /logs/stats/{uid}`）、三个评价按钮、两个跳转入口。
- **满意度反馈**：新表 `dish_feedback`（迁移 `c8d2e3f4a5b6`），字段 user_id / dish_id / log_id / rating(1–3) / created_at。**单独建表而不是给 eating_logs 加列**：同一道菜在不同时间可以有不同评价，「上次好吃这次踩雷」本身是信号。同一 log 重复提交按更新处理。接口 `POST /logs/{log_id}/feedback`，校验归属（他人提交返回 403，实测通过）。
- **去哪吃**：外食菜 → `uri.amap.com/search?keyword=店名`（100% 有准确店名）；所有菜 → `i.meituan.com/s/菜名`。**不做比价**，只跳搜索页。下厨菜不显示「去这家店」（共享菜谱无门店）。
- 踩坑：
  1. `fetchLogStats` 忘了 import，结果面板三项全显示 `—`/`¥0`；两处 `from '../../api'` 导入要合并。
  2. `.rsheet` 的 `z-index: 70` 低于底部 Tab 栏（Tab 用 50 但层级上下文不同），「继续逛」被压在 Tab 下面点不到；提到 120 并把面板 `padding-bottom` 加到 74px。

## 52. 评价从打卡页移到足迹页（2026-10-31 凌晨）

- 用户指出：点「就吃这个」是**准备吃**的时刻，此时弹「好吃/一般/踩雷」逻辑不对。
- 改法：打卡结果面板移除评价区块，只留菜名、本周数据、去哪吃、一句提示「吃完可以在『足迹』里给这一顿打个评价」。
- 评价落到 `FootprintV5`：每条时间线记录下方，未评价显示虚线按钮「吃完了？评价一下」，已评价显示「😋 好吃 + 改」；点开后展开三个选项，提交后原地更新。
- 后端配合：`TimelineItem` 增加 `rating`（0=未评价），timeline 查询一次取出这批流水的评价（避免逐条查的 N+1）。

## 53. 用户画像页（2026-10-31 凌晨）

- 后端 `GET /admin/users/{id}/overview`：一次返回用户信息、偏好（base_vector/预算/忌口/红黑榜计数）、概览（流水数/累计花费/单均/平均评价）、菜系 Top6、满意度分布、最近 12 条决策。**一次查询替代五六个接口**，避免画像页打开时打一串请求。
- 前端 `/admin/users/:id`（`UserDetail.vue`）：顶部身份条 + 八维偏好雷达（复用 `DishRadar`）+ 数据概览 + 菜系条形 + 满意度条形 + 最近决策表（含每条的评价状态）。
- 用户管理页操作列加「画像」入口。
- 验证：`pytest -q` **430 passed / 1 skipped**，本次改动（timeline 加 rating、新接口）无回归。
- 至此，用户 2026-10-31 提出的六项清单（背景全局 / 资料编辑 / 打卡结果页 / 满意度反馈 / 用户画像 / 去哪吃跳转）全部完成；另有头像上传与组合入口收敛两项附加需求。

## 54. 文档同步至 SSOT v2.3.7（2026-10-31 下午）

用户要求「更新所有相关文档，同步现在项目的进度」。本轮只改文档、不动代码，但改动面很大，因为**主规格已经漂移了一个版本周期**。

**最危险的一处漂移**：`MASTER_SPEC` 第五章 §0 原文写「不做真实注册登录鉴权与 Token 体系，身份一律走 `X-User-Id`」。实际早在 §30 就已恢复 `/auth/login` 并给 `/admin/*` 加了 `require_admin`，本次又补了注册、登出、`/auth/me`。按旧文档施工的人会以为管理接口不需要令牌——这不是措辞问题，是会导致越权判断错误的事实错误。

**MASTER_SPEC v2.3.6 → v2.3.7 改了什么**：

| 位置 | 改动 |
|---|---|
| 标题 + 修订块 | 新增 v2.3.7 九条修订说明（身份升级 / 身份锁定 / 6 张新表 / 参数热加载 / 打标队列 / 大屏抽屉化 / 移动端闭环 / 去哪吃边界 / 测试基线） |
| 第一章 目录契约 | 后端 routers 从 6 个补到 11 个（补 `auth_local` / `catalog` / `admin` / `admin_ext` / `admin_stats` / `admin_experiments`，删去不存在的 `admin_sandbox.py`）；后台视图从「2 大」改为 7 个真实文件名 |
| 第三章 | 表数 9 → **15**，新增 10–15 号表定义（`auth_credentials` / `auth_tokens` / `admin_audit_logs` / `system_settings` / `tagging_jobs` / `dish_feedback`），并把三支迁移号并入原「schema 迁移约束」 |
| 第五章 §0 | 身份口径重写为「账号 + 令牌」，`X-User-Id` 降级为未登录演示身份；管理接口只认 Bearer；天气降级链补 open-meteo |
| 第五章 路由表 | 新增**模块0（账号 4 个）** 与**模块6.5（后台系统能力 11 个）**；模块1 补 `PATCH profile` / `POST avatar`；模块5 补 timeline 与 feedback；`GET /admin/dishes` 补 `needs_tag` |
| 第六章 §3 | 人设卡改为「编辑」入口 + 登录后隐藏「切换室友」；补背景图全局渲染 |
| 第六章 §5 | 新增「v2.3.7 实际落地结构」（侧栏子导航 + 单主题 + 取消轮播 + 88px KPI 行下限 + 数据不足不上屏）；17 项图表补**落地状态表** |
| 附录 D | 系统设计改 15 张表；答辩亮点按现状重写（参数热加载、快捷账号、人话解释、行为闭环）；新增「待补的证据链」行 |
| 第八章 | 新增批次进度快照（1–4 已实现、5 未开工），并声明**不构成验收结论** |

**同批修正的账本错误**：
1. §45 结尾的「`pytest -q` 405 passed / 25 failed」已过时，改为标注「历史数字，现基线 430 passed，债已在 §46 关闭」——否则后人会以为还有 25 个失败。
2. §48「产品层第二批（未开工）」已全部完成，标题改为「已于 §49–§53 全部完成」。

**实测数据（2026-10-31 15:30，PG 重启后核对）**：门店 7,704 / 菜品 6,560（外食 120、下厨 6,440、`is_synthetic` 6,400）/ 用户 7 / 流水 **23**（此前记的 9 条已过时，界面联调点「就吃这个」又加了约 14 条）/ 投票 0 / 反馈 1 / `SUCCESS` 6,560 / 缺 `allergen_tags` 843。

**环境事故（本轮顺带处理）**：PostgreSQL 进程在 03:48 之后被异常终止（退出码 `1073807364` = `0xC0000409`），15:29 重启时触发崩溃恢复（`redo done at 0/25396D0`），**数据完整、无丢失**。两条操作经验：
1. 重启 PG 必须用后台任务方式启动 `postgres.exe`；`pg_ctl -w start` 会在前台等待，被 SIGTERM 连带杀掉，日志里已经 `ready to accept connections` 但端口立刻消失。
2. 日志出现 `could not open file "./pg_console.log": sharing violation` 时不必慌，是 PG 在 fsync 时自己持有该日志，属自检噪音。

## 55. 待补：推荐有效性的证据链（未开工，2026-10-31 记录）

用户提出「项目功能只是给人推荐，不会有实质性产出，感觉功能不太有用」。判断：**这不是功能数量问题，是证据链缺了后半段**。

- 现有闭环：`数据 → 算法 → 推荐 → 用户看到`。
- 缺失闭环：`推荐 → 用户采纳 → 满意度 → 反哺偏好`。
- 现有实验只能证明**算法 A 优于算法 B**（重样率 0 vs 基线 18.4%；群组最低满意度 77.07 vs 随机 40.34），**不能证明「用了系统比不用更好」**。答辩若被问「推荐有没有用」，目前只能答前者。

三个补强方向（按答辩价值排序，均未开工）：

| 方向 | 内容 | 产出 | 工作量 |
|---|---|---|---|
| A 决策效率对照 | 真人 A/B（用系统 vs 自己刷外卖）或反事实模拟，测决策耗时 / 切换次数 / 预算超标率 / 后悔率 | 「决策时间从 4.2 分钟降到 40 秒」 | 大（要组织人） |
| B 个性化在线学习 | 采纳信号按小步长回写 `base_vector` | 「准确率随使用次数上升」曲线 | 中 |
| C 可独立交付物 | 校园餐饮数据集（7,704 门店 + 6,560 菜谱 + 八维标签）、四算法消融报告 | 论文附录 / 开源数据集 | 小 |

结论：**不再加后台模块与图表**，边际价值递减且稀释论文主线；应把已有能力转成证据。用户已认可 B 方向「还可以」，但尚未排期。

## 56. PG 启动失败的真因：日志文件被占用（2026-10-31 下午，对 §54-2 的修正）

§54 第 2 条把 `sharing violation` 判为「自检噪音」，**这条只对了一半**。同一天下午复现了它的致命版本：

- 现象：`postgres.exe -D D:/PGData/16 >> D:/PGData/16/server.log` 启动后 30 秒退出，退出码 1，`server.log` 无任何新增；`netstat` 无 5433；进程一度存在但 12MB / CPU 0 / 不监听端口，`postmaster.pid` 被占用无法读取。
- 真因：**bash 在命令执行前打开重定向目标失败**（`/d/PGData/16/server.log: Permission denied`），postgres 根本没被拉起。之前那次「卡住」的 12MB 进程是另一路重定向（`pg_run.log`）拉起的 postgres，它自己卡在数据目录 fsync。
- 正确做法：**日志写到数据目录之外**（本次用 `D:/PGLogs/run.log`），启动即成功，崩溃恢复 10 秒完成，`redo done at 0/2539830`，数据无损。
- 判据补充：日志「无新增 + 进程存在但 CPU 0 + 端口不监听」三者同时出现时，先查重定向是否成功，再怀疑数据损坏。

**另一个反复出现的根因（未解决）**：PG 至今**没有注册成 Windows 服务**，每次靠会话内后台任务启动，会话/任务结束即被回收。所以「PG 又在跑 / 又挂了」不是数据库坏了，是宿主进程生命周期问题。根治只需管理员执行一次：

```
"D:\PostgreSQL\16\bin\pg_ctl.exe" register -N postgresql-16 -D "D:\PGData\16" -S auto
```

在此之前，任何「PG 已在后台运行」的结论都只在当前会话内成立。

**顺带核出的版本漂移**：`GET /health` 返回 `"version": "2.3.2"`，与 SSOT `v2.3.7` 不一致。该字段大概率指 API 契约版本而非文档版本，但两者混用会让排查时误判，建议改成明确的 `api_version` 或同步到当前值。

## 57. 独立审查整改（2026-10-31 晚，第二轮）

按独立审查意见逐条整改，全部改动均有验证。

### 前端
- **P0 口令**：删除 `Login.vue` 的 `DEMO_PASSWORD`，快捷账号只填用户名；7 个账号口令统一重置为 `〔演示口令已脱敏，见本地答辩材料〕`；`dist` 重建后已无旧口令；`.env.bak.20261030` 删除、`.gitignore` 补 `.env.bak*`。
- **足迹评价静默崩溃**：`notice` 从未声明，catch 里再抛 ReferenceError。补声明 + 提示条 + 计时器清理。
- **房间投票不回滚**：后端 ERROR 补 `dish_id`/`rejected`，前端删除本地票并 `deck.reset()`。
- **重复渲染**：`HomeV5Exact` 的「一餐搭配」块复制了两遍，删掉一份。
- **limit 失效**：`api/index.js` 传 `{params:{limit}}` → `?params=[object Object]`，改为 `{limit}`。
- **定时器泄漏**：DataManage 轮询、Profile/Fridge 的 toast 计时器统一托管并在卸载时清理。
- **请求竞态**：`algo.refresh` 加 `requestSeq`，旧响应丢弃。
- **参数页自相矛盾**：`dirty` 改与「已保存基线」比较。
- **错误文案**：新增 `utils/errorText.js`（处理 FastAPI 422 数组 detail），6 个页面接入。
- **路由守卫**：`/admin/*` 未登录跳登录页；`AdminShell` 显示真实昵称与角色（原来写死「测试账号 ADMIN」）。
- **颜色令牌化**：427 处 → **0**。`main.css` 新增 `--v5-*` / `--rgb-v5-*` / `--v5-photo-*` / `--v5-illus-*` 令牌组；`Home.vue` 与 `HomeV5.vue`（已不在路由上）移到 `docs/_legacy_views/`。

### 后端
- **参数双源**：`_load_params` 删除 `algo_configs` 覆盖，统一走 `current_algo_params()`；`eating_log` 的 λ 同源。
- **软删除**：`single_recommender`、`group_recommender`、`catalog` 共 6 处补 `deleted_at.is_(None)`。
- **时区**：`time_decay._days_since` 改按 `Asia/Shanghai` 取日期。
- **WS 令牌**：`room_socket` 支持 `Authorization` 与 `?token=`，身份必须与路径 `user_id` 一致。
- **导入**：编码 UTF-8→GB18030→422；行键同步 strip；价格/角色/时长校验；`errors` 真正回传；补写 `cook_minutes`；`dish_role` 缺省给 `ONE_MEAL`（NOT NULL 不能写 None）。
- **零权重除零**：归一化回退后仍为 0 时退化成等权；后台同时拒绝「四权重全 0」。
- **种子校区**：`init_seed_data` 按序号对半分思源/建大；`migrate_default_runtime_v236` 删掉一刀切改校区。
- **GET 结算不广播**：`get_room` 改 async，结算载荷非空即广播；重计算走线程池。
- **配置静默回退**：新增 `APP_ENV`，prod 缺 `DATABASE_URL`/`CORS_ORIGINS` 拒绝启动；启动打 `startup_config` 横幅。
- **登录限流**：5 次/5 分钟按「用户名+IP」锁；用户不存在也跑 PBKDF2 消除时序差。
- **审计语义**：注释与实现相反，改为业务优先 + 失败 `logger.exception`；`admin_ext` 三个接口补 `Request`。
- **房间快照**：`recommend_single` 加 `only_dish_ids`，快照只算本局候选。
- **catalog**：`?ids=abc` 全非法时 422（原来静默返回全量）。

### 测试（430 → 445）
- 新增 `tests/test_admin_ext.py`（14 条）：鉴权负例 4 条、参数热更新 2 条、导入 4 条、角色变更 2 条、登录限流 2 条。
- 新增 `user_client` 夹具（普通用户令牌），此前只有 admin_client。
- 修假绿：`test_admin.py` 的主断言包在 `if not DEFAULT_BENCHMARK_PATH.exists()` 里，文件实际存在 → 改为无条件执行。
- 修语义矛盾：`test_no_votes_at_all_means_no_consensus` 断言与用例名相反 → 改名 `test_all_timeout_still_produces_winner` 并写清 TIMEOUT=60 的口径。
- 测试自身踩的坑：`admin_client` 带 Bearer 令牌，而 `require_user_id` 是令牌优先，`X-User-Id` 被忽略 → 推荐用的是无偏好的 fixture 管理员，补 `_ensure_admin_preference`。
- 状态污染：改参写进程级 `_ALGO_RUNTIME`，不还原会污染 `test_s04` 的归一化断言 → 加 autouse 还原夹具。

### 门禁
```
✓ check-colors: 66 个文件无裸色值
PASS 390x844 | 一屏装下 | 滚到底 overlap 0
PASS 390x667 | 需滚动 122px | 初始遮挡 37px | 滚到底 overlap 0
PASS 「换一批」给的是新候选
PASS 沙盒与首页卡组同源
pytest: 445 passed, 1 skipped
```

### 第三轮补充（同日 20:00-20:30）
- **双人早结算测试**：`test_room.py` 新增 2 条。内存库是 StaticPool（两连接会互相踩事务），
  所以不走双 WS，而是直接构造 20 条票后调 `_maybe_settle_early`，覆盖「判定 → 抢锁 → 幂等」三段：
  两人各 10 票 → 结算一次且第二次返回 False；只有一人投满 → 不结算。
- **tag-jobs 审计**：`create_tag_job` 补 `record_audit`（action=`dish.llm_tag_job`），
  此前 500 道菜的批量改写完全不可追溯；顺带把非数字 `dish_ids` 从 500 改成 422。
- **大屏采样**：`geo` 与 `scatter` 全量返回实测 1.26MB / 2.29MB。改为按 `id % step` 均匀采样
  （不是"取前 N 个"，否则空间分布会塌成一片），`meta` 里回传 `sampled` / `total` / `sample_limit`。
  实测 `geo` 628KB（-50%）、`scatter` 506KB（-78%），耗时同步减半。
- 测试总数 430 → **447**。

### 已知未做
- `overview` 仍对 5 个 campus block 各跑一次全表查询（响应仅 1.1KB 但要 0.64s）。
  合并成一次查询需要按 `restaurant.campus` 在内存分组，改动面较大，收益约 0.5s，暂留。
