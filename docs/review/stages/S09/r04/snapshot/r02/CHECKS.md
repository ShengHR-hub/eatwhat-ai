# CHECKS —— S09 / r02

- 执行日期：2026-10-25（Asia/Shanghai）
- 工作目录：`D:\EatWhat`；pytest 在 `backend/`。
- 高德 Key 只在命令环境变量中注入，未写入任何文件；证据中 Key 字段为 `<redacted>`。
- 日志在 `logs/`，结构化结果在 `data/`。

| # | 命令/动作 | 退出码 | 实际结果 | 日志/证据 |
|---:|---|---:|---|---|
| 1 | 地名搜索（环境变量 Key）：`geocode/geo`，`address=西安思源学院`，`city=西安` | 0 | HTTP 200；`status=1/OK`；返回 `109.078487,34.234818`（GCJ-02），`level=兴趣点`，`adcode=610111` | `logs/01_geocode.log`、`data/amap_geocode.json` |
| 2 | 3km 周边搜索 smoke：`place/around`，`types=050000`，page=1 | 0 | `count=600`；返回 25；样例行含 `tag`/`rating`/`cost` | `logs/02_poi_smoke.log`、`data/amap_poi_smoke.json` |
| 3 | 分页上限探针：page=1/8/9/16/24/25 | 0 | page 1/8 各 25 条；page 9 起 0 条；`count` 仍为 600 | `logs/03_pagination_probe.log`、`data/amap_pagination_probe.json` |
| 4 | 3km 网格采集：`amap_collect.py`（45 个初始 800m 网格 + 递归细分，`types=050000`，QPS 退避） | 0 | 133 次调用；61 个处理格；0 错误/0 未完成；原始 2,230；`poi.id` 去重 1,258；3km 内 607；剔除 2 条非餐饮 → **真实 POI 605**。2026-10-25T02:25:40 用与建大同版递归脚本复跑，数字不变 | `logs/04_amap_collect.log`、`logs/20_siyuan_recollect.log`、`data/amap_collection.json`、`data/amap_pois.jsonl` |
| 5 | 合并直接 count 与网格去重摘要：`finalize_poi_summary.py` | 0 | 直接 count=600；采集 605；差 5；真实 605 + 合成食堂 200 = 805；原目标 1500 未达、差额 895；**D03 已裁决接受实际 605** | `logs/05_finalize_poi.log`、`data/amap_collection.json` |
| 6 | 合成食堂方案 `data/canteen_plan.json` | — | `target_count=200`、`is_synthetic=1`、`PLAN_ONLY_NOT_IMPORTED`、与真实 POI 分列 | `data/canteen_plan.json` |
| 7 | `python docs/review/stages/S09/r02/probes/baseline_probe.py` | 0 | env/file_hashes/db_baseline/routes/route_gap/external_deps/assets 生成；无 commit；`/admin/stats/*` 0 个 | `logs/06_baseline.log`、`data/*.json` |
| 8 | `python .../validate_evidence.py`（PowerShell 仅把用户环境变量注入子进程，不打印 Key） | 0 | `ok=true`；思源 605+200=805、建大 6,659+200=6,859；两校区 POI 文件唯一/0 越界/无禁止字段；SSOT v2.3.5 含 13、双校区/C10/建大；S09=BLOCKED、S10=LOCKED；演示库 SHA 未变；Key 未泄漏 | `logs/07_validate.log`、`validation.json`、`data/evidence_index.json` |
| 9 | `cd backend; python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s09r02` | 0 | **161 passed**（S09 未改业务代码，基线） | `logs/08_pytest.log` |
| 10 | 证据哈希/manifest 复核 | 0 | `SOURCE_MANIFEST.json` 84 项，每项 SHA-256/字节复核无差异 | `SOURCE_MANIFEST.json` |
| 11 | `python .../sanitize_pois.py`（思源 + 建大） | 0 | 思源 605、建大 6,659 条 POI 只保留契约字段；删除 tel/email/photos/website/shopinfo/reviews/opentime2；`validation` 两校区 `forbidden_fields=[]` | `logs/09_sanitize_pois.log`、`logs/17_sanitize_siyuan.log`、`logs/18_sanitize_jianda.log`、`logs/21_sanitize_siyuan_recollect.log`、`data/amap_pois.jsonl`、`data/amap_jianda_pois.jsonl` |
| 12 | 2026-10-25 v2.3.4/v2.3.5 双校区与建大结果文档同步 | 0 | 更新 MASTER_SPEC/DASHBOARD_EXPANSION/AGENTS/README/AGENT_MEMORY/STAGE_STATUS 与 r02 契约；不改代码/DB/`/admin`；S09 当前 BLOCKED（提交时 REVIEW_PENDING）、S10 仍 LOCKED | `logs/10_doc_sync.log`（同步时 doc_changed 列表）、`logs/12_doc_sync_final.log`（最终 live_stale=0、code_changed=[]、DB 未变、admin=[]） |
| 13 | 建大雁塔试抓（PowerShell 从用户环境变量注入 Key，不打印值） | 0 | 中心 `108.967153,34.236991`（碑林区雁塔校区，非草堂）；真实 POI **6,659**；合成食堂 200；合计 **6,859**；1,206 次调用、0 错误/0 未完成 | `logs/15_jianda_geocode.log`、`logs/16_jianda_collect.log`、`logs/18_sanitize_jianda.log`、`data/amap_jianda_geocode.json`、`data/amap_jianda_collection.json`、`data/amap_jianda_pois.jsonl` |
| 14 | `python .../poi_field_stats.py` | 0 | 思源 rating 604/1、cost 427/178、tag 309/296；建大 rating 6,652/7、cost 5,411/1,248、tag 3,871/2,788（有值/缺失）；缺失保持 NULL | `logs/23_poi_field_stats.log`、`data/poi_field_stats.json`、两份 collection JSON |
| 15 | `python .../poi_spotcheck.py --file data/amap_jianda_pois.jsonl` | 0 | 6,659 行/6,659 唯一 ID；最远 2,999.5m；0 条 >3km；同名同址重复 0 组；同名 ≤50m 4 对、≤100m 5 对；同坐标 116 组（多为商场不同店）；前 20 条与分段分布见 JSON | `logs/22_jianda_spotcheck.log`、`data/jianda_poi_spotcheck.json` |
| 16 | D03 裁决落盘 | — | 思源 605=样本 A、建大 6,659=样本 B；分校区报，不是 1700 合计；不得建大补思源/跨校区混算；S09 台账仍 BLOCKED，未自行改台账 | `DECISIONS.md` D03；`SUBMISSION.md` |
| 17 | `python .../doc_sync_check.py`（最终） | 0 | `live_stale_files=[]`；`code_changed=[]`；DB SHA 未变、`group_rooms=0`/`room_votes=0`；`admin_routes=[]`；r01 历史保留 | `logs/25_doc_sync_check.log`、`data/doc_sync_check.json` |

## 关键数字

```text
center_gcj02        = 109.078487,34.234818
direct_count        = 600
raw_pois            = 2230
unique_pois         = 1258
within_3km          = 607
non_dining_excluded = 2
real_poi_count      = 605
synthetic_canteen   = 200
combined            = 805
target_1500_met     = false
target_shortfall    = 895
d03_decision        = ACCEPT_ACTUAL_605_AS_SAMPLE_A
cells_planned       = 45
cells_processed     = 61
api_calls           = 133
errors              = 0
incomplete_cells    = 0
rating_present      = 604
rating_missing      = 1
cost_present        = 427
cost_missing        = 178
tag_present         = 309
tag_missing         = 296

jianda_center_gcj02 = 108.967153,34.236991
jianda_real_poi     = 6659
jianda_combined     = 6859
jianda_cells        = 425
jianda_api_calls    = 1206
jianda_rating       = 6652 present / 7 missing
jianda_cost         = 5411 present / 1248 missing
jianda_tag          = 3871 present / 2788 missing
jianda_outside_3km  = 0 (max 2999.5m)
jianda_exact_name_addr_duplicate_groups = 0
jianda_same_name_pairs_50m = 4
```

## 未执行项（符合 S09 禁令）

- 未导入 605 条 POI 或 200 条合成食堂到数据库（S10）。
- 未实现/未运行 LLM 打标与查询扩容（S11）；未配置模型/预算。
- 未运行 S12/S13 正式仿真或对照实验。
- 未实现 S14+ CRUD/stats/大屏；未新增后台页面；未修改 `/admin`。
- 未修改 schema/核心算法/生产演示库；未执行 `--force`。
- 未创建/未修改 `REVIEW.md`，未签 PASS；台账 S09 当前为 `BLOCKED`（提交时曾为 `REVIEW_PENDING`），S10 仍 LOCKED。

## 限制

- 直接 `count=600` 与网格去重 605 相差 5；两者都按原样报告，不互相冒充。两者均低于 1500+ 原目标，但 **D03 已裁决接受 605 为样本 A**，差额仅作历史记录，不再阻塞。
- 建大同名且相距 ≤50m 的 4 对、≤100m 的 5 对为疑似同店多 ID（如 `双酱饼皇` 0.0m、`茶话弄` 6.5m/14.9m、`品汉源` 8.9m、`老李家biangbiang面` 68.7m），S10 导入前需人工裁决是否合并；当前证据保留原始 ID，不擅自删除。
- S09 台账仍为 `BLOCKED`，S10 继续 LOCKED；台账解封由 Codex/用户处理，本包未自行改台账或签 PASS。
- 高德 Key 只在采集命令环境变量中出现，未持久化；证据中无 Key。
- 菜品图、LLM、Android 等仍按“仅本地/后续步骤”处理，不写成 S09 已解决。
