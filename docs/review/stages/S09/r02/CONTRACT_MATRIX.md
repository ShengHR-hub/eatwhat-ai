# S09 / r02 统计接口与大屏指标契约矩阵

- 日期：2026-10-25（Asia/Shanghai）
- 依据：`MASTER_SPEC.md` v2.3.5 §5/§5.5/§6.5/§7；用户已确认口径。
- 性质：契约定稿，不在本步实现。
- 通用响应：不适用筛选统一 `200 {"applicable": false, "reason": "...", "items": [], "meta": {}}`；空结果 `200` + 空数组/0；不返回假数据。

## 1. 13 个 stats 接口

| # | 路由 | 参数 | 返回 | 数据源/口径 | mode | cuisine | 空态 | 下钻 | PNG 数据 | 时间/固定图 |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | `GET /api/v1/admin/stats/overview` | `mode_type?`, `campus?` | `by_campus,total,feature_values_total,logs_total,votes_total,rooms_total,tagging_coverage,meta` | 各表计数；`feature_values_total=8×成功打标行`；`tagging_coverage=成功/快照dishes总数`；`meta.scope` 说明 mode/campus 作用范围 | 部分字段（见 meta.scope） | 不适用 | 全 0；coverage=0 | DataManage 概览 | 当前数字带（分校区+合计） | 全库；非固定图 |
| 2 | `GET /api/v1/admin/stats/geo` | `mode_type?`, `cuisine_type?` | `points[]:{id,name,lng,lat,rating,heat}` | `restaurants` + `eating_logs`；heat=该店菜品被吃次数；GCJ-02；rating 缺失 NULL | OUT_DINING 适用；HOME 不适用 | 可用（联表） | `points=[]` | `restaurant.id`→DataManage | 当前点集 | 全库；非固定图 |
| 3 | `GET /api/v1/admin/stats/calendar` | 无 | `daily[]:{date,count}` | `eating_logs.eaten_at` 本地日期 | 固定 | 不适用 | `daily=[]` | 无 | 全日期 | 全库；非固定图 |
| 4 | `GET /api/v1/admin/stats/heatmap` | `mode_type?` | `matrix[]:{weekday,slot,count}` | `eating_logs.eaten_at`；7×4：早[05,10)/午[10,15)/晚[15,21)/夜[21,05)；weekday 0=周一 | 是 | 不适用 | `matrix=[]` | 无 | 7×4 | 全库；非固定图 |
| 5 | `GET /api/v1/admin/stats/cuisine` | `mode_type?` | `items[]:{cuisine_type,count,share}` | `dishes_and_recipes` 行数 | 是 | 是（过滤单类） | `items=[]` | 菜系→DataManage 菜品 | 当前口径 | 全库；非固定图 |
| 6 | `GET /api/v1/admin/stats/cuisine-trend` | `mode_type?` | `dates[],series[]:{cuisine_type,data[]}` | `eating_logs` join dishes 按日 | 是 | 建议高亮/过滤 | 空数组 | 日期/菜系 | 全日期×菜系 | 全库；非固定图 |
| 7 | `GET /api/v1/admin/stats/personas` | 无 | `personas[]:{user_id,nickname,base_vector}` | 4 演示角色 + prefs | 固定 | 不适用 | `personas=[]` | Profile | 4×8 | 固定图 |
| 8 | `GET /api/v1/admin/stats/scatter` | `mode_type?`, `campus?` | `points[]:{name,price,rating,freq,entity_id,entity_type}`; `meta.not_plotted_no_rating`（整数） | `restaurants` 全量 + `dishes` 全量；OUT_DINING 用门店真实 rating，HOME 无真实 rating 时 `rating=NULL`；评分轴只绘非空点；freq=出现频次 | 是 | 建议支持 | `points=[]` | `entity_id`→DataManage | 当前点集 | 全库；非固定图 |
| 9 | `GET /api/v1/admin/stats/flow` | 无 | `nodes[],links[]:{source,target,value}` | `group_rooms`+`room_votes`；**单位=票**；赢家/其他/否决/缺席；房间结果另列 | 固定 | 不适用 | 空数组 | 无 | 全量票 | 全库；非固定图 |
| 10 | `GET /api/v1/admin/stats/keywords` | `mode_type?` | `words[]:{name,value}` | `allergen_tags` + 菜名分词；词频/TopN | 是 | 建议支持 | `words=[]` | 词→筛选 | 当前 TopN | 全库；非固定图 |
| 11 | `GET /api/v1/admin/stats/race` | 无 | `weeks[],series[]:{dish_id,dish_name,data[]},latest_top10[]` | logs+votes 按周；latest_top10=当前/最近周 Top10；VETO 不计 | 固定 | 不适用 | 空数组 | `dish_id`→DataManage | 全周+Top10 | 全库；非固定图 |
| 12 | `GET /api/v1/admin/stats/cooccurrence` | `top_n?` | `nodes[]:{name,value},links[]:{source,target,value}` | HOME 主辅料无序对；次数≥3；top_n=30/上限100；过滤盐/水/油/葱/姜/蒜 | 固定 HOME | 不适用 | 空数组 | 食材→筛选菜品 | TopN 子图 | 全库；非固定图 |
| 13 | `GET /api/v1/admin/stats/quality` | 无 | `tagging_coverage,missing_fields[],vector_anomalies` | 分母=快照 dishes 总数；分子=8 维完整且成功；异常分缺键/多键/非数值/非有限/越界/NULL | 固定 | 不适用 | coverage=0、空清单 | DataManage 质量 | 当前摘要 | 全库；固定图 |

**模块 8 共 13 个**（含 `quality`）。不删除 `quality` 凑数；不新增第 14 个 stats；C08 复用 `race.latest_top10`。

## 1.1 双校区筛选（v2.3.4）

- 适用 stats 增加可选 `campus`：`SIYUAN` / `JIANDA_YANTA` / `JIANDA_CAOTANG`（预留）/ `ALL`。
- `overview` 同时返回 `by_campus` 与 `total`；合计不得掩盖单校区数；`dishes_total` 等若含共享下厨菜谱，需在 `meta.scope` 标明 `SHARED`，不得重复计入单校区合计。
- 外食/POI/房间/投票按 `campus` 过滤；下厨菜谱共享，不按校区复制。
- 固定图 C05/C06/C09 为 `scope=GLOBAL`，campus 筛选返回 `applicable:false`；C16 为 `scope=SHARED`；C11 按房间 `campus` 过滤。
- C02 地图按校区分层/分色；思源与建大合成食堂不共用图层。
- C08/C10/C11/C13/C17 增加 `campus` 作用域；`C10` 全量 `restaurants+dishes`，HOME 无真实 rating 时 `rating=NULL`，评分轴只绘非空点，`meta.not_plotted_no_rating` 报未绘制点数（整数），不得伪造。
- 缺失外食 `campus` 的推荐请求返回 422；群组 join 跨校区返回 409。

## 2. 17 项大屏指标

| ID | 图 | 业务问题 | 数据/公式 | 粒度 | 默认筛选 | 联动 | 空态 | 下钻 | PNG 数据 | 不适用 |
|---|---|---|---|---|---|---|---|---|---|---|
| C01 | 翻牌 ×5 | 规模多大？ | overview 实际计数；特征值=8×成功 | 快照 | 无 | mode 按 meta.scope | 全 0 | 无 | 当前数字 | 不适用字段 null+scope |
| C02 | POI 地图 | 门店在哪/密度？ | 思源 605 + 建大 6,659 真实 POI，各加 200 合成食堂（按校区分层/分色，合成单独图例）；heat=日志频次 | 全库 | 无 | campus/mode/cuisine | 空地图 | restaurant.id | 当前点集 | HOME→applicable:false |
| C03 | 日历热力 | 哪天吃得多？ | logs 按日 | 日 | 全量 | 固定 | 空日历 | 无 | 全日期 | 有筛选→applicable:false |
| C04 | 星期×时段 | 什么时候吃？ | logs 7×4 | 周×四档 | 全量 | mode | 空矩阵 | 无 | 7×4 | cuisine 不适用 |
| C05 | 防腻双曲线 | 衰减降重样？ | benchmark 14 点 | 日累计 | 固定实验 | 不随筛选 | 缺 benchmark 提示 | 无 | 14 点 | 固定图 |
| C06 | 群组柱状 | 三策略谁稳？ | benchmark 三策略 avg/least | 实验汇总 | 固定实验 | 不随筛选 | 空提示 | 无 | 三组柱值 | 固定图 |
| C07 | 菜系环形 | 菜系结构？ | dishes 行数 count/share | 快照 | 无 | mode/cuisine | 空环 | 菜系→DataManage | 当前口径 | cuisine 是维度 |
| C08 | 热门轮播 | 哪些菜最热？ | logs+votes 被选/被投次数降序 Top10；VETO 不计；按 campus 过滤 | 当前/最近周 | 无 | campus/mode | 空列表 | dish_id | Top10+口径 | 按 campus 分层；ALL=合计 |
| C09 | 人设雷达 | 四角色差异？ | 4 人 base_vector | 快照 | 固定 4 人 | 否 | 空 | Profile | 4×8 | 固定图 |
| C10 | 价格×评分 | 性价比？ | `restaurants` 全量 + `dishes` 全量；OUT_DINING 真实 rating，HOME 无真实 rating 时 NULL；size=freq；评分轴只绘非空，`meta.not_plotted_no_rating` 报未绘制点数（整数） | 快照 | 无 | campus/mode/cuisine | 空散点 | entity_id | 当前点集 | 按 campus 分层；HOME 不伪造评分 |
| C11 | 决策桑基 | 票流向哪？ | 40,000 票→票型→赢家/其他/否决/缺席；单位=票；按房间 campus 过滤 | 实验汇总 | 固定 | campus（房间） | 空节点 | 无 | 全量票/分校区 | campus=ALL 合计；单校区过滤 |
| C12 | 菜系趋势 | 结构怎么变？ | logs×菜系×日 | 日 | 全量 | mode | 空序列 | 日期/菜系 | 全日期×菜系 | cuisine 高亮 |
| C13 | 口味词云 | 高频词？ | allergen_tags + 菜名分词；词频/TopN；campus/ shared 作用域 | 快照 | 无 | campus/mode | 空词云 | 词→筛选 | 当前 TopN | 下厨 SHARED；外食按 campus |
| C14 | 导出 PNG | 能进论文？ | 当前渲染数据；ECharts getDataURL；地图 S17 实测 | 当前 | 跟随 | 跟随 | 禁用+提示 | 无 | 当前筛选后数据 | 地图方法 S17 |
| C15 | 周热度竞赛 | 榜单怎么变？ | logs+votes 周 Top10；VETO 不计 | 周 | 全量 | mode 待定 | 空周补 0/提示 | dish_id | 全周 | 固定图 |
| C16 | 食材共现 | 哪些搭配？ | HOME 主辅料无序对≥3；top_n=30/100；停用词 | 快照 | 固定 HOME | 否 | 空图 | 食材→筛选 | TopN 子图 | OUT_DINING 不适用 |
| C17 | 打标覆盖率 | 真的打标了？ | 成功/快照 dishes 总数；异常计数；分校区+共享分别报 | 快照 | 固定 | 否 | 0%+说明 | DataManage 质量 | 当前摘要 | 分校区/共享；合计不掩盖单校区 |

**统一口径**：
- C07=dishes 行数；C12=logs 决策量；C08/C15 热度=被选日志+被投票，VETO 不计；C01 数字全部来自库，不写死 24,000/40,000/60,000。
- 所有图按 Asia/Shanghai 本地日期；默认全库；C05/C06/C09 为全局固定图，campus 筛选返回 `applicable:false`；C16 为共享固定图；C11/C17 可按 campus 过滤并报合计。
- C02 地图同时展示真实 POI 与合成食堂时，必须分图层/图例标注 `is_synthetic`，不得把合成食堂计入真实 POI 数。
- 地图 PNG 导出能力在 S17 实现并实测；S09 不实现。

## 3. 图→端点交叉表

| 图 | 端点 | 备注 |
|---|---|---|
| C01 | overview | 数字带 |
| C02 | geo | 高德 JS API；真实/合成分层 |
| C03 | calendar | 固定 |
| C04 | heatmap | 7×4 |
| C05/C06 | `GET /api/v1/admin/experiments` | 非 stats |
| C07 | cuisine | 行数 |
| C08 | race.latest_top10 | 不新增第 14 个 stats |
| C09 | personas | 固定 4 人 |
| C10 | scatter | restaurants+dishes 全量；HOME 无 rating NULL |
| C11 | flow | 单位=票；按 campus |
| C12 | cuisine-trend | logs |
| C13 | keywords | allergen_tags+菜名 |
| C14 | 前端能力 | S17 |
| C15 | race | 周序列 |
| C16 | cooccurrence | HOME 固定 |
| C17 | quality + overview | 同源公式 |

## 4. 查询与数据边界

- 统计库：独立统计库（D20）；演示库不参与大屏计数，保持 4 用户/20 门店/100 菜/9 日志、`group_rooms=0`、`room_votes=0`。
- 思源真实 POI 605 + 合成食堂 200 = 805；建大真实 POI 6,659 + 合成食堂 200 = 6,859；两校区分列，必须能按 `campus`/`is_synthetic` 拆分；不得按 1,700 合计，不得用合计掩盖单校区数。
- 所有聚合在 SQL 完成；禁止前端拉全表；S15 记录 SQL 次数/耗时。
- `distance_meters` 为直线距离；`rating`/`cost` 缺失 NULL；不得伪默认。
- 空库/空筛选返回合法空态；不 500、不假数字。

## 5. 裁决状态

- **D03 已裁决（2026-10-25）**：思源 605 为样本 A、建大 6,659 为样本 B；分校区报，不按 1700 合计；建大数据不得补思源、不得跨校区混算；禁止合成补足。
- S11 LLM Key/模型/预算、S18 Android/真机为后续步骤外部条件，不是 S09 已解决项。
