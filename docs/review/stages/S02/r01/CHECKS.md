# S02 / r01 检查记录（CHECKS）

日期：2026-10-26（Asia/Shanghai）
所有命令在本机执行；cwd 与退出码逐条保留。日志在 `logs/`，数据在 `data/`。

## 1. 命令总表

| # | 命令 | cwd | 退出码 | 结果 | 日志 / 证据 |
| --- | --- | --- | --- | --- | --- |
| 1 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02-baseline` | `D:/EatWhat/backend` | **0** | 210 passed, 1 skipped（改动前基线；与 S01/r01 受审版本一致） | 本次仅终端尾部；同版本完整日志见 `docs/review/stages/S01/r01/logs/20_backend_pytest.log` |
| 2 | `python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02-red` | `D:/EatWhat/backend` | **1（预期红灯）** | 24 failed, 11 passed | `logs/00_red_baseline.log` |
| 3 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02-full` | `D:/EatWhat/backend` | **0** | 249 passed, 1 skipped（首轮实现后） | `logs/10_backend_pytest_full.log` |
| 4 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02-final` | `D:/EatWhat/backend` | **0** | 255 passed, 1 skipped（补历史向量守卫后） | `logs/11_backend_pytest_full_after_final.log` |
| 5 | `python -m pytest tests/test_s02_numeric_bounds.py -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02-target-final2` | `D:/EatWhat/backend` | **0** | **47 passed**（最终专项） | `logs/14_backend_pytest_s02_final2.log` |
| 6 | `python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s02-final3` | `D:/EatWhat/backend` | **0** | **257 passed, 1 skipped**（最终全量） | `logs/15_backend_pytest_full_final2.log` |
| 7 | `DATABASE_URL='sqlite:///D:/EatWhat/backend/eatwhat_s02_r01_iso.db' python -m uvicorn backend.main:app --host 127.0.0.1 --port 8013` | `D:/EatWhat` | 0（手动 `taskkill` 停止） | 启动成功，端口已释放 | `logs/20_live_server.log` |
| 8 | `python docs/review/stages/S02/r01/data/live_api_probe.py` | `D:/EatWhat` | **0** | 40 个真实 HTTP 用例通过；状态集合 `{200,404,422}`，无 500 | `data/live_api_probe.json`、`logs/21_live_probe.err.log` |
| 9 | `python docs/review/stages/S02/r01/data/build_db_protection.py` | `D:/EatWhat` | **0** | 三库未变、隔离库 schema 同源、行数符合预期 | `data/db_protection.json` |
| 10 | `python docs/review/stages/S02/r01/data/build_manifest.py` | `D:/EatWhat` | **0** | 145 项，fingerprint `eb17fe30…f9b03f` | `SOURCE_MANIFEST.json`、`data/build_manifest.stdout.txt` |
| 11 | `python docs/review/stages/S02/r01/data/build_validation.py` | `D:/EatWhat` | **0** | 生成机器可读验收摘要 | `validation.json` |

> 所有 pytest 均使用仓库内独立 `--basetemp=D:/EatWhat/.pytest-tmp-s02-*`，未触发 Windows 临时目录权限问题；临时目录运行后已清理，日志保留。
> 红灯保留：`logs/00_red_baseline.log` 是修复前真实执行结果；实现后同一文件 47 条全通过（#5）。
> #3/#4 是过程中间版本的全量结果；`logs/12`、`logs/13` 是补“超大整数历史值守卫”之前的一版专项/全量（46/256），同样保留；最终以 #6 为准。

## 2. 专项覆盖（47 条）

`backend/tests/test_s02_numeric_bounds.py`：

- **向量语义**：两键部分合并后仍 8 键、未提供维度保持原值；`{}` 422；额外键 422；历史缺键用 0.5 补齐；历史越界值/超大整数 409 且要求完整覆盖；0/1 边界接受；-0.01、1.01、95 拒绝。
- **类型冒充**：布尔、字符串、`NaN`、`Infinity`、`-Infinity` 全部 422 且库内向量不变；JSON 体 `NaN/Infinity` 经全局校验错误处理器返回 422，不再 500。
- **偏好其它字段**：预算 8/500 接受，7.99/500.01/-1 拒绝；忌口 16 字接受、17 字拒绝；21 条拒绝；`default_budget=NaN` 422 且库不变。
- **推荐**：`budget/limit/weather_temp/max_distance_meters/exclude_dish_ids` 布尔 422；未知气泡 422；合法但不适用模式的气泡仍 200 并列入 `ignored`；override 六个参数的边界接受、越界/布尔拒绝；预算 0/2000、天气 -30/50、limit 1/100、距离 0/100000 均 200，且 `radar_5d` 0–100、`total_score` 0–100、`decay_weight` 0–1、四权重和≈1。
- **天气**：`temp=nan/inf/1000/-40`、33 字文本 422；-30/50、32 字文本 200。
- **打卡**：`dish_id`/`cost_amount` 布尔 422；负金额 422；未知气泡 422；不存在菜品 404；模式不一致 400；所有失败路径日志数不变。
- **冰箱/引用**：空白名、33 字名、空白数量描述、布尔 `expire_days` 均 422 且行数不变；购物清单 `[有效,99999]` 404 且不写库；`dish_ids=[true]` 422。
- **红黑榜/房间**：布尔 `target_id` 422 且收藏不变；不存在目标 404 且收藏不变；房间布尔 budget/override 422 且不建房。
- **契约一致性**：`schemas.GENE_KEYS` 与 `vector_spec.FEATURE_KEYS` 一致；测试内独立抄写的 8 键与之集合一致；`BUBBLE_IDS` 与 `STATUS_BUBBLE_RULES` 一致。

## 3. 全量回归与警告

- 最终全量：**257 passed, 1 skipped, 513 warnings, exit 0**（14.57s）。
- skip 为既有 Windows 符号链接权限用例，本步未新增 skip。
- warnings 为既有 `datetime.utcnow()` 弃用与 `requests/urllib3` 版本提示；无新增未处理异常。
- 未删除旧断言、未扩大容差；唯一新增是 `test_s02_numeric_bounds.py`。既有 `test_preferences_accept_valid_payload` 的两键写法在方案 A 下仍为合法用例。

## 4. 真实 HTTP 与隔离库

隔离副本：`backend/eatwhat_s02_r01_iso.db`，由 `backend/eatwhat_dev_pre00_r02.db`（`b965e73e…706a579`）复制；schema fingerprint 与源库一致。

| 项目 | 结果 |
| --- | --- |
| 用例数 | 40（health + 偏好 + 推荐 + 天气 + 打卡 + 冰箱 + 购物清单 + 红黑榜 + 房间） |
| 状态码集合 | `{200, 404, 422}`；**0 个 500** |
| 合法写 | 仅 1 次合法打卡（`cost_amount=0`），`eating_logs` 9→10 |
| 非法写 | 全部 4xx；偏好向量、收藏、日志、冰箱、房间行数前后不变 |
| 收尾向量 | 8 键、全部有限、0–1 |
| 受保护库 | 演示库 / S10 库 / 开发源库 SHA-256 前后一致 |
| 服务端 | `127.0.0.1:8013` 已停止，端口已释放 |

中途还跑过两次同脚本：`data/live_api_probe_pre_guard.json`（首轮修复前）与 `data/live_api_probe_pre_hugeint.json`（补超大整数守卫前），两次均通过。最终 `data/live_api_probe.json` 在最终运行时上重跑，绑定最终 manifest；此后只修改证据文档，不再改运行时代码。

## 5. 未执行

- 前端无改动：未跑 `npm run build`、未跑三条界面门禁、未启浏览器。理由见 `BASELINE.md` §6；预算/天气控件范围只做只读核对，未改控件。
- 多人 WS、S03 时效、S04 四算法、S10/`/admin`、APK 不在本步，未验证也未触碰。
