# S02 / r02 检查记录（CHECKS）

日期：2026-10-26（Asia/Shanghai）
所有命令在本机执行；cwd 与退出码逐条保留。日志在 `logs/`，数据在 `data/`。

## 1. 命令总表

| # | 命令 | cwd | 退出码 | 结果 | 日志 / 证据 |
| --- | --- | --- | --- | --- | --- |
| 1 | `python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02r02-red` | `D:/EatWhat/backend` | **1（预期红灯）** | 42 failed, 54 passed | `logs/00_red_baseline.log` |
| 2 | `python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02r02-target-final` | `D:/EatWhat/backend` | **0** | **96 passed** | `logs/12_backend_pytest_s02_final.log` |
| 3 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02r02-full` | `D:/EatWhat/backend` | **0** | **306 passed, 1 skipped** | `logs/10_backend_pytest_full.log` |
| 4 | `DATABASE_URL='sqlite:///D:/EatWhat/backend/eatwhat_s02_r02_iso.db' python -m uvicorn backend.main:app --host 127.0.0.1 --port 8014` | `D:/EatWhat` | 0（手动 `taskkill` 停止） | 启动成功，端口已释放 | `logs/20_live_server.log` |
| 5 | `python docs/review/stages/S02/r02/data/live_api_probe.py` | `D:/EatWhat` | **0** | 45 个真实 HTTP 用例；状态 `{200,404,409,422}`，无 500 | `data/live_api_probe.json`、`logs/21_live_probe.err.log` |
| 6 | `python docs/review/stages/S02/r02/data/build_db_protection.py` | `D:/EatWhat` | **0** | 三库未变、隔离库 schema 同源 | `data/db_protection.json` |
| 7 | `python docs/review/stages/S02/r02/data/build_manifest.py` | `D:/EatWhat` | **0** | 146 项，fingerprint `2c8cc39d…c9556a` | `SOURCE_MANIFEST.json`、`data/build_manifest.stdout.txt` |
| 8 | `python docs/review/stages/S02/r02/data/build_validation.py` | `D:/EatWhat` | **0** | 机器可读验收摘要 | `validation.json` |

> 所有 pytest 使用仓库内独立 `--basetemp=D:/EatWhat/.pytest-tmp-s02r02-*`，未触发 Windows 临时目录权限问题；临时目录运行后已清理，日志保留。
> 红灯保留：`logs/00_red_baseline.log` 是修复前真实失败（含复审报告两条复现）；修复后同一文件 96 条全通过。

## 2. 复审阻断项的定向回归

| 复审项 | 用例 | 断言 |
| --- | --- | --- |
| S02-R01-01：预算更新绕过坏向量 | `test_invalid_history_blocks_every_update_path[budget_only-*]`（9 种历史状态） | 409；`base_vector/default_budget/veto_tags/preferred_cuisines/红黑榜` 快照完全一致 |
| S02-R01-01：忌口/菜系/向量路径 | 同矩阵 `veto_only-*`、`cuisine_only-*`、`vector_only-*` | 409；整行快照一致 |
| S02-R01-02：未知键被静默丢弃 | `test_invalid_history_blocks_every_update_path[vector_only-unknown_key]`、`test_full_vector_cannot_bypass_invalid_history[unknown_key]` | 409；`umami_level` 仍在库内 |
| 组合请求原子失败 | `test_invalid_history_blocks_combined_update` | 409；四个字段全部未写 |
| 合法缺键补齐 | `test_valid_but_incomplete_history_is_completed_on_every_update_path`（4 条） | 200；补齐 8 键、已有值保留、请求字段生效 |
| 合法完整不被改写 | `test_valid_complete_history_keeps_vector_on_non_vector_updates` | 200；预算/忌口/菜系更新后向量逐键不变 |

## 3. 专项覆盖（96 条）

历史状态矩阵（9 种 × 4 条更新路径 = 36）：

- 未知键 `umami_level`；
- 越界 `spicy_level=95`；
- `NaN`、`Infinity`；
- 布尔 `True`；
- 字符串 `"0.5"`；
- `null` 值；
- 超大整数 `10**400`；
- 非对象（列表）。

另含：完整八维覆盖不能绕过非法历史值（9 条）、组合更新（1 条）、合法缺键 4 条、合法完整 1 条。r01 原有 47 条中保留 45 条；删除 2 条与统一守卫冲突的旧断言（“完整覆盖可修复坏向量”“超大整数单独一条”，后者已并入矩阵）。

## 4. 全量回归与警告

- 最终全量：**306 passed, 1 skipped, 513 warnings, exit 0**（15.47s）。
- skip 为既有 Windows 符号链接权限用例；本步未新增 skip。
- warnings 为既有 `datetime.utcnow()` 弃用与 `requests/urllib3` 版本提示；无新增未处理异常。
- 未删除与历史向量无关的旧断言、未扩大容差。

## 5. 真实 HTTP 与隔离库

隔离副本：`backend/eatwhat_s02_r02_iso.db`，由 `backend/eatwhat_dev_pre00_r02.db`（`b965e73e…706a579`）复制；schema fingerprint 与源库一致。

| 项目 | 结果 |
| --- | --- |
| 用例数 | 45 |
| 状态码集合 | `{200, 404, 409, 422}`；**0 个 500** |
| 复审场景 1 | 历史 `{"spicy_level":95,"oily_level":0.8}` + `default_budget:31` → **409**，预算/向量均未变 |
| 复审场景 2 | 历史含 `umami_level` + 合法部分向量 → **409**，未知键仍在、字段未变 |
| 组合请求 | 坏历史 + 向量/预算/忌口/菜系 → **409**，整行不变 |
| 合法缺键 | 历史两键 + 预算更新 → **200**，补齐 8 键、缺键 0.5、预算 31 |
| 合法完整 | 用户 1 仅改预算 → **200**，向量逐键不变 |
| 合法写 | 仅 1 次合法打卡（`cost_amount=0`），`eating_logs` 9→10 |
| 受保护库 | 演示库 / S10 库 / 开发源库 SHA-256 前后一致 |
| 服务端 | `127.0.0.1:8014` 已停止，端口已释放 |

## 6. 未执行

- 前端无改动：未跑 `npm run build`、三条界面门禁、浏览器。理由见 `BASELINE.md` §7。
- 多人 WS、S03 时效、S04 四算法、S10/`/admin`、APK 不在本步，未验证也未触碰。
