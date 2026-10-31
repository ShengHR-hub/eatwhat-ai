# 《食刻 (EatWhat AI)》系统架构与全量开发主契约 (MASTER_SPEC v2.3.1)

> **文档定位 (Single Source of Truth, SSOT)**：
> 本文档是毕业设计《基于多维上下文感知与群组偏好博弈的智能饮食决策系统设计与实现》的唯一事实来源。在任何 AI 对话窗口中开发或排查问题时，请先投喂本文档以锁定命名、表结构、算法公式与接口契约。

> **v2.1 修订说明（2026-10-22，对照原始讨论逐项核对后修正）**：
> 1. 补回 v1 已锁定但 v2.0 丢失的字段默认值：餐馆评分默认 `4.5`、距离默认 `500` 米、高德坐标系 `GCJ-02`、做菜时长默认 `15` 分钟、厨具默认 `炒锅`、冰箱数量描述默认 `适量`、保质期默认 `3` 天。
> 2. 补回前端动效库 **Lottie**（与 `canvas-confetti` 为一组），用于动态天气图标与共识揭晓动画。
> 3. 修正数据量口径自相矛盾：v2.0 分项相加约 6,700 条却宣称总量 8,000~10,000+；v2.1 调整分项构成使总量成立（见第七章）。
> 4. 新增附录 A~D：项目背景与立意、交付形态选型理由（为何不做微信小程序）、双模型协作开发流程、LLM 批量打标提示词契约、论文章节与答辩亮点映射。
> 5. v2.0 中由模糊说法形式化出的三处细节——下厨模式绿色主色、群组算法先验/划卡 `0.4/0.6` 权重配比、预算分公式与冰箱临期双倍提权——在 v2.1 起正式锁定为项目决策（见 0.5），后续开发不得再自行改动。
> 6. **v2.1 补充修订（2026-10-22 晚，用户拍板）**：①新增第五个动效库 `gsap`（Draggable 专用于划卡、Timeline 专用于揭晓编排）；②`WeatherPill` 玻璃质感锁定 Apple 官方 Figma 文件复制 CSS 的免费施工法；③动效参照来源锁定 `60fps.design` 免费层；④**明确不采用** React 组件库（21st.dev / Aceternity / Magic UI 原版）移植路线，转 Vue 效果无保证，弃用。
> 7. **v2.1 背景补充修订（2026-10-22 晚，用户拍板）**：背景改走「现成纹理底 + 高透明罩色」构造法（见第六章 1），纹理底锁定 backgrounds.supply 免费区的 Smudge / Etherial / Iridescence 三张候选；AI 仅允许对 Iridescence 做色相迁移改色（派生暖橙/鼠尾草绿双模式版），禁止纯 CSS/AI 单调渐变充当整页背景；免费图授权风险已在第六章留痕。
> 8. **v2.1 控件补充修订（2026-10-22 晚，用户拍板）**：按钮/开关/滑块/气泡等小控件锁定现成来源——主力 `daisyUI`（自定义主题接入，控件颜色只许引用主题令牌、与背景同源呼应）+ 主 CTA 用 Inspira UI 的 Shimmer Button（见第六章 2.7）。
>
> **v2.2 开工前裁决说明（2026-10-23，导师通过后、批次 1 开工前逐项拍板，本文档即刻取代 v2.1）**：
> 1. **仿真流水口径**：24,000 条成立的前提写死为“200 人 × 60 天 × **每人每天 2 餐**”（见第七章）；40,000 条投票 = 1,000 场 × 4 人 × 10 张卡，不变。
> 2. **PASS 刻度统一**：划卡分 `swipe_score` 唯一值域为百分制（`SUPER_LIKE=120 / LIKE=100 / PASS=40`）；`room_votes` 表只存枚举、不再标注数值，`VETO` 只走掩码淘汰、无 -999 分值（见第三、四章）。
> 3. **`appliance_tag` 改 JSON 数组**：取值补入 `一锅出`，默认 `["炒锅"]`；气泡规则按“数组含任一”判定（见第二、三章）。
> 4. **黑榜分对象**：以菜品为准保留 `blacklist_dish_ids`，另新增 `blacklist_restaurant_ids` 管门店；Profile 文案与算法过滤已同步（见第三、四、六章）。
> 5. **管理后台补 CRUD 接口**：`/admin/restaurants` 与 `/admin/dishes` 各补齐增删改查（见第五章）。
> 6. **扫码进房补 join 接口**：新增 `POST /rooms/{room_code}/join` 为成员落库的唯一时机，房间表新增 `member_user_ids`；WebSocket 只订阅、不落库（见第三、五章）。
> 7. **身份口径锁定**：毕设演示系统不做真实登录鉴权，用户身份一律经请求头 `X-User-Id` 传递（见第五章开头）；论文中如实表述为演示级身份方案。
> 8. **`benchmark_json` 结构与天气数据源补定义**：`benchmark_json` 给出完整 JSON 结构（见第三章）；天气锁定高德天气 API、与 POI 共用同一 Key（见第五章）。
> 9. 小项：`room_code` 字段宽 10 位保留、实际值固定 6 位数字并注明；算法 4 措辞降级为“角色分组枚举 + 约束筛选”，不再称“改进背包”（见第四章与附录 D）。
>
> **v2.3 视觉与展示修订说明（2026-10-23 晚，用户拍板，本文档即刻取代 v2.2；批次 1 后端内容不受影响）**：
> 1. **配色整体推翻**：暖橙 + 森林绿 + 奶油白作废，全系统改 **黑、灰、银、白单色**高级感路线。0.5 第 1 条「双模式主色」废止——双模式不再靠颜色区分，改由图标 + 文案标签 + 分段开关选中态（深灰实底）区分，两模式共用同一套单色令牌（见第六章 1）。
> 2. **背景构造法更换**：v2.1 的「现成纹理底 + 高透明罩色」（backgrounds.supply 三张纹理图）作废，改 **Vue Bits 三背景分工**：`Grainient`（谷物）银灰版作移动端全局底、`Liquid Chrome` 仅限首页顶部与共识揭晓页、`Silk` 仅限启动/登录页；三层架构与「组件不受底影响」硬规则见第六章 1，细节以 `MOBILE_VISUAL_SPEC.md` 为准。backgrounds.supply 素材不再使用，其 $49 授权问题随之消失；Vue Bits 为 MIT + Commons Clause（自用合规，不得转售其组件本身）。
> 3. **daisyUI 主题令牌改单色**：`primary` = 近黑 `#17171A`、`secondary` = 银灰 `#55555E`、`base` = 白/浅灰（`#FFFFFF` / `#F4F4F5`）；「颜色只许引用主题令牌、严禁写死」的硬约束不变（见第六章 2.7）。
> 4. **WeatherPill 玻璃参数已实测提取**：Apple 官方 Figma「macOS 27」的 Liquid Glass - Small（Light）样本参数已于 2026-10-23 提取完毕，存 `WEATHERPILL_GLASS.md`；施工直接引用该文件的参数表与生产组合版 CSS，不再执行「打开 Figma 复制 CSS」的流程（见第六章 2.6）。
> 5. **答辩展示与桌面端定位定案**：移动端与 PC 管理后台按原计划开发；全部功能完成并冻结后新增 **批次 5（网页展示版 + 移动端真机录屏）**——同代码库新增桌面壳，聚合移动端与后台的全部功能供答辩投屏展示，移动端另录真机使用视频交代移动端效果。桌面端定位 = 管理后台 + 展示版，不做独立桌面用户端（见第八章与 `MOBILE_VISUAL_SPEC.md` §5）。
>
> **v2.3.1 大屏扩容修订说明（2026-10-23 晚，用户拍板“三档全要”，本文档即刻取代 v2.3；批次 1/2 内容不受影响）**：
> 1. **实验大屏全量扩容**：`ExperimentDashboard.vue` 图表由原 3 项扩至 **17 项**（翻牌数字带、POI 地图、日历热力、星期×时段矩阵热力、人设雷达、价格×评分散点、决策桑基、菜系趋势、词云、动态排序竞赛、食材共现关系图、覆盖率水球等），完整清单与版式见第六章新增 §5，调研与数据映射见 `DASHBOARD_EXPANSION.md`。
> 2. **新增大屏统计接口组**：第五章新增「模块 8：大屏统计」`/admin/stats/*` 共 12 个聚合接口（概览/地理/日历/热力/菜系与趋势/人设/散点/流向/词云/竞赛/共现/质量），均支持 `mode_type`、`cuisine_type` 全局筛选参数以支撑大屏联动。
> 3. **大屏交互定案**：全局筛选联动、图表下钻跳 DataManage 明细、每图导出 PNG（供论文第五章插图）为必备功能；图表标题一律问题式（先结论后证据）。
> 4. **地图实现红线**：地图层走高德 JS API（热力图插件 + 点聚合，坐标 GCJ-02 天然一致）；**禁用** ECharts 的百度地图系示例（`heatmap-bmap` 等），与已锁定的高德数据源冲突。
> 5. **批次 4 范围同步扩大**：批次 4 新增「大屏全部 17 图 + stats 接口组 + DataManage 数据质量面板」，工作量评估与批次细化在 BATCH4_PLAN 中另行拆解（见第八章）。

---

## 0. AI 协同开发最高铁律

1. **命名绝对锁定**：所有数据库表名、字段名、JSON 键名、API 路由路径、WebSocket 事件名及 8 维特征向量键名，必须 100% 严格遵循本文档，严禁自行缩写、改名或发明新字段。
2. **双模式底层同源**：外食模式 (`OUT_DINING`) 与下厨模式 (`HOME_COOKING`) 在算法层共享同一套 8 维特征向量结构与防腻衰减函数，严禁拆分为两套互不兼容的推荐逻辑。
3. **白盒可解释与实时调参**：推荐接口必须返回五维雷达图分项得分与归因文案；所有算法超参数 (`lambda_decay`, `omega_group`, `alpha`, `beta`, `gamma`, `delta`) 必须支持请求参数动态覆盖，以支撑前端“算法上帝视角调试抽屉”。
4. **60fps 动效与交付规范**：后端采用 Python (`FastAPI` + `Pydantic` + `SQLAlchemy`)；前端采用 `Vue 3 (<script setup>)` + `Tailwind CSS` + `ECharts`，强制集成 `@formkit/auto-animate`、`@vueuse/motion`、`canvas-confetti`、**Lottie (`lottie-web` / `@lottiefiles/dotlottie-vue`)** 与 **`gsap`（含 Draggable 插件，100% 免费含商用）** 现成动效库，严禁用 AI 手写 CSS 动画冒充上述库的效果。分工锁定：简单弹性动效用 `@vueuse/motion`，列表过渡用 `auto-animate`，**划卡拖拽与揭晓编排专用 GSAP**，不得混用重复造轮子。

### 0.5 v2.1 正式锁定的形式化决策

以下三处在原始讨论中只有方向性说法，v2.0 将其形式化，v2.1 起正式锁定：

1. **双模式主色**：~~外食暖橙 / 下厨森林绿~~（v2.3 废止）——改黑灰银白单色，两模式共用令牌、靠图标与文案区分（见 v2.3 修订说明第 1 条与第六章 1）。
2. **群组算法权重配比**：个体满意度 `R[u, i] = 0.4 * prior_score + 0.6 * swipe_score`（见算法 3）。
3. **预算分与临期提权公式**：`budget_score` 公式与冰箱临期食材（`expire_days <= 2`）覆盖率双倍提权（见算法 2 与第六章）。

---

## 一、 工程目录结构契约

```text
eatwhat-ai-system/
├── MASTER_SPEC.md                  # 系统主契约与架构说明书
├── backend/                        # Python FastAPI 后端工程
│   ├── main.py                     # FastAPI 启动入口、CORS 配置、路由挂载
│   ├── config.py                   # 环境变量配置（高德Key、国产LLM API Key、数据库URL）
│   ├── database.py                 # SQLAlchemy 引擎、Session 管理与表初始化
│   ├── models.py                   # 9 张核心数据库表的 ORM 模型定义
│   ├── schemas.py                  # Pydantic 请求与响应数据契约模型
│   ├── algorithms/                 # 核心推荐与博弈算法引擎
│   │   ├── vector_spec.py          # 8维特征向量规范、情绪气泡与天气映射字典
│   │   ├── time_decay.py           # 算法1：基于艾宾浩斯遗忘曲线的跨场景防腻衰减
│   │   ├── single_recommender.py   # 算法2：多维上下文单人效用推荐与红黑榜修正
│   │   ├── group_recommender.py    # 算法3：融合最小痛苦策略(Least Misery)的群组博弈算法
│   │   └── combo_optimizer.py      # 算法4：一荤一素一汤组合优化与买菜差额清单计算
│   ├── routers/                    # RESTful API 与 WebSocket 路由层
│   │   ├── auth_user.py            # 模块1：登录、演示角色一键切换、用户主页饮食基因与红黑榜
│   │   ├── recommend.py            # 模块2：单人双模式推荐、环境感知胶囊接口
│   │   ├── fridge.py               # 模块3：虚拟冰箱库存 CRUD、余料反推、买菜清单合并
│   │   ├── group_room.py           # 模块4：多人干饭房间管理与 WebSocket 实时状态机
│   │   ├── eating_log.py           # 模块5：一键打卡、防腻冷却看板、周度干饭报告
│   │   └── admin_sandbox.py        # 模块6&7：后台数据管理、LLM批量打标、算法实验沙盒
│   ├── scripts/                    # 万级数据工程脚本
│   │   ├── fetch_amap_poi.py       # 脚本1：高德地图周边真实餐馆采集（place/around 接口）+ 校园食堂档口生成
│   │   ├── import_open_recipes.py  # 脚本2：开源中式家常菜谱清洗与导入（含香菜/海鲜/葱姜蒜等过敏原识别标注）
│   │   ├── llm_batch_tagger.py     # 脚本3：调用国产模型批量蒸馏 8 维特征向量
│   │   └── simulate_personas.py    # 脚本4：200虚拟用户×60天流水×1000场群组博弈仿真器
│   └── eatwhat.db                  # SQLite 数据库文件（含万级初始化数据）
└── frontend/                       # Vue 3 + Vite + Tailwind CSS + ECharts 前端工程
    ├── index.html
    ├── tailwind.config.js          # 黑灰银白单色主题令牌与毛玻璃动效配置
    ├── capacitor.config.json       # 一键打包 Android APK 配置文件
    └── src/
        ├── router/index.js         # 移动端 (/m/*) 与 PC 管理后台 (/admin/*) 路由
        ├── stores/                 # Pinia 状态管理（当前演示角色、当前模式、算法实时参数）
        ├── components/             # 高复用微交互组件
        │   ├── WeatherPill.vue     # 顶部灵动岛风格天气环境毛玻璃胶囊
        │   ├── ModeSwitcher.vue    # 外食/下厨双模式分段滑动开关
        │   ├── StatusBubbles.vue   # 弹簧动画情绪/状态气泡选择器
        │   ├── SwipeCardDeck.vue   # 多人房间 15 秒探探式表决卡片堆（GSAP Draggable 实现，拖动 >60px 触发判定，倾斜时显示想吃/达咩印章）
        │   ├── ExplainRadar.vue    # 可解释性 AI 五维匹配度雷达图弹窗
        │   └── AlgoSandboxDrawer.vue # 右上角算法参数实时调节抽屉（答辩演示神器）
        └── views/
            ├── mobile/             # 移动端 5 大核心视图
            │   ├── Home.vue        # 首页：上下文感知与双模式智能决策
            │   ├── Fridge.vue      # 冰箱：余料库存管理、临期提醒与买菜清单
            │   ├── Room.vue        # 干饭房：扫码进房、15秒闪电划卡与共识揭晓大屏
            │   ├── Footprint.vue   # 足迹：防腻冷却看板与周度干饭统计报告
            │   └── Profile.vue     # 用户主页：演示角色切换、饮食基因、忌口台、美食红黑榜、成就战绩
            └── admin/              # PC端 2 大管理视图
                ├── DataManage.vue          # 门店/菜谱 CRUD 与国产模型批量打标控制台
                └── ExperimentDashboard.vue # 全站大数据看板与仿真实验对比图表生成器
```

---

## 二、 核心数据字典：8 维风味向量与状态气泡映射

### 1. 菜品与个人 8 维特征向量 (`feature_vector` / `base_vector`，取值 `0.0 ~ 1.0`)

| 键名 (JSON Key) | 中文含义 | 数值定义说明 (`0.0` ~ `1.0`) |
| --- | --- | --- |
| `spicy_level` | 辣度等级 | `0.0` 完全不辣（清汤/甜品），`0.3` 微辣，`0.7` 中辣，`1.0` 重度麻辣 |
| `oily_level` | 油腻厚重度 | `0.0` 极度清淡（白灼/蒸菜），`0.5` 家常小炒，`1.0` 重油重盐/油炸/浓油赤酱 |
| `soup_level` | 汤水温热感 | `0.0` 干拌/烧烤/干锅，`0.5` 带卤汁盖饭，`1.0` 纯汤面/砂锅炖汤/小火锅 |
| `temp_fit` | 适宜环境温度 | `0.0` 极寒天气专属热食，`0.5` 四季皆宜，`1.0` 酷暑专属凉菜/冷面/冰饮 |
| `satiety_level` | 饱腹与碳水度 | `0.0` 轻食小吃，`0.5` 标准正餐，`1.0` 碳水炸弹/高热量硬菜 |
| `prep_speed` | 出餐/制作速度 | `0.0` 慢炖/排队>45分钟，`0.5` 常规现炒(20分钟)，`1.0` 10分钟极速快餐/快手菜 |
| `social_fit` | 社交聚餐属性 | `0.0` 一人食简餐，`0.5` 双人便餐，`1.0` 多人共享（火锅/烤肉/大盘菜） |
| `comfort_level` | 情绪抚慰指数 | `0.0` 功能性减脂餐，`0.5` 日常普通饮食，`1.0` 高幸福感解压治愈美食 |

### 2. 情绪与状态气泡动态提权规则 (`STATUS_BUBBLE_RULES`)

| 气泡 ID (`bubble_id`) | 前端展示文案 | 适用模式 | 触发的算法权重与向量修正逻辑 |
| --- | --- | --- | --- |
| `exhausted` | 😫 刚加完班累瘫 | 通用 | 状态权重 `delta=0.45`；目标向量拉高 `comfort_level=0.9`, `prep_speed=0.9` |
| `broke_end_month` | 💸 月底吃土模式 | 外食 | 预算权重 `gamma=0.55`；过滤超预算菜品，优先 `satiety_level>=0.7` |
| `craving_heavy` | 🌶️ 嘴馋想吃重口 | 通用 | 口味权重 `alpha=0.50`；目标向量拉高 `spicy_level>=0.7`, `oily_level>=0.6` |
| `light_healthy` | 🥗 肠胃负担重想清淡 | 通用 | 任何 `oily_level>0.5` 或 `spicy_level>0.3` 的菜品得分强制乘以 `0.2` |
| `need_hot_soup` | 🍲 手脚冰凉想喝热汤 | 通用 | 天气权重 `beta=0.45`；强制要求 `soup_level>=0.7` 且 `temp_fit<=0.4` |
| `lazy_one_pot` | 🍚 只有电饭煲/不想洗碗 | 下厨 | 仅筛选 `appliance_tag` 数组含 `电饭煲` 或 `一锅出` 任一值，且 `prep_speed>=0.7` 的菜谱 |

---

## 三、 数据库详细设计（9 张核心关联表 Schema）

1. **`users`（用户与演示角色表）**
* `id` (INT, PK), `username` (VARCHAR, UNIQUE), `nickname` (VARCHAR), `avatar` (VARCHAR)
* `persona_title` (VARCHAR, 饮食人设称号，如 `"川渝无辣不欢星人"` / `"广东清淡养生党"`)
* `is_demo_persona` (BOOL, 默认 True，用于用户主页一键切换答辩演示角色), `created_at` (DATETIME)


2. **`user_preferences`（饮食基因、忌口红线与美食红黑榜表）**
* `id` (INT, PK), `user_id` (INT, FK `users.id`, UNIQUE)
* `base_vector` (JSON, 用户长期口味偏好 8 维向量)
* `default_budget` (FLOAT, 日常单餐默认预算上限，默认 `25.0`)
* `veto_tags` (JSON, 绝对忌口/过敏原数组，如 `["香菜", "折耳根", "海鲜"]`，触发一票否决)
* `preferred_cuisines` (JSON, 偏好菜系数组，如 `["川湘菜", "粤菜"]`)
* `favorite_dish_ids` (JSON, **红榜宝藏收藏菜品 ID 数组**，推荐计算时赋予 `1.15` 倍提权)
* `blacklist_dish_ids` (JSON, **黑榜拉黑菜品 ID 数组**，以菜品为对象，在单人与多人推荐中永久一票否决)
* `blacklist_restaurant_ids` (JSON, **黑榜拉黑门店 ID 数组**，以门店为对象；外食模式下该门店的全部菜品一并剔除，默认空数组)


3. **`restaurants`（周边真实门店与校园食堂档口表）**
* `id` (INT, PK), `name` (VARCHAR), `source_type` (`AMAP_POI` | `CANTEEN`), `category` (VARCHAR)
* `avg_price` (FLOAT), `rating` (FLOAT, 默认 `4.5`), `longitude` (FLOAT), `latitude` (FLOAT)（经纬度统一采用高德 `GCJ-02` 坐标系，严禁混入 WGS-84）
* `distance_meters` (INT, 距学校中心步行距离, 默认 `500`), `address` (VARCHAR)


4. **`dishes_and_recipes`（菜品与家常菜谱核心主表）**
* `id` (INT, PK), `name` (VARCHAR), `mode_type` (`OUT_DINING` | `HOME_COOKING`)
* `restaurant_id` (INT, FK `restaurants.id`, 下厨模式为 `NULL`), `cuisine_type` (VARCHAR)
* `dish_role` (`MEAT` | `VEG` | `SOUP` | `ONE_MEAL`), `price_or_cost` (FLOAT), `cook_minutes` (INT, 默认 `15`)
* `appliance_tag` (JSON 数组，元素取值 `炒锅` | `电饭煲` | `空气炸锅` | `免开火凉拌` | `一锅出`，默认 `["炒锅"]`；一道菜可多值，如同时支持电饭煲与一锅出的菜记为 `["电饭煲", "一锅出"]`)
* `ingredients_main` (JSON, 核心主料数组), `ingredients_aux` (JSON, 辅料数组)
* `recipe_steps` (TEXT), `feature_vector` (JSON, 8维标准化特征向量), `image_url` (VARCHAR)


5. **`fridge_inventory`（虚拟冰箱库存表）**
* `id` (INT, PK), `user_id` (INT, FK), `ingredient_name` (VARCHAR)
* `category` (`肉禽蛋奶` | `新鲜果蔬` | `冷冻速食` | `豆制品与干货`)
* `quantity_desc` (VARCHAR, 默认 `适量`), `expire_days` (INT, 默认 `3`; `<=2` 在前端高亮临期并在算法中双倍提权), `created_at` (DATETIME)


6. **`eating_logs`（饮食足迹与防腻历史流水表）**
* `id` (INT, PK), `user_id` (INT, FK), `dish_id` (INT, FK), `mode_type` (VARCHAR)
* `cost_amount` (FLOAT), `weather_snapshot` (VARCHAR), `status_bubbles` (JSON)
* `eaten_at` (DATETIME, INDEX, 用于计算艾宾浩斯时间间隔)


7. **`group_rooms`（多人干饭房间主表）**
* `id` (INT, PK), `room_code` (VARCHAR(10), UNIQUE, 邀请码；字段宽 10 位为预留，实际值固定为 6 位数字字符串，如 `886421`), `host_user_id` (INT, FK)
* `member_user_ids` (JSON, 成员 user_id 数组；建房时写入房主，其余成员只能经 `POST /rooms/{room_code}/join` 幂等追加，WebSocket 建连不落库)
* `mode_type` (`OUT_DINING` | `HOME_COOKING`), `status` (`WAITING` | `SWIPING` | `FINISHED`)
* `candidate_dish_ids` (JSON, 初筛10道候选ID), `winner_dish_id` (INT, NULLABLE)
* `consensus_report` (JSON, 群组平均分、最低分及各成员妥协度明细), `created_at` (DATETIME)


8. **`room_votes`（房间实时划卡表决记录表）**
* `id` (INT, PK), `room_code` (VARCHAR, FK), `user_id` (INT, FK), `dish_id` (INT, FK)
* `vote_type` (枚举，仅存 `LIKE` | `SUPER_LIKE` | `PASS` | `VETO`，本表不存分值), `voted_at` (DATETIME)
* 分值映射唯一出处为第四章算法 3：划卡分 `swipe_score` 采用百分制 `SUPER_LIKE=120 / LIKE=100 / PASS=40`；`VETO` 不计分、只触发掩码淘汰。严禁在其他任何位置再定义第二套刻度（如 0.2 / 1.0 / -999）。


9. **`algo_configs`（算法超参数与实验对比表）**
* `id` (INT, PK), `config_name` (VARCHAR, 默认 `default_production`)
* `lambda_decay` (FLOAT, 默认 `0.5`), `omega_group` (FLOAT, 默认 `0.5`)
* `alpha_taste` (`0.35`), `beta_weather` (`0.25`), `gamma_budget` (`0.20`), `delta_status` (`0.20`)
* `benchmark_json` (JSON, 仿真实验对比数据，结构锁定如下，PC 后台与论文第五章直接按此渲染 ECharts；`GET /admin/experiments` 的 `duplication_rate_curve` 与 `group_satisfaction_bars` 即取自此结构同名字段)

```json
{
  "generated_at": "2026-11-01T00:00:00",
  "sample": {"personas": 200, "days": 60, "meals_per_day": 2, "rooms": 1000, "members_per_room": 4},
  "duplication_rate_curve": {
    "days": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    "ours_lambda_0.5": [0.00, 0.05, 0.08],
    "baseline_no_decay": [0.00, 0.18, 0.26]
  },
  "group_satisfaction_bars": {
    "strategies": ["mixed_omega_0.5", "average_omega_1.0", "random"],
    "avg_scores": [82.5, 84.1, 61.3],
    "least_misery_scores": [71.2, 52.6, 38.9]
  }
}
```

（数组示例长度仅示意；落库时 `days` 固定 14 个点、各曲线数组与 `days` 等长，`group_satisfaction_bars` 三个数组与 `strategies` 等长，分值均为 0~100。）



---

## 四、 四大核心算法数学公式与实现逻辑

### 算法 1：跨场景防腻时间衰减模型 (`time_decay.py`)

查询用户近 14 天的 `eating_logs`。同款菜品 (`dish_id` 相同) 间隔天数记为 `dt_exact`，同菜系 (`cuisine_type` 相同) 或同主料 (`ingredients_main` 有交集) 间隔天数记为 `dt_similar`：

```python
W_decay = (1.0 - math.exp(-lambda_decay * dt_exact)) * (1.0 - 0.4 * math.exp(-lambda_decay * dt_similar))
```

* 若当天刚吃过 (`dt_exact == 0`)，强制设 `W_decay = 0.05`；若 14 天内未吃过，设 `W_decay = 1.0`。

### 算法 2：多维上下文单人推荐与红黑榜修正 (`single_recommender.py`)

1. **硬性红线过滤**：剔除 `ingredients_main / aux` 命中用户 `veto_tags`、菜品 ID 在用户 `blacklist_dish_ids` 中、所属门店 ID 在用户 `blacklist_restaurant_ids` 中（仅外食模式）、或超出距离限制的候选菜品。群组场景（算法 3）同样取全体成员两类黑榜的并集执行。
2. **五维效用计算（归一化至 `0 ~ 100` 分，直接对应前端五维雷达图）**：
* `taste_score`: 用户 `base_vector` 与菜品 `feature_vector` 的余弦相似度映射至 `[0, 100]`。
* `weather_score`: 根据实时气温与降雨生成理想环境向量，计算匹配度。
* `budget_score`: 若 `price <= budget`，得分为 `85 + 15 * (1 - price / budget)`；若超支则按比例指数扣分。
* `freshness_score`: 直接等于 `W_decay * 100`。
* `status_score`: 外食模式计算对当前所选“情绪气泡”的满足度；下厨模式计算菜品主料命中 `fridge_inventory`（临期食材 `expire_days <= 2` 权重翻倍）的覆盖率。


3. **红榜提权与综合得分合成**：
```python
boost_fav = 1.15 if dish.id in user.favorite_dish_ids else 1.0
total_score = W_decay * (alpha * taste_score + beta * weather_score + gamma * budget_score + delta * status_score) * boost_fav
```



### 算法 3：融合最小痛苦策略的群组协同博弈算法 (`group_recommender.py`)

1. **阶段一（建房初筛 Top-10）**：取房间内所有成员 `veto_tags` 与 `blacklist_dish_ids` 的并集进行一票否决过滤，基于成员静态 `base_vector` 均值选出 Top-10 候选菜品下发至各端用于 15 秒划卡。
2. **阶段二（15 秒实时划卡后的博弈定夺）**：
* 成员 `u` 对菜品 `i` 的个体满意度：`R[u, i] = 0.4 * prior_score[u, i] + 0.6 * swipe_score[u, i]`（其中 `SUPER_LIKE=120`, `LIKE=100`, `PASS=40`）。
* 若任意成员投出 `VETO`，则 `Mask_veto(i) = 0`，否则为 `1`。
* 群组博弈共识分计算（结合 Average 均值策略与 Least Misery 最小痛苦策略）：
```python
G_score(i) = Mask_veto(i) * (omega_group * mean(R[:, i]) + (1.0 - omega_group) * min(R[:, i]))
```





### 算法 4：一餐多菜品组合优化与买菜差额清单 (`combo_optimizer.py`)

当开启“一荤一素一汤套餐模式”时，从单品得分 Top-20 中按 `dish_role` 提取 `(MEAT, VEG, SOUP)` 组合，满足总价 `<= budget` 且三道菜平均 `oily_level <= 0.65`（荤素冷热互补）。在下厨模式下，自动计算 `菜谱所需主辅料并集 - 冰箱现有食材集合`，输出合并同类项后的《待采购买菜清单》。

> **命名口径（论文措辞锁定）**：本算法的实质是“Top-20 候选内的角色分组三元组枚举 + 约束筛选”，候选规模小、枚举即最优解。论文与答辩中一律按此如实表述，**不得称为“改进背包算法”或动态规划**；如后续确需引入背包/DP，须先升级本文档并补复杂度分析后再改口径。

---

## 五、 前后端接口契约（RESTful API 与 WebSocket 协议）

### 0. 身份与数据源口径（开工前锁定）

* **身份传递**：本系统为毕业设计演示系统，**不做真实注册登录鉴权与 Token 体系**。前端通过 `GET /users/demo-list` 取得演示角色、用户在主页一键切换当前角色；此后所有需要用户上下文的 `/api/v1` 请求，一律在请求头携带 **`X-User-Id: <当前角色的 user_id>`**，后端据此查 `users` 表确定身份，查无此人返回 404。请求体/查询参数中凡已声明 `user_id` 的接口，其值必须与 `X-User-Id` 一致，不一致以请求头为准并在日志中记录。论文中须如实表述为“演示级身份方案”，不得描述为完整鉴权系统。
* **天气数据源**：`GET /context/weather` 的数据**锁定为高德天气 API**（`https://restapi.amap.com/v3/weather/weatherInfo`，实况用 `extensions=base`、预报提示用 `extensions=all`），与高德 POI 共用同一 Key（`config.py` 中同一环境变量），不得另引第三方天气源。

### 1. RESTful API 路由总表（前缀 `/api/v1`）

| 所属模块 | 请求路径 | 功能描述 | 核心请求体 / 参数 | 核心响应内容 |
| --- | --- | --- | --- | --- |
| **模块1：用户与主页** | `GET /users/demo-list` | 获取预设演示角色列表 | 无 | `users[]`（含人设称号、头像、口味基因） |
|  | `GET /users/{id}/profile` | 获取用户主页完整数据 | `user_id` | 基因向量、忌口、红黑榜详情、干饭成就战绩统计 |
|  | `PUT /users/{id}/preferences` | 更新基因、预算与忌口胶囊 | `base_vector`, `default_budget`, `veto_tags[]` | 更新后的 `user_preferences` |
|  | `POST /users/{id}/red-black-list` | 增删美食红榜(收藏)或黑榜(拉黑) | `target_type` (`DISH` \| `RESTAURANT`), `target_id`, `list_type` (`FAV` \| `BLACK`), `action`（`FAV` 仅允许 `DISH`） | 更新后的 `favorite_dish_ids`, `blacklist_dish_ids`, `blacklist_restaurant_ids` |
| **模块2：单人决策** | `GET /context/weather` | 获取顶部环境胶囊实时数据（数据源：高德天气 API，见本章 0） | `city` 或 `lat, lng` | `temp`, `weather_text`, `capsule_tip` |
|  | `POST /recommend/single` | **单人双模式智能推荐核心接口** | `user_id`, `mode_type`, `budget`, `bubbles[]`, `combo_mode`, `override_params` | `recommendations[]`（含 `total_score`, `radar_5d`, `explain_reason`） |
| **模块3：虚拟冰箱** | `GET /fridge/{user_id}` | 获取冰箱库存（临期置顶） | `user_id` | `items[]`（含 `is_expiring_soon` 布尔标识） |
|  | `POST /fridge/{user_id}` | 录入/删除冰箱食材 | `ingredient_name`, `category`, `expire_days` | 更新后的库存列表 |
|  | `POST /fridge/shopping-list` | 多菜谱智能合并买菜清单 | `user_id`, `dish_ids[]` | `owned_ingredients[]`, `to_buy_ingredients[]` |
| **模块4：多人房间** | `POST /rooms/create` | 创建多人干饭房间（房主自动成为首位成员，写入 `member_user_ids`） | `host_user_id`, `mode_type`, `budget` | `room_code` (6位码), `candidate_dishes[]` |
|  | `POST /rooms/{room_code}/join` | **扫码/输码进房（成员落库的唯一入口）**：校验房间存在且状态为 `WAITING`，将 `user_id` 幂等写入 `member_user_ids`（重复 join 不重复落库），落库后才允许建立 WebSocket 连接 | `user_id` | 房间详情、`members[]`（含本次落库后的完整成员） |
|  | `GET /rooms/{room_code}` | 获取房间状态与共识揭晓报告 | `room_code` | 房间详情、`members[]`、`winner_dish`、`consensus_report` |
| **模块5：饮食足迹** | `POST /logs/checkin` | 点击“就吃这个”一键打卡 | `user_id`, `dish_id`, `mode_type`, `bubbles[]` | `log_id`, `new_decay_weight` |
|  | `GET /logs/stats/{user_id}` | 防腻冷却看板与周度干饭报告 | `user_id` | `cooling_dishes[]`, `weekly_expense`, `cuisine_pie_data[]` |
| **模块6&7：管理后台** | `GET /admin/restaurants` | 门店/食堂列表（分页、按 `source_type`/分类筛选） | `page`, `source_type`, `category` | `items[]`, `total` |
|  | `POST /admin/restaurants` | 新增门店/食堂档口 | 门店字段（同第三章） | 新建的餐厅记录 |
|  | `PUT /admin/restaurants/{id}` | 编辑门店/食堂档口 | 待改字段 | 更新后的餐厅记录 |
|  | `DELETE /admin/restaurants/{id}` | 删除门店/食堂档口（其外食菜品一并下架处理） | 无 | 删除结果 |
|  | `GET /admin/dishes` | 菜品/菜谱列表（按 `mode_type`/菜系/角色筛选） | `page`, `mode_type`, `cuisine_type`, `dish_role` | `items[]`, `total` |
|  | `POST /admin/dishes` | 新增菜品/菜谱 | 菜品字段（同第三章） | 新建的菜品记录 |
|  | `PUT /admin/dishes/{id}` | 编辑菜品/菜谱（含 `feature_vector`、`appliance_tag`） | 待改字段 | 更新后的菜品记录 |
|  | `DELETE /admin/dishes/{id}` | 删除菜品/菜谱 | 无 | 删除结果 |
|  | `POST /admin/llm-tag` | 调用国产模型批量蒸馏8维向量 | `dish_ids[]` | 生成的 `feature_vector` 数组及入库状态 |
|  | `GET /admin/experiments` | 获取算法仿真对比曲线数据（数据源为 `algo_configs.benchmark_json`，结构见第三章） | `lambda_val`, `omega_val` | `duplication_rate_curve`, `group_satisfaction_bars` |
| **模块8：大屏统计（v2.3.1 新增）** | `GET /admin/stats/overview` | 大屏顶部数字带与概览：各表总量与打标覆盖率 | `mode_type`（可选） | `restaurants_total`, `dishes_total`, `feature_values_total`, `logs_total`, `votes_total`, `rooms_total`, `tagging_coverage` |
|  | `GET /admin/stats/geo` | POI 地图点位与热力权重（GCJ-02 原样返回，前端不得二次偏移） | `mode_type`, `cuisine_type`（可选） | `points[]`（`id`, `name`, `lng`, `lat`, `rating`, `heat`，heat=该店流水出现频次） |
|  | `GET /admin/stats/calendar` | 日历热力：仿真期每日决策量 | 无（取 `eating_logs` 全周期） | `daily[]`（`date`, `count`） |
|  | `GET /admin/stats/heatmap` | 星期 × 时段矩阵热力（时段固定四档：早餐/午餐/晚餐/夜宵，按 `eaten_at` 小时划分，划分口径在实现注释中写明） | `mode_type`（可选） | `matrix[]`（`weekday` 0–6, `slot`, `count`） |
|  | `GET /admin/stats/cuisine` | 菜系构成（环形图） | `mode_type`（可选） | `items[]`（`cuisine_type`, `count`, `share`） |
|  | `GET /admin/stats/cuisine-trend` | 菜系决策量按日趋势（堆叠面积） | `mode_type`（可选） | `dates[]`, `series[]`（`cuisine_type`, `data[]`） |
|  | `GET /admin/stats/personas` | 演示角色口味画像雷达（8 维同图对比） | 无 | `personas[]`（`user_id`, `nickname`, `base_vector`） |
|  | `GET /admin/stats/scatter` | 价格 × 评分散点（气泡大小=出现频次） | `mode_type`（可选，决定取门店或菜品） | `points[]`（`name`, `price`, `rating`, `freq`） |
|  | `GET /admin/stats/flow` | 决策流向桑基：候选生成 → 投票类型（LIKE/SUPER_LIKE/PASS/VETO）→ 揭晓结果聚合 | 无 | `nodes[]`, `links[]`（`source`, `target`, `value`） |
|  | `GET /admin/stats/keywords` | 词云：忌口标签与菜品高频词 | `mode_type`（可选） | `words[]`（`name`, `value`） |
|  | `GET /admin/stats/race` | 动态排序竞赛：菜品热度按周 Top 10 演变 | 无 | `weeks[]`, `series[]`（`dish_id`, `dish_name`, `data[]`） |
|  | `GET /admin/stats/cooccurrence` | 食材共现关系图（下厨菜谱主辅料共现，共现次数 ≥ 阈值才入图，阈值与 TopN 在实现注释中写明） | `top_n`（可选） | `nodes[]`（`name`, `value`）, `links[]`（`source`, `target`, `value`） |
|  | `GET /admin/stats/quality` | 数据质量面板：打标覆盖率、缺失字段 Top、向量越界/异常计数 | 无 | `tagging_coverage`, `missing_fields[]`, `vector_anomalies` |

### 2. 多人房间 WebSocket 实时协议 (`ws://{host}/ws/room/{room_code}/{user_id}`)

* 前置条件：建立 WebSocket 连接前必须已通过 `POST /rooms/{room_code}/join` 落库为成员，未落库的连接直接拒绝（HTTP 403）；连接本身只订阅与广播，不写入成员。
* `MEMBER_SYNC` (服务端广播): 成员进房（join 落库后触发）/准备状态更新，`members: [{user_id, nickname, avatar, progress}]`。
* `START_SWIPING` (房主触发 -> 全员广播): 同步开启 15 秒倒计时与 10 张探探式划卡堆叠。
* `SUBMIT_VOTE` (客户端上报): `{"type": "SUBMIT_VOTE", "dish_id": 108, "vote_type": "LIKE"}`。
* `PROGRESS_UPDATE` (服务端广播): 实时同步各室友划卡进度（如 `8/10`）。
* `CONSENSUS_REVEAL` (服务端广播): 全员完成或倒计时结束，广播博弈获胜菜品及各成员妥协照顾度报告，触发全屏礼花。

---

## 六、 前端 UI/UX 视觉规范、用户主页与 60fps 动效工程

### 1. 全局色彩与视觉质感（v2.3 全面改版，细节以 `MOBILE_VISUAL_SPEC.md` 为准）

* **色彩令牌（黑灰银白单色）**：全局以黑、灰、银、白为唯一色系；深色令牌近黑 `#17171A`、银灰 `#55555E`，浅色令牌白 `#FFFFFF` / 浅灰 `#F4F4F5`。双模式（外食/下厨）**不靠颜色区分**，靠图标 + 文案标签 + 分段开关选中态（深灰实底白字）区分。原暖橙/森林绿/奶油白令牌与 `from-orange-500`、`from-emerald-600` 等渐变类一律禁用。
* **背景分工锁定为 Vue Bits 三背景（v2.3，用户拍板）**，全部为原生 Vue 单文件组件、颜色参数化，严禁施工模型另找或手写背景：
  1. **全局底 `Grainient`（谷物）**：移动端所有页面打底；三色全设银灰（深色版 `#3A3A40 / #17171A / #55555E`），`timeSpeed ≈ 0.2` 接近静止，颗粒细腻低强度；禁用其默认蓝紫配色。内容密集页允许冻结为静态帧或大幅降帧。
  2. **重点区域 `Liquid Chrome`（液态铬）**：仅首页顶部与共识揭晓页；底色保持近黑 `#1A1A1A`（最亮不超 `#222226`）；文字严禁直接压铬面，必须落在玻璃或实底组件上。
  3. **启动/登录页 `Silk`（丝绸）**：银灰色，Speed 由默认 5 降至 1–2；仅限只看几秒的页面，不得作全局底（墨池已用 Silk 作全局背景，两作品须区分）。
* **三层架构（硬约束，保「组件不受底影响」）**：第 0 层背景只负责氛围不承载信息；第 1 层玻璃组件（§2.6）只给小面积悬浮件，靠 backdrop 磨砂与底解耦；第 2 层内容（菜品卡片、列表、表单）一律实底（白或深灰实色），菜品图片只许放实底卡片内、不直接贴动效底。`backdrop-filter` 不支持时玻璃降级实底 `rgba(246,246,246,0.85)`。
* **背景素材授权备注**：Vue Bits 许可为 MIT + Commons Clause，自用/毕设合规、不得转售其组件本身；原 backgrounds.supply 纹理图方案已作废、不再使用，其 $49 商业授权问题随之消失。
* **卡片规范**：统一采用 Bento Grid 便当盒大圆角布局 (`rounded-3xl`) + 弥散柔光阴影 (`shadow-[0_8px_30px_rgb(0,0,0,0.04)]`) + 单色（黑/银灰）图标，不再用双色图标。

### 2. 强制集成的 5 大开源前端动效库规范

1. **`@formkit/auto-animate`（零配置列表自动过渡）**：
* 必须挂载于：**虚拟冰箱食材列表**、**用户主页忌口胶囊与红黑榜列表**、以及**主界面推荐结果列表**。当在右上角“算法调试抽屉”拖动滑块改变参数时，推荐卡片自动产生丝滑的上下浮动换位动画。


2. **`@vueuse/motion`（物理弹簧阻尼引擎）**：
* 用于顶部 `WeatherPill.vue` 灵动岛展开、情绪气泡 `StatusBubbles.vue` 点击时的果冻按压回弹 (`stiffness: 300, damping: 20`)，以及双模式切换滑块的物理惯性过渡。


3. **`Inspira UI / Magic UI` 风格微动效**：
* 推荐匹配度百分比（如 `94.6%`）采用数字滚动牌 (`Number Ticker`) 动效；核心主按钮采用流光扫过特效 (`Shimmer Button`)。


4. **`canvas-confetti` + `Lottie`（氛围粒子与矢量动画）**：
* 在多人房间 `CONSENSUS_REVEAL` 共识揭晓瞬间，调用 `confetti()` 触发全屏彩色礼花庆祝。
* **Lottie（v2.1 补回，原始讨论已定）**：顶部天气胶囊的动态天气图标（晴/雨/雪矢量小动画）、共识揭晓与空状态插画一律使用 Lottie JSON 动画文件播放，严禁使用静态图片或手写 CSS 动画替代；动画文件统一放在前端 `src/assets/lottie/` 下按场景命名。

5. **`gsap` + `Draggable` 插件（划卡拖拽与编排时间线，v2.1 补充修订新增）**：
* **唯一指定用途一：`SwipeCardDeck.vue` 划卡**。拖拽、甩出惯性、倾斜印章、松手阈值判定（拖动 `>60px` 触发 `LIKE / PASS`）一律用 Draggable 实现，严禁用手写 touch 事件或 Swiper 冒充；`onDragEnd` 回调将判定结果映射为 `SUBMIT_VOTE` 的 `vote_type`。
* **唯一指定用途二：共识揭晓与结果弹窗的 Timeline 编排**（倒计时结束 → 卡片翻牌 → 礼花 → 共识报告展开的多段顺序动画），以及匹配度数字滚动的补间。
* **Vue 集成纪律**：GSAP 为命令式 DOM 动画，必须用 `gsap.context()` 包裹并在组件 `onUnmounted` 时 `ctx.revert()` 清理，严禁动画实例泄漏；插件在使用前 `gsap.registerPlugin(Draggable)` 注册一次。
* **不引入的部分**：`Flip` 与 `auto-animate` 功能重叠，默认不装；`ScrollTrigger` 仅 PC 后台与干饭报告页确有滚动叙事需求时再评估，移动端不得预装。

### 2.5 动效参照来源与明确不采用的方案（v2.1 补充修订）

* **动效参照来源锁定为 `60fps.design` 免费浏览层**：划卡 (Swipe / Card Stack)、底部抽屉 (Bottom Sheet)、列表错峰 (Stagger) 等场景，先在该站找到对应参照片段，把其配套 prompt 与规律描述喂给施工模型再写代码；其 PRO 订阅与 MCP 均不购买（MCP 输出为 SwiftUI 代码，与 Vue 技术栈不符）。
* **明确不采用 React 组件库移植**：`21st.dev`、`ui.aceternity.com`、`magicui.design` 均为 React 代码，转写 Vue 后效果与维护均无保证，**不作为本项目的参考与移植来源**；已采用的 `Inspira UI` 系 Magic UI 设计语言的 Vue 社区实现，继续保留，两者不得混为一谈。严禁施工模型将 React 组件代码直接粘贴或机械转译进本项目。



### 2.6 `WeatherPill.vue` 液态玻璃质感施工法（v2.1 补充修订新增）

顶部天气胶囊的毛玻璃/液态玻璃质感**不凭模型想象手写 CSS**。参数已实测提取完毕（v2.3 更新，原「打开 Figma 复制 CSS」流程已完成、废止）：

1. **唯一数值来源**：`WEATHERPILL_GLASS.md`（与本文档同目录）——Apple 官方 Figma「macOS 27」Materials 页 **Liquid Glass - Small（Light 变体）** 的完整参数表（两层填充、3 内阴影 + 4 外阴影、Glass 折射参数）与 Web 生产组合版 CSS（经典材质实测填充/模糊 + 液态玻璃阴影塑形）。施工直接引用该文件，数值不得改动、不得凭想象另写。
2. **适用范围**：玻璃材质只用于小面积悬浮件——`WeatherPill.vue`、顶部导航条、底部 Tab 栏、模式切换器、抽屉把手；严禁铺给内容卡片与整页（理由见第六章 1 三层架构）。
3. **禁用路线**：GitHub 上的 Liquid Glass 类开源复刻项目实测效果不佳，不作为实现基础；施工模型不得自行引入此类库。

### 2.7 小控件指定来源：按钮 / 开关 / 滑块 / 气泡（v2.1 补充修订，用户拍板）

按钮、开关等小控件**一律用现成组件设计，严禁施工模型凭想象手写样式**。指定来源如下（均已实地核验为免费）：

**主力来源：`daisyUI`（MIT 免费，Tailwind 纯 CSS 插件，零 JS 依赖，框架无关）**
| 本项目控件 | 指定 daisyUI 组件 | 说明 |
| --- | --- | --- |
| 普通按钮 | `btn` | 主按钮再叠加本项目渐变令牌 |
| 双模式分段开关 `ModeSwitcher` | `filter`（一组 radio，选中高亮） | 语义正对外食/下厨二选一 |
| 开关（Toggle） | `toggle` | 忌口、设置类开关 |
| 预算滑块 / 算法沙盒滑块 | `range` | 轨道与手柄颜色取主题令牌 |
| 状态气泡 `StatusBubbles` | `filter` / `badge` 组合 | 选中态高亮沿用单色令牌（深灰实底白字，v2.3 已无模式色） |
| 卡片与小徽章 | `card` / `badge` | 只用其结构类，圆角阴影仍服从第六章 1 的卡片规范 |

**特效补充来源：`Inspira UI`（Vue 原生，开源免费）**
* 全 App 唯一的主 CTA 按钮（“开始智能决策”）直接使用其 **Shimmer Button**（或 Gradient Button）现成实现，不再手写流光效果。

**呼应规则（硬约束）**：daisyUI 只许通过**一套自定义主题**接入——主题变量按 v2.3 单色令牌定：`primary` = 近黑 `#17171A`、`secondary` = 银灰 `#55555E`、`base` = 白/浅灰（`#FFFFFF` / `#F4F4F5`）；所有控件颜色只能引用主题/令牌变量，**严禁在组件代码里写死任何十六进制颜色**。这样按钮、开关与三层背景天然呼应，后续调色只改主题一处。

**不作指定来源**：`shadcn-vue` 覆盖虽全且换色机制好，但属自建组件库模式、默认风格中性且无现成流光按钮，暂不引入，后续确需无障碍原语时再评估；`uiverse.io` 量大（7400+）但质量参差、颜色逐个写死，只许作单个特效灵感参考，不得整站照搬；`hyperui` / `flowbite-vue` 控件齐全但风格偏朴素后台风，不采用。

### 3. 用户主页 (`Profile.vue`) 四大核心区块规范

1. **顶部人设卡与“答辩演示角色一键切换器”**：展示当前头像、昵称、饮食人设称号（如“川渝无辣不欢星人”），右上角设 `🔄 切换演示室友账号` 快捷胶囊，点击秒切预设账号以方便答辩演示。
2. **我的饮食基因与忌口红线控制台**：八维口味偏好可视化进度条 + 日常默认预算滑块 + 支持随时点击增删的“绝对忌口/过敏原”胶囊管理区（配 `v-auto-animate` 动效）。
3. **美食红黑榜（宝藏收藏夹 vs 踩雷黑名单）**：双 Tab 切换展示两类对象并分别注明口径——**红榜只对菜品**（`favorite_dish_ids`，提示“推荐时享 1.15x 提权”）；**黑榜分菜品与门店两类**（菜品拉黑提示“该菜永久一票否决”，门店拉黑提示“该店全部菜品不再推荐”），支持一键移出。文案严禁再把黑榜笼统写成“黑榜店铺”。
4. **个人干饭成就与战绩概览**：展示累计解决“吃什么”世纪难题次数、本月外食与下厨花费占比环形图、以及历史参与的“多人干饭房间”拼单战绩记录。

### 4. 答辩演示专属组件：`AlgoSandboxDrawer.vue`（右上角算法上帝视角抽屉）

* 移动端右上角常驻 `🛠️ 算法沙盒` 悬浮按钮，拉开后提供 4 个实时滑块：`防腻衰减系数 λ (0.1~2.0)`、`群组折中系数 ω (0.0~1.0)`、`天气权重 β`、`预算权重 γ`。拖动滑块实时重算并触发主界面排名动画与五维雷达图面积变形。

### 5. PC 管理后台与实验大屏规范（v2.3.1 全量扩容，调研依据见 `DASHBOARD_EXPANSION.md`）

**版式锁定（1920×1080 基准画布，深色版单色令牌）**：近黑底 `#17171A`、银灰线、白字；图表色板只许灰阶 + 银色渐变，热力图用单色深浅（深灰→银白），**严禁彩虹色板与蓝绿科技风**（与移动端口径统一）。自上而下：标题栏（右侧放全局筛选器）→ 翻牌数字带 → 三列主体（左：菜系环形 / 时段矩阵热力 / 人设雷达；中：POI 地图 C 位 + 底部横贯日历热力；右：实验一曲线 / 实验二柱状 / 热门菜品轮播榜）→ 其余图表（散点、桑基、趋势、词云、竞赛、关系图、水球）以同页第二屏区或 Tab 分区承载，仍服从「一屏一主题」。

**图表清单锁定（17 项，数据源与接口见第五章模块 8 与 `DASHBOARD_EXPANSION.md` §2）**：
- 必备档：①翻牌数字带 ×5（门店/菜品/特征值/流水 24,000/投票 40,000）②POI 地图（气泡散点 + 热力叠加 + 点聚合）③60 天日历热力图 ④星期×时段矩阵热力图 ⑤实验一双曲线（已有）⑥实验二分组柱状（已有）⑦菜系构成环形图 ⑧热门菜品轮播排行榜（自动轮播 + 逐行高亮）
- 加分档：⑨4 人设 8 维雷达对比 ⑩价格×评分散点 ⑪决策流向桑基图 ⑫菜系趋势堆叠面积 ⑬口味标签词云（`echarts-wordcloud` 扩展）⑭每图导出 PNG 按钮（ECharts `getDataURL`，供论文第五章插图，导出图须带图题与数据口径注脚）
- 进阶档：⑮菜品热度按周动态排序竞赛（bar-race）⑯食材共现关系图（力导向）⑰打标覆盖率水球/环形进度（亦进 DataManage 质量面板）

**交互硬约束**：顶部全局筛选器（模式 `mode_type`、菜系 `cuisine_type`）一处切换、全图联动刷新；点地图门店气泡或榜单行可下钻跳 `DataManage.vue` 对应明细；每张图标题写成问题式（如实验一标题「防腻衰减真的降低了重样率吗？」），图下给一句话结论，严禁只写「实验一结果图」式空标题。

**实现路线**：图表一律 ECharts 手写 option（对照官方示例 ID，见 `DASHBOARD_EXPANSION.md` §1.3）；版式与组件语言借鉴 GoView 组件清单与 DataV 边框/翻牌/轮播语言，**不引入 GoView/DataEase 等平台本体**（许可证与体积均不合适，DataV 主仓为 Vue 2、只借视觉语言）。地图层走**高德 JS API**（热力图插件 + 点聚合）；禁用百度地图系示例与插件。

**DataManage 数据质量面板（v2.3.1 新增）**：`DataManage.vue` 顶部增质量概览区——打标覆盖率（水球/环形）、缺失字段 Top 列表、向量异常计数，数据来自 `GET /admin/stats/quality`；定位为「数据真实性证据」，与原 CRUD 表格同页。

---

## 七、 万级数据工程与仿真实验规范（支撑论文第五章）

1. **真实周边门店 + 开源菜谱底座 (`fetch_amap_poi.py` & `import_open_recipes.py`)**：
* 调用高德 Web 服务 API (`https://restapi.amap.com/v3/place/around`) 抓取高校周边 3km 内餐饮 POI（约 1,500+ 真实门店）及 200 个校园食堂窗口；导入开源中式家常菜谱数据集（约 6,300 ~ 8,000 道菜谱），三项合计构建 **8,000 ~ 9,700+ 条** 基础数据。
* **口径说明（v2.1 修正）**：v2.0 中菜谱只写 5,000+，三项相加仅约 6,700 条，与宣称的 8,000~10,000+ 对不上；v2.1 将菜谱目标上调至 6,300~8,000 道使总量成立。对外汇报（论文/答辩）统一使用本节口径，严禁再引用 v2.0 的旧数字。


2. **国产大模型批量特征蒸馏 (`llm_batch_tagger.py`)**：
* 异步批处理脚本每次打包 20 道菜品调用国产大模型 API，自动输出 `dish_role` 与 8 维 `feature_vector` 浮点数 JSON 并入库（累计生成 **60,000+ 个** 细粒度特征值）。


3. **多智能体仿真实验生成器 (`simulate_personas.py`)**：
* 构建 **200 个不同口味人设的虚拟大学生**，按 **每人每天 2 餐（午餐 + 晚餐）** 模拟连续 **60 天饮食打卡流水（200 × 60 × 2 = 24,000+ 条）** 与 **1,000 场四人寝室拼单投票（1,000 × 4 人 × 10 张卡 = 40,000+ 条）**。论文第五章引用数据规模时必须带上“每人每天 2 餐”口径，严禁只写人数天数。
* 自动计算并向 `algo_configs.benchmark_json` 写入两组核心实验数据（供 PC 后台与论文第五章直接出图）：
* **实验一**：本系统艾宾浩斯衰减 (`λ=0.5`) vs 无衰减传统推荐的 **连续 14 天菜系重样率对比曲线**。
* **实验二**：本系统混合博弈策略 (`ω=0.5`) vs 随机抽签 vs 纯均值策略 (`ω=1.0`) 的 **群组平均满意度与最挑剔成员最低满意度（Least Misery Score）柱状对比图**。





---

## 八、 分阶段 AI 指挥开发路线图（5 批次执行，批次 5 为 v2.3 新增）

* **批次 1（后端数据库与算法内核）**：生成 `database.py`、`models.py`（9张表）、`algorithms/` 四大算法模块，以及内置 100 道真实菜品+门店+4个演示角色的种子脚本 `init_seed_data.py`，通过 FastAPI `/docs` 验证推荐与博弈计算输出。
* **批次 2（移动端单人双模式闭环 + 用户主页 + 算法沙盒抽屉）**：搭建 Vue 3 + Tailwind 工程，实现 `Home.vue`（天气胶囊、双模式切换、情绪气泡、五维雷达图）、`Footprint.vue`（打卡与防腻看板）、`Profile.vue`（角色切换、忌口与红黑榜）及 `AlgoSandboxDrawer.vue`。
* **批次 3（虚拟冰箱 + 多人 WebSocket 干饭房间）**：实现 `Fridge.vue`（余料反推与买菜清单合并）及 `Room.vue`（扫码进房、15秒探探划卡组件与礼花揭晓大屏）。
* **批次 4（万级数据扩充 + PC 管理后台实验大屏 + APK 打包）**：运行高德采集、LLM 批量打标与 200 虚拟人仿真脚本，生成 PC 端 `DataManage.vue` 与 `ExperimentDashboard.vue`，最后通过 Capacitor/HBuilderX 一键打包输出 Android APK。**（v2.3.1 扩容）**：本批次另含——第五章模块 8 的 `/admin/stats/*` 统计接口组（12 个）、`ExperimentDashboard.vue` 全量 17 项图表与联动/下钻/导出功能（清单与版式见第六章 §5）、`DataManage.vue` 数据质量面板；大屏部分工作量显著大于原口径，须在 BATCH4_PLAN 中单独拆步，不得与数据扩充挤在同一步验收。
* **批次 5（网页展示版 + 移动端真机录屏，v2.3 新增，收尾批次）**：**前置条件：批次 1–4 全部完成、功能冻结后才开工，严禁提前或双线维护。** 在同一 Vue 工程内新增桌面壳路由（如 `/showcase/*`，顶部/侧边导航 + 内容区），聚合移动端全部页面与 PC 后台全部页面供答辩投屏展示：多数移动页面在内容区限宽居中原样呈现，仅首页、共识揭晓、实验大屏做横屏扩展；严禁另起工程复制代码、严禁逐页重排桌面布局。同步录制一份移动端真机使用视频（建房 → 划卡 → 揭晓完整流程）作为移动端效果的答辩交代与兜底。桌面端定位至此定案：**管理后台 + 网页展示版**，不做独立桌面用户端；论文中展示版表述为「答辩演示聚合端」，不得虚构为第三个产品端。实施护栏详见 `MOBILE_VISUAL_SPEC.md` §5.4。

---

## 附录 A、 项目背景、立意与交付形态选型理由（v2.1 新增）

### A.1 项目背景与核心痛点

* **选题来源**：源于日常生活里每天反复出现的真实提问——“中午吃什么”。该问题频率高、共鸣强，且长期无好的数字化解法。
* **深层立意（论文绪论可用）**：困境的本质不是没有选择，而是**选择过载 (Choice Overload)**——周边数千家门店、上万道菜谱同时涌向决策者，叠加预算、天气、身体状态、近期重复、他人忌口等多重隐性约束，导致决策成本极高；多人场景下个体偏好冲突进一步放大为“随便”式决策死锁。本系统要解决的不是“随机选一道菜”，而是**在多维约束下做可解释的智能决策**。
* **与同类简单方案的区别**：随机大转盘无约束、无记忆；普通菜谱应用只有 CRUD，无上下文感知、无防腻、无群组博弈。本系统的差异化即第二至四章的算法引擎。

### A.2 交付形态选型：移动端响应式 Web (H5) + Android APK，不做微信小程序

| 方案 | 结论 | 理由 |
| --- | --- | --- |
| 微信小程序 | ❌ 不采用 | 需 30 元认证费、企业/个体资质与 ICP 备案（周期约半个月至一个月）、平台审核约束多，与毕设周期不匹配 |
| 独立原生 App | ❌ 不采用 | 开发成本高，AI 辅助生成成功率低 |
| **响应式 Web (H5) + Capacitor/HBuilderX 套壳 APK** | ✅ 采用 | AI 写 Web 代码成功率最高、调试最快；H5 扫码即用便于答辩演示；套壳打包零成本生成 APK 便于分发；避开备案与审核 |

---

## 附录 B、 双模型协作开发流程（v2.1 新增）

开发分工锁定为“**强模型 = 总指挥/架构师/审查者，国产模型 = 主力施工者**”，严禁颠倒或混用：

1. **强模型定契约（只出图纸，不写大段业务代码）**：输出目录结构、数据库表设计、API Schema、算法数学伪代码；一切以本文档为准，本文档未定义的命名先回本文档增补再开发。
2. **强模型拆原子级施工单**：把每个模块拆成单文件、单功能的提示词交给国产模型执行，施工单必须写明输入/输出格式、类型注解要求与边界条件（参考口径：“实现 `recommender.py` 的某函数，包含完整类型注解和内置模拟数据”）。
3. **国产模型流水线施工**：在契约锁死的前提下逐文件生成代码，一次通过率目标 90% 以上；不得让国产模型自行改表名、字段名、接口路径。
4. **强模型 Code Review 与疑难排错**：每批次产物必须回强模型审查后才放行下一批次；WebSocket 并发、博弈算法等难点直接由强模型处理。
5. **上下文防丢失纪律**：新开任何 AI 会话，第一件事投喂本文档 (MASTER_SPEC) 再下施工单；文档与代码冲突时以文档为准，先改文档再改代码。

---

## 附录 C、 LLM 批量打标提示词契约（v2.1 补全）

`llm_batch_tagger.py` 每次打包 20 道菜品调用国产大模型 API，System Prompt 锁定如下，后续开发不得自行改写核心约束（输出字段与取值范围）：

```text
你是一个中式餐饮营养学与风味特征工程专家。请根据输入的菜品名称、分类与主辅料，为每道菜评估 8 个维度的标准化特征分值，并判断其套餐搭配角色。
8 个维度键名固定为：spicy_level, oily_level, soup_level, temp_fit, satiety_level, prep_speed, social_fit, comfort_level，取值范围严格在 0.0 到 1.0 之间的小数。
套餐搭配角色 dish_role 只能从 MEAT / VEG / SOUP / ONE_MEAL 中选一。
同时识别并输出该菜品命中的常见过敏原/忌口标签数组 allergen_tags（如：香菜、海鲜、花生、葱姜蒜）。
只输出 JSON 数组，不要输出任何解释文字；数组元素字段固定为：dish_name, dish_role, feature_vector{8个键}, allergen_tags[]。
```

* 输入格式：JSON 数组，每元素含 `name`、`cuisine_type`、`ingredients_main`、`ingredients_aux`。
* 入库校验：返回 JSON 解析失败、键名缺失或数值越界的批次整批重试，最多 3 次，仍失败则记录到失败清单人工处理，严禁用默认值蒙混入库。

---

## 附录 D、 论文章节与答辩亮点映射（v2.1 新增）

| 论文/答辩环节 | 对应本系统内容 |
| --- | --- |
| 绪论/研究背景 | 附录 A：选择过载、多人决策死锁、清库存痛点 |
| 需求分析 | 第一、二章的双模式场景 + “5+2”功能模块全景 |
| 系统设计 | 第一章目录契约、第三章 9 张表、第五章接口与 WebSocket 协议 |
| 核心算法（创新点） | 第四章四大算法：防腻时间衰减、多维上下文效用、Least Misery 群组博弈、组合优化 |
| 实验与结果分析（第五章） | 第七章仿真数据：14 天菜系重样率对比曲线、群组满意度与 Least Misery Score 对比 |
| 答辩演示亮点 | ①算法沙盒抽屉实时调参看排名变化 ②多人房间 15 秒划卡 + 共识揭晓 ③用户主页一键切换演示角色 ④五维雷达图可解释推荐 ⑤（v2.3）网页展示版聚合全部功能投屏演示 + 移动端真机录屏交代移动端效果（见第八章批次 5） ⑥（v2.3.1）17 图数据与实验大屏：POI 地图热力、人设雷达、决策桑基等真实数据可视化 + 图表导出 PNG 直接进论文第五章（见第六章 §5） |
| 开题报告核心亮点口径 | 多维上下文感知（非随机抽签）、群组偏好博弈（非简单均值）、万级多源数据工程（非手工造数）、双模型 AI 协作开发流程（方法论创新） |
