# G1 执行记录（命令 / 退出码 / 日志）

所有命令在 `D:\EatWhat` 或注明的子目录执行；日志在 `docs/review/consolidated/G1/logs/`。

## 1. 自动化测试与构建

| 命令 | cwd | 结果 | 日志 |
| --- | --- | --- | --- |
| `python -m pytest -q --basetemp=D:/EatWhat/.pytest-g1-20261028` | `backend/` | **391 passed, 1 skipped**, exit 0（31.85s） | `24_pytest_full.log` |
| `npm run build` | `frontend/` | 构建成功，exit 0（10.77s） | `25_frontend_build.log` |
| `node scripts/home-fit.mjs` | 根 | 390×844 / 390×667 均 PASS，exit 0 | `20_gate_home_fit.log` |
| `node scripts/refill-fresh.mjs` | 根 | PASS，exit 0 | `21_gate_refill_fresh.log` |
| `node scripts/sandbox-sync.mjs` | 根 | PASS，exit 0 | `22_gate_sandbox_sync.log` |
| `node scripts/check-colors.mjs` | 根 | 38 文件无裸色值，exit 0 | `23_gate_check_colors.log` |

## 2. 服务

| 命令 | 日志 |
| --- | --- |
| `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_g1_s07_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` | `00_backend_start.log` |
| `npm run dev -- --host 0.0.0.0 --port 5173` | `01_vite_dev.log` |
| 断线重连测试中停/启 Vite 代理 | `01b_vite_restart.log`、`reconnect_step1/2.json` |

## 3. 浏览器场景（真实输入事件）

| 场景 | 命令 | exit | 日志 / 数据 | 截图 |
| --- | --- | --- | --- | --- |
| A 两独立身份全流程 | `node docs/review/consolidated/G1/browser/s07_two_identity.mjs` | 0 | `10_s07_two_identity.log`、`browser/s07_two_identity.json` | `shots/a01–a07` |
| B 四身份 + 三种冲突 | `.../s07_four_identity.mjs` | 0 | `11_s07_four_identity.log`、`browser/s07_four_identity.json` | `shots/b01–b04` |
| C 刷新 / 后台 / 揭晓恢复 | `.../s07_recovery.mjs` | 0 | `12_s07_recovery.log`、`browser/s07_recovery.json` | `shots/c01–c06` |
| C 断线重连（两阶段） | `.../reconnect_step1.mjs` → 重启 Vite → `.../reconnect_step2.mjs` | 0 / 0 | `browser/reconnect_step1.json`、`reconnect_step2.json` | — |
| D 负例与全否决 | `.../s07_negative.mjs` | 0 | `13_s07_negative.log`、`browser/s07_negative.json` | `shots/d01–d03` |
| S08 总回归 | `.../s08_regression.mjs` | 0 | `14_s08_regression.log`、`browser/s08_regression.json` | `shots/s08_*` |
| S08 返回路径 / 动效 | `.../s08_addendum.mjs` | 0 | `15_s08_addendum.log`、`browser/s08_addendum.json` | `shots/s08_back_paths.png` |

浏览器为 4 个独立 headless Chrome（各自 `--user-data-dir`，端口 9222–9225），不是同一浏览器的两个标签；身份由每个实例的 localStorage 提供，并通过实际请求头 `X-User-Id` 核验。运行前清理残留标签，避免后台标签节流影响计时。

## 4. 数据与保护

| 命令 | 结果 | 日志 / 数据 |
| --- | --- | --- |
| `python docs/review/consolidated/G1/data/prepare_g1_db.py` | 创建隔离库 + fixture，受保护库 SHA 未变 | `data/db_provenance.json` |
| `python docs/review/consolidated/G1/data/probe_db_protection.py` | 7 个受保护库 SHA 与基线一致，`all_protected_unchanged=true` | `data/db_protection.json` |
| `python docs/review/stages/S09/r04/probes/verify_sealed.py` | `validation_ok=true` / `evidence_checks_ok=true`，manifest 未变 | `30_s09_seal_verify.log` |

## 5. 未执行 / BLOCKED

| 项 | 原因 |
| --- | --- |
| 真机相机扫码 | 本会话没有可操作的第二台设备；二维码载荷、局域网可达性与「链接进房」已验证，扫码动作未实测 |
| Lottie 揭晓动画 | 自绘素材在 `lottie-web` light 下不可见（`docs/AGENT_MEMORY.md` §10.4），当前用内联 SVG + GSAP + confetti；未改用其他动效库，也不声称 Lottie 揭晓通过 |
| 断线后继续投票 | 代理重启会触发 Vite 开发期整页重载，重连后房间已按 15 秒截止结算；重连本身（socket=open、错误清空、现场恢复）已验证，刷新路径单独证明本人票保留 |
| 真机 APK / 小屏物理设备 | 属 S18，不在 G1 范围 |
