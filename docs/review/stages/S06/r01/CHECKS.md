# S06 / r01 检查记录

执行日期：2026-10-27（Asia/Shanghai）
机器可读退出码/时间：`data/command_results.json`
复跑入口：`data/run_checks.py`（测试/构建/门禁/探针）；真实 REST/WS 与重启见 `data/probe_rest_ws_flow.py`、`data/probe_restart_*.py`。

## 1. 自动化检查

| 检查 | cwd | 命令 | 退出码 | 结果 | 日志 |
| --- | --- | --- | ---: | --- | --- |
| S06 专项 | `backend` | `python -m pytest tests/test_room.py tests/test_identity_s01.py tests/test_s02_numeric_bounds.py tests/test_s06_room_contract.py -q` | 0 | **168 passed**（9.57s） | `logs/06_s06_targeted_tests.log` |
| 后端全量 | `backend` | `python -m pytest -q` | 0 | **388 passed, 1 skipped, 10 warnings**（17.96s） | `logs/07_backend_full_tests.log` |
| 前端构建 | `frontend` | `npm run build` | 0 | 775 modules；**built in 5.43s** | `logs/08_frontend_build.log` |
| 颜色门禁 | 仓库根 | `node scripts/check-colors.mjs` | 0 | 38 个文件无裸 hex/rgb/hsl | `logs/08b_check_colors.log` |
| 迁移 | 仓库根 | `python -m backend.scripts.migrate_s06_room_contract --db backend/eatwhat_s06_r01_iso.db --json-out .../migration.json` | 0 | 创建 `uq_room_votes_room_user_dish`；预启动行数 0 | `logs/02_migration.log` |
| 迁移幂等 | 仓库根 | 同命令（带 `--json-out .../migration_idempotent.json`） | 0 | `idempotent=true`，SHA 前后一致 | `logs/02b_migration_idempotent.log` |
| 启动前目标探针 | 仓库根 | `DATABASE_URL=... python .../probe_db_target.py` | 0 | 21/21；目标为 S06 隔离库，rooms/votes=0/0 | `logs/04_db_target_probe.log` |
| 运行后目标探针 | 仓库根 | `.../probe_db_target.py --allow-existing --output .../db_target_probe_post.json` | 0 | 仍为 S06 隔离库；记录 9 房间/51 票 | `logs/04b_db_target_probe_post.log` |
| 真实 REST/WS | 仓库根 | `python .../probe_rest_ws_flow.py` | 0 | **25 步全过** | `logs/09_rest_ws_flow.log` |
| 重启准备 | 仓库根 | `python .../probe_restart_prepare.py` | 0 | 房间 488981，1 票 | `logs/10a_restart_prepare.log` |
| 停止服务 | 仓库根 | `taskkill /F /PID <8025 listener>` | 0 | 端口释放 | `logs/10b_backend_stop.log` |
| 重启服务 | 仓库根 | `DATABASE_URL=... python -m uvicorn backend.main:app --port 8025` | 0 | health 200 | `logs/10c_backend_restart.log` |
| 重启验证 | 仓库根 | `python .../probe_restart_verify.py` | 0 | 无客户端请求前 DB 已 FINISHED；1 票；报告 10 道 | `logs/10d_restart_verify.log` |
| 数据库保护 | 仓库根 | `python .../probe_db_protection.py` | 0 | 五份受保护库 SHA 不变 | `logs/11_db_protection.log` |
| ω 手算 | 仓库根 | `python .../omega_matrix_handcalc.py` | 0 | A=60；B=24/46/68；赢家 A/A/B | `logs/12_omega_matrix_handcalc.log` |
| validation 汇总 | 仓库根 | `python .../build_validation.py` | 0 | **20/20** | `logs/14_build_validation.log` |

## 2. 基线/隔离

| 检查 | 命令 | 退出码 | 日志/数据 |
| --- | --- | ---: | --- |
| 基线采集 | `python .../capture_baseline.py` | 0 | `logs/00_baseline.log`、`data/baseline.json` |
| 隔离副本 | `python .../copy_iso_db.py` | 0 | `logs/01_iso_db_prepare.log`、`data/db_provenance.json` |
| fixture | `python .../prepare_s06_fixture.py` | 0 | `logs/03_fixture.log`、`data/fixture.json` |

## 3. 真实服务

- 地址：`http://127.0.0.1:8025` / `ws://127.0.0.1:8025`。
- 启动命令：仓库根 `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s06_r01_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8025`。
- 启动前已跑目标探针；服务日志 `logs/05_backend_start.log`、`logs/10c_backend_restart.log`。
- 服务已停止；8025/8000/5173 均无监听。
- 未使用真实浏览器；未调用高德/LLM/付费服务。

## 4. 警告与跳过

- 1 skipped：`test_pre00_runtime_migration.py` 的符号链接/硬链接环境依赖用例（Windows 权限/文件系统），非 S06 新增。
- 10 warnings：既有 `datetime.utcnow` 弃用、`requests` 依赖版本提示、pytest 缓存权限提示；退出码 0，未作为失败隐藏。
- 全量日志保留完整输出；未只贴成功尾行。

## 5. 未执行项

- S07 真实多人划卡/扫码/四身份/真机：DEFERRED，不在本步。
- 真实浏览器点击：用户明确本步用 REST/WS 验收，不以浏览器替代。
- `npm run build` 之外的 UI 门禁（home-fit/refill/sandbox-sync）：本轮未改 Home/store/router；`Room.vue/api` 仅 campus 透传，已用 build 验证。
- `/admin`、S10 数据导入、S11–S20、APK、高德/LLM 在线调用：未执行。
- 真实演示库迁移：未执行；演示库保持只读。
