# S00 / r01 基线

日期：2026-10-25（Asia/Shanghai）
工作目录：`D:\EatWhat`
基线采集：`logs/00_baseline.txt`、`data/baseline.json`
源码清单：`SOURCE_MANIFEST.json`，143 项，fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0`
git 状态：`logs/01_git_status.txt`

## 1. 源码与文档版本

| 项 | 值 |
| --- | --- |
| 分支 / HEAD | `master` / 无 commit（`git rev-parse HEAD` 退出码 128） |
| 工作区 | staged 280 / unstaged 130 / untracked 53（采集时）；本包未清理、未覆盖 |
| staged diff SHA-256 | `cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb` |
| SSOT | `MASTER_SPEC.md` v2.3.5，SHA `5463f88f…ef2c8b3` |
| 施工细则 | `BATCH4_PLAN.md` v1.1，SHA `6c95dfe4…6d14fba` |
| 审查规则 | `docs/REVIEW_RULES.md` v1.1，SHA `f9857dab…47c9f05` |
| 前置清理计划 | `docs/review/PRE_S10_REMEDIATION_PLAN.md` v1.0，SHA `177beb64…985943` |
| 工程记忆 | `docs/AGENT_MEMORY.md` 最后更新 2026-10-25，SHA `a3e21506…bccfe` |
| 台账 | `docs/review/STAGE_STATUS.md`：PRE-00/r02 PASS、S00 READY，SHA `a4bf33c6…cdf772` |
| 入场须知 | `AGENTS.md`，SHA `d1a6e946…493e2c` |
| PRE-00/r02 复审 | PASS，SHA `ba9da2a1…6fb0f71e` |

未把旧审查报告、旧截图或旧账本勾选当作当前版本通过；它们只在 FINDINGS 中标注为历史证据。

## 2. 环境与依赖

| 组件 | 版本 |
| --- | --- |
| OS / Shell | Windows 10.0.22631 x64 / Git Bash |
| Python | 3.13.9 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |
| HTTPX | 0.28.1 |
| Uvicorn | 0.30.0 |
| pytest | 9.0.3 |
| Node / npm | v24.19.0 / 11.17.0 |
| 前端构建 | Vite 6（`npm run build`），Vue 3.5、Pinia 2.3、Tailwind 3.4、daisyUI 4.12、ECharts 5.6、GSAP 3.12、Lottie 5.12、auto-animate 0.8、vueuse/motion 2.2 |

依赖锁：`requirements.txt` `842533ee…10f1c73`；`frontend/package.json` `66e99826…48c49b`；`frontend/package-lock.json` `adc87fc7…20c297`。逐文件哈希见 manifest。

## 3. 数据库身份与保护

| 库 | 大小 | SHA-256 | schema 指纹 | 行数摘要 | 用途/状态 |
| --- | ---: | --- | --- | --- | --- |
| `backend/eatwhat.db` | 217,088 | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | `b708e1d2…e5228f` | 4 用户 / 20 门店 / 100 菜 / 12 库存 / 9 日志 / 0 房 / 0 票 | 演示库，**只读**；旧 schema，直接作为运行库会 500 |
| `backend/eatwhat_batch4.db` | 6,316,032 | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | `ed2a27c8…866759` | 7,664 门店 / 6,400 菜 / 0 用户 | S10 独立导入库，**只读**；未接线 |
| `backend/eatwhat_dev_pre00_r02.db` | 217,088 | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | `82f1b327…ccaeb7` | 同演示库（4/20/100/12/9/0/0） | 开发运行库（PRE-00/r02 迁移后）；S00 只读探针用它 |

- 三库均无 `-wal` / `-journal` / `-shm` 旁文件。
- 服务启动时 `main.py` lifespan 会调用 `init_db()`/`create_all`；开发库 9 张表已存在，启动前后 SHA、schema 指纹、行数均未变化，未补建或改动任何表。演示库与 S10 库没有被连接。
- S00 启动只读服务前后：三库 SHA、schema 指纹、行数全部不变（`data/db_before_server.json`、`data/db_after_server.json`、`logs/07_db_after_server.log`）。
- 未执行清空、迁移、播种、打卡、建房、偏好保存、库存增删；写型复现留给 S01–S06 在隔离库执行。
- 演示库当前 `deleted_at` 非空=0、`feature_vector IS NULL`=0、门店 `campus=NULL`=20/20（`logs/08_latent_db_conditions.log`）。

## 4. 端口、启动与代理

| 项 | 当前配置 |
| --- | --- |
| 后端 | FastAPI，`python -m uvicorn backend.main:app`；开发端口 **8000** |
| 数据库连接 | `DATABASE_URL` 环境变量；`backend/config.py` 默认指向 `backend/eatwhat.db`（**S00 不使用默认值**） |
| 首页验证命令 | `DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00_r02.db" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` |
| 前端开发 | Vite，端口 **5173**，`npm run dev` |
| API 代理 | `/api` → `http://127.0.0.1:8000`；`/ws` → `ws://127.0.0.1:8000`（`frontend/vite.config.js`） |
| 构建入口 | `frontend/index.html` + `frontend/src/main.js`；`cd frontend; npm run build` |
| 测试命令 | `DATABASE_URL=sqlite:///D:/EatWhat/backend/_pytest_s00.db python -m pytest -q`（隔离库，未生成文件） |
| 静态门禁 | `node scripts/check-colors.mjs` |
| 浏览器门禁 | `node scripts/home-fit.mjs`、`refill-fresh.mjs`、`sandbox-sync.mjs`（需前后端+浏览器，S00 未执行） |

S00 实际用 8000 端口启动过只读服务，验证后停止；5173 前端开发服务器未在 S00 启动。

## 5. 首页与页面入口（只记录现状）

| 页面/功能 | 入口 | 当前实现 |
| --- | --- | --- |
| 首页 | `/m/home` | `Home.vue`：模式/气泡/预算/CTA、卡组、候选条、操作行、`AlgoSandboxDrawer` |
| 足迹 | `/m/footprint` | 底部 Tab；`Footprint.vue` |
| 我的 | `/m/profile` | 底部 Tab；`Profile.vue`：角色切换、基因/忌口/红黑榜、冰箱/房间入口 |
| 虚拟冰箱 | `/m/fridge` | Profile 内入口；`Fridge.vue` |
| 干饭房 | `/m/room` | Profile 内入口；`Room.vue` |
| 角色切换 | Profile「切换室友」 | `persona.switchUser → setUserId`，后续请求带 `X-User-Id` |
| 算法沙盒 | 首页内 `AlgoSandboxDrawer` | 滑块写 algo store；Home 监听 `reloadTick` 防抖重取 |

底部 Tab 只有首页/足迹/我的；冰箱与房间从「我的」进入。

## 6. 接口现状（dev 库只读探针，端口 8000）

| 请求 | 状态 | 关键结果 |
| --- | ---: | --- |
| `GET /health` | 200 | `{"status":"ok","version":"2.3.2"}` |
| `GET /api/v1/users/demo-list` | 200 | 4 个角色（1–4） |
| `GET /api/v1/users/1/profile` | 200 | 8 维向量，veto_tags=`["折耳根"]` |
| `GET /api/v1/users/2/profile` + 头 1 | 403 | 路径/头冲突被拒 |
| `GET /api/v1/fridge/2` + 头 1 | **200** | 返回 user_id=2、4 条（F07 残留） |
| `GET /api/v1/logs/stats/2` + 头 1 | **200** | 返回用户 2 周统计（F07 残留） |
| `POST /api/v1/recommend/single`（外食） | 200 | 5 条，Top 24/86.7 |
| 同上 + `campus=SIYUAN` | 200 | 与不带 campus 完全相同（campus 被忽略，N02） |
| `POST /api/v1/recommend/single`（下厨） | 200 | 5 条 |
| `GET /api/v1/logs/stats/1` | 200 | 3 条冷却 / 72.0 元 / 3 餐 / 2 类 |
| `GET /api/v1/fridge/1` | 200 | 3 条 |
| `GET /api/v1/context/weather` | 200 | offline 22℃/晴（未配高德 Key） |
| `GET /api/v1/catalog/dishes?ids=24,89` | 200 | 2 条 |
| `GET /api/v1/rooms/000000` | 404 | 不存在房间 |

- 服务端日志无 500、无 traceback；S00 未观察到 Internal Server Error。
- 错误路径反例保留：`GET /api/v1/dishes?ids=24,89` 返回 404（正确路径是 `/api/v1/catalog/dishes`）。
- OpenAPI 中 `SingleRecommendRequest`、`RoomCreateRequest`、`RoomJoinRequest` 均无 `campus` 字段；全 schema `campus_anywhere=false`。

## 7. 基线检查结果

| 检查 | 退出码 | 结果 | 日志 |
| --- | ---: | --- | --- |
| 后端全量（隔离库） | 0 | `175 passed, 1 skipped, 505 warnings in 10.38s`；隔离库未生成 | `logs/02_pytest_full_isolated.log` |
| 前端构建 | 0 | `✓ built in 18.79s` | `logs/03_frontend_build.log` |
| 颜色静态门禁 | 0 | 38 个文件无裸 hex/rgb/hsl | `logs/04_check_colors.log` |

1 skipped 为 PRE-00 的 Windows 符号链接权限用例；不是业务 skip。505 warnings 为既有 `datetime.utcnow()` 弃用与 `requests` 依赖提示，没有 failure/error。

## 8. 基线限制

1. 演示库是旧 schema；本计划只允许通过 `eatwhat_dev_pre00_r02.db` 或临时副本运行，不能把演示库直接启动为运行库。
2. S10 库未接线；campus、软删除、NULL 向量的真实数据影响留到 BRIDGE-10/S10。
3. S00 未做真实浏览器点击；S05/S08 必须重新采集两档 viewport、console/network、截图与按钮命中。
4. S07 明确 DEFERRED；不因本清单存在而视为完成。
