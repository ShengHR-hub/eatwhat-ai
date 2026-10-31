# 《食刻 (EatWhat AI)》系统架构与全量开发主契约 (MASTER_SPEC v2.1.1)

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
> 9. **v2.1.1 决议修订（2026-10-23，用户拍板 10 条落地决议，强制锁死）**：
>   ① 仿真流水口径锁定 `200 人 × 60 天 × 每日午晚 2 餐 = 24,000 条`（见第七章 3）；
>   ② 划卡分值统一为百分制刻度 `SUPER_LIKE=120.0 / LIKE=100.0 / PASS=40.0 / VETO=-999.0`，超时未滑默认 `60.0`，废除表 8 旧 `[+1.0/+1.5/0.2]` 写法；
>   ③ `appliance_tag` 枚举扩为 5 项并补 `一锅出`，`lazy_one_pot` 筛选锁定 `IN ('电饭煲','一锅出','免开火凉拌')`；
>   ④ 红黑榜唯一粒度锁定为菜品/套餐 `dish_id`，不设独立店铺黑榜；
>   ⑤ 管理后台补齐门店/菜品 CRUD 与高德同步路由（见第五章）；
>   ⑥ `group_rooms` 新增 `member_user_ids`，新增 `POST /rooms/{room_code}/join`，初筛时机改为房主触发 `START_SWIPING` 时；
>   ⑦ 身份传递锁定请求头 `X-User-Id`（缺省回退 `1`），新增 `POST /auth/login`；
>   ⑧ `algo_configs` 四权重锁定 `FLOAT NOT NULL`，天气接口锁定高德天气 API + `temp/weather` 离线参数，`benchmark_json` 结构锁定（见第三章表 9）；
>   ⑨ LLM 打标 `allergen_tags` 去重合并进 `ingredients_aux`，输入输出统一以 `dish_id` 对齐；
>   ⑩ 算法 4 升级为真分支限界（Branch-and-Bound）求解（见第四章算法 4）。

---

## 0. AI 协同开发最高铁律

1. **命名绝对锁定**：所有数据库表名、字段名、JSON 键名、API 路由路径、WebSocket 事件名及 8 维特征向量键名，必须 100% 严格遵循本文档，严禁自行缩写、改名或发明新字段。
2. **双模式底层同源**：外食模式 (`OUT_DINING`) 与下厨模式 (`HOME_COOKING`) 在算法层共享同一套 8 维特征向量结构与防腻衰减函数，严禁拆分为两套互不兼容的推荐逻辑。
3. **白盒可解释与实时调参**：推荐接口必须返回五维雷达图分项得分与归因文案；所有算法超参数 (`lambda_decay`, `omega_group`, `alpha`, `beta`, `gamma`, `delta`) 必须支持请求参数动态覆盖，以支撑前端“算法上帝视角调试抽屉”。
4. **60fps 动效与交付规范**：后端采用 Python (`FastAPI` + `Pydantic` + `SQLAlchemy`)；前端采用 `Vue 3 (<script setup>)` + `Tailwind CSS` + `ECharts`，强制集成 `@formkit/auto-animate`、`@vueuse/motion`、`canvas-confetti`、**Lottie (`lottie-web` / `@lottiefiles/dotlottie-vue`)** 与 **`gsap`（含 Draggable 插件，100% 免费含商用）** 现成动效库，严禁用 AI 手写 CSS 动画冒充上述库的效果。分工锁定：简单弹性动效用 `@vueuse/motion`，列表过渡用 `auto-animate`，**划卡拖拽与揭晓编排专用 GSAP**，不得混用重复造轮子。

### 0.5 v2.1 正式锁定的形式化决策

以下三处在原始讨论中只有方向性说法，v2.0 将其形式化，v2.1 起正式锁定：

1. **双模式主色**：外食模式暖橙 `from-orange-500 to-amber-500`；下厨模式森林绿 `from-emerald-600 to-teal-500`。
2. **群组算法权重配比**：个体满意度 `R[u, i] = 0.4 * prior_score + 0.6 * swipe_score`（见算法 3）。
3. **预算分与临期提权公式**：`budget_score` 公式与冰箱临期食材（`expire_days <= 2`）覆盖率双倍提权（见算法 2 与第六章）。

### 0.6 v2.1.1 十项补充锁定（2026-10-23，用户拍板，与 0.5 同级）

1. **仿真流水**：`200 名虚拟大学生 × 60 天 × 每日午晚 2 餐 = 24,000 条 eating_logs`；与 `1,000 场 × 4 人 × 10 张 = 40,000 条 room_votes` 严格对齐。
2. **划卡刻度**：全系统 `swipe_score` 百分制：`SUPER_LIKE=120.0`、`LIKE=100.0`、`PASS=40.0`、`VETO=-999.0`；15 秒超时未滑按 `60.0` 计。
3. **厨具枚举**：`炒锅 | 电饭煲 | 一锅出 | 空气炸锅 | 免开火凉拌`（默认 `炒锅`）；`lazy_one_pot` 筛选 `appliance_tag IN ('电饭煲','一锅出','免开火凉拌') AND prep_speed >= 0.7`。
4. **红黑榜粒度**：唯一粒度 `dish_id`，`favorite_dish_ids` / `blacklist_dish_ids` 不变，前端展示菜品/套餐名（外食附门店名）。
5. **管理后台 CRUD**：`/admin/restaurants`、`/admin/dishes` 各四个方法 + `POST /admin/sync-amap`。
6. **进房与初筛**：`group_rooms.member_user_ids`（JSON, NOT NULL, 默认 `[]`，建房初始化为 `[host_user_id]`）；`candidate_dish_ids` 在 `WAITING` 允许 `[]`；`POST /rooms/{room_code}/join` 去重入房并广播 `MEMBER_SYNC`；房主触发 `START_SWIPING` 时才按全体成员忌口并集初筛 Top-10 落库。
7. **身份协议**：请求头 `X-User-Id: <int>` 为全局当前角色，缺省回退 `1`；路由显式 `user_id` 优先；`POST /auth/login` 提供基础登录。
8. **表 9 与天气**：四权重 `FLOAT NOT NULL`；天气走高德 `https://restapi.amap.com/v3/weather/weatherInfo`，支持 `?temp=&weather=` 或离线回退；`benchmark_json` 结构见第三章表 9。
9. **LLM 打标合并**：`allergen_tags` 去重后并入 `ingredients_aux`，输入输出主键统一 `dish_id`。
10. **算法 4**：`combo_optimizer.py` 使用分支限界搜索预算、角色配比、平均油腻度约束下的最优套餐。

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
    ├── tailwind.config.js          # 暖色食欲感主题色与毛玻璃动效配置
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
| `lazy_one_pot` | 🍚 只有电饭煲/不想洗碗 | 下厨 | 仅筛选 `appliance_tag IN ('电饭煲','一锅出','免开火凉拌')` 且 `prep_speed>=0.7` 的菜谱 |

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
* `blacklist_dish_ids` (JSON, **黑榜踩雷拉黑菜品 ID 数组**，在单人与多人推荐中永久一票否决)


3. **`restaurants`（周边真实门店与校园食堂档口表）**
* `id` (INT, PK), `name` (VARCHAR), `source_type` (`AMAP_POI` | `CANTEEN`), `category` (VARCHAR)
* `avg_price` (FLOAT), `rating` (FLOAT, 默认 `4.5`), `longitude` (FLOAT), `latitude` (FLOAT)（经纬度统一采用高德 `GCJ-02` 坐标系，严禁混入 WGS-84）
* `distance_meters` (INT, 距学校中心步行距离, 默认 `500`), `address` (VARCHAR)


4. **`dishes_and_recipes`（菜品与家常菜谱核心主表）**
* `id` (INT, PK), `name` (VARCHAR), `mode_type` (`OUT_DINING` | `HOME_COOKING`)
* `restaurant_id` (INT, FK `restaurants.id`, 下厨模式为 `NULL`), `cuisine_type` (VARCHAR)
* `dish_role` (`MEAT` | `VEG` | `SOUP` | `ONE_MEAL`), `price_or_cost` (FLOAT), `cook_minutes` (INT, 默认 `15`)
* `appliance_tag` (`炒锅` | `电饭煲` | `一锅出` | `空气炸锅` | `免开火凉拌`, 默认 `炒锅`)
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
* `id` (INT, PK), `room_code` (VARCHAR(10), UNIQUE, 6位邀请码), `host_user_id` (INT, FK)
* `mode_type` (`OUT_DINING` | `HOME_COOKING`), `status` (`WAITING` | `SWIPING` | `FINISHED`)
* `member_user_ids` (JSON, NOT NULL, 默认 `[]`; 建房时初始化为 `[host_user_id]`, 进房去重追加)
* `candidate_dish_ids` (JSON, 初筛10道候选ID; `WAITING` 阶段允许为空数组 `[]`, 房主触发 `START_SWIPING` 时初筛落库), `winner_dish_id` (INT, NULLABLE)
* `consensus_report` (JSON, 群组平均分、最低分及各成员妥协度明细), `created_at` (DATETIME)


8. **`room_votes`（房间实时划卡表决记录表）**
* `id` (INT, PK), `room_code` (VARCHAR, FK), `user_id` (INT, FK), `dish_id` (INT, FK)
* `vote_type` (`LIKE` | `SUPER_LIKE` | `PASS` | `VETO`), 映射百分制 `swipe_score`: `LIKE=100.0`, `SUPER_LIKE=120.0`, `PASS=40.0`, `VETO=-999.0`; 15 秒超时未滑按 `60.0` 计, `voted_at` (DATETIME)


9. **`algo_configs`（算法超参数与实验对比表）**
* `id` (INT, PK), `config_name` (VARCHAR, 默认 `default_production`)
* `lambda_decay` (FLOAT, 默认 `0.5`), `omega_group` (FLOAT, 默认 `0.5`)
* `alpha_taste` (FLOAT NOT NULL, 默认 `0.35`), `beta_weather` (FLOAT NOT NULL, 默认 `0.25`), `gamma_budget` (FLOAT NOT NULL, 默认 `0.20`), `delta_status` (FLOAT NOT NULL, 默认 `0.20`)
* `benchmark_json` (JSON, 存储仿真实验对比数据供 PC 后台与论文第五章直接渲染 ECharts), 结构锁定为:

```json
{
  "exp1_duplication_curve": {
    "days": ["Day1", "Day2", "Day3", "Day4", "Day5", "Day6", "Day7", "Day8", "Day9", "Day10", "Day11", "Day12", "Day13", "Day14"],
    "no_decay_rate": [0.15, 0.28, 0.39, 0.45, 0.50, 0.54, 0.58, 0.60, 0.62, 0.63, 0.65, 0.66, 0.67, 0.68],
    "cooldown_filter_rate": [0.08, 0.14, 0.21, 0.25, 0.28, 0.30, 0.31, 0.32, 0.33, 0.34, 0.34, 0.35, 0.35, 0.36],
    "ebbinghaus_decay_rate": [0.04, 0.07, 0.09, 0.11, 0.12, 0.13, 0.14, 0.14, 0.15, 0.15, 0.16, 0.16, 0.16, 0.17]
  },
  "exp2_group_satisfaction": {
    "strategies": ["随机抽签 (Random)", "纯均值策略 (ω=1.0)", "纯最小痛苦 (ω=0.0)", "本系统混合博弈 (ω=0.5)"],
    "avg_satisfaction": [52.4, 84.6, 76.2, 83.1],
    "least_misery_score": [28.5, 54.0, 74.8, 76.5]
  }
}
```



---

## 四、 四大核心算法数学公式与实现逻辑

### 算法 1：跨场景防腻时间衰减模型 (`time_decay.py`)

查询用户近 14 天的 `eating_logs`。同款菜品 (`dish_id` 相同) 间隔天数记为 `dt_exact`，同菜系 (`cuisine_type` 相同) 或同主料 (`ingredients_main` 有交集) 间隔天数记为 `dt_similar`：

```python
W_decay = (1.0 - math.exp(-lambda_decay * dt_exact)) * (1.0 - 0.4 * math.exp(-lambda_decay * dt_similar))
```

* 若当天刚吃过 (`dt_exact == 0`)，强制设 `W_decay = 0.05`；若 14 天内未吃过，设 `W_decay = 1.0`。

### 算法 2：多维上下文单人推荐与红黑榜修正 (`single_recommender.py`)

1. **硬性红线过滤**：剔除 `ingredients_main / aux` 命中用户 `veto_tags`、菜品 ID 在用户 `blacklist_dish_ids`（黑榜）中、或超出距离限制的候选菜品。
2. **五维效用计算（归一化至 `0 ~ 100` 分，直接对应前端五维雷达图）**：
* `taste_score`: 用户 `base_vector` 与菜品 `feature_vector` 的余弦相似度映射至 `[0, 100]`。
* `weather_score`: 根据实时气温与降雨生成理想环境向量，计算匹配度。
* `budget_score`: 若 `price <= budget`，得分为 `85 + 15 * (1 - price / budget)`；若超支则按比例指数扣分。
* `freshness_score`: 直接等于 `W_decay * 100`。
* `status_score`: 外食模式计算对当前所选“情绪气泡”的满足度；下厨模式计算菜品主料命中 `fridge_inventory`（临期食材 `expire_days <= 2` 权重翻倍）的覆盖率。


3. **红榜提权与综合得分合成**：
```python
boost_fav = 1.15 if dish.id in user.favorite_dish_ids else 1.0
raw_score = W_decay * (alpha * taste_score + beta * weather_score + gamma * budget_score + delta * status_score) * boost_fav
total_score = round(min(100.0, raw_score), 1)
```
4. **权重归一化与封顶规则（v2.1.1 收尾拍板，强制锁定）**：
* 应用状态气泡的 `param_overrides` 与请求 `override_params` 后，对 `alpha_taste / beta_weather / gamma_budget / delta_status` 四权重做**和为 `1.0` 的归一化**（负值先截断为 `0`；四者全为 `0` 时回退默认配比），保证五维加权基础分严格落在 `[0, 100]`。
* 候选列表**先按未截断的 `raw_score` 降序排序**（保留 `W_decay` 与红榜 `1.15x` 的排序区分度），仅在输出 `total_score` 字段时执行 `round(min(100.0, raw_score), 1)` 封顶。
* 组合优化（算法 4）内部使用 `raw_score` 作为目标函数，不使用封顶后的展示分。



### 算法 3：融合最小痛苦策略的群组协同博弈算法 (`group_recommender.py`)

1. **阶段一（建房初筛 Top-10）**：取房间内所有成员 `veto_tags` 与 `blacklist_dish_ids` 的并集进行一票否决过滤，基于成员静态 `base_vector` 均值选出 Top-10 候选菜品下发至各端用于 15 秒划卡。
2. **阶段二（15 秒实时划卡后的博弈定夺）**：
* 成员 `u` 对菜品 `i` 的个体满意度：`R[u, i] = 0.4 * prior_score[u, i] + 0.6 * swipe_score[u, i]`。
* **划卡百分制刻度（v2.1.1 锁定）**：`SUPER_LIKE=120.0`, `LIKE=100.0`, `PASS=40.0`, `VETO=-999.0`；15 秒超时未滑默认按 `60.0` 计。`VETO` 不参与 `R` 的加权，只作用于 `Mask_veto`。
* 若任意成员投出 `VETO`，则 `Mask_veto(i) = 0`，否则为 `1`。
* 群组博弈共识分计算（结合 Average 均值策略与 Least Misery 最小痛苦策略）：
```python
G_score(i) = Mask_veto(i) * (omega_group * mean(R[:, i]) + (1.0 - omega_group) * min(R[:, i]))
```





### 算法 4：一餐多菜品组合优化与买菜差额清单 (`combo_optimizer.py`)

当开启“一荤一素一汤套餐模式”时，从单品得分 Top-20 中按 `dish_role` 分别建立 `MEAT` / `VEG` / `SOUP` 候选集，使用**分支限界（Branch-and-Bound）**搜索最优组合：以已选菜品得分之和为目标函数，按候选得分降序 DFS，用“当前和 + 剩余角色各自最高分”作乐观上界剪枝；硬约束为总价 `<= budget` 且三道菜平均 `oily_level <= 0.65`（荤素冷热互补）。禁止用三重循环全枚举冒充分支限界。在下厨模式下，自动计算 `菜谱所需主辅料并集 - 冰箱现有食材集合`，输出合并同类项后的《待采购买菜清单》。

---

## 五、 前后端接口契约（RESTful API 与 WebSocket 协议）

### 1. RESTful API 路由总表（前缀 `/api/v1`）

| 所属模块 | 请求路径 | 功能描述 | 核心请求体 / 参数 | 核心响应内容 |
| --- | --- | --- | --- | --- |
| **模块1：用户与主页** | `POST /auth/login` | 基础登录（演示环境免密） | `username` | `user_id`, `nickname`, `persona_title` |
|  | `GET /users/demo-list` | 获取预设演示角色列表 | 无 | `users[]`（含人设称号、头像、口味基因） |
|  | `GET /users/{id}/profile` | 获取用户主页完整数据 | `user_id` | 基因向量、忌口、红黑榜详情、干饭成就战绩统计 |
|  | `PUT /users/{id}/preferences` | 更新基因、预算与忌口胶囊 | `base_vector`, `default_budget`, `veto_tags[]` | 更新后的 `user_preferences` |
|  | `POST /users/{id}/red-black-list` | 增删美食红榜(收藏)或黑榜(拉黑) | `dish_id`, `list_type` (`FAV` \| `BLACK`), `action` | 更新后的 `favorite_dish_ids`, `blacklist_dish_ids` |
| **模块2：单人决策** | `GET /context/weather` | 获取顶部环境胶囊实时数据（高德天气 API，支持 `?temp=12&weather=小雨` 离线覆盖） | `city` 或 `lat, lng`；可选 `temp`, `weather` | `temp`, `weather_text`, `capsule_tip` |
|  | `POST /recommend/single` | **单人双模式智能推荐核心接口** | `user_id`, `mode_type`, `budget`, `bubbles[]`, `combo_mode`, `override_params` | `recommendations[]`（含 `total_score`, `radar_5d`, `explain_reason`） |
| **模块3：虚拟冰箱** | `GET /fridge/{user_id}` | 获取冰箱库存（临期置顶） | `user_id` | `items[]`（含 `is_expiring_soon` 布尔标识） |
|  | `POST /fridge/{user_id}` | 录入/删除冰箱食材 | `ingredient_name`, `category`, `expire_days` | 更新后的库存列表 |
|  | `POST /fridge/shopping-list` | 多菜谱智能合并买菜清单 | `user_id`, `dish_ids[]` | `owned_ingredients[]`, `to_buy_ingredients[]` |
| **模块4：多人房间** | `POST /rooms/create` | 创建多人干饭房间 | `host_user_id`, `mode_type`, `budget` | `room_code` (6位码), `candidate_dishes[]`（`WAITING` 阶段可为空） |
|  | `POST /rooms/{room_code}/join` | 扫码进房 | `user_id` | 更新后的 `members[]`；同时广播 `MEMBER_SYNC` |
|  | `GET /rooms/{room_code}` | 获取房间状态与共识揭晓报告 | `room_code` | 房间详情、`members[]`、`winner_dish`、`consensus_report` |
| **模块5：饮食足迹** | `POST /logs/checkin` | 点击“就吃这个”一键打卡 | `user_id`, `dish_id`, `mode_type`, `bubbles[]` | `log_id`, `new_decay_weight` |
|  | `GET /logs/stats/{user_id}` | 防腻冷却看板与周度干饭报告 | `user_id` | `cooling_dishes[]`, `weekly_expense`, `cuisine_pie_data[]` |
| **模块6&7：管理后台** | `GET /admin/restaurants` | 门店列表（分页/关键词） | `page`, `page_size`, `keyword` | `restaurants[]`, `total` |
|  | `POST /admin/restaurants` | 新增门店 | 门店字段 | 新建门店 |
|  | `PUT /admin/restaurants/{id}` | 编辑门店 | 门店字段 | 更新后的门店 |
|  | `DELETE /admin/restaurants/{id}` | 删除门店 | `id` | `{"ok": true}` |
|  | `GET /admin/dishes` | 菜品/菜谱列表（分页/模式筛选） | `page`, `page_size`, `mode_type`, `keyword` | `dishes[]`, `total` |
|  | `POST /admin/dishes` | 新增菜品/菜谱 | 菜品字段 | 新建菜品 |
|  | `PUT /admin/dishes/{id}` | 编辑菜品/菜谱 | 菜品字段 | 更新后的菜品 |
|  | `DELETE /admin/dishes/{id}` | 删除菜品/菜谱 | `id` | `{"ok": true}` |
|  | `POST /admin/sync-amap` | 按经纬度/关键词同步高德 POI | `lat`, `lng`, `keywords`, `radius` | `created`, `updated`, `skipped` |
|  | `POST /admin/llm-tag` | 调用国产模型批量蒸馏8维向量 | `dish_ids[]` | 生成的 `feature_vector` 数组及入库状态 |
|  | `GET /admin/experiments` | 获取算法仿真对比曲线数据 | `lambda_val`, `omega_val` | `duplication_rate_curve`, `group_satisfaction_bars` |

### 1.1 身份传递协议（v2.1.1 锁定）

* 前端全局通过请求头 `X-User-Id: <int>` 传递当前激活的用户/演示角色 ID；**未传时回退为 `1`**。
* 若路由或请求体显式携带 `user_id`，以显式值为准；两者冲突时显式优先。
* WebSocket 连接沿用路径参数 `{user_id}`，不读请求头。

### 2. 多人房间 WebSocket 实时协议 (`ws://{host}/ws/room/{room_code}/{user_id}`)

* `MEMBER_SYNC` (服务端广播): 成员扫码进房/准备状态更新，`members: [{user_id, nickname, avatar, progress}]`。
* `START_SWIPING` (房主触发 -> 全员广播): 同步开启 15 秒倒计时与 10 张探探式划卡堆叠。
* `SUBMIT_VOTE` (客户端上报): `{"type": "SUBMIT_VOTE", "dish_id": 108, "vote_type": "LIKE"}`。
* `PROGRESS_UPDATE` (服务端广播): 实时同步各室友划卡进度（如 `8/10`）。
* `CONSENSUS_REVEAL` (服务端广播): 全员完成或倒计时结束，广播博弈获胜菜品及各成员妥协照顾度报告，触发全屏礼花。

---

## 六、 前端 UI/UX 视觉规范、用户主页与 60fps 动效工程

### 1. 全局色彩与视觉質感（参考 `60fps.design` / `iconly.design` / `backgrounds.supply`）

* **色彩令牌**：背景采用温暖奶油白 `bg-[#FFFDF9]` 与噪点流体渐变 (Grainy Gradient)；外食模式主色为食欲暖橙 `from-orange-500 to-amber-500`；下厨模式主色为清新森林绿 `from-emerald-600 to-teal-500`。
* **背景构造法锁定为「现成纹理底 + 高透明罩色」（v2.1 补充修订，用户拍板）**：禁止用纯 CSS/AI 生成的单调渐变色充当整个背景。标准做法分两层：
  1. **纹理底层（现成素材）**：从 `backgrounds.supply` 免费区（邮箱登录、免绑卡）选定以下三张之一作纹理底——`Smudge` 系列暖珊瑚+奶油笔触图（颗粒笔触感最强）、`Etherial` 系列暖琥珀柔光+磨砂玻璃质感图、`Iridescence` 系列浅底粉彩波浪丝带图（最浅最干净）。素材均为约 3K 的 16:9 PNG，移动端使用时裁剪为竖屏构图。
  2. **罩色层（统一色调）**：纹理底之上罩一层高透明度的项目令牌色（以奶油白 `#FFFDF9` 为主，透明度约 70%~85%，只透出隐约纹理），使质感来自现成素材、色调归本项目令牌；食物照片与白色卡片仍是页面视觉主体，背景严禁抢色。
  3. **AI 只许改色、不许造底**：`Iridescence` 波浪丝带原图为粉紫色调，与本项目色不贴时，用 AI 图像工具仅做色相迁移——保留其波形、光泽与浅底质感，分别改出暖橙版（外食模式）与鼠尾草绿版（下厨模式）两张派生图，两模式背景同源同形、只换色相；严禁用 AI 整张新生成背景替代现成素材的质感。原图与派生图统一存放于前端 `src/assets/backgrounds/` 下，按 `texture-smudge / texture-etherial / texture-wave-orange / texture-wave-sage` 命名。
* **背景素材授权备注**：上述免费图授权为仅限个人使用，其 FAQ 将 apps 列入 $49 商业授权范围，措辞存在模糊地带。本项目为不售卖的毕业设计演示，按个人使用处理并在此留痕；若后续转为商业发布，必须先更换为自有/已授权素材或购买其 $49 一次性商业授权，`$49` 付费包现阶段不购买。
* **卡片规范**：统一采用 Bento Grid 便当盒大圆角布局 (`rounded-3xl`) + 弥散柔光阴影 (`shadow-[0_8px_30px_rgb(0,0,0,0.04)]`) + 圆润双色图标。

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

顶部天气胶囊的毛玻璃/液态玻璃质感**不凭模型想象手写 CSS**，锁定以下免费工作流：

1. 打开 Apple 官方发布的 Figma 社区文件「macOS 27 | Figma」（Apple Design Resources，免费复制）：`https://www.figma.com/community/file/1651309434229735362/macos-27`
2. 在文件中找到 **Material 页的玻璃材料**，选中后 `Copy as code → CSS (all layers)`。
3. 把复制出的 CSS 粘给施工模型，要求其参照该 CSS 的模糊、折射边缘与高光参数实现 `WeatherPill.vue` 的胶囊、悬浮菜单与托盘质感，并映射到本项目 Tailwind 令牌上。
4. **禁用路线**：GitHub 上的 Liquid Glass 类开源复刻项目实测效果不佳，不作为实现基础；施工模型不得自行引入此类库。

### 2.7 小控件指定来源：按钮 / 开关 / 滑块 / 气泡（v2.1 补充修订，用户拍板）

按钮、开关等小控件**一律用现成组件设计，严禁施工模型凭想象手写样式**。指定来源如下（均已实地核验为免费）：

**主力来源：`daisyUI`（MIT 免费，Tailwind 纯 CSS 插件，零 JS 依赖，框架无关）**
| 本项目控件 | 指定 daisyUI 组件 | 说明 |
| --- | --- | --- |
| 普通按钮 | `btn` | 主按钮再叠加本项目渐变令牌 |
| 双模式分段开关 `ModeSwitcher` | `filter`（一组 radio，选中高亮） | 语义正对外食/下厨二选一 |
| 开关（Toggle） | `toggle` | 忌口、设置类开关 |
| 预算滑块 / 算法沙盒滑块 | `range` | 轨道与手柄颜色取主题令牌 |
| 状态气泡 `StatusBubbles` | `filter` / `badge` 组合 | 选中态高亮沿用模式色 |
| 卡片与小徽章 | `card` / `badge` | 只用其结构类，圆角阴影仍服从第六章 1 的卡片规范 |

**特效补充来源：`Inspira UI`（Vue 原生，开源免费）**
* 全 App 唯一的主 CTA 按钮（“开始智能决策”）直接使用其 **Shimmer Button**（或 Gradient Button）现成实现，不再手写流光效果。

**呼应规则（硬约束）**：daisyUI 只许通过**一套自定义主题**接入——在其主题变量中把 `primary` 定为外食暖橙、`secondary` 定为下厨鼠尾草绿、`base` 定为奶油白，与背景「纹理底 + 罩色」同源取色；所有控件颜色只能引用主题/令牌变量，**严禁在组件代码里写死任何十六进制颜色**。这样按钮、开关与背景天然呼应，后续调色只改主题一处。

**不作指定来源**：`shadcn-vue` 覆盖虽全且换色机制好，但属自建组件库模式、默认风格中性且无现成流光按钮，暂不引入，后续确需无障碍原语时再评估；`uiverse.io` 量大（7400+）但质量参差、颜色逐个写死，只许作单个特效灵感参考，不得整站照搬；`hyperui` / `flowbite-vue` 控件齐全但风格偏朴素后台风，不采用。

### 3. 用户主页 (`Profile.vue`) 四大核心区块规范

1. **顶部人设卡与“答辩演示角色一键切换器”**：展示当前头像、昵称、饮食人设称号（如“川渝无辣不欢星人”），右上角设 `🔄 切换演示室友账号` 快捷胶囊，点击秒切预设账号以方便答辩演示。
2. **我的饮食基因与忌口红线控制台**：八维口味偏好可视化进度条 + 日常默认预算滑块 + 支持随时点击增删的“绝对忌口/过敏原”胶囊管理区（配 `v-auto-animate` 动效）。
3. **美食红黑榜（宝藏收藏夹 vs 踩雷黑名单）**：双 Tab 切换展示用户收藏的红榜菜品/套餐（提示“推荐时享 1.15x 提权”）与拉黑的黑榜菜品/套餐（提示“单人及多人拼单已永久一票否决”），外食模式附带展示所属门店名；唯一粒度锁定 `dish_id`，不设独立店铺黑榜，支持一键移出。
4. **个人干饭成就与战绩概览**：展示累计解决“吃什么”世纪难题次数、本月外食与下厨花费占比环形图、以及历史参与的“多人干饭房间”拼单战绩记录。

### 4. 答辩演示专属组件：`AlgoSandboxDrawer.vue`（右上角算法上帝视角抽屉）

* 移动端右上角常驻 `🛠️ 算法沙盒` 悬浮按钮，拉开后提供 4 个实时滑块：`防腻衰减系数 λ (0.1~2.0)`、`群组折中系数 ω (0.0~1.0)`、`天气权重 β`、`预算权重 γ`。拖动滑块实时重算并触发主界面排名动画与五维雷达图面积变形。

---

## 七、 万级数据工程与仿真实验规范（支撑论文第五章）

1. **真实周边门店 + 开源菜谱底座 (`fetch_amap_poi.py` & `import_open_recipes.py`)**：
* 调用高德 Web 服务 API (`https://restapi.amap.com/v3/place/around`) 抓取高校周边 3km 内餐饮 POI（约 1,500+ 真实门店）及 200 个校园食堂窗口；导入开源中式家常菜谱数据集（约 6,300 ~ 8,000 道菜谱），三项合计构建 **8,000 ~ 9,700+ 条** 基础数据。
* **口径说明（v2.1 修正）**：v2.0 中菜谱只写 5,000+，三项相加仅约 6,700 条，与宣称的 8,000~10,000+ 对不上；v2.1 将菜谱目标上调至 6,300~8,000 道使总量成立。对外汇报（论文/答辩）统一使用本节口径，严禁再引用 v2.0 的旧数字。


2. **国产大模型批量特征蒸馏 (`llm_batch_tagger.py`)**：
* 异步批处理脚本每次打包 20 道菜品调用国产大模型 API，自动输出 `dish_role` 与 8 维 `feature_vector` 浮点数 JSON 并入库（累计生成 **60,000+ 个** 细粒度特征值）。


3. **多智能体仿真实验生成器 (`simulate_personas.py`)**：
* 构建 **200 个不同口味人设的虚拟大学生**，模拟连续 **60 天饮食打卡流水（200 × 60 天 × 每日午晚 2 餐 = 24,000 条）** 与 **1,000 场四人寝室拼单投票（1,000 × 4 × 10 = 40,000 条）**。
* 自动计算并向 `algo_configs.benchmark_json` 写入两组核心实验数据（供 PC 后台与论文第五章直接出图）：
* **实验一**：本系统艾宾浩斯衰减 (`λ=0.5`) vs 无衰减传统推荐的 **连续 14 天菜系重样率对比曲线**。
* **实验二**：本系统混合博弈策略 (`ω=0.5`) vs 随机抽签 vs 纯均值策略 (`ω=1.0`) 的 **群组平均满意度与最挑剔成员最低满意度（Least Misery Score）柱状对比图**。





---

## 八、 分阶段 AI 指挥开发路线图（4 批次执行）

* **批次 1（后端数据库与算法内核）**：生成 `database.py`、`models.py`（9张表）、`algorithms/` 四大算法模块，以及内置 100 道真实菜品+门店+4个演示角色的种子脚本 `init_seed_data.py`，通过 FastAPI `/docs` 验证推荐与博弈计算输出。
* **批次 2（移动端单人双模式闭环 + 用户主页 + 算法沙盒抽屉）**：搭建 Vue 3 + Tailwind 工程，实现 `Home.vue`（天气胶囊、双模式切换、情绪气泡、五维雷达图）、`Footprint.vue`（打卡与防腻看板）、`Profile.vue`（角色切换、忌口与红黑榜）及 `AlgoSandboxDrawer.vue`。
* **批次 3（虚拟冰箱 + 多人 WebSocket 干饭房间）**：实现 `Fridge.vue`（余料反推与买菜清单合并）及 `Room.vue`（扫码进房、15秒探探划卡组件与礼花揭晓大屏）。
* **批次 4（万级数据扩充 + PC 管理后台实验大屏 + APK 打包）**：运行高德采集、LLM 批量打标与 200 虚拟人仿真脚本，生成 PC 端 `DataManage.vue` 与 `ExperimentDashboard.vue`，最后通过 Capacitor/HBuilderX 一键打包输出 Android APK。

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
只输出 JSON 数组，不要输出任何解释文字；数组元素字段固定为：dish_id, dish_name, dish_role, feature_vector{8个键}, allergen_tags[]。
```

* 输入格式：JSON 数组，每元素含 `dish_id`、`name`、`cuisine_type`、`ingredients_main`、`ingredients_aux`。
* **主键与合并规则（v2.1.1 锁定）**：输入输出统一以 `dish_id` 对齐；返回的 `allergen_tags` 先去重，再合并进表 4 `dishes_and_recipes.ingredients_aux` 数组（与已有辅料去重并集），不单独建表。
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
| 答辩演示亮点 | ①算法沙盒抽屉实时调参看排名变化 ②多人房间 15 秒划卡 + 共识揭晓 ③用户主页一键切换演示角色 ④五维雷达图可解释推荐 |
| 开题报告核心亮点口径 | 多维上下文感知（非随机抽签）、群组偏好博弈（非简单均值）、万级多源数据工程（非手工造数）、双模型 AI 协作开发流程（方法论创新） |
