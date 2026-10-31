# BASELINE —— S09 / r01

- 采样时间：2026-10-24 23:24–23:35（Asia/Shanghai）
- 版本控制：**仓库尚无 commit**；`git rev-parse HEAD` 输出 `HEAD` 且报 `unknown revision`，因此 `HEAD=null`。完整 `git status --short` 见 `data/git_status_short.txt`（含既有的 staged/unstaged/untracked 文件；不因 S09 清空或提交）。
- 运行环境：Windows 11 / Git Bash + PowerShell / Python 3.13.9 / Node v24.19.0 / npm 11.17.0；SQLite（SQLAlchemy 2.x）。
- 证据：`data/env.json`、`data/file_hashes.json`、`data/db_baseline.json`、`data/dataset_fingerprint.json`、`data/routes.json`、`data/route_gap.json`。

## 1. 数据库只读基线

`backend/eatwhat.db` 以 SQLite `mode=ro` 读取；不写库。

| 表 | 行数 |
|---|---:|
| users | 4 |
| user_preferences | 4 |
| restaurants | 20（AMAP_POI 10 / CANTEEN 10） |
| dishes_and_recipes | 100（OUT_DINING 60 / HOME_COOKING 40） |
| fridge_inventory | 12 |
| eating_logs | 9 |
| group_rooms | 0 |
| room_votes | 0 |
| algo_configs | 1 |

- 唯一菜名 95；跨模式同名 5 组；唯一 `(name, ingredients_main)` 95。
- 有效 8 维向量 100/100；当前特征值 800。
- 数据集指纹：`3e24f458071d67f3097d28ffb1d997d7a0188c18b0e28251aca7b7cf0c27625e`。
- 文件 SHA-256 与逻辑摘要见 `data/db_baseline.json`；S09 前后对比见 `CHECKS.md`。

## 2. 路由基线

- FastAPI 共 22 条路由（含 openapi/docs/health）；`/api/v1` 16 条；WS 1 条。
- `/admin/*` 实际 **0** 条；`/admin/stats/*` 实际 **0** 条。
- 预期 13 个 stats 路由全部缺失，详见 `data/route_gap.json`。
- 说明：S09 只读核对；S14/S15 才实现 CRUD/stats。

## 3. 外部条件

| 项 | 实测 |
|---|---|
| `AMAP_API_KEY` | 缺失；无 Key 请求返回 `INVALID_USER_KEY/10001` |
| `LLM_API_KEY` / `LLM_BASE_URL` | 缺失 |
| Java / javac | 25.0.2（均存在） |
| adb / gradle | 缺失 |
| ANDROID_HOME / ANDROID_SDK_ROOT | 缺失 |
| Capacitor 配置 / android 工程 / 依赖 | 均缺失 |
| echarts | 5.6.0（已安装） |
| echarts-wordcloud | 缺失 |
| html2canvas | 缺失 |

## 4. 素材基线

- 菜品图：95 个文件 / 95 条台账；来源为小红书笔记截图；台账无 license 字段，公开再分发授权未证明。
- Lottie：天气三件来自 `@meteocons/lottie`（MIT），空状态自绘（随仓库 MIT）；见 `docs/LOTTIE_SOURCES.md`。
- Vue Bits：MIT + Commons Clause（自用合规，不得转售组件本身）。
- ECharts Apache-2.0；daisyUI MIT；GSAP Standard no-charge license；lottie-web MIT；canvas-confetti ISC；auto-animate/vueuse-motion MIT。

## 5. 本步保护声明

- 只读：DB、路由、文件哈希、官方文档、公开仓库许可证。
- 未写 `backend/eatwhat.db`；未运行 `init_seed_data --force`；未改 schema。
- 未改 `MASTER_SPEC.md` / `BATCH4_PLAN.md` / `DASHBOARD_EXPANSION.md` / `STAGE_STATUS.md`。
- 未创建 `REVIEW.md`；未签 PASS。
- 未发起大规模付费调用；无 Key 请求是空 Key 错误探测。
