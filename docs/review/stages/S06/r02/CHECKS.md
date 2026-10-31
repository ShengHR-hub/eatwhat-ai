# S06 / r02 检查记录

执行日期：2026-10-27（Asia/Shanghai）
机器可读退出码/时间：`data/command_results.json`
真实服务：`http://127.0.0.1:8026` / `ws://127.0.0.1:8026`；服务已停止，8026/8000/5173 无监听。

## 1. 自动化检查

| 检查 | cwd | 命令 | 退出码 | 结果 | 日志 |
| --- | --- | --- | ---: | --- | --- |
| S06 定向 | `backend` | `python -m pytest tests/test_room.py tests/test_identity_s01.py tests/test_s02_numeric_bounds.py tests/test_s06_room_contract.py -q` | 0 | **171 passed**（9.89s） | `logs/06_s06_targeted_tests.log` |
| 后端全量 | `backend` | `python -m pytest -q` | 0 | **391 passed, 1 skipped, 10 warnings**（18.29s） | `logs/07_backend_full_tests.log` |
| 前端构建 | `frontend` | `npm run build` | 0 | 775 modules；built in 5.21s | `logs/08_frontend_build.log` |
| 颜色门禁 | 仓库根 | `node scripts/check-colors.mjs` | 0 | 38 个文件通过 | `logs/08b_check_colors.log` |
| 迁移 | 仓库根 | `python -m backend.scripts.migrate_s06_room_contract --db backend/eatwhat_s06_r02_iso.db --json-out .../migration.json` | 0 | 创建唯一索引；预启动行数 0 | `logs/02_migration.log` |
| 迁移幂等 | 仓库根 | 同命令（`migration_idempotent.json`） | 0 | idempotent=true，SHA 不变 | `logs/02b_migration_idempotent.log` |
| 启动前目标探针 | 仓库根 | `DATABASE_URL=... python .../probe_db_target.py` | 0 | 22/22；r02 隔离库；rooms/votes=0/0 | `logs/04_db_target_probe.log` |
| 运行后目标探针 | 仓库根 | `... probe_db_target.py --allow-existing --output .../db_target_probe_post.json` | 0 | 仍为 r02 隔离库 | `logs/04b_db_target_probe_post.log` |
| 完整 REST/WS 回归 | 仓库根 | `python .../probe_rest_ws_flow.py` | 0 | **25 步全过** | `logs/09_rest_ws_flow.log` |
| **P2-S06-02** | 仓库根 | `python .../probe_p2_join_state.py` | 0 | SWIPING/FINISHED 既有成员 join 均 400；无副作用 | `logs/09b_p2_join_state.log` |
| **P2-S06-01** | 仓库根 | `python .../probe_p2_sweeper_fault.py` | 0 | 先 `room_sweeper_failed`、后 `room_sweep_settled`；无定时器/客户端；DB FINISHED | `logs/09c_p2_sweeper_fault.log` |
| 重启准备 | 仓库根 | `python .../probe_restart_prepare.py` | 0 | 房间 617709，1 票 | `logs/10a_restart_prepare.log` |
| 停止服务 | 仓库根 | `taskkill /F /PID <8026 listener>` | 0 | 端口释放 | `logs/10b_backend_stop.log` |
| 重启服务 | 仓库根 | `DATABASE_URL=... python -m uvicorn backend.main:app --port 8026` | 0 | health 200 | `logs/10c_backend_restart.log` |
| 重启验证 | 仓库根 | `python .../probe_restart_verify.py` | 0 | 任何客户端请求前 DB FINISHED；1 票 | `logs/10d_restart_verify.log` |
| 数据库保护 | 仓库根 | `python .../probe_db_protection.py` | 0 | 六份受保护库（含 r01 隔离库）SHA 不变 | `logs/11_db_protection.log` |
| ω 手算 | 仓库根 | `python .../omega_matrix_handcalc.py` | 0 | A=60；B=24/46/68；赢家 A/A/B | `logs/12_omega_matrix_handcalc.log` |
| validation 汇总 | 仓库根 | `python .../build_validation.py` | 0 | **22/22** | `logs/14_build_validation.log` |

## 2. 两项 P2 的复验结论

### P2-S06-02

`data/p2_join_state.json`：

- 房间 381152；SWIPING 既有成员 join → 400；FINISHED 既有成员 join → 400；FINISHED 房主 join → 400。
- 成员始终 `[1,2]`；候选 ID 不变；票数 0；赢家/报告不变；`no_side_effects=true`。

### P2-S06-01

`data/p2_sweeper_fault.json`：

- 房间 970002 直接插入为 SWIPING、deadline `15:30:50`；**没有 WS START（无定时器）**、**没有房间客户端**。
- 独立 `BEGIN EXCLUSIVE` 持锁 30s；本轮服务日志先 `room_sweeper_failed`，后 `room_sweep_settled` 且包含 `970002`。
- 释放后无任何房间请求，只读 DB：`FINISHED`、`settled_at=15:31:18` > deadline、赢家 101、`vote_count=0`。
- `server_log.failure_before_recovery=true`、`room_code_in_settled_log=true`。

## 3. 警告与跳过

- 1 skipped：既有 `test_pre00_runtime_migration.py` 的符号链接/硬链接环境依赖用例。
- 10 warnings：既有 `datetime.utcnow` 弃用、`requests` 依赖版本、pytest 缓存权限提示；退出码 0，未隐藏。
- 全量日志保留完整输出。

## 4. 未执行项

- S07 真实划卡/扫码/四身份/真机：DEFERRED。
- 真实浏览器点击：本步以独立 REST/WS 复验，不以浏览器替代。
- `/admin`、S10 数据导入、S11–S20、APK、高德/LLM 在线调用：未执行。
- 演示库迁移/写入：未执行。
