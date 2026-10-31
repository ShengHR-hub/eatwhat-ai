# BASELINE —— S09 / r02

- 采样时间：2026-10-25 00:24–00:37（Asia/Shanghai；最终 POI 采集 00:36:33）
- 版本控制：**仓库尚无 commit**；`git rev-parse HEAD` 输出 `HEAD` 并报 `unknown revision`，`head=null`。完整 `git status --short` 见 `data/git_status_short.txt`；未清空/提交既有变更。
- 运行环境：Windows 11 / Git Bash + PowerShell / Python 3.13.9 / Node v24.19.0 / npm 11.17.0；SQLite（SQLAlchemy 2.x）。
- 证据：`data/env.json`、`data/file_hashes.json`、`data/db_baseline.json`、`data/dataset_fingerprint.json`、`data/routes.json`、`data/route_gap.json`。

## 1. 高德 Key 与查询

- Key 在 **Windows 用户环境变量** 中存在（长度 32）；当前 Qoder 进程未继承，通过 PowerShell 仅为子进程注入，未打印/写入源码、JSON、日志或证据包。证据中的 `key` 字段一律 `<redacted>`。
- `amap_geocode.json` 记录 `key_present=true`（仅布尔），不含 Key 值。
- `validate_evidence.py` 在带 Key 的环境下扫描 r02 全部文件，`leaked_files=[]`。
- 地名搜索：`address=西安思源学院`、`city=西安`；实际返回 `109.078487,34.234818`（GCJ-02），`level=兴趣点`，`adcode=610111`，API `status=1/info=OK`。
- 3km 查询：`types=050000`；直接 `count=600`；page 1–8 有数据、page 9 起为空。
- 网格采集：45 个 800m 网格，133 次调用，0 错误/0 未完成；真实餐饮 POI **605**。
- 原目标约 1500+，实测 605，差额 895；`target_1500_met=false`。D03 已于 2026-10-25 裁决：接受 605 为样本 A，差额仅历史记录，不再阻塞；建大 6,659 为样本 B，两校区分开报。
- **校区 B 建大雁塔**：中心 `108.967153,34.236991`（实际地名搜索）；真实餐饮 POI **6,659**（3km/050000/递归网格，1,206 次调用，0 未完成）；合成食堂 200 单列，合计 **6,859**；未返回草堂。

## 2. 数据库只读基线

`backend/eatwhat.db` 以 SQLite `mode=ro` 读取；S09 未写库。

| 表 | 行数 |
|---|---:|
| users | 4 |
| user_preferences | 4 |
| restaurants | 20（AMAP_POI 10 / CANTEEN 10，均为旧种子） |
| dishes_and_recipes | 100（OUT_DINING 60 / HOME_COOKING 40） |
| fridge_inventory | 12 |
| eating_logs | 9 |
| group_rooms | 0 |
| room_votes | 0 |
| algo_configs | 1 |

- 当前 schema **没有** `allergen_tags`、`deleted_at`、`source_dataset`、`tagging_status`、`is_synthetic`；SSOT v2.3.5 只写了可空字段方案，S09 不迁移。
- 演示库文件 SHA 与基线相同；`group_rooms=0`、`room_votes=0`（`validation.json`）。
- 当前数据集指纹沿用 r01 基线：`3e24f458071d67f3097d28ffb1d997d7a0188c18b0e28251aca7b7cf0c27625e`（S13 必须用独立统计库重新生成）。

## 3. 路由与 schema 基线

- FastAPI 共 22 条路由（含 openapi/docs/health）；`/api/v1` 16 条；WS 1 条。
- `/admin/*` 实际 **0** 条；`/admin/stats/*` 实际 **0** 条；预期 13 个 stats 全部缺失（`data/route_gap.json`）。
- 本步只核对，不实现 S14/S15。

## 4. 外部条件

| 项 | 实测 |
|---|---|
| 高德 Key | 采集时由环境变量提供；不落盘；当前交互 shell 未持久化 |
| LLM Key/模型/单价 | 缺失/未定；S11 BLOCKED |
| Java/javac | 25.0.2（存在） |
| adb/gradle/Android SDK | 缺失 |
| Capacitor 配置/依赖/Android 工程 | 缺失 |
| 菜品图 | 95 张，来自小红书截图；仅本地演示，不公开发布/APK 公开分发/论文公开素材 |
| ECharts | 5.6.0 已安装；echarts-wordcloud/html2canvas 缺失（S17 再定） |

## 5. 本步保护声明

- 只读：DB、路由、公开 API/网页、文件哈希。
- 未写 `backend/eatwhat.db`；未运行 `--force`；未改 schema/业务代码/`/admin`。
- 未导入 605 条 POI 到数据库；`data/amap_pois.jsonl` 仅为只读采集证据。
- 未创建/未修改 `REVIEW.md`；未签 PASS；台账 S09 当前为 `BLOCKED`（提交时曾为 `REVIEW_PENDING`），S10 仍 LOCKED。
