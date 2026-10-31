# G2 执行记录

命令均在 `D:\EatWhat` 执行；日志在 `docs/review/consolidated/G2/logs/`。

## 1. 小样 → 全量导入

| 命令 | 结果 | 日志 |
| --- | --- | --- |
| `python -m backend.scripts.fetch_amap_poi pois --db backend/eatwhat_g2_s10_smoke.db --campus SIYUAN --limit 20 ...` | 20 条，rejected 0 | `10_smoke_poi_siyuan.log` |
| 同上（JIANDA_YANTA / 食堂 / 菜谱） | 20 + 10 + 10 + 60，rejected 0 | `data/smoke/*` |
| `python docs/review/consolidated/G2/data/check_smoke_mapping.py` | 40/40 POI、60/60 菜谱映射通过 | `data/smoke_mapping.json` |
| `python docs/review/consolidated/G2/data/prepare_empty_import_db.py backend/eatwhat_g2_s10_full.db` | 空白 schema + 唯一索引 | `data/eatwhat_g2_s10_full_schema.json` |
| 全量 POI（两校区） | 605 + 6,659，rejected 0 | `11_full_poi.log`、`data/full/poi_*.json` |
| 全量食堂 + 菜谱 | 200 + 200、6,400，rejected 0 | `12_full_canteen_recipes.log` |
| `python -m backend.scripts.verify_s10_import --db backend/eatwhat_g2_s10_full.db ...` | **36/36 checks，overall_ok=true** | `13_full_verify.log`、`data/full_verify/` |
| 复跑导入（幂等） | 行数/指纹 delta 0 | `14_rerun_idempotency.log` |
| 复跑后验证 | **37/37 checks，含 idempotent_reimport=true** | `15_idempotency_verify.log`、`data/full_verify_after_rerun/` |

## 2. BRIDGE-10

| 命令 | 结果 | 证据 |
| --- | --- | --- |
| `python backend/scripts/bridge_s10_runtime.py` | 桥接库生成；复跑新增 0 行；源库/模板 SHA 不变 | `data/bridge_provenance.json` |
| `python docs/review/consolidated/G2/data/bridge_api_probe.py` | 群组校区过滤通过、跨校区 409、下厨共享通过；**单人推荐校区 FAIL** | `data/bridge_api.json` |

## 3. S11（BLOCKED，0 付费调用）

| 命令 | 结果 | 证据 |
| --- | --- | --- |
| `python docs/review/consolidated/G2/data/s11_preflight.py` | 6,400 道 / 320 批 / 最多 960 次调用；`status=BLOCKED`，`network_calls=0` | `data/s11_preflight.json`、`data/coverage.json`、`16_s11_preflight.log` |
| `python docs/review/consolidated/G2/data/query_budget_probe.py` | 下厨库存查询恒 1（旧实现 32）；limit 5/10/24 总 SQL 恒 6；top3 等价 | `data/query_budget.json` |

## 4. 校区修复后的复验

| 命令 | 结果 | 日志 |
| --- | --- | --- |
| `python -m pytest -q`（backend，隔离 basetemp） | **396 passed, 1 skipped**，exit 0 | `35_recheck_pytest_full.log` |
| `node scripts/home-fit.mjs` / `refill-fresh.mjs` / `sandbox-sync.mjs` | 全部 PASS，exit 0 | `30–32_recheck_*.log` |
| `npm run build` / `node scripts/check-colors.mjs` | exit 0 | `33–34_recheck_*.log` |
| `node docs/review/consolidated/G1/browser/s08_regression.mjs` | exit 0，两档布局/身份/状态通过 | `36_recheck_s08.log` |
| `python docs/review/consolidated/G2/data/bridge_api_probe.py` | 单人/群组校区、422、NULL 排除全部通过 | `data/bridge_api.json` |

## 5. 数据保护

| 命令 | 结果 |
| --- | --- |
| `python docs/review/consolidated/G2/data/probe_db_protection.py` | 8 个受保护库 SHA 未变；S09 manifest 未变 | `21_db_protection.log` |
| `python docs/review/stages/S09/r04/probes/verify_sealed.py` | `validation_ok=true` / `evidence_checks_ok=true` | `22_s09_seal_verify.log` |

## 5. 未执行 / BLOCKED

| 项 | 原因 |
| --- | --- |
| LLM 全量打标 | Key/模型/预算未确认，按 G2 规则不发起付费调用 |
| 单人推荐校区过滤与缺失 campus 422 | 应用未实现；记 P1，未擅自扩大改动（见 SUBMISSION §2） |
| `/admin/stats/*` 联动 | 统计接口属 S15，本组不实现（探针 404） |
| 前端校区切换 UI | SSOT v2.3.6 留后续专项 |
| 全量 JIANDA POI 复跑 | 逐行去重耗时约 10 分钟，本轮取前 50 条复跑 + 唯一来源索引/指纹证明幂等 |
