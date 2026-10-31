# 食刻 EatWhat AI

面向高校学生的「今天吃什么」决策系统 —— 本科毕业设计作品。

一个人时它替你决定吃哪一顿；宿舍多人时它把五个人的口味求成一个交集；冰箱里有快过期的食材，它先把它们排到前面。移动端（`/m/*`）负责吃饭的决策，PC 后台（`/admin/*`）负责数据、算法参数与实验看板，两端同一工程，最终由 Capacitor 打成 Android APK。

- 后端：`backend/` FastAPI + SQLAlchemy 2 + Alembic，运行库 PostgreSQL 16（无 PG 时回退 SQLite）
- 前端：`frontend/` Vue 3 + Vite + Tailwind + daisyUI + Pinia + ECharts，**纯 JavaScript，不引入 TypeScript**
- 唯一事实来源：根目录 [`MASTER_SPEC.md`](MASTER_SPEC.md)；工程记忆与踩坑见 [`docs/AGENT_MEMORY.md`](docs/AGENT_MEMORY.md)

> 本仓库为毕设成果展示，不是商业产品。演示数据、仿真底表与真实用户量级都在「数据与实验」一节如实标出。

---

## 目录

1. [它解决什么](#它解决什么)
2. [功能地图](#功能地图)
3. [技术栈](#技术栈)
4. [仓库结构](#仓库结构)
5. [快速开始](#快速开始)
6. [接口概览](#接口概览)
7. [推荐算法口径](#推荐算法口径)
8. [数据与实验](#数据与实验)
9. [视觉与动效约束](#视觉与动效约束)
10. [测试与门禁](#测试与门禁)
11. [文档索引](#文档索引)
12. [已知限制](#已知限制)
13. [声明](#声明)

---

## 它解决什么

| 场景 | 痛点 | 本系统的做法 |
|---|---|---|
| 一个人不知道吃什么 | 决策疲劳，反复点同几家店 | 天气 + 预算 + 用餐状态 + 八维口味向量 → 效用评分排序，并给出一张可解释的雷达图 |
| 宿舍几个人一起吃饭 | 群里聊半小时定不下来 | 扫码建房 → 各自划卡投票 → 求交集共识 → 共同揭晓；有人投否决的项直接被硬屏蔽 |
| 吃腻了、重复率高 | 推荐只看「你上次点了什么」 | 艾宾浩斯式时间衰减：越久没吃加分越多，近期吃过同类压制 |
| 冰箱食材放坏 | 想不起来有什么、忘了快过期 | 拍照识别入库 → 临期优先 → 匹配家常菜菜谱 |
| 运营/毕设答辩要看数据 | 只有截图没有证据 | `/admin/dashboard` 大屏：门店覆盖、打标质量、实验对照组与每用户分布 |

## 功能地图

### 移动端 `/m/*`

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 启动登录页 | 本地账号 + PBKDF2 凭据，快捷账号只填用户名、不填密码 |
| `/m/home` | 今日推荐（卡组） | 390×844 一屏装下；顶卡液态玻璃 + 候选条 + 划卡操作行；支持「换一批」 |
| `/m/footprint` | 吃饭足迹 | 进食记录、口味雷达、八维饮食基因 |
| `/m/profile` | 我的 | 偏好编辑、饮食基因 8 维滑块、账号信息 |
| `/m/fridge` | 冰箱 | 拍照识别入库、临期提醒、按库存匹配菜谱 |
| `/m/room` | 多人房间 | WebSocket 实时协议 `START_SWIPING / SUBMIT_VOTE / CONSENSUS_REVEAL` |

### PC 后台 `/admin/*`

| 路由 | 页面 | 说明 |
|---|---|---|
| `/admin/data` | 数据管理 | 门店 / 菜品 / 标签，分页检索与编辑 |
| `/admin/users`、`/admin/users/:id` | 用户管理 | 列表、详情（口味向量与个人概览）、角色授予与回收 |
| `/admin/settings` | 系统设置 | 算法参数（λ / ω / α / β / γ / δ）运行期生效 |
| `/admin/import` | 数据导入 | 目录导入、打标任务 |
| `/admin/audit` | 审计日志 | 后台写操作留痕 |
| `/admin/dashboard` | 数据大屏 | 覆盖度、质量、A/B 实验看板（含仿真只读接口） |

双校区（思源 / 建大）在 v2.3.4 起按 `campus` 分库存储，外食推荐、群组外食与统计都按校区过滤，跨校区不能拼同一桌；下厨菜谱两端共享。

## 技术栈

**后端**

| 组件 | 选型 | 备注 |
|---|---|---|
| Web 框架 | FastAPI ≥ 0.115 | 路由统一挂载在 `/api/v1` |
| ORM | SQLAlchemy 2.x | 声明式模型集中在 `backend/models.py` |
| 迁移 | Alembic | `backend/migrations/`，生产结构只走 `alembic upgrade head` |
| 数据库 | PostgreSQL 16（首选）/ SQLite（回退） | `DATABASE_URL` 决定，启动横幅会打印实际生效的库 |
| 认证 | 自研本地账号 | PBKDF2-SHA256 / 120k 轮 / 16 字节随机盐；令牌只存 SHA-256 摘要；登录限速 5 次 / 300 秒 |
| 实时 | FastAPI WebSocket | `/ws/room/{code}/{user_id}` |
| 地理与天气 | 高德 Web 服务 API（可选） | 未配 Key 时天气回退 Open-Meteo |
| 视觉识别 | 任意 OpenAI 兼容视觉端点 | 冰箱拍照识别 |

**前端**

| 用途 | 选型 |
|---|---|
| 框架 | Vue 3.5 + Vite 6 + Vue Router 4 + Pinia 2 |
| 样式 | Tailwind 3 + daisyUI 4，颜色令牌唯一出口 `frontend/tailwind.config.js` + `src/styles/` CSS 变量 |
| 图表 | ECharts 5 + vue-echarts（含 wordcloud） |
| 动效 | gsap（划卡与揭晓时间线）、lottie-web（天气/空状态/插画）、@formkit/auto-animate（列表增删）、@vueuse/motion（微交互）、canvas-confetti（仅揭晓） |
| 背景 | ogl —— `Grainient` 全局底、`LiquidChrome` 首页顶部与揭晓页、`Silk` 启动登录页 |
| 打包 | Capacitor 8 → Android APK |

## 仓库结构

```
EatWhat/
├── MASTER_SPEC.md              唯一事实来源（SSOT）：架构、契约、算法、视觉、路线图
├── AGENTS.md                   给 AI 协作者的入场须知与硬性红线
├── MOBILE_VISUAL_SPEC.md       移动端视觉细则与首页尺寸基线
├── WEATHERPILL_GLASS.md        悬浮小件玻璃配方
├── BATCH4_PLAN.md              执行细则（整改复核 / 批次 4 / 批次 5）
├── backend/
│   ├── main.py                 FastAPI 入口，挂 12 个路由 + WS，启动横幅
│   ├── config.py               环境变量、算法参数运行期缓存、prod 拒绝隐式回退
│   ├── database.py             引擎 / 会话 / init_db（PG 默认不建表）
│   ├── models.py               20 张 ORM 表（PG 里含 alembic_version 共 21 张）
│   ├── routers/                接口层（64 个端点）
│   ├── algorithms/             time_decay / single_recommender / group_recommender /
│   │                           combo_optimizer / veto_rules / fridge_clock / vector_spec
│   ├── migrations/             Alembic
│   ├── scripts/                种子、高德 POI 抓取、仿真、ETL、迁移与运维脚本
│   └── tests/                  pytest 套件
├── frontend/
│   ├── src/views/mobile/       移动端页面
│   ├── src/views/admin/        PC 后台页面（含大屏）
│   ├── src/components/         卡组、雷达、玻璃件、背景、bits
│   ├── src/styles/             CSS 变量与三层玻璃样式（颜色唯一出口）
│   ├── src/api/                接口封装
│   ├── public/dishes/          菜品图
│   └── android/                Capacitor 工程
├── scripts/                    浏览器门禁探针（home-fit / refill-fresh / sandbox-sync / check-colors 等）
├── design/                     定稿设计稿与配色实验
└── docs/                       工程记忆、部署方案、素材台账、分阶段审查证据
```

## 快速开始

### 环境要求

- Python 3.13（3.11+ 应可用）
- Node.js 24（18+ 应可用）
- PostgreSQL 16（可选，不装则自动使用 SQLite）

### 1. 配置后端环境变量

```powershell
cd backend
copy .env.example .env      # 按需修改；不配 DATABASE_URL 会落到 ./eatwhat.db
```

`.env` 已在 `.gitignore` 内，**不要把任何 Key 或口令提交进仓库**。

### 2. 起数据库（可选）

```powershell
docker compose -f docker-compose.dev.yml up -d      # postgres:16-alpine，映射到本机 5433
```

用 5433 是为了避开本机可能已装的 5432。这套 compose 只做本机联调，账号口令是占位值，不要拿去当生产库；也可以完全不用它，让后端回落到 SQLite 单文件。

### 3. 启动后端

```powershell
python -m pip install -r requirements.txt
# 必须在仓库根启动：backend/ 里跑 `uvicorn main:app` 会相对导入报错
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

建表与种子数据：

```powershell
# SQLite：启动时自动 create_all；PostgreSQL：AUTO_CREATE_SCHEMA 默认关闭，必须先跑迁移
cd backend
python -m alembic upgrade head          # 日常命令都在 backend/ 里执行，连接串取 backend/.env
cd ..

# 20 家门店/档口 + 60 道外食 + 40 道家常菜 + 4 个地域演示人设
python -m backend.scripts.init_seed_data
python -m backend.scripts.grant_admin --username <用户名>    # 需要管理员时（--revoke / --list）
```

`init_seed_data --force` 会重播 `backend/scripts/benchmark_snapshot.json`，仿真重跑后要先把快照刷新再播种，否则库里的曲线会被旧快照覆盖。

### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173，Vite 代理 /api 与 /ws → 127.0.0.1:8000
npm run build        # 产物 dist/
```

8000 被占用时用备用端口起两份实例：`$env:VITE_API_TARGET="http://127.0.0.1:8001"`，前端不会写死后端域名。

### 5. Android（可选）

```powershell
cd frontend
npm run build
npx cap sync android
npx cap open android
```

## 接口概览

全部业务接口挂在 `/api/v1` 下，共 **12 个路由、64 个端点**，另有房间 WebSocket 挂在根路径 `/ws/room/{code}/{user_id}`。

| 路由文件 | 前缀 | 端点数 | 职责 |
|---|---|---|---|
| `auth_user.py` | — | 6 | 注册、登录、登出、令牌与个人资料 |
| `auth_local.py` | `/auth` | 4 | 本地账号体系与限速 |
| `recommend.py` | — | 2 | 单人推荐与换一批 |
| `eating_log.py` | — | 4 | 吃饭足迹、打卡 |
| `catalog.py` | `/catalog` | 2 | 门店与菜品目录 |
| `fridge.py` | — | 5 | 冰箱库存、拍照识别、临期 |
| `group_room.py` | — | 3 | 多人房间 HTTP 部分 |
| `admin.py` | `/admin` | 12 | 后台基础数据管理 |
| `admin_ext.py` | `/admin` | 10 | 后台扩展（导入、打标、审核） |
| `admin_stats.py` | `/admin/stats` | 13 | 统计与大屏数据（含人设 demo/real 范围切换） |
| `admin_simulation.py` | `/admin/stats/simulation` | 2 | 仿真只读接口 |
| `admin_experiments.py` | `/admin` | 1 | 实验配置 |

后台路由整体 `Depends(require_admin)`；仿真接口只读，不写任何业务表。

## 推荐算法口径

### 时间衰减（避免吃腻）

`backend/algorithms/time_decay.py`

```
M(t) = (1 - e^(-λ·Δt_exact)) · (1 - 0.4·e^(-λ·Δt_similar))
```

前项按「距上次吃同一道菜的真实天数」增长，后项按「近期吃过同类」压制；λ 默认 0.5，可在后台运行期调整，无需重启。

### 单用户效用评分

`backend/algorithms/single_recommender.py`

```
Score = α·口味 + β·天气 + γ·预算 + δ·状态 + 时间衰减项   (α+β+γ+δ = 1)
```

八维口味向量（辣度 / 油腻度 / 汤水感 / 适宜温度 / 饱腹度 / 出餐速度 / 社交属性 / 抚慰指数，定义在 `backend/algorithms/vector_spec.py`）来自注册问卷或「我的 → 饮食基因」编辑，默认每人一组 0.5 的中性向量；忌口标签命中直接过滤，不进入排序（类别词表 + 别名展开走 `veto_rules.py`）。

### 多人共识

`backend/algorithms/group_recommender.py`

```
G = Mask_veto · ( ω·mean(U₁…Uₙ) + (1-ω)·min(U₁…Uₙ) )
```

`ω·mean` 是集体满意度，`(1-ω)·min` 逼结果照顾最不情愿的那个人；`Mask_veto` 硬屏蔽任何投了否决的人的忌口项。共识权重在房间投票中按 0.4 先验 + 0.6 划卡行为更新。

### 组合推荐

`backend/algorithms/combo_optimizer.py`

按「荤 MEAT / 素 VEG / 汤 SOUP」三个角色各枚举一道，约束为总价 ≤ 预算、三道平均油腻度 ≤ 0.65，并用后缀最小价做剪枝。**不是背包问题**——角色互斥且组合规模极小，枚举更诚实，答辩时这一点会被问。

## 数据与实验

### 演示库规模（截至 2026-11-01，PostgreSQL）

| 表 | 行数 | 说明 |
|---|---|---|
| `restaurants` | 7,704 | 高德 POI 7,284 + 合成食堂档口 420，按 `campus` 分思源 / 建大 |
| `dishes_and_recipes` | 6,560 | 家常菜 6,440（HOME）+ 外食 120（OUT）；八维特征值共 52,480 个，843 条过敏原字段缺失 |
| `users` | 7 | 4 个地域演示人设 + 1 个管理员 + 2 个自动化测试账号 |
| `algo_configs` | 1 | 算法参数唯一行（λ / ω / α / β / γ / δ + benchmark 快照），后台改完运行期生效 |
| `system_settings` | 1 | 键值配置（当前存 `algo_params`），服务启动时装进运行期缓存 |
| `eating_logs` / `fridge_inventory` / `dish_feedback` | 25 / 12 / 1 | 真实业务表只留演示操作痕迹 |
| `group_rooms` / `room_votes` | 0 / 0 | 多人房间在真机演示中即时创建，数据未沉淀 |
| `simulation_meal_logs` / `simulation_rooms` / `simulation_room_votes` / `simulation_group_results` | 48,000 / 1,000 / 40,000 / 3 | 独立仿真底表，与真实业务表完全隔离 |

### G3 仿真与 A/B 对照

底表由 `backend/scripts/simulate_g3_parallel.py` 生成，`import_simulation.py` 通过 ETL 只写入 `simulation_*` 五张表，真实业务表零改动。

**规模**：200 个人设 × 60 天 × 每日 2 餐 × 2 个对照组 = 48,000 条用餐记录；1,000 个房间、40,000 条房间投票、3 条群体结果。

**主指标：14 天内同菜重样率**（同一用户在 14 天窗口里再次选到同一个 `dish_id` 的餐次占比）

| 组 | 餐次 | 同菜重样率 | 用户级均值 ± 标准差 | 用户级最小 / 中位 / 最大 |
|---|---|---|---|---|
| 无衰减基线 | 24,000 | 69.68% | 0.6968 ± 0.0202 | 0.658 / 0.700 / 0.742 |
| 本系统（时间衰减） | 24,000 | **13.75%** | 0.1375 ± 0.0402 | 0.050 / 0.133 / 0.275 |

同一指标下同类重样率为基线 93.03%、本系统 86.59%；看板同时给出逐日曲线与 200 个用户的箱线分布，避免「只看均值」。

> 口径提醒：早期版本的「连续同菜率」恒为 0.0%，那是 `simulate_personas.py` 里逐日相邻比较的定义造成的，不是算法效果。现口径已换成 14 天窗口同 `dish_id` 重样，并给出每用户分布。

**复现**

```powershell
# 重新生成底表原始产出（默认写到 docs/review/consolidated/G3/data/，约 188MB，已被 .gitignore 排除）
python -m backend.scripts.simulate_g3_parallel --seed 20261024 --workers 8

# ETL 进 simulation_* 五张表；--replace 会先清掉同名 run，不要在生产库上跑
python -m backend.scripts.import_simulation --replace
```

克隆仓库后拿不到那 188MB 原始 JSONL，必须重跑模拟器才能复现底表；仓库内保留 `docs/review/clearance-codex-2026-10-24/` 的 6 份压缩样本（seed7 与 default-a/b 各两臂，每份 24,000 行）作为可独立核查的小样本证据。

## 视觉与动效约束

视觉规范是本仓库约束最硬、返工最多的部分，由 `AGENTS.md` 的红线和 `scripts/check-colors.mjs` 共同守住：

- **单色体系（v2.3）**：黑 `#17171A` / 银灰 `#55555E` / 白 / 浅灰 `#F4F4F5`。状态靠**图标 + 文案 + 分段开关选中态**区分，不靠颜色。
- **颜色只有一个出口**：`tailwind.config.js` 主题令牌 + `src/styles/` CSS 变量；组件、页面、图表、动效里禁止裸 hex / 裸 `rgb()`，JS 侧（ECharts / confetti / Lottie）统一经 `src/utils/theme.js` 读 CSS 变量。`scripts/check-colors.mjs` 会拦住违规。
- **三层架构**：L0 背景只做氛围 → L1 玻璃只给小面积悬浮件 → L2 内容卡用液态玻璃 G 方案（折射层 + 112° 对角高光 + 亮边内阴影 + 深投影，四层缺一不可）。两套玻璃配方同源不同方，不许混用。
- **玻璃性能分级**：SVG 位移折射只开在一级卡（TOP 1 主卡 / 卡组顶卡 / 主页区块卡），候选索引与列表次卡一律磨砂降级，禁止整页全开。
- **首页高度策略**：`/m/home` 在 390×844 必须一屏装下；矮屏（<780，如 390×667）允许内容区内部滚动，但页面自身不滚、滚到底操作行完整可见、按钮中心 `elementFromPoint` 命中自身。任何单一元素不得超过 60% 屏高，卡高由 flex 分配、禁止写死像素。

## 测试与门禁

```powershell
# 后端（本机基线：454 passed / 1 skipped）
python -m pytest -q

# 前端构建
cd frontend; npm run build

# 界面门禁：三条必须全 PASS 才算改完
node scripts/home-fit.mjs        # 初始态如实报告是否需滚动 + 滚到底后操作行不被遮挡 + 按钮命中自身
node scripts/refill-fresh.mjs    # 「换一批」必须给出新候选
node scripts/sandbox-sync.mjs    # 算法沙盒参数与首页卡组同源
node scripts/check-colors.mjs    # 颜色只能从令牌出口取
```

门禁脚本用 CDP 驱动本机 Chrome，运行前提有三个：Chrome 以 `--remote-debugging-port=9222` 启动、前端在 `http://127.0.0.1:5173`、后端在 `127.0.0.1:8000`（这些地址写死在脚本里）。`home-fit.mjs` 支持把视口尺寸作为位置参数传入，例如 `node scripts/home-fit.mjs 390 667`。

**验收口径**：`scrollHeight == innerHeight` 不等于「装得下」——卡组曾用 `flex:0 0 auto` 把溢出藏进 `overflow:hidden`，按钮沉到底栏底下。必须同时断言元素矩形不相交、按钮中心 `elementFromPoint` 命中自身。

## 文档索引

| 文件 | 作用 |
|---|---|
| [`MASTER_SPEC.md`](MASTER_SPEC.md) | 唯一事实来源：架构、契约、算法口径、批次路线图 |
| [`AGENTS.md`](AGENTS.md) | AI 协作红线与验证命令 |
| [`docs/AGENT_MEMORY.md`](docs/AGENT_MEMORY.md) | 工程记忆账本：文档没写但施工要知道的决策、漂移、坑 |
| [`docs/README.md`](docs/README.md) | `docs/` 目录地图与不同读者的入口 |
| [`MOBILE_VISUAL_SPEC.md`](MOBILE_VISUAL_SPEC.md) | 移动端视觉细则、首页尺寸基线 |
| [`WEATHERPILL_GLASS.md`](WEATHERPILL_GLASS.md) | 悬浮小件玻璃配方数值 |
| [`docs/选题方向.md`](docs/选题方向.md) | 开题材料与选题背景 |
| [`docs/BACKEND_DEPLOYMENT_PLAN.md`](docs/BACKEND_DEPLOYMENT_PLAN.md) / [`docs/DEPLOYMENT_PHASE_A.md`](docs/DEPLOYMENT_PHASE_A.md) | 部署方案 |
| [`docs/DISH_IMAGES_LEDGER.md`](docs/DISH_IMAGES_LEDGER.md) | 逐张菜品图来源与校验值 |
| [`docs/review/`](docs/review/) | 分阶段独立审查报告与台账（含 `STAGE_STATUS.md`） |

## 已知限制

如实列出，答辩与论文同样口径：

- **数据是演示数据**：门店来自高德 POI 抓取 + 合成食堂档口，用户行为来自仿真，不是真实运营流水。思源 605、建大 6,659 是两个校区样本，不可跨校区混算。
- **实验只有单一 seed**：14 天重样率给出的是 200 用户的分布，不是多 seed 的均值方差；补跑 3–5 个 seed 是后续工作。
- **Room 划卡的端到端真机验证尚未收口**：协议与后端测试已覆盖，真机联机体验待冻结前补验。
- **没有支付、没有社交、没有真实配送**：范围就是「决策」这一件事。
- **仅打包 Android**：iOS 未做。
- **APK 构建产物、数据库文件、`.env`、用户上传与浏览器缓存全部不入库**，克隆后需要自己灌种子。
- **`--database-url` 指向全新 SQLite 时需要先建表**（当前依赖 `init_db`，直接跑 ETL 会报表不存在）。

## 声明

本科毕业设计作品，代码与文档仅作课程成果展示与学习交流，未附标准开源许可证；菜品图片、高德 POI、Lottie 素材与第三方组件（Vue Bits、ogl）的版权归原作者，来源与授权分别记录在 `docs/DISH_IMAGES_LEDGER.md`、`docs/LOTTIE_SOURCES.md` 与 `docs/vuebits-diff.md`。

演示账号口令、真实 Key 一律不写入仓库；本地答辩材料另行提供。
