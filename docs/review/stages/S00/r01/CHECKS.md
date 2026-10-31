# S00 / r01 命令与检查记录

工作目录：`D:\EatWhat`
时间：2026-10-25（Asia/Shanghai）；表中时间为日志文件 mtime
环境：Windows Git Bash、Python 3.13.9、Node v24.19.0；中文输出使用 `PYTHONIOENCODING=utf-8`

## 1. 命令清单

| # | 时间 | 命令 | 退出码 | 结果 / 日志 |
| --- | --- | --- | ---: | --- |
| 1 | 13:58:45 | `git status --short`、`git diff --cached --stat`、`git diff --stat`、`git diff --cached --binary \| sha256sum`、`git ls-files --others --exclude-standard` | 0 | staged 280 / unstaged 130 / untracked 53；HEAD 不存在；`logs/01_git_status.txt` |
| 2 | 13:59:00 | 内联 Python：环境/依赖/文档 hash/三库 SHA/schema/行数/旁文件/前端配置 | 0 | `logs/00_baseline.txt`、`data/baseline.json`、`data/schema_*.json` |
| 3 | 13:59:18 | `DATABASE_URL="sqlite:///D:/EatWhat/backend/_pytest_s00.db" python -m pytest -q` | **0** | `175 passed, 1 skipped, 505 warnings in 10.38s`；隔离库未生成；`logs/02_pytest_full_isolated.log` |
| 4 | 13:59:42 | `cd frontend; npm run build` | **0** | `✓ built in 18.79s`；`logs/03_frontend_build.log` |
| 5 | 13:59:42 | `node scripts/check-colors.mjs` | **0** | 38 个文件无裸 hex/rgb/hsl；`logs/04_check_colors.log` |
| 6 | 13:59:51 | 内联 Python：启动前记录三库 SHA/行数 | 0 | `logs/05_db_before_server.log`、`data/db_before_server.json` |
| 7 | 13:59:55 | `DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00_r02.db" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info` | n/a（后台，验证后停止） | `logs/06_server_current_state.log` |
| 8 | 14:00:06–14:00:14 | 内联 httpx：health、demo-list、profile、fridge/stats 跨用户、推荐（带/不带 campus）、下厨、足迹、冰箱、天气、房间不存在、catalog、openapi | 0（客户端） | 各响应 JSON 与 `logs/22_current_state_summary.json`；错误路径 404 保留为反例 |
| 9 | 14:00:29 | 停止 uvicorn | n/a | 端口 8000 已释放 |
| 10 | 14:00:39 | 内联 Python：启动后三库 SHA/行数/旁文件对比 | 0 | 三库全部不变；`logs/07_db_after_server.log`、`data/db_after_server.json` |
| 11 | 14:00:39 | 内联 SQL（只读）：deleted_at / feature_vector NULL / campus 分布 / 用户库存与日志数 | 0 | `logs/08_latent_db_conditions.log` |
| 12 | 14:06:04 | `python docs/review/stages/S00/r01/data/probe_fridge_boundary.py` | 0 | 2.5 天已过 → remaining=0 / expired；`logs/09_fridge_boundary_probe.log` |
| 13 | 14:01:42 | 内联 Python：F01 忌口只读复算 + F13 排除 ID 只读复算 | 0 | user 3：35 候选、0 忌口命中；24+24 候选、交集 0；`logs/10_f01_f13_readonly_probe.log` |
| 14 | 14:02:15 | 内联 Python：汇总当前状态与数据库保护 | 0 | `logs/11_compose_state.log`、`data/current_state.json`、`data/db_protection.json` |
| 15 | 14:06:05 | `python docs/review/stages/S00/r01/data/build_s00_docs.py` | **0** | 18 条缺陷、8 步矩阵；`logs/12_defect_matrix_build.log`、`FINDINGS.md`、`VERIFICATION_MATRIX.md`、`data/*.json` |
| 16 | 14:03:51 | `python docs/review/stages/S00/r01/data/build_manifest.py` | **0** | 143 项，fingerprint `16123ade…5c8a1c0`；`logs/13_manifest_build.log` |
| 17 | 14:07:11 | `python docs/review/stages/S00/r01/data/build_validation.py` | **0** | 生成 `validation.json`，状态 `SUBMITTED_FOR_REVIEW`；`logs/14_validation_build.log` |
| 18 | 14:07:25 | 内联 Python：必需文件、manifest 143 项复算、validation 一致性、三库 SHA/行数、台账/SSOT hash、端口 | 0 | `final_check: OK`；`logs/15_final_checks.log` |
| 19 | 14:06:40 | `find backend frontend/src scripts -newermt "2026-10-25 13:58:00" …` | 0 | 输出为空：S00 未修改业务源码；`logs/16_no_source_changes.log` |

## 2. 关键结果

### 2.1 构建与测试基线

| 项 | 结果 |
| --- | --- |
| 后端全量 | 175 passed, 1 skipped；skip 为 Windows 符号链接权限用例 |
| warning | 505 条，均为既有 `datetime.utcnow()` 弃用与 `requests` 依赖版本提示；无 failure/error |
| 前端构建 | 成功；产物在 `frontend/dist`（未作为源码证据） |
| 颜色静态门禁 | 38 文件通过 |
| 浏览器门禁 | **未执行**：S00 不做真实点击，留给 S05/S08 |

### 2.2 接口现状（dev 库，8000）

| 请求 | 状态 | 备注 |
| --- | ---: | --- |
| `GET /health` | 200 | `version=2.3.2` |
| 外食/下厨推荐 | 200 | 各 5 条；Top 稳定 |
| 外食推荐 + `campus=SIYUAN` | 200 | 与不带 campus 完全相同；字段被忽略 |
| `GET /logs/stats/1` | 200 | 3 冷却 / 72.0 / 3 餐 / 2 类 |
| `GET /fridge/1` | 200 | 3 条 |
| `GET /users/1/profile` | 200 | 8 维 |
| `GET /users/2/profile` + 头 1 | 403 | 路径/头冲突 |
| `GET /fridge/2` + 头 1 | **200** | 用户 2 数据，F07 残留 |
| `GET /logs/stats/2` + 头 1 | **200** | 用户 2 数据，F07 残留 |
| `GET /api/v1/catalog/dishes?ids=24,89` | 200 | 2 条 |
| `GET /api/v1/rooms/000000` | 404 | 不存在 |

服务端日志无 500、无 traceback；S00 未观察到 Internal Server Error。

### 2.3 失败反例（保留）

| 反例 | 结果 | 处理 |
| --- | --- | --- |
| 错误路径 `/api/v1/dishes?ids=24,89` | 404 `{"detail":"Not Found"}` | 保留在 `logs/http_20_catalog_wrong_path.json`；正确路径为 `/api/v1/catalog/dishes` |
| 未带 X-User-Id 的路径型资源 | 当前按演示默认/路径放行 | 列入 F07，S01 需锁定契约，S00 不改 |
| 符号链接测试 | skip（WinError 1314） | PRE-00 已记录，本步不重复；不是业务失败 |
| 浏览器门禁 | 未执行 | S00 未启动 Vite/浏览器，不能写成通过 |

### 2.4 数据库保护

| 库 | 启动前 SHA | 启动后 SHA | 行数 | 旁文件 |
| --- | --- | --- | --- | --- |
| `backend/eatwhat.db` | `775da775…bd3a60b` | 同 | 不变 | 无 |
| `backend/eatwhat_batch4.db` | `315eb3da…6918c28` | 同 | 不变 | 无 |
| `backend/eatwhat_dev_pre00_r02.db` | `b965e73e…706a579` | 同 | 不变 | 无 |

服务启动时 `backend/main.py` 的 lifespan 会调用 `init_db()`/`create_all`；开发库 9 张表已存在，启动前后 SHA、schema 指纹、行数均未变化，未补建/改动任何表。演示库与 S10 库没有被连接。

S00 未执行清空、迁移、播种、打卡、建房、偏好保存、库存增删；只读 HTTP 探针后三库 SHA/schema/行数均未变化。

## 3. 独立复跑方法

```bash
# 1) 环境与数据库只读基线
python docs/review/stages/S00/r01/data/build_manifest.py

# 2) 后端测试（隔离库，不写演示库）
DATABASE_URL="sqlite:///D:/EatWhat/backend/_pytest_s00_recheck.db" python -m pytest -q

# 3) 前端构建与静态门禁
cd frontend && npm run build && cd ..
node scripts/check-colors.mjs

# 4) 只读接口现状（使用开发库副本）
DATABASE_URL="sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00_r02.db" \
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# GET /health
# GET /api/v1/users/1/profile
# POST /api/v1/recommend/single {"mode_type":"OUT_DINING","budget":30,"limit":5}
# GET /api/v1/logs/stats/1
# GET /api/v1/fridge/1
# GET /api/v1/catalog/dishes?ids=24,89

# 5) 复核数据库 SHA（与 BASELINE 表对照）
sha256sum backend/eatwhat.db backend/eatwhat_batch4.db backend/eatwhat_dev_pre00_r02.db
```

写入型复现（F07 建房身份、F08 部分向量、F02–F05 房间、N03/N04）必须使用新的隔离库/临时副本，留给 S01–S06；S00 没有执行。

## 4. 未执行项与原因

| 项 | 原因 |
| --- | --- |
| `node scripts/home-fit.mjs` / `refill-fresh.mjs` / `sandbox-sync.mjs` | 需要 Vite + 真实浏览器；S05/S08 执行 |
| 真实浏览器点击 390×844/390×667 | S00 只冻结基线，不做 UI 验收；S05/S08 执行 |
| 建房/打卡/偏好/库存写入 | S00 禁止业务写入；隔离库留给 S01–S06 |
| S07 多人真实交互/扫码 | 用户明确 DEFERRED，不执行、不签通过 |
| `/admin`、S10/S11 数据与统计 | 批次边界禁止提前实现 |
