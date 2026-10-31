# S09 统计接口与大屏指标契约矩阵

- 日期：2026-10-24（Asia/Shanghai）
- 性质：**契约设计，不是接口实现**。S15/S17 才实现；本步不改路由、不加页面、不改 schema。
- 依据：`MASTER_SPEC.md` 第五章模块 8、第六章 §5、`DASHBOARD_EXPANSION.md`、`BATCH4_PLAN.md` 第 6 节。
- 未决项：`DECISIONS.md` D11–D15、D23、D24、D28–D32。

## 1. 通用约定（建议，待用户确认）

| 项 | 约定 |
|---|---|
| 前缀 | 全部挂在 `/api/v1` 下；统计路由完整路径 `/api/v1/admin/stats/*` |
| 身份 | 按 SSOT 演示级方案；后台是否强制 `X-User-Id` 未定义（D28），不在本步新增鉴权 |
| 时间 | 统一 Asia/Shanghai；`date` 用本地日期 `YYYY-MM-DD`；`eaten_at` 按本地时间分桶 |
| 时间范围 | 描述性图默认覆盖当前统计库全范围；实验图固定取 `algo_configs.benchmark_json`；不新增 `from/to`（D29） |
| 空结果 | `200` + 空数组/0 值；不返回 404/500，不返回假数据 |
| 非法参数 | 未知 `mode_type`/非法 `cuisine_type`：建议 422；SSOT 未定义，待确认 |
| 固定图遇到全局筛选 | 建议 `200 {applicable:false, reason, items:[], meta:{...}}`；不静默返回全量冒充联动（D12） |
| 分页 | SSOT 未定义分页；geo 返回全部点，race/cooccurrence 受 TopN 限制；若点过多需前端聚合 |
| 下钻键 | geo 用 `id`；scatter 需补 `entity_id/entity_type`；race 用 `dish_id`；其余按名称/日期 |
| PNG | 导出“当前筛选后的实际数据”，图题+口径脚注；ECharts 用 `getDataURL`；高德地图容器方法待定（D24） |
| 查询成本 | 禁止前端拉全表计算；SQL 聚合、必要索引；大数据下记录 SQL 次数/耗时 |

## 2. 13 个 stats 接口逐条清单

> 数量冲突见 §6：SSOT 文字写 12，表列 13（含 `quality`）。本矩阵按 **13 个** 编写，建议保留 `quality`。

| # | 路由 | 请求参数 | 返回顶层结构 | 数据源/字段 | mode_type | cuisine_type | 空态 | 分页/下钻键 | PNG 数据 | 时间/固定图 | 不适用筛选 |
|---:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `GET /admin/stats/overview` | `mode_type?` | `restaurants_total, dishes_total, feature_values_total, logs_total, votes_total, rooms_total, tagging_coverage` | 各表计数；`feature_values_total=8×有效向量数`；`tagging_coverage=成功/应打标` | 部分字段受影响（D32） | 未定义 | 全 0，coverage=0 | 无；可跳 DataManage 概览 | 当前筛选下数字带 | 全库；非固定图 | 不适用字段建议 `null` + `scope`（D32） |
| 2 | `GET /admin/stats/geo` | `mode_type?`, `cuisine_type?` | `points[]`：`id,name,lng,lat,rating,heat` | `restaurants` + `eating_logs`；heat=该店菜品被吃次数 | `OUT_DINING` 适用；`HOME_COOKING` 不适用（无门店） | 可按门店菜系/菜品菜系联表 | `points=[]` | 无分页；下钻 `restaurant.id` → DataManage 门店 | 当前点集（未聚合/聚合口径需注明） | 全库；非固定图 | `200 applicable:false`（D12） |
| 3 | `GET /admin/stats/calendar` | 无 | `daily[]`：`date,count` | `eating_logs.eaten_at` 按本地日期 | 否（固定全量） | 否 | `daily=[]` | 无；日期 tooltip，无 DataManage 下钻 | 全日期范围 | 全库；非固定图 | 有筛选参数时 `applicable:false`（D12） |
| 4 | `GET /admin/stats/heatmap` | `mode_type?` | `matrix[]`：`weekday 0–6, slot, count` | `eating_logs.eaten_at`；四档边界待定（D23） | 是 | 否 | `matrix=[]` | 无；格子 tooltip | 全范围 7×4 | 全库；非固定图 | cuisine 不适用 |
| 5 | `GET /admin/stats/cuisine` | `mode_type?` | `items[]`：`cuisine_type,count,share` | `dishes_and_recipes.cuisine_type` | 是 | 是（过滤到单类） | `items=[]` | 下钻 `cuisine_type` → DataManage 菜品筛选 | 当前口径 | 全库；非固定图 | cuisine 是维度，不属于“不适用” |
| 6 | `GET /admin/stats/cuisine-trend` | `mode_type?` | `dates[], series[]: {cuisine_type,data[]}` | `eating_logs` join `dishes.cuisine_type` 按日 | 是 | 建议支持高亮/过滤（D31） | `dates=[],series=[]` | 日期/菜系；无实体下钻 | 全日期×菜系 | 全库；非固定图 | cuisine 过滤建议=高亮，待确认 |
| 7 | `GET /admin/stats/personas` | 无 | `personas[]`：`user_id,nickname,base_vector` | `users` + `user_preferences`（4 演示角色） | 否（固定人设） | 否 | `personas=[]` | 无；可跳 Profile | 固定 4 人 | 固定图 | `applicable:false`（D12） |
| 8 | `GET /admin/stats/scatter` | `mode_type?` | `points[]`：`name,price,rating,freq`（建议加 `entity_id,entity_type`） | OUT_DINING: `restaurants.avg_price/rating` + 频次；HOME_COOKING: `dishes.price_or_cost`，**无 rating**（D15） | 是（决定实体） | 建议支持（D31） | `points=[]` | 下钻需补 `entity_id`（缺口） | 当前点集 | 全库；非固定图 | HOME 模式 rating 不适用（D15） |
| 9 | `GET /admin/stats/flow` | 无 | `nodes[], links[]` | `group_rooms` + `room_votes`；守恒模型待定（D14） | 否 | 否 | 空 nodes/links | 无实体下钻 | 全量 | 全库；非固定图 | `applicable:false` |
| 10 | `GET /admin/stats/keywords` | `mode_type?` | `words[]`：`name,value` | `allergen_tags`（缺字段，D16）+ 菜名/主辅料词；停用词规则待定 | 是 | 建议支持（D31） | `words=[]` | 点击词→筛选菜品（需前端/接口） | 当前 TopN 词 | 全库；非固定图 | cuisine 待确认 |
| 11 | `GET /admin/stats/race` | 无 | `weeks[], series[]: {dish_id,dish_name,data[]}` | `eating_logs` + `room_votes` 按周菜品热度；周起点/热度定义待定（D31） | 否 | 否 | 空数组 | 下钻 `dish_id` → DataManage 菜品 | 全周序列 | 全库；非固定图 | `applicable:false` |
| 12 | `GET /admin/stats/cooccurrence` | `top_n?` | `nodes[]: {name,value}, links[]: {source,target,value}` | HOME_COOKING 菜谱主辅料共现；阈值/停用词待定（D30） | 固定 HOME（无可选） | 否 | 空 nodes/links | 点击食材→筛选菜品（需实现） | 当前 TopN 子图 | 全库；非固定图 | `mode=OUT_DINING` 不适用 |
| 13 | `GET /admin/stats/quality` | 无 | `tagging_coverage, missing_fields[], vector_anomalies` | `dishes_and_recipes` 有效向量/缺失字段/异常 | 否（固定全量） | 否 | coverage=0、空清单 | 无；跳 DataManage 质量面板 | 当前质量摘要 | 全库；固定图 | `applicable:false` |

### 2.1 重点端点补充

**overview**
- `feature_values_total` 只能=8×合法 8 维向量行数；不能=dishes_total×8 含失败。
- `tagging_coverage` 的“应打标”分母需在 D18 打标状态落地后明确：建议 `SUCCESS/(SUCCESS+PENDING+FAILED)`，不把未尝试算失败。
- `restaurants_total` 是否随 `mode_type=HOME_COOKING` 变化未定义（D32）；建议返回 `scope` 标记。

**geo**
- `heat` 建议=该门店所有 OUT_DINING 菜品在 `eating_logs` 的出现次数；0 也要返回点（热力 0）。
- `mode=HOME_COOKING` 无门店 → 建议 `applicable:false`，不返回全量门店冒充联动。
- `cuisine_type` 过滤需先 join dishes；若门店无该菜系菜品，点消失；需在口径脚注写明。

**calendar / heatmap**
- 时区 Asia/Shanghai；`date` 本地日期。
- heatmap 四档边界建议 [05,10)/[10,15)/[15,21)/[21,05)，覆盖 24h；`weekday` 0=周一（D23）。
- 当前 9 条演示日志只能得到稀疏图；S12 的 24,000 条必须进入 stats 读的库（D20）。

**cuisine / cuisine-trend**
- C07 建议按 `dishes_and_recipes` 行数；C12 按 `eating_logs` 决策量；两者分母不同，标题/脚注必须写明（D31）。
- `share` 分母=过滤后 total；空态 `items=[]`，不返回 NaN。

**scatter**
- 当前响应字段没有实体 ID，无法下钻（C10 要求点图下钻）。建议增加 `entity_id`/`entity_type`；这是 SSOT 缺口（D15）。
- HOME_COOKING 无 rating，建议该模式不适用或改用价格×满意度；后者不是 SSOT 字段，不能私定。

**flow**
- 候选卡 10,000、投票 40,000、房间 1,000 单位不同，不能直接连线。建议按“票”守恒：40,000 → 票型 → 赢家/其他/否决/缺席；房间结果另列（D14）。
- 若坚持三阶段图，必须标注每段单位，且不得声称总流量守恒。

**keywords**
- 当前无 `allergen_tags`；只能从菜名/主辅料提取。词云若声称“忌口词来自 LLM”，在 D16 落地前不成立。
- 停用词、分词、最小词频需锁定；建议不新增分词依赖，先用主辅料 token + 菜名 n-gram。

**race**
- 周起点建议周一；热度建议=被吃次数+被投票次数，分开字段或明确权重（D31）。
- `weeks` 完整覆盖实验期；空周不跳过（补 0）以免趋势断裂。

**cooccurrence**
- 只统计 HOME_COOKING；主辅料无序对；建议共现≥3、TopN 30/上限 100、过滤通用调味料（D30）。
- 节点值=关联边权和；边值=共现菜谱数；需能复算。

**quality**
- `missing_fields[]` 建议 Top 10，字段名/缺失数/占比。
- `vector_anomalies` 至少分：缺键、多键、非数值、非有限、越界、null。
- 与 C17 水球、DataManage 质量面板同源，不能三处各算一套。

## 3. 17 项大屏指标契约

> C14 是导出能力项，不另算一张图；C17 与 quality 面板同源。所有图标题问题式，图下给一句结论 + 口径脚注。

| ID | 图表 | 业务问题 | 数据源/字段 | 聚合公式 | 时间粒度 | 默认筛选 | 联动 | 空态 | 下钻 | PNG 数据 | 不适用筛选 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | 翻牌数字带 ×5 | 数据规模到底多大？ | 各表计数 + 有效向量 | 见 §2 overview；特征值=8×有效向量 | 当前快照 | 无 | mode 只影响可适用字段 | 全 0 | 无 | 当前 5 个数字 | 不适用字段 `null`+scope |
| C02 | POI 地图 | 门店在哪里、密度如何？ | `restaurants` + logs | 点=门店；气泡=rating/heat；热力=heat | 全库 | 无 | mode/cuisine | 空地图+说明 | `restaurant.id`→DataManage | 当前点集/视口范围需注明 | HOME → applicable:false |
| C03 | 60 天日历热力 | 哪些天决策多？ | `eating_logs.eaten_at` | 每日 count | 日 | 全量 | 否（固定） | 空日历 | 无 | 全日期 | 有筛选→applicable:false |
| C04 | 星期×时段热力 | 什么时候吃得多？ | `eating_logs.eaten_at` | 7×4 count | 周×四档 | 全量 | mode | 空矩阵 | 无 | 7×4 全量 | cuisine 不适用 |
| C05 | 防腻双曲线 | 衰减真的降低重样率吗？ | `benchmark_json.duplication_rate_curve` | 14 点重样率 | 日累计 | 固定实验 | 不随 mode/cuisine | 空/缺 benchmark→明确提示 | 无 | 14 点原值 | 固定图，不适用 |
| C06 | 群组柱状 | 三种策略谁更稳？ | `benchmark_json.group_satisfaction_bars` | 三策略 avg/least | 实验汇总 | 固定实验 | 不随筛选 | 空→提示 | 无 | 三组柱值 | 固定图，不适用 |
| C07 | 菜系环形 | 菜系结构是什么？ | `dishes.cuisine_type` | count/share | 当前快照 | 无 | mode/cuisine | 空环+说明 | 菜系→DataManage | 当前口径 | cuisine 是维度 |
| C08 | 热门菜品轮播 | 哪些菜最热？ | logs+votes | 热度=被吃+被投（待定） | 当前/最近周 | 无 | mode/cuisine 待定 | 空列表 | `dish_id`→DataManage | Top10 + 口径 | 需确定端点（D13） |
| C09 | 人设雷达 | 四个角色差在哪？ | `users`+prefs | 8 维 base_vector | 快照 | 固定 4 人 | 否 | 空 | Profile | 4×8 | 固定图，不适用 |
| C10 | 价格×评分散点 | 性价比分布？ | restaurants/dishes | 点=实体；x=price,y=rating,size=freq | 当前快照 | 无 | mode/cuisine | 空散点 | `entity_id`（缺） | 当前点集 | HOME 无 rating |
| C11 | 决策桑基 | 票最后流向哪？ | rooms+votes | 见 D14 守恒模型 | 实验汇总 | 固定 | 否 | 空节点 | 无 | 全量 | 固定图 |
| C12 | 菜系趋势堆叠 | 菜系结构怎么变？ | logs join dishes | 日×菜系 count | 日 | 全量 | mode | 空序列 | 日期/菜系 | 全日期×菜系 | cuisine 过滤=高亮 |
| C13 | 口味标签词云 | 高频词是什么？ | allergen_tags（缺）+ 名称/主辅料 | 词频/TopN | 当前快照 | 无 | mode | 空词云 | 词→筛选 | 当前 TopN | 需 D16 |
| C14 | 每图导出 PNG | 能否直接进论文？ | 各图当前渲染数据 | `getDataURL`/地图截图 | 当前 | 跟随各图 | 跟随 | 导出按钮禁用+提示 | 无 | 当前筛选后实际数据 | 地图方法待定 D24 |
| C15 | 周热度竞赛 | 热度榜怎么变？ | logs+votes 按周 | 每周 Top10 + 热度 | 周 | 全量 | mode 待定 | 空周补 0/提示 | `dish_id` | 全周序列 | 固定图 |
| C16 | 食材共现图 | 哪些食材常搭配？ | HOME 菜谱主辅料 | 共现对计数≥阈值 | 当前快照 | 固定 HOME | 否 | 空图 | 食材→筛选 | TopN 子图 | OUT_DINING 不适用 |
| C17 | 打标覆盖率 | 数据真的打标了吗？ | dishes 向量/状态 | 成功/应打标；异常计数 | 当前快照 | 固定 | 否 | 0% + 说明 | DataManage 质量 | 当前摘要 | 固定图 |

### 3.1 17 项与 13 端点的交叉表

| 图 | 主数据端点 | 备注 |
|---|---|---|
| C01 | `overview` | 5 个数字 |
| C02 | `geo` | 高德地图容器 |
| C03 | `calendar` | 固定 |
| C04 | `heatmap` | 7×4 |
| C05/C06 | `GET /admin/experiments` | 不属于 stats；读 benchmark |
| C07 | `cuisine` | 菜系维度 |
| C08 | **缺口** | 13 个 stats 无“热门菜品”；见 D13 |
| C09 | `personas` | 固定 4 人 |
| C10 | `scatter` | 需补实体 ID/评分口径 |
| C11 | `flow` | 需守恒模型 |
| C12 | `cuisine-trend` | 日×菜系 |
| C13 | `keywords` | 需 allergen_tags 或降级声明 |
| C14 | 前端能力 | 非 stats 端点 |
| C15 | `race` | 周序列 |
| C16 | `cooccurrence` | HOME 固定 |
| C17 | `quality`（+`overview.tagging_coverage`） | 必须同源 |

## 4. 关键缺口（不能“实现时再定”）

1. **C08 无端点**：必须扩 `race` 或新增 `hot-dishes`；否则只能用假数组。
2. **C10 无实体 ID / HOME 无 rating**：下钻与 y 轴口径未定义。
3. **C11 单位不守恒**：候选/投票/房间不能直连。
4. **C13 无 allergen_tags 字段**：词云来源不成立。
5. **C17/quality/overview 三处覆盖率必须同公式**：D18 打标状态未落地前只能算“有效向量/总菜品”。
6. **C02 地图 PNG**：ECharts `getDataURL` 不覆盖高德容器；D24 未定。
7. **固定图筛选响应**：C03/C05/C06/C09/C11/C16/C17 需要统一 `applicable:false` 或“忽略筛选”口径。
8. **统计库边界**：D20 未定，24,000/40,000 可能根本不在 stats 读的库里。

## 5. 12 / 13 数量冲突决策记录

**SSOT 现状（原文）**

- 第五章模块 8 标题与 v2.3.1 修订说明写“**12 个**聚合接口”。
- 同一路由表实际列 **13 行**：overview、geo、calendar、heatmap、cuisine、cuisine-trend、personas、scatter、flow、keywords、race、cooccurrence、quality。
- 第八章批次 4 也写“模块 8 的 `/admin/stats/*` 统计接口组（12 个）”。

**冲突**

文字 12 ≠ 路由表 13；差异项是 `quality`（DataManage 质量面板 / C17 覆盖率的数据源）。

**建议**

1. 保留 `quality`，不删除。
2. 把 SSOT 的“12 个”改为“13 个”，并在模块 8 明确 `quality` 是质量面板/覆盖率数据源。
3. S15 按 13 条逐项验收；S17 的 C17 与 DataManage 共用 `quality`。
4. 不改路由表、不新增第 14 个接口；C08 用 `race` 扩展或另议（D13）。

**状态**：`OPEN`，需用户确认后才能改 SSOT；本步未修改 `MASTER_SPEC.md`。

## 6. 查询与性能约束（S15 验收用）

- 所有统计必须在 SQL 聚合，禁止前端拉全表。
- `eating_logs(eaten_at)` 已有索引；`room_votes(room_code)`、`dishes(cuisine_type/mode_type)` 需在 S15 评估索引。
- 大数据目标：1,700 门店 / 6,300–8,000 菜 / 24,000 日志 / 40,000 票；每接口记录 SQL 次数与耗时。
- 地图点过多时前端聚合，不把 1,700 点逐点渲染成卡顿；聚合规则需在 S17 说明。
- 空库/空筛选必须返回合法空态，不 500、不假数字。

## 7. 待确认清单

见 `DECISIONS.md` D11–D15、D23、D24、D28–D32。未确认前，本矩阵中标注“建议/待定”的单元格不构成施工契约。
