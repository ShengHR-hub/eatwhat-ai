# S09 / r02 设计决策清单

- 日期：2026-10-25（Asia/Shanghai）
- 性质：用户已确认口径的落盘记录；r02 提交后等待 Codex 独立复审，开发方不签 PASS。
- 状态：`CONFIRMED` 已由用户拍板并写入 SSOT；`BLOCKED` 缺外部条件；`DEFERRED` 明确留给后续步骤。

## 1. 已确认并写入 SSOT v2.3.5

| ID | 决策 | 状态 | 落盘 |
|---|---|---|---|
| D01 | 中心点=西安思源学院主校区；高德地名搜索实际 GCJ-02 `109.078487,34.234818`（2026-10-25T00:24:28+08:00）；3km | **CONFIRMED** | SSOT v2.3.5 §7；`data/amap_geocode.json` |
| D02 | 高德 Key 只从本地环境变量读取，不入源码/JSON/日志/证据 | **CONFIRMED** | `probes/amap_collect.py`；证据中 `<redacted>` |
| D04 | 200 个食堂窗口为**合成**，`source_type=CANTEEN`、`is_synthetic=1`、`source_dataset=synthetic_canteen_v1`，不计真实 POI | **CONFIRMED** | SSOT §3/§7；`data/canteen_plan.json` |
| D05 | 菜谱使用**合成数据**，`is_synthetic=1`、`source_dataset=synthetic_recipe_v1`；不得包装成真实采集 | **CONFIRMED** | SSOT §7 |
| D06 | 特征值=成功打标菜品数×8；不再固定声称 60,000+；要写 60,000+，成功数须≥7,500 | **CONFIRMED** | SSOT §7；`DATA_PLAN.md` §6 |
| D07 | 菜谱实体按数据行统计，同时单独报告唯一菜名数；不得用重复行凑规模 | **CONFIRMED** | SSOT §7；`DATA_PLAN.md` §6 |
| D08 | 外食菜品=人工整理菜单，AMap `tag` 仅作补充；不得把菜谱库菜名任意绑定门店并称真实菜单 | **CONFIRMED** | SSOT §7；`DATA_PLAN.md` §5 |
| D09 | POI `rating`/`cost` 缺失保持 NULL，不得填 4.5/500 伪默认 | **CONFIRMED** | SSOT §3/§7 |
| D10 | `distance_meters` 定义为直线距离；保留旧字段名但契约明确不是步行距离 | **CONFIRMED** | SSOT §3/§7 |
| D11 | 保留 13 个 stats 接口（含 `quality`）；SSOT 旧计数改为 13 | **CONFIRMED** | SSOT v2.3.5 §5/§8 |
| D12 | 不适用筛选统一 `200 {applicable:false, reason, items:[], meta:{}}` | **CONFIRMED** | SSOT §5 模块 8 |
| D13 | C08 由 `eating_logs+room_votes` 聚合，被选/被投次数降序 Top10，VETO 不计；不新增第 14 个 stats，扩展现有 `race` 的 `latest_top10` | **CONFIRMED** | SSOT §5 `race`/§6.5 |
| D14 | C11 桑基守恒单位为“票” | **CONFIRMED** | SSOT §5 `flow` |
| D15 | C10 数据源为 `restaurants` 全量 + `dishes_and_recipes` 全量，气泡=出现频次；OUT_DINING 用真实 rating，HOME 无真实 rating 时 `rating=NULL`，评分轴只绘非空点并报 `not_plotted_no_rating`，不伪造评分 | **CONFIRMED** | SSOT v2.3.4 §5/§6.5 |
| D16 | `allergen_tags` 用可空 JSON 列；供词云/质量面板消费，不默认加入算法 2 硬过滤 | **CONFIRMED** | SSOT §3/§7 |
| D17 | 软删除：`deleted_at` 可空；推荐/列表过滤已删除，历史流水/投票/报告仍可联表；不硬删被引用对象 | **CONFIRMED** | SSOT §3；`DATA_PLAN.md` §9.1 |
| D18 | `feature_vector` 可空表示未完成；新增 `tagging_status`、`tagging_error`、`llm_meta`；失败不写占位向量 | **CONFIRMED** | SSOT §3/§7 |
| D19 | 来源字段：`source_dataset`、`source_record_id`、`source_url`、`data_version`；可空 | **CONFIRMED** | SSOT §3 |
| D20 | 仿真数据写独立统计库，不写演示库；stats 指向统计库 | **CONFIRMED** | SSOT §7.3 |
| D21 | random baseline 固定 R=30，保存种子、均值、区间 | **CONFIRMED** | SSOT §7.4；`EXPERIMENT_PROTOCOL.md` |
| D22 | 重复率=相邻餐次同菜系次数/累计餐次；第一餐入分母但不算重复 | **CONFIRMED** | SSOT §7.3；`EXPERIMENT_PROTOCOL.md` |
| D23 | 7×4 时段：早餐[05,10)、午餐[10,15)、晚餐[15,21)、夜宵[21,05)；weekday 0=周一 | **CONFIRMED** | SSOT §5/§7.4 |
| D24 | 地图 PNG 导出在 S17 实现并实测；S09 不偷渡 | **DEFERRED** | SSOT §7.4 |
| D25 | 菜品图仅本地毕设演示，不进入公开发布/APK 公开分发/论文公开素材 | **CONFIRMED** | SSOT §7.1 |
| D28 | 后台身份沿用演示级 `X-User-Id`，不新增 JWT；后台是否强制该头在 S14 实现时按 SSOT 演示级口径记录 | **CONFIRMED** | SSOT §5 0 |
| D29 | stats 按 Asia/Shanghai 本地日期、默认全库范围 | **CONFIRMED** | SSOT §5/§7.4 |
| D30 | 共现：无序主辅料对，次数≥3 入图，top_n=30/上限100，过滤盐/水/油/葱/姜/蒜等 | **CONFIRMED** | SSOT §5 `cooccurrence` |
| D31 | C07 按 dishes 行数；C12 按 eating_logs 决策量；C08/C15 热度=被选日志+被投票，VETO 不计 | **CONFIRMED** | SSOT §6.5/§7.4 |
| D32 | `overview` 返回 `meta.scope`，明确 mode 过滤对哪些计数生效 | **CONFIRMED** | SSOT §5 `overview` |
| D33 | 双校区：A 思源（中心 109.078487,34.234818；真实 POI 605；合成食堂 200；合计 805）；B 建大雁塔（中心 108.967153,34.236991；真实 POI 6,659；合成食堂 200；合计 6,859）；两校区 3km/050000/网格/去重，实际数不合成 | **CONFIRMED（均已试抓）** | SSOT v2.3.5 §5.5/§7 |
| D34 | `restaurants.campus`、`group_rooms.campus` 可空；外食推荐/群组按校区过滤，跨校区不能拼桌；下厨菜谱共享 | **CONFIRMED** | SSOT v2.3.4 §3/§5.5 |
| D35 | 前端校区切换（默认思源）；切换后推荐/POI/统计同步；`overview` 返回 `by_campus`+`total`，合计不掩盖单校区 | **CONFIRMED** | SSOT v2.3.5 §5.5 |
| D36 | 食堂窗口按校区分别合成/标注（思源 200、建大 200 目标），不混用；实数按校区替换，不足 200 按实际记 | **CONFIRMED** | SSOT v2.3.4 §5.5/§7 |
| D37 | `1700` 是原规格总数目标，不是实际数；`17` 只是大屏图数量；“2km 不足 1700 再扩 3km”作废；两校区固定 3km | **CONFIRMED** | SSOT v2.3.4 修订说明/§5.5 |
| D38 | 固定图 C05/C06/C09 为 `scope=GLOBAL`，campus 筛选 `applicable:false`；下厨共享数据 `scope=SHARED`，不重复计入单校区合计 | **CONFIRMED** | SSOT v2.3.4 §5.5/§6.5 |

## 2. 实测结果与 D03 裁决

### D03 双校区真实 POI 目标（2026-10-25 用户正式裁决）

- 原目标：每个校区约 **1500+** 真实高德餐饮 POI（固定 3km、`types=050000`、网格、去重），禁止合成补足；实际数按 API 返回。
- **校区 A 思源**：直接 `count=600`；与建大同版递归脚本重跑（2026-10-25T02:25:40+08:00，45 个初始 800m 网格、61 个处理格、133 次调用、0 错误/0 未完成）；原始 2,230、`poi.id` 去重 1,258、3km 内 607、扣除 2 条非餐饮后 **605**；合成食堂 **200**；合计 **805**；原目标差额 895，`target_1500_met=false`。
- **校区 B 建大雁塔**：地名搜索实际返回 `108.967153,34.236991`（碑林区雁塔校区，未返回草堂）；3km 递归网格、425 个处理格、1,206 次调用、0 未完成；真实餐饮 POI **6,659**；合成食堂 200 单列，合计 **6,859**；原目标 1500+ 已满足。
- **用户裁决（CONFIRMED）**：
  1. 思源 **605** 作为样本 A 接受，按实际值写论文/大屏（1500+ 为原目标、未达，不再要求补足）；
  2. 建大 **6,659** 作为样本 B 接受，按实际值使用；
  3. `1700` 不是总数实际值，**分校区报**（思源 605+200=805；建大 6,659+200=6,859）；
  4. 建大数据**不得补贴思源**，两校区**不得跨校区混算**、不得用合计掩盖单校区数；
  5. 合成食堂仍分别 200 目标、分别标注，不计入真实 POI。
- **禁止**：用合成 POI、复制行、把合成食堂计入真实 POI、把 1700 当实际数、用两校区合计掩盖单校区数、跨校区挪用数据。

### D26 / D27 外部条件（非 S09 阻塞，后续步骤用）

- **D26 Android/真机**：`adb`、`gradle`、Android SDK、Capacitor 配置/依赖缺失；Java 25.0.2 可能不匹配 AGP。S18 BLOCKED。
- **D27 LLM**：Key/模型/单价未定；S11 BLOCKED。按 7,500 道/20 道每批=375 批，建议硬上限 ¥50，实际以模型报价为准。
- **D25 图片**：已确认仅本地演示；不进入公开发布/APK 公开分发/论文公开素材，因此不再作为公开分发阻塞，但不得对外声称已授权。

## 3. 不再保留的旧 OPEN 项

r01 的 D21/D22/D23/D24/D30/D31/D32 等默认口径已由用户确认，**不再以“建议”留在 OPEN**；均写入 SSOT v2.3.4 与 r02 契约。r01 原文保留，不覆盖。

## 4. 结论

- D03 已由用户正式裁决：思源 605 为样本 A、建大 6,659 为样本 B，分校区报，不是 1700 合计，建大数据不得补思源、不得跨校区混算。
- 除后续 S11/S18 外部条件外，S09/r02 的契约、数据方案、统计/大屏指标与实验协议均已闭合。
- 开发方不签 PASS；S09 台账当前仍为 `BLOCKED`（提交时曾为 `REVIEW_PENDING`），S10 继续 LOCKED。台账解封由 Codex/用户按流程处理，开发方不自行修改台账。
