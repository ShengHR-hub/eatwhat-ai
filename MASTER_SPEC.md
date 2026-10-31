# 《食刻 (EatWhat AI)》系统架构与全量开发主契约 (MASTER_SPEC v2.3.7)

> **文档定位 (Single Source of Truth, SSOT)**：
> 本文档是毕业设计《基于多维上下文感知与群组偏好博弈的智能饮食决策系统设计与实现》的唯一事实来源。在任何 AI 对话窗口中开发或排查问题时，请先投喂本文档以锁定命名、表结构、算法公式与接口契约。

> **v2.1 修订说明（2026-10-22，对照原始讨论逐项核对后修正）**：
> 1. 补回 v1 已锁定但 v2.0 丢失的字段默认值：餐馆评分默认 `4.5`、距离默认 `500` 米、高德坐标系 `GCJ-02`、做菜时长默认 `15` 分钟、厨具默认 `炒锅`、冰箱数量描述默认 `适量`、保质期默认 `3` 天。
> 2. 补回前端动效库 **Lottie**（与 `canvas-confetti` 为一组），用于动态天气图标与共识揭晓动画。
> 3. 修正数据量口径自相矛盾：v2.0 分项相加约 6,700 条却宣称总量 8,000~10,000+；v2.1 调整分项构成使总量成立（见第七章）。
> 4. 新增附录 A~D：项目背景与立意、交付形态选型理由（为何不做微信小程序）、双模型协作开发流程、LLM 批量打标提示词契约、论文章节与答辩亮点映射。
> 5. v2.0 中由模糊说法形式化出的三处细节——下厨模式绿色主色、群组算法先验/划卡 `0.4/0.6` 权重配比、预算分公式与冰箱临期双倍提权——在 v2.1 起正式锁定为项目决策（见 0.5），后续开发不得再自行改动。
> 6. **v2.1 补充修订（2026-10-22 晚，用户拍板）**：①新增第五个动效库 `gsap`（Draggable 专用于划卡、Timeline 专用于揭晓编排）；②`WeatherPill` 玻璃质感锁定 Apple 官方 Figma 文件复制 CSS 的免费施工法；③动效参照来源锁定 `60fps.design` 免费层；④**明确不采用** React 组件库（21st.dev / Aceternity / Magic UI 原版）移植路线，转 Vue 效果无保证，弃用。
> 7. **v2.1 背景补充修订（2026-10-22 晚，用户拍板）**：背景改走「现成纹理底 + 高透明罩色」构造法（见第六章 1），纹理底锁定 backgrounds.supply 免费区的 Smudge / Etherial / Iridescence 三张候选；AI 仅允许对 Iridescence 做色相迁移改色（派生暖橙/鼠尾草绿双模式版），禁止纯 CSS/AI 单调渐变充当整页背景；免费图授权风险已在第六章留痕。
> 8. **v2.1 控件补充修订（2026-10-22 晚，用户拍板）**：按钮/开关/滑块/气泡等小控件锁定现成来源——主力 `daisyUI`（自定义主题接入，控件颜色只许引用主题令牌、与背景同源呼应）+ 主 CTA 用 Inspira UI 的 Shimmer Button（见第六章 2.7）。
>
> **v2.2 开工前裁决说明（2026-10-23，导师通过后、批次 1 开工前逐项拍板，本文档即刻取代 v2.1）**：
> 1. **仿真流水口径**：24,000 条成立的前提写死为“200 人 × 60 天 × **每人每天 2 餐**”（见第七章）；40,000 条投票 = 1,000 场 × 4 人 × 10 张卡，不变。
> 2. **PASS 刻度统一**：划卡分 `swipe_score` 唯一值域为百分制（`SUPER_LIKE=120 / LIKE=100 / PASS=40`）；`room_votes` 表只存枚举、不再标注数值，`VETO` 只走掩码淘汰、无 -999 分值（见第三、四章）。
> 3. **`appliance_tag` 改 JSON 数组**：取值补入 `一锅出`，默认 `["炒锅"]`；气泡规则按“数组含任一”判定（见第二、三章）。
> 4. **黑榜分对象**：以菜品为准保留 `blacklist_dish_ids`，另新增 `blacklist_restaurant_ids` 管门店；Profile 文案与算法过滤已同步（见第三、四、六章）。
> 5. **管理后台补 CRUD 接口**：`/admin/restaurants` 与 `/admin/dishes` 各补齐增删改查（见第五章）。
> 6. **扫码进房补 join 接口**：新增 `POST /rooms/{room_code}/join` 为成员落库的唯一时机，房间表新增 `member_user_ids`；WebSocket 只订阅、不落库（见第三、五章）。
> 7. **身份口径锁定**：毕设演示系统不做真实登录鉴权，用户身份一律经请求头 `X-User-Id` 传递（见第五章开头）；论文中如实表述为演示级身份方案。**（此条已被 v2.3.7 第 1 条取代：系统已具备本地账号 + Bearer 令牌，`X-User-Id` 仅保留为未登录演示身份。）**
> 8. **`benchmark_json` 结构与天气数据源补定义**：`benchmark_json` 给出完整 JSON 结构（见第三章）；天气锁定高德天气 API、与 POI 共用同一 Key（见第五章）。
> 9. 小项：`room_code` 字段宽 10 位保留、实际值固定 6 位数字并注明；算法 4 措辞降级为“角色分组枚举 + 约束筛选”，不再称“改进背包”（见第四章与附录 D）。
>
> **v2.3 视觉与展示修订说明（2026-10-23 晚，用户拍板，本文档即刻取代 v2.2；批次 1 后端内容不受影响）**：
> 1. **配色整体推翻**：暖橙 + 森林绿 + 奶油白作废，全系统改 **黑、灰、银、白单色**高级感路线。0.5 第 1 条「双模式主色」废止——双模式不再靠颜色区分，改由图标 + 文案标签 + 分段开关选中态（深灰实底）区分，两模式共用同一套单色令牌（见第六章 1）。
> 2. **背景构造法更换**：v2.1 的「现成纹理底 + 高透明罩色」（backgrounds.supply 三张纹理图）作废，改 **Vue Bits 三背景分工**：`Grainient`（谷物）银灰版作移动端全局底、`Liquid Chrome` 仅限首页顶部与共识揭晓页、`Silk` 仅限启动/登录页；三层架构与「组件不受底影响」硬规则见第六章 1，细节以 `MOBILE_VISUAL_SPEC.md` 为准。backgrounds.supply 素材不再使用，其 $49 授权问题随之消失；Vue Bits 为 MIT + Commons Clause（自用合规，不得转售其组件本身）。
> 3. **daisyUI 主题令牌改单色**：`primary` = 近黑 `#17171A`、`secondary` = 银灰 `#55555E`、`base` = 白/浅灰（`#FFFFFF` / `#F4F4F5`）；「颜色只许引用主题令牌、严禁写死」的硬约束不变（见第六章 2.7）。
> 4. **WeatherPill 玻璃参数已实测提取**：Apple 官方 Figma「macOS 27」的 Liquid Glass - Small（Light）样本参数已于 2026-10-23 提取完毕，存 `WEATHERPILL_GLASS.md`；施工直接引用该文件的参数表与生产组合版 CSS，不再执行「打开 Figma 复制 CSS」的流程（见第六章 2.6）。
> 5. **答辩展示与桌面端定位定案**：移动端与 PC 管理后台按原计划开发；全部功能完成并冻结后新增 **批次 5（网页展示版 + 移动端真机录屏）**——同代码库新增桌面壳，聚合移动端与后台的全部功能供答辩投屏展示，移动端另录真机使用视频交代移动端效果。桌面端定位 = 管理后台 + 展示版，不做独立桌面用户端（见第八章与 `MOBILE_VISUAL_SPEC.md` §5）。
>
> **v2.3.1 大屏扩容修订说明（2026-10-23 晚，用户拍板“三档全要”，本文档即刻取代 v2.3；批次 1/2 内容不受影响）**：
> 1. **实验大屏全量扩容**：`ExperimentDashboard.vue` 图表由原 3 项扩至 **17 项**（翻牌数字带、POI 地图、日历热力、星期×时段矩阵热力、人设雷达、价格×评分散点、决策桑基、菜系趋势、词云、动态排序竞赛、食材共现关系图、覆盖率水球等），完整清单与版式见第六章新增 §5，调研与数据映射见 `DASHBOARD_EXPANSION.md`。
> 2. **新增大屏统计接口组**：第五章新增「模块 8：大屏统计」`/admin/stats/*` 共 13 个聚合接口（概览/地理/日历/热力/菜系与趋势/人设/散点/流向/词云/竞赛/共现/质量；v2.3.3 更正：原计数漏掉 quality，实际共 13），均支持 `mode_type`、`cuisine_type` 全局筛选参数以支撑大屏联动。
> 3. **大屏交互定案**：全局筛选联动、图表下钻跳 DataManage 明细、每图导出 PNG（供论文第五章插图）为必备功能；图表标题一律问题式（先结论后证据）。
> 4. **地图实现红线**：地图层走高德 JS API（热力图插件 + 点聚合，坐标 GCJ-02 天然一致）；**禁用** ECharts 的百度地图系示例（`heatmap-bmap` 等），与已锁定的高德数据源冲突。
> 5. **批次 4 范围同步扩大**：批次 4 新增「大屏全部 17 图 + stats 接口组 + DataManage 数据质量面板」，工作量评估与批次细化在 BATCH4_PLAN 中另行拆解（见第八章）。
>
> **v2.3.2 裁决与定款修订说明（2026-10-23 深夜，审核裁决 + 用户定款，本文档即刻取代 v2.3.1；其余内容不变）**：
> 1. **内容卡定款液态玻璃（G 方案）**：用户否决平白实底卡，内容卡片改为**液态玻璃**——折射层（SVG 位移滤镜作用于背景采样）+ 半透明填充 + 亮边高光 + `WEATHERPILL_GLASS.md` 阴影组；第六章 1 的三层架构第 2 层与卡片规范、§2.6 适用范围已同步改写，配方与性能分级以 `MOBILE_VISUAL_SPEC.md` §3–§4 为准。原「内容一律实底」口径作废。
> 2. **`lazy_one_pot` 删除速度门槛（审核裁决）**：该气泡语义为厨具可用性（低动手），与速度偏好正交；第二章气泡表已删 `prep_speed>=0.7` 条件，只保留厨具数组筛选。种子数据中一锅出菜的 `prep_speed`（0.40–0.45）为真实值，**不许改数据迁就规则**。
> 3. **`total_score` 封顶口径入正文**：排序用原始分，展示值 `min(100, 原始分)`；四权重和为 1 的归一化不变（见第四章公式注）。雷达图画 `radar_5d` 分项分，与总分封顶无关。
>
> **v2.3.3 S09/r02 数据与实验契约修订（2026-10-24，用户确认；本文档即刻取代 v2.3.2；视觉与四算法公式不变）**：
> 1. **中心点与 POI**：中心点为西安思源学院主校区；高德地名搜索实际返回 GCJ-02 中心点 **109.078487,34.234818**（2026-10-25T00:24:28+08:00）。固定 3km 半径。真实高德 POI 目标约 1500+，必须按真实 API 返回结果验收，**禁止合成补足**；S09/r02 实测 `types=050000` 直接 count=600、网格去重后 605 个真实餐饮 POI（扣除 2 个非餐饮）。**D03 已于 2026-10-25 裁决：接受实际 605 为校区 A 样本，不再要求补足到 1500+。** 另有 **200 个合成食堂窗口**，必须显式标记 `is_synthetic=1`，不计入真实高德 POI。证据必须分别报告真实 POI 数、合成食堂窗口数、两者合计数；“1700”只是门店/档口总规模目标，不是 2km 阈值；“17”只表示大屏图数量。
> 2. **菜谱与图片**：菜谱使用**合成数据**，必须显式标记 `is_synthetic=1`，不得包装成真实采集；实体数按数据行统计，同时单独报告唯一菜名数，不得用重复行凑规模。菜品图片仅用于本地毕业设计演示，不进入公开发布、APK 公开分发或论文公开素材。
> 3. **特征值**：特征值总量定义为 **成功打标菜品数 × 8**；不再固定声称 60,000+，除非实际成功打标菜品数达到 7,500 以上。失败/未完成不得计入。
> 4. **统计接口**：模块 8 保留 **13 个** stats 接口（含 `quality`）；SSOT 中旧计数统一更正为 13，不得为凑数删除 `quality`。
> 5. **Schema 边界**：允许新增可空字段或独立表，不改变现有字段语义；允许承接 `allergen_tags`、软删除（`deleted_at`）、来源追溯、打标状态/失败记录、LLM 元数据。`feature_vector` 允许 `NULL` 表示未完成；不得用默认向量蒙混。
> 6. **大屏口径**：C08 由 `eating_logs + room_votes` 聚合，按被选/被投次数降序取 Top10，VETO 不计热门；C10 数据源为 `restaurants` 全量 + `dishes_and_recipes` 全量（v2.3.4 修正：不再只画 OUT_DINING），OUT_DINING 用真实 rating，HOME_COOKING 无真实 rating 时 `rating=NULL` 且 **不返回 `applicable=false`**；评分轴只绘 rating 非空点，`meta.not_plotted_no_rating` 报未绘制点数（整数），不得伪造评分；C11 桑基守恒单位为“票”；C13 来源为 `allergen_tags + 菜名分词`；C17 分母为快照时 `dishes_and_recipes` 总数，分子为 8 维完整且成功的打标数。
> 7. **默认口径**：不可适用筛选统一 `200 {applicable:false, reason, items:[], meta:{}}`；random baseline 固定 R=30；重复率沿用“相邻餐次同菜系次数 / 累计餐次”；星期×时段 7×4（早餐 [05,10)、午餐 [10,15)、晚餐 [15,21)、夜宵 [21,05)，weekday 0=周一）；stats 按 Asia/Shanghai 本地日期、默认全库范围；共现用无序主辅料对，次数≥3 入图，`top_n=30`、上限 100，过滤盐/水/油/葱/姜/蒜等通用项；C07 按 dishes 行数，C12 按 eating_logs 决策量；`overview` 必须返回 `meta.scope` 说明 mode 过滤作用范围；`distance_meters` 为直线距离（保留旧字段名，但契约明确不是步行距离）。
> 8. **仿真数据**：S12/S13 写入**独立统计库**，不写入演示库；stats 指向该统计库。S09 只定契约，不实现 schema/迁移/导入/统计。
>
> **v2.3.4 双校区与口径纠错（2026-10-25，用户确认；本文档取代 v2.3.3；v2.3.3 的历史数字保留不改写）**：
> 1. **校区注册表**：校区 A 西安思源学院主校区，中心 GCJ-02 `109.078487,34.234818`，固定 3km；实测真实餐饮 POI **605**，加 200 个合成食堂窗口合计 **805**。校区 B 西安建筑科技大学雁塔校区，中心 GCJ-02 `108.967153,34.236991`（碑林区，未返回草堂），固定 3km；实测真实餐饮 POI **6,659**，加 200 个合成食堂窗口合计 **6,859**。两校区采样方法一致（3km、`types=050000`、网格、去重、唯一且在 3km 内），报实际数，不合成补齐；若高德返回**草堂校区**，必须先停下来询问用户，不得自行替代。
> 2. **口径纠错**：`1700` 是原规格总数目标（约 1500+ 真实门店 + 200 食堂窗口），**不是任何校区的实际数**；`17` 只表示大屏图数量，不是门店数。旧“2km 内不足 1700 再扩 3km”规则**作废**，不得再使用；两校区均固定 3km。
> 3. **双校区数据归属**：`restaurants` 新增可空 `campus`（`SIYUAN` / `JIANDA_YANTA` / `JIANDA_CAOTANG` 预留）；思源与建大 POI/合成食堂分别存储。`group_rooms` 新增可空 `campus`；外食推荐、群组外食必须按校区过滤，**跨校区不能拼一桌外食**。下厨菜谱共享，不按校区复制。
> 4. **前端校区切换**：顶部/全局提供校区切换；切换后推荐、POI、统计、大屏同步刷新；默认思源（两校区均有数据，可切换），未选择时不得混算。校区切换不改变用户身份。
> 5. **统计口径**：所有适用 stats 增加可选 `campus`（`SIYUAN` / `JIANDA_YANTA` / `JIANDA_CAOTANG` / `ALL`）；`overview` 必须同时返回 `by_campus` 与 `total`，合计不得掩盖单校区数；固定实验/人设图（C05/C06/C09）为全局仿真，campus 筛选返回 `applicable:false` 并注明 `scope=GLOBAL`；下厨共享数据标 `scope=SHARED`，不重复计入单校区合计。
> 6. **C10 澄清**：数据源为 `restaurants` 全量 + `dishes_and_recipes` 全量，气泡大小=出现频次；OUT_DINING 使用门店真实 rating，HOME_COOKING 无真实 rating 时 `rating=NULL`，不得伪造；评分轴只绘制 rating 非空点，并在 `meta` 报 `not_plotted_no_rating`。C08/C11/C13/C17 按 v2.3.3 口径并增加校区作用域。
> 7. **合成边界**：菜谱为合成数据，`is_synthetic=1`，文档/论文口径“演示菜谱为合成数据，仅用于验证算法”；食堂窗口先按校区分别合成并标注，思源与建大的合成食堂**不得混用**，实数按校区逐个替换，实数不足 200 按实际数记，不硬凑。
> 8. **图片与范围**：菜品图仅本地演示，不进入公开发布、APK 公开分发、论文公开素材；来源台账保留，标注“演示示意图”。本项目仅为毕业设计，不真实使用、不公开发布。
> 9. **状态**：本修订只同步文档；S09/r02 仍 `REVIEW_PENDING`，未签 PASS；S10 及后续仍 LOCKED；r03 历史结论保留（R02 FAIL、F12 FAIL、R01 PASS），r04 后续 PASS 记录不变。
>
> **v2.3.5 建大雁塔试抓结果与状态更正（2026-10-25，用户确认；本文档取代 v2.3.4；v2.3.4 历史保留）**：
> 1. **建大雁塔校区**：高德地名搜索实际返回 GCJ-02 **108.967153,34.236991**（formatted_address=陕西省西安市碑林区西安建筑科技大学雁塔校区，level=兴趣点，adcode=610103）；未返回草堂。
> 2. **建大真实 POI**：固定 3km、`types=050000`、45 个初始 800m 网格 + 递归细分（425 个网格、1,206 次调用、0 错误/0 未完成）；原始 25,857、`poi.id` 去重 12,990、3km 内 6,730、剔除 71 条非餐饮后 **真实餐饮 POI 6,659**；字段分列：rating 有值 6,652/缺失 7，cost 有值 5,411/缺失 1,248，tag 有值 3,871/缺失 2,788。直接查询 `count=600` 是 API 截断值，不能当 3km 总量。
> 3. **建大合成食堂**：单独 200 个目标，`is_synthetic=1`、`campus=JIANDA_YANTA`，不与思源混用；建大真实 6,659 + 合成 200 = **6,859**；目标 1500+ 已满足。
> 4. **思源**：真实 605 + 合成 200 = 805；**D03 已裁决接受 605 为样本 A**，按实际值报（1500+ 为原目标、未达，不再要求补足）；不得合成补足、不得借用建大数据、不得跨校区混算。建大 6,659 为样本 B，两校区分开报，不是 1700 合计。
> 5. **状态更正**：r02 独立复审后台账 S09 为 **BLOCKED**（不是 REVIEW_PENDING），S10–S20 及 `/admin` 仍 LOCKED；r03 历史结论与 r04 后续 PASS 记录保留。两校区均有数据后，默认仍为思源，前端可切换；不得跨校区混算/拼桌。
>
> **v2.3.5 补充裁定：冰箱库存时效口径（2026-10-26，用户确认；仅精确化第三章 `fridge_inventory` 与第五章模块 3，其余条款不变）**：
> 1. **到期边界**：`expire_days` 是**入库时的保质期（天）**，到期时刻 `expires_at = created_at + expire_days × 24h`，统一按 **UTC 绝对时间**计算；时区与 DST 不改变结果。`now >= expires_at` 即过期，过期剩余天数返回 `0`。
> 2. **剩余天数**：未过期时 `remaining_days = ceil(剩余秒数 / 86400)`，最小为 1 天（实际剩余 2.4 天显示 3 天，剩余 0.5 天显示 1 天）。
> 3. **临期定义**：**未过期且实际剩余 ≤48 小时**。因此 `remaining_days <= 2` 与「实际剩余 ≤48h」严格等价；`is_expiring_soon` 只对该区间为 `true`，过期项不计临期。
> 4. **统一消费**：冰箱列表、下厨推荐的库存命中与临期双倍提权、采购清单的已有库存扣减、组合采购共用同一口径；过期项不抵扣、不加分、不计临期。外食推荐不读取冰箱。
> 5. **同名重录**：同一用户再次 `ADD` 同名食材视为**重新入库**：覆盖属性并把 `created_at` 重置为当前时间；历史重复行不自动合并/删除，任一条有效匹配即视为已有。
>
> **v2.3.6 S06 房间协议与参数链裁定（2026-10-27，用户确认；本文档取代 v2.3.5；v2.3.5 历史保留）**：
> 1. **校区严格过滤**：`POST /rooms/create` 与 `POST /rooms/{code}/join` 均必填 `campus`（`SIYUAN` | `JIANDA_YANTA`；草堂未开放）；建房写入 `group_rooms.campus`。外食候选只取 `restaurant.campus == room.campus`；`campus IS NULL`、无门店或找不到门店的外食菜品一律排除，不得默认共享给任一校区。下厨菜谱共享，不做校区过滤，但建房/join 仍须同校区。join 不一致返回 409。历史 `campus IS NULL` 房间仅允许在 `WAITING` 由首个 join 请求绑定校区，并在同一事务内按全员约束重算候选；重算 0 道则回滚绑定与成员写入并拒绝；非 WAITING 拒绝绑定的 join；未绑定校区的房间不得开局。**join 只允许 `WAITING`，既有成员也不例外；`SWIPING`/`FINISHED` 的重复 join 一律 400，不返回成功快照；恢复读取走 `GET /rooms/{code}` 或 WS `ROOM_STATE`。**
> 2. **成员变化重算**：`WAITING` 新成员 join 后必须用全体成员忌口、菜品黑榜、门店黑榜、预算与校区的并集重算 Top-10；1–9 道按实际数量返回，0 道允许加入但禁止开局（历史 NULL 房间的绑定例外见上条）。`MEMBER_SYNC` 同时下发最新候选。
> 3. **投票枚举与缺席**：`room_votes.vote_type` 仅允许 `LIKE` | `SUPER_LIKE` | `PASS` | `VETO`；客户端提交 `TIMEOUT` 一律拒绝。未投票成员在结算时按内部缺席分 `60` 参与（不落 `room_votes`）；全员 0 票仍按先验+缺席分结算，不因无人投票而跳过结算；`VETO` 仍为独立掩码。
> 4. **重复投票**：`SWIPING` 且未到截止时刻前，同一成员对同一菜品以最后一次为准（更新同一行与 `voted_at`）；截止后或 `FINISHED` 后一律拒绝。`room_votes` 增加唯一索引 `(room_code, user_id, dish_id)`；迁移前必须先检查历史重复行，有重复则中止建索引。
> 5. **ω 冻结**：`POST /rooms/create` 按“请求 `override_params.omega_group` → `algo_configs.default_production.omega_group` → 默认 `0.5`”确定本房有效 ω，在建房时写入 `group_rooms.algo_params`（只存 `omega_group`）并冻结；join/START/投票/结算/重连均不再改变或重新读取 DB 的 ω。结算报告与 `RoomSnapshot` 返回只读 `omega_group`。单人请求的 `override_params` 仍为请求级，不写 DB、不影响已建房间；群组结算只消费 ω，其余五个参数不参与群组计算。
> 6. **结算与恢复**：15 秒截止以服务端 `deadline_at` 为唯一事实；所有结算入口（GET、WS 重连、到点定时器、全员完成早结算、启动/周期扫描）共用同一幂等结算。结算先只读计算报告，再以 `status='SWIPING' AND settled_at IS NULL` 为条件的原子更新写入；`rowcount=0` 表示竞争失败，不得写第二份结果。应用启动时扫描过期房间，并每 5 秒兜底扫描一次；进程重启且无客户端连接时仍应结算。**周期任务遇到单次扫描级异常（数据库暂时不可用、扫描查询失败等）只记录并继续下一周期，不得退出循环；单个房间失败必须隔离，不能阻断同轮其它房间。** 结算失败不得留下半结算状态，房间保持 `SWIPING` 可重试。
> 7. **快照恢复**：`GET /rooms/{code}` 与 WS `ROOM_STATE` 必须包含成员、候选、本人票、进度、`deadline_at/remaining_ms`、`campus`、`omega_group`、赢家或无共识、完整报告；不得要求客户端刚好收到广播。
> 8. **已知限制（S06 记录，不改行为）**：建房预算在初筛中为 `1.25` 倍软上限；`MAX_MEMBERS=8`；`ROOM_STATE`/`ERROR` 为恢复与错误提示的附加事件；`deadline_at` 为 naive UTC；WS hub 为单进程内存态，不支持多 worker 广播；无 leave/close 端点，房间结束以 `FINISHED` 与断线重连/快照恢复表达。
> 9. **数据边界**：当前演示种子 20 家门店 `campus` 均为 NULL；按严格过滤，S10 回填前演示版外食房间没有候选，这是已知数据限制。S06 的 10 候选证据使用隔离库中明确标注的 `source_dataset=s06_fixture_v1`、`is_synthetic=1` 的校区 fixture；fixture 不得写入演示库或种子脚本。
> 10. **前端范围**：S06 只把默认校区 `SIYUAN` 透传给建房/join；全局校区切换 UI 不在 S06，仍按 §5.5.3 在后续 UI 专项验收。

> **v2.3.7 身份体系升级与产品闭环补齐（2026-10-31，用户确认；本文档取代 v2.3.6；v2.3.6 历史保留不改写）**：
>
> 1. **身份方案升级（取代第五章 §0 原「不做真实登录」表述）**：系统已具备**真实账号体系**——`POST /auth/register`、`POST /auth/login`、`POST /auth/logout`、`GET /auth/me`，凭据存 `auth_credentials`（密码哈希），会话存 `auth_tokens`（Bearer Token）。**管理接口只认 `Authorization: Bearer <token>` 且 `role=ADMIN`**，不再接受 `X-User-Id` 冒充管理员。`X-User-Id` 降级为**未登录时的演示身份**，仅对移动端普通接口有效。论文中表述为「演示系统内的本地账号 + 会话令牌」，不得描述为生产级鉴权（无验证码、无找回、无多因子）。
> 2. **身份锁定**：登录后前端锁定当前账号，隐藏「切换室友」；演示切换改由登录页的**快捷账号**（5 个按钮，点击只填充用户名密码、不自动提交）承担。原「登录成 A 还能切成 B 看 B 的数据」与账号体系冲突，已废止。
> 3. **新增 6 张表，核心表由 9 张增至 15 张**：`auth_credentials`、`auth_tokens`、`admin_audit_logs`、`system_settings`、`tagging_jobs`、`dish_feedback`（见第三章 10–15）。
> 4. **算法参数改为运行期可配置**：λ / ω / α / β / γ / δ 落 `system_settings`，后台保存后**热加载**（`current_algo_params()`），推荐接口下一次请求即生效；服务启动从库加载一次。论文中可作为「参数灵敏度现场演示」的支撑。
> 5. **打标由同步调用改为任务队列**：`tagging_jobs` 落任务行，后台线程逐批（20 道）推进，前端轮询 `done/total/failed`。同步等待数十秒的模型调用会撑爆 HTTP 超时，原 `POST /admin/llm-tag` 保留为同步兼容入口。
> 6. **大屏结构改为抽屉式分析台（取代第六章 §5 的「三屏轮播」）**：左侧栏「实验大屏」下挂主题子导航（数据概览 / 数据质量 / 算法实验），右侧为单主题内容区，**取消 12 秒自动轮播与底部圆点**。原 17 项图表按「有无数据支撑」收敛：**桑基流向（0 票）、周度竞赛（仅 2 周且值恒为 1）、星期×时段热力（9 条流水全落夜宵）已移除**，不做无数据支撑的图。
> 7. **移动端闭环补齐**：打卡后新增结果面板（本周餐数 / 本周花费 / 预算剩余 + 去哪吃）；满意度评价落在**足迹页**（打卡是「准备吃」，不在此时问好不好吃）；新增 `PATCH /users/{id}/profile`（昵称头像）与 `POST /users/{id}/avatar`（Pillow 裁 256×256 JPEG）；背景图由 `MobileShell` 统一渲染，全部 `/m/*` 生效。
> 8. **去哪吃（新增，边界明确）**：外食菜 → 高德搜索页搜**门店名**（外食菜品 100% 有 `restaurant_id`，店名精确到档口）；所有菜 → 美团搜索页搜**菜名**。**不做跨平台比价**：美团/饿了么无公开商品查询 API，需商家授权或爬虫（前者毕设拿不到、后者违规）。导航跳系统地图 App，**不做 App 内导航**。下厨菜不显示「去这家店」——共享菜谱无门店。
> 9. **测试基线**：`pytest -q` → **430 passed / 1 skipped / 0 failed**；前端 `npm run build` 通过。

---

## 0. AI 协同开发最高铁律

1. **命名绝对锁定**：所有数据库表名、字段名、JSON 键名、API 路由路径、WebSocket 事件名及 8 维特征向量键名，必须 100% 严格遵循本文档，严禁自行缩写、改名或发明新字段。
2. **双模式底层同源**：外食模式 (`OUT_DINING`) 与下厨模式 (`HOME_COOKING`) 在算法层共享同一套 8 维特征向量结构与防腻衰减函数，严禁拆分为两套互不兼容的推荐逻辑。
3. **白盒可解释与实时调参**：推荐接口必须返回五维雷达图分项得分与归因文案；所有算法超参数 (`lambda_decay`, `omega_group`, `alpha`, `beta`, `gamma`, `delta`) 必须支持请求参数动态覆盖，以支撑前端“算法上帝视角调试抽屉”。
4. **60fps 动效与交付规范**：后端采用 Python (`FastAPI` + `Pydantic` + `SQLAlchemy`)；前端采用 `Vue 3 (<script setup>)` + `Tailwind CSS` + `ECharts`，强制集成 `@formkit/auto-animate`、`@vueuse/motion`、`canvas-confetti`、**Lottie (`lottie-web` / `@lottiefiles/dotlottie-vue`)** 与 **`gsap`（含 Draggable 插件，100% 免费含商用）** 现成动效库，严禁用 AI 手写 CSS 动画冒充上述库的效果。分工锁定：简单弹性动效用 `@vueuse/motion`，列表过渡用 `auto-animate`，**划卡拖拽与揭晓编排专用 GSAP**，不得混用重复造轮子。

### 0.5 v2.1 正式锁定的形式化决策

以下三处在原始讨论中只有方向性说法，v2.0 将其形式化，v2.1 起正式锁定：

1. **双模式主色**：~~外食暖橙 / 下厨森林绿~~（v2.3 废止）——改黑灰银白单色，两模式共用令牌、靠图标与文案区分（见 v2.3 修订说明第 1 条与第六章 1）。
2. **群组算法权重配比**：个体满意度 `R[u, i] = 0.4 * prior_score + 0.6 * swipe_score`（见算法 3）。
3. **预算分与临期提权公式**：`budget_score` 公式与冰箱临期食材（未过期且实际剩余 ≤48h，边界见本章 v2.3.5 补充裁定）覆盖率双倍提权（见算法 2 与第六章）。

---

## 一、 工程目录结构契约

```text
eatwhat-ai-system/
├── MASTER_SPEC.md                  # 系统主契约与架构说明书
├── backend/                        # Python FastAPI 后端工程
│   ├── main.py                     # FastAPI 启动入口、CORS 配置、路由挂载
│   ├── config.py                   # 环境变量配置（高德Key、国产LLM API Key、数据库URL）
│   ├── database.py                 # SQLAlchemy 引擎、Session 管理与表初始化
│   ├── models.py                   # 15 张核心数据库表的 ORM 模型定义（v2.3.7 由 9 张增至 15 张）
│   ├── schemas.py                  # Pydantic 请求与响应数据契约模型
│   ├── algorithms/                 # 核心推荐与博弈算法引擎
│   │   ├── vector_spec.py          # 8维特征向量规范、情绪气泡与天气映射字典
│   │   ├── time_decay.py           # 算法1：基于艾宾浩斯遗忘曲线的跨场景防腻衰减
│   │   ├── single_recommender.py   # 算法2：多维上下文单人效用推荐与红黑榜修正
│   │   ├── group_recommender.py    # 算法3：融合最小痛苦策略(Least Misery)的群组博弈算法
│   │   └── combo_optimizer.py      # 算法4：一荤一素一汤组合优化与买菜差额清单计算
│   ├── routers/                    # RESTful API 与 WebSocket 路由层
│   │   ├── auth_user.py            # 模块1：演示角色、用户主页基因与红黑榜、资料编辑（PATCH profile）、头像上传
│   │   ├── auth_local.py           # 模块0（v2.3.7）：本地注册 / 登录 / 登出 / me，签发与校验会话令牌
│   │   ├── catalog.py              # 移动端菜品与门店只读目录（推荐页与详情共用）
│   │   ├── recommend.py            # 模块2：单人双模式推荐、环境感知胶囊接口
│   │   ├── fridge.py               # 模块3：虚拟冰箱库存 CRUD、余料反推、买菜清单合并
│   │   ├── group_room.py           # 模块4：多人干饭房间管理与 WebSocket 实时状态机
│   │   ├── eating_log.py           # 模块5：一键打卡、足迹时间线、满意度反馈、防腻冷却看板、周度报告
│   │   ├── admin.py                # 模块6：门店/菜品 CRUD、LLM 批量打标（同步入口）、审计日志查询
│   │   ├── admin_ext.py            # 模块6.5（v2.3.7）：用户管理、算法参数、打标任务队列、数据导入、单用户画像
│   │   ├── admin_stats.py          # 模块8：大屏 13 个聚合统计接口
│   │   └── admin_experiments.py    # 模块7：算法仿真对比曲线（读 algo_configs.benchmark_json）
│   ├── scripts/                    # 万级数据工程脚本
│   │   ├── fetch_amap_poi.py       # 脚本1：高德地图周边真实餐馆采集（place/around 接口）+ 校园食堂档口生成
│   │   ├── import_open_recipes.py  # 脚本2：开源中式家常菜谱清洗与导入（含香菜/海鲜/葱姜蒜等过敏原识别标注）
│   │   ├── llm_batch_tagger.py     # 脚本3：调用国产模型批量蒸馏 8 维特征向量
│   │   └── simulate_personas.py    # 脚本4：200虚拟用户×60天流水×1000场群组博弈仿真器
│   └── eatwhat.db                  # SQLite 数据库文件（含万级初始化数据）
└── frontend/                       # Vue 3 + Vite + Tailwind CSS + ECharts 前端工程
    ├── index.html
    ├── tailwind.config.js          # 黑灰银白单色主题令牌与毛玻璃动效配置
    ├── capacitor.config.json       # 一键打包 Android APK 配置文件
    └── src/
        ├── router/index.js         # 移动端 (/m/*) 与 PC 管理后台 (/admin/*) 路由
        ├── stores/                 # Pinia 状态管理（当前演示角色、当前模式、算法实时参数）
        ├── components/             # 高复用微交互组件
        │   ├── WeatherPill.vue     # 顶部灵动岛风格天气环境毛玻璃胶囊
        │   ├── ModeSwitcher.vue    # 外食/下厨双模式分段滑动开关
        │   ├── StatusBubbles.vue   # 弹簧动画情绪/状态气泡选择器
        │   ├── SwipeCardDeck.vue   # 多人房间 15 秒探探式表决卡片堆（GSAP Draggable 实现，拖动 >60px 触发判定，倾斜时显示想吃/达咩印章）
        │   ├── ExplainRadar.vue    # 可解释性 AI 五维匹配度雷达图弹窗
        │   └── AlgoSandboxDrawer.vue # 右上角算法参数实时调节抽屉（答辩演示神器）
        └── views/
            ├── mobile/             # 移动端 5 大核心视图
            │   ├── Home.vue        # 首页：上下文感知与双模式智能决策
            │   ├── Fridge.vue      # 冰箱：余料库存管理、临期提醒与买菜清单
            │   ├── Room.vue        # 干饭房：扫码进房、15秒闪电划卡与共识揭晓大屏
            │   ├── Footprint.vue   # 足迹：防腻冷却看板与周度干饭统计报告
            │   └── Profile.vue     # 用户主页：演示角色切换、饮食基因、忌口台、美食红黑榜、成就战绩
            └── admin/              # PC端管理视图（v2.3.7 起 7 个）
                ├── DataManage.vue          # 门店/菜谱 CRUD、质量面板、批量打标（任务队列）
                ├── ExperimentDashboard.vue # 三主题抽屉式大屏：数据概览 / 数据质量 / 算法实验
                ├── Users.vue               # 用户列表：角色、流水数、投票数、角色切换、画像入口
                ├── UserDetail.vue          # 单用户画像：偏好雷达、菜系分布、满意度、最近决策
                ├── Settings.vue            # 算法参数：λ/ω/α/β/γ/δ 落库并热加载
                ├── Import.vue              # 数据导入：CSV/XLSX 上传 → 字段映射 → 预览 → 写库
                └── AuditLog.vue            # 操作审计日志
```

---

## 二、 核心数据字典：8 维风味向量与状态气泡映射

### 1. 菜品与个人 8 维特征向量 (`feature_vector` / `base_vector`，取值 `0.0 ~ 1.0`)

| 键名 (JSON Key) | 中文含义 | 数值定义说明 (`0.0` ~ `1.0`) |
| --- | --- | --- |
| `spicy_level` | 辣度等级 | `0.0` 完全不辣（清汤/甜品），`0.3` 微辣，`0.7` 中辣，`1.0` 重度麻辣 |
| `oily_level` | 油腻厚重度 | `0.0` 极度清淡（白灼/蒸菜），`0.5` 家常小炒，`1.0` 重油重盐/油炸/浓油赤酱 |
| `soup_level` | 汤水温热感 | `0.0` 干拌/烧烤/干锅，`0.5` 带卤汁盖饭，`1.0` 纯汤面/砂锅炖汤/小火锅 |
| `temp_fit` | 适宜环境温度 | `0.0` 极寒天气专属热食，`0.5` 四季皆宜，`1.0` 酷暑专属凉菜/冷面/冰饮 |
| `satiety_level` | 饱腹与碳水度 | `0.0` 轻食小吃，`0.5` 标准正餐，`1.0` 碳水炸弹/高热量硬菜 |
| `prep_speed` | 出餐/制作速度 | `0.0` 慢炖/排队>45分钟，`0.5` 常规现炒(20分钟)，`1.0` 10分钟极速快餐/快手菜 |
| `social_fit` | 社交聚餐属性 | `0.0` 一人食简餐，`0.5` 双人便餐，`1.0` 多人共享（火锅/烤肉/大盘菜） |
| `comfort_level` | 情绪抚慰指数 | `0.0` 功能性减脂餐，`0.5` 日常普通饮食，`1.0` 高幸福感解压治愈美食 |

### 2. 情绪与状态气泡动态提权规则 (`STATUS_BUBBLE_RULES`)

| 气泡 ID (`bubble_id`) | 前端展示文案 | 适用模式 | 触发的算法权重与向量修正逻辑 |
| --- | --- | --- | --- |
| `exhausted` | 😫 刚加完班累瘫 | 通用 | 状态权重 `delta=0.45`；目标向量拉高 `comfort_level=0.9`, `prep_speed=0.9` |
| `broke_end_month` | 💸 月底吃土模式 | 外食 | 预算权重 `gamma=0.55`；过滤超预算菜品，优先 `satiety_level>=0.7` |
| `craving_heavy` | 🌶️ 嘴馋想吃重口 | 通用 | 口味权重 `alpha=0.50`；目标向量拉高 `spicy_level>=0.7`, `oily_level>=0.6` |
| `light_healthy` | 🥗 肠胃负担重想清淡 | 通用 | 任何 `oily_level>0.5` 或 `spicy_level>0.3` 的菜品得分强制乘以 `0.2` |
| `need_hot_soup` | 🍲 手脚冰凉想喝热汤 | 通用 | 天气权重 `beta=0.45`；强制要求 `soup_level>=0.7` 且 `temp_fit<=0.4` |
| `lazy_one_pot` | 🍚 只有电饭煲/不想洗碗 | 下厨 | 仅筛选 `appliance_tag` 数组含 `电饭煲` 或 `一锅出` 任一值的菜谱（v2.3.2 裁决：无速度门槛，该气泡为厨具硬约束、与速度偏好正交） |

---

## 三、 数据库详细设计（15 张核心关联表 Schema）

1. **`users`（用户与演示角色表）**
* `id` (INT, PK), `username` (VARCHAR, UNIQUE), `nickname` (VARCHAR), `avatar` (VARCHAR)
* `persona_title` (VARCHAR, 饮食人设称号，如 `"川渝无辣不欢星人"` / `"广东清淡养生党"`)
* `is_demo_persona` (BOOL, 默认 True，用于用户主页一键切换答辩演示角色), `created_at` (DATETIME)


2. **`user_preferences`（饮食基因、忌口红线与美食红黑榜表）**
* `id` (INT, PK), `user_id` (INT, FK `users.id`, UNIQUE)
* `base_vector` (JSON, 用户长期口味偏好 8 维向量)
* `default_budget` (FLOAT, 日常单餐默认预算上限，默认 `25.0`)
* `veto_tags` (JSON, 绝对忌口/过敏原数组，如 `["香菜", "折耳根", "海鲜"]`，触发一票否决)
* `preferred_cuisines` (JSON, 偏好菜系数组，如 `["川湘菜", "粤菜"]`)
* `favorite_dish_ids` (JSON, **红榜宝藏收藏菜品 ID 数组**，推荐计算时赋予 `1.15` 倍提权)
* `blacklist_dish_ids` (JSON, **黑榜拉黑菜品 ID 数组**，以菜品为对象，在单人与多人推荐中永久一票否决)
* `blacklist_restaurant_ids` (JSON, **黑榜拉黑门店 ID 数组**，以门店为对象；外食模式下该门店的全部菜品一并剔除，默认空数组)


3. **`restaurants`（周边真实门店与校园食堂档口表）**
* `id` (INT, PK), `name` (VARCHAR), `source_type` (`AMAP_POI` | `CANTEEN`), `category` (VARCHAR)
* `avg_price` (FLOAT, **可空**；高德缺失时保持 NULL，不得用 0/500 伪默认), `rating` (FLOAT, **可空**；高德缺失时保持 NULL，不得用 4.5 伪默认), `longitude` (FLOAT), `latitude` (FLOAT)（经纬度统一采用高德 `GCJ-02` 坐标系，严禁混入 WGS-84）
* `distance_meters` (INT, **直线距离**；保留旧字段名，但契约明确不是步行距离), `address` (VARCHAR)
* **v2.3.3 新增（全部可空）**：`source_dataset` (VARCHAR), `source_record_id` (VARCHAR), `source_url` (VARCHAR), `data_version` (VARCHAR), `is_synthetic` (BOOL, NULL=未知/历史, 0=真实, 1=合成), `deleted_at` (DATETIME, NULL=未删除；软删除标记)
* **v2.3.4 新增（可空）**：`campus` (VARCHAR, NULL=未归属；`SIYUAN` | `JIANDA_YANTA` | `JIANDA_CAOTANG` 预留)；思源/建大 POI 与合成食堂按校区分别存储，不得混用


4. **`dishes_and_recipes`（菜品与家常菜谱核心主表）**
* `id` (INT, PK), `name` (VARCHAR), `mode_type` (`OUT_DINING` | `HOME_COOKING`)
* `restaurant_id` (INT, FK `restaurants.id`, 下厨模式为 `NULL`), `cuisine_type` (VARCHAR)
* `dish_role` (`MEAT` | `VEG` | `SOUP` | `ONE_MEAL`), `price_or_cost` (FLOAT, 可空), `cook_minutes` (INT, 默认 `15`)
* `appliance_tag` (JSON 数组，元素取值 `炒锅` | `电饭煲` | `空气炸锅` | `免开火凉拌` | `一锅出`，默认 `["炒锅"]`；一道菜可多值，如同时支持电饭煲与一锅出的菜记为 `["电饭煲", "一锅出"]`)
* `ingredients_main` (JSON, 核心主料数组), `ingredients_aux` (JSON, 辅料数组)
* `recipe_steps` (TEXT), `feature_vector` (JSON, 8维标准化特征向量，**可空**；NULL=未完成/失败，成功时必须完整 8 键、有限、0–1), `image_url` (VARCHAR)
* **v2.3.3 新增（全部可空）**：`allergen_tags` (JSON 数组；LLM 输出，供词云/质量面板消费，**不默认加入算法 2 硬过滤**), `tagging_status` (VARCHAR: `PENDING` | `SUCCESS` | `FAILED`), `tagging_error` (TEXT), `llm_meta` (JSON: 模型/提示词版本/批次/请求 ID 等), `source_dataset` (VARCHAR), `source_record_id` (VARCHAR), `source_url` (VARCHAR), `data_version` (VARCHAR), `is_synthetic` (BOOL, NULL=未知/历史, 0=真实, 1=合成), `deleted_at` (DATETIME, NULL=未删除；软删除标记)

**schema 迁移约束（v2.3.3；v2.3.4 增补）**：以上新增字段全部可空；不得改变已有字段语义；`feature_vector` 仅放宽为可空，成功记录仍必须为完整 8 维。迁移脚本必须幂等，先加列/建表，再回填可空元数据；历史行 `is_synthetic`、`campus` 未回填前保持 NULL，不得冒充真实/合成或某校区。软删除统一用 `deleted_at IS NULL` 表示有效；推荐/列表查询过滤已删除行，历史流水/投票/报告仍可通过原 ID 联表读取。旧种子数据（当前 20 门店/100 菜）在 S10 迁移时标记为合成或由新数据替换。**v2.3.7 增补**：新增 6 张表的迁移为 `0a755691cec1`（审计）、`b7f1c2d3e4a5`（系统设置 + 打标任务）、`c8d2e3f4a5b6`（满意度反馈）；`auth_credentials` / `auth_tokens` 由 `init_db()` 同步建表，PG 环境需确认已存在。


5. **`fridge_inventory`（虚拟冰箱库存表）**
* `id` (INT, PK), `user_id` (INT, FK), `ingredient_name` (VARCHAR)
* `category` (`肉禽蛋奶` | `新鲜果蔬` | `冷冻速食` | `豆制品与干货`)
* `quantity_desc` (VARCHAR, 默认 `适量`；自由文本描述，不做数量/单位算术), `expire_days` (INT, 默认 `3`；**入库时的保质期**，精确到期边界见本章上方 v2.3.5 补充裁定；`remaining_days <= 2` = 未过期且实际剩余 ≤48h，前端高亮临期并在算法中双倍提权), `created_at` (DATETIME，同名食材再次 `ADD` 时重置为当前时间)


6. **`eating_logs`（饮食足迹与防腻历史流水表）**
* `id` (INT, PK), `user_id` (INT, FK), `dish_id` (INT, FK), `mode_type` (VARCHAR)
* `cost_amount` (FLOAT), `weather_snapshot` (VARCHAR), `status_bubbles` (JSON)
* `eaten_at` (DATETIME, INDEX, 用于计算艾宾浩斯时间间隔)


7. **`group_rooms`（多人干饭房间主表）**
* `id` (INT, PK), `room_code` (VARCHAR(10), UNIQUE, 邀请码；字段宽 10 位为预留，实际值固定为 6 位数字字符串，如 `886421`), `host_user_id` (INT, FK)
* `member_user_ids` (JSON, 成员 user_id 数组；建房时写入房主，其余成员只能经 `POST /rooms/{room_code}/join` 幂等追加，WebSocket 建连不落库)
* `mode_type` (`OUT_DINING` | `HOME_COOKING`), `status` (`WAITING` | `SWIPING` | `FINISHED`)
* `candidate_dish_ids` (JSON, 初筛10道候选ID), `winner_dish_id` (INT, NULLABLE)
* `consensus_report` (JSON, 群组平均分、最低分及各成员妥协度明细), `created_at` (DATETIME)
* **v2.3.4 新增（可空）**：`campus` (VARCHAR, NULL=未归属；建房时写入，join 必须同校区；跨校区禁止拼桌)
* **v2.3.6 补充**：`budget` (FLOAT, 可空；建房预算，初筛 `1.25` 倍软上限)、`algo_params` (JSON, 可空；建房时冻结的算法参数快照，S06 只存 `omega_group`)、`deadline_at` (DATETIME, 可空；服务端截止时间)、`settled_at` (DATETIME, 可空；结算幂等标记)。`campus` 建房必填，join 必须同校区；外食候选严格按 `restaurant.campus == room.campus` 过滤，NULL 门店排除。


8. **`room_votes`（房间实时划卡表决记录表）**
* `id` (INT, PK), `room_code` (VARCHAR, FK), `user_id` (INT, FK), `dish_id` (INT, FK)
* `vote_type` (枚举，仅存 `LIKE` | `SUPER_LIKE` | `PASS` | `VETO`，本表不存分值), `voted_at` (DATETIME)
* 分值映射唯一出处为第四章算法 3：划卡分 `swipe_score` 采用百分制 `SUPER_LIKE=120 / LIKE=100 / PASS=40`；`VETO` 不计分、只触发掩码淘汰。严禁在其他任何位置再定义第二套刻度（如 0.2 / 1.0 / -999）。
* **v2.3.6 补充**：唯一索引 `(room_code, user_id, dish_id)`；同一成员同一菜品在 `SWIPING` 且未截止前以最后一次为准，更新同一行与 `voted_at`。客户端提交 `TIMEOUT` 拒绝；`TIMEOUT` 只作为结算时未投票成员的内部缺席分 `60`，不落本表。


9. **`algo_configs`（算法超参数与实验对比表）**
* `id` (INT, PK), `config_name` (VARCHAR, 默认 `default_production`)
* `lambda_decay` (FLOAT, 默认 `0.5`), `omega_group` (FLOAT, 默认 `0.5`)
* `alpha_taste` (`0.35`), `beta_weather` (`0.25`), `gamma_budget` (`0.20`), `delta_status` (`0.20`)
* `benchmark_json` (JSON, 仿真实验对比数据，结构锁定如下，PC 后台与论文第五章直接按此渲染 ECharts；`GET /admin/experiments` 的 `duplication_rate_curve` 与 `group_satisfaction_bars` 即取自此结构同名字段)

```json
{
  "generated_at": "2026-11-01T00:00:00",
  "sample": {"personas": 200, "days": 60, "meals_per_day": 2, "rooms": 1000, "members_per_room": 4},
  "duplication_rate_curve": {
    "days": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    "ours_lambda_0.5": [0.00, 0.05, 0.08],
    "baseline_no_decay": [0.00, 0.18, 0.26]
  },
  "group_satisfaction_bars": {
    "strategies": ["mixed_omega_0.5", "average_omega_1.0", "random"],
    "avg_scores": [82.5, 84.1, 61.3],
    "least_misery_scores": [71.2, 52.6, 38.9]
  }
}
```

（数组示例长度仅示意；落库时 `days` 固定 14 个点、各曲线数组与 `days` 等长，`group_satisfaction_bars` 三个数组与 `strategies` 等长，分值均为 0~100。）


10. **`auth_credentials`（本地账号凭据表，v2.3.7 新增）**
* `id` (INT, PK), `user_id` (INT, FK `users.id`, UNIQUE), `password_hash` (VARCHAR, PBKDF2 加盐哈希，禁止存明文)
* `updated_at` (DATETIME)
* 一个用户至多一条凭据；演示人设与管理员口令统一为 `〔演示口令已脱敏，见本地答辩材料〕`，仅用于答辩演示，论文须说明。**口令不得写入前端源码或构建产物**（登录页只填充用户名），否则解包 `dist`/APK 即可获得管理员权限。

11. **`auth_tokens`（会话令牌表，v2.3.7 新增）**
* `id` (INT, PK), `user_id` (INT, FK `users.id`), `token` (VARCHAR, UNIQUE, 索引), `created_at` (DATETIME), `expires_at` (DATETIME, 默认签发后 **7 天**)
* 登出即删行；管理接口校验 `token` 有效且 `users.role == 'ADMIN'`。**令牌是管理端唯一身份凭证**，`X-User-Id` 不得用于管理接口。无刷新令牌轮换机制，过期即需重新登录（演示系统可接受，论文须如实说明）。

12. **`admin_audit_logs`（后台操作审计表，v2.3.7 新增）**
* `id` (INT, PK), `user_id` (INT, FK `users.id`, 索引), `action` (VARCHAR(32), 索引；固定「资源.动作」格式，如 `restaurant.delete` / `dish.update` / `algo.update`，便于按前缀过滤)
* `resource_type` (VARCHAR(32), 索引), `resource_id` (INT, 可空, 索引), `summary` (VARCHAR(255), 给人看的一句话), `detail` (JSON, 可空；存原始 payload，便于追查改前改后), `ip` (VARCHAR(64), 可空), `created_at` (DATETIME, 索引)
* 写审计的时机：角色变更、算法参数保存、菜品/门店增删改、批量打标。审计失败不得阻断主操作，但必须落日志。

13. **`system_settings`（系统级键值配置表，v2.3.7 新增）**
* `key` (VARCHAR(64), PK), `value` (JSON, NOT NULL), `updated_by` (INT, FK `users.id`, 可空), `updated_at` (DATETIME)
* 当前只承载 `algo_params` 一个键（λ / ω / α / β / γ / δ）。用 JSON 而非多列：参数集会继续增加，每加一个键就改表结构不划算。**运行期以内存缓存为准，保存后热加载，服务启动从本表读一次**。

14. **`tagging_jobs`（批量打标任务表，v2.3.7 新增）**
* `id` (INT, PK), `status` (`PENDING` | `RUNNING` | `DONE` | `FAILED`), `total` / `done` / `failed` (INT)
* `dish_ids` (JSON, 本次任务的目标菜品), `message` (VARCHAR(255), 失败原因或完成摘要)
* `created_by` (INT, FK `users.id`, 可空), `created_at` (DATETIME, 索引), `finished_at` (DATETIME, 可空)
* 打标要调外部模型，单次可能数十秒到数分钟，**不得占用 HTTP 请求**；后台线程逐批推进，线程内必须使用独立 `SessionLocal`（请求 session 在响应后已关闭）。

15. **`dish_feedback`（满意度反馈表，v2.3.7 新增）**
* `id` (INT, PK), `user_id` (INT, FK `users.id`, 索引), `dish_id` (INT, FK `dishes_and_recipes.id`, 索引)
* `log_id` (INT, FK `eating_logs.id`, 可空, 索引；兼容历史无关联记录), `rating` (INT, `3`=好吃 `2`=一般 `1`=踩雷), `created_at` (DATETIME, 索引)
* **单独建表而不给 `eating_logs` 加列**：同一道菜在不同时间可以有不同评价，「上次说好吃、这次踩雷」本身是信号，加列会把它压成最后一次。同一条 `log_id` 重复提交按更新处理（用户可能改主意），不堆多条。




---

## 四、 四大核心算法数学公式与实现逻辑

### 算法 1：跨场景防腻时间衰减模型 (`time_decay.py`)

查询用户近 14 天的 `eating_logs`。同款菜品 (`dish_id` 相同) 间隔天数记为 `dt_exact`，同菜系 (`cuisine_type` 相同) 或同主料 (`ingredients_main` 有交集) 间隔天数记为 `dt_similar`：

```python
W_decay = (1.0 - math.exp(-lambda_decay * dt_exact)) * (1.0 - 0.4 * math.exp(-lambda_decay * dt_similar))
```

* 若当天刚吃过 (`dt_exact == 0`)，强制设 `W_decay = 0.05`；若 14 天内未吃过，设 `W_decay = 1.0`。

### 算法 2：多维上下文单人推荐与红黑榜修正 (`single_recommender.py`)

1. **硬性红线过滤**：剔除 `ingredients_main / aux` 命中用户 `veto_tags`、菜品 ID 在用户 `blacklist_dish_ids` 中、所属门店 ID 在用户 `blacklist_restaurant_ids` 中（仅外食模式）、或超出距离限制的候选菜品。群组场景（算法 3）同样取全体成员两类黑榜的并集执行。
2. **五维效用计算（归一化至 `0 ~ 100` 分，直接对应前端五维雷达图）**：
* `taste_score`: 用户 `base_vector` 与菜品 `feature_vector` 的余弦相似度映射至 `[0, 100]`。
* `weather_score`: 根据实时气温与降雨生成理想环境向量，计算匹配度。
* `budget_score`: 若 `price <= budget`，得分为 `85 + 15 * (1 - price / budget)`；若超支则按比例指数扣分。
* `freshness_score`: 直接等于 `W_decay * 100`。
* `status_score`: 外食模式计算对当前所选“情绪气泡”的满足度；下厨模式计算菜品主料命中 `fridge_inventory`（仅用未过期库存；临期 = 实际剩余 ≤48h，权重翻倍）的覆盖率。


3. **红榜提权与综合得分合成**：
```python
boost_fav = 1.15 if dish.id in user.favorite_dish_ids else 1.0
total_score = W_decay * (alpha * taste_score + beta * weather_score + gamma * budget_score + delta * status_score) * boost_fav
> **封顶口径（v2.3.2 入正文）**：上式为**原始分**，只用于排序；一切展示场景（卡片匹配度、接口返回的展示字段）用 `total_score_display = min(100, total_score)`。四权重之和恒为 1（气泡调整后须重新归一化）。`radar_5d` 为五维分项分、各自落在 0–100，与总分封顶无关。
```



### 算法 3：融合最小痛苦策略的群组协同博弈算法 (`group_recommender.py`)

1. **阶段一（建房初筛 Top-10）**：取房间内所有成员 `veto_tags` 与 `blacklist_dish_ids` 的并集进行一票否决过滤，基于成员静态 `base_vector` 均值选出 Top-10 候选菜品下发至各端用于 15 秒划卡。
2. **阶段二（15 秒实时划卡后的博弈定夺）**：
* 成员 `u` 对菜品 `i` 的个体满意度：`R[u, i] = 0.4 * prior_score[u, i] + 0.6 * swipe_score[u, i]`（其中 `SUPER_LIKE=120`, `LIKE=100`, `PASS=40`）。
* 若任意成员投出 `VETO`，则 `Mask_veto(i) = 0`，否则为 `1`。
* 群组博弈共识分计算（结合 Average 均值策略与 Least Misery 最小痛苦策略）：
```python
G_score(i) = Mask_veto(i) * (omega_group * mean(R[:, i]) + (1.0 - omega_group) * min(R[:, i]))
```





### 算法 4：一餐多菜品组合优化与买菜差额清单 (`combo_optimizer.py`)

当开启“一荤一素一汤套餐模式”时，从单品得分 Top-20 中按 `dish_role` 提取 `(MEAT, VEG, SOUP)` 组合，满足总价 `<= budget` 且三道菜平均 `oily_level <= 0.65`（荤素冷热互补）。在下厨模式下，自动计算 `菜谱所需主辅料并集 - 冰箱现有食材集合`，输出合并同类项后的《待采购买菜清单》。

> **命名口径（论文措辞锁定）**：本算法的实质是“Top-20 候选内的角色分组三元组枚举 + 约束筛选”，候选规模小、枚举即最优解。论文与答辩中一律按此如实表述，**不得称为“改进背包算法”或动态规划**；如后续确需引入背包/DP，须先升级本文档并补复杂度分析后再改口径。

---

## 五、 前后端接口契约（RESTful API 与 WebSocket 协议）

### 0. 身份与数据源口径（开工前锁定；v2.3.7 升级为账号 + 令牌）

* **身份传递（v2.3.7 修订，取代 v2.2 的「一律 X-User-Id」）**：系统具备**本地账号体系**——`POST /auth/register` 注册、`POST /auth/login` 登录取令牌、`POST /auth/logout` 登出、`GET /auth/me` 查当前身份。令牌存 `auth_tokens`，请求头 `Authorization: Bearer <token>` 携带。
* **两类身份并存，作用域不同**：
  1. **已登录**：前端锁定当前账号，移动端接口以 Bearer 令牌解析身份；此时**禁止再切换演示角色**（登录成 A 还能切成 B 看 B 的数据，与账号体系冲突）。
  2. **未登录**：仍可按旧口径以 `X-User-Id: <演示角色 user_id>` 传身份，供答辩快速演示。请求体/查询参数中已声明 `user_id` 的接口，其值必须与令牌身份或 `X-User-Id` 一致，不一致以令牌/请求头为准并记日志。
* **管理接口（`/admin/*`）只认令牌**：必须 `Authorization: Bearer` 且该用户 `role='ADMIN'`，**不接受 `X-User-Id` 冒充管理员**；未登录 401、非管理员 403。
* **论文表述**：如实写作「演示系统内的本地账号 + 会话令牌」，不得描述为生产级鉴权——无验证码、无找回密码、无多因子、无刷新令牌轮换。
* **天气数据源**：`GET /context/weather` 的数据**锁定为高德天气 API**（`https://restapi.amap.com/v3/weather/weatherInfo`，实况用 `extensions=base`、预报提示用 `extensions=all`），与高德 POI 共用同一 Key（`config.py` 中同一环境变量）。降级链为 **高德 → open-meteo → 离线常量**，任一环节失败不得 500；响应 `source` 字段必须如实反映实际来源。

### 1. RESTful API 路由总表（前缀 `/api/v1`）

| 所属模块 | 请求路径 | 功能描述 | 核心请求体 / 参数 | 核心响应内容 |
| --- | --- | --- | --- | --- |
| **模块0：账号与会话（v2.3.7 新增）** | `POST /auth/register` | 注册本地账号：建 `users` + `auth_credentials` + 空 `user_preferences`，返回令牌 | `username`, `password`, `nickname?` | `token`, `user` |
|  | `POST /auth/login` | 账号密码登录取令牌（写入 `auth_tokens`） | `username`, `password` | `token`, `user`（含 `role`，供前端按角色分流） |
|  | `POST /auth/logout` | 登出并删除当前令牌 | 无（Bearer） | `{"ok": true}` |
|  | `GET /auth/me` | 查当前登录身份 | 无（Bearer） | `user`（`user_id`/`username`/`nickname`/`role`/`avatar`） |
| **模块1：用户与主页** | `GET /users/demo-list` | 获取预设演示角色列表 | 无 | `users[]`（含人设称号、头像、口味基因） |
|  | `GET /users/{id}/profile` | 获取用户主页完整数据 | `user_id` | 基因向量、忌口、红黑榜详情、干饭成就战绩统计 |
|  | `PATCH /users/{id}/profile` | **改昵称与头像（v2.3.7 新增）**；与 `preferences` 分开：一支管展示、一支管算法输入 | `nickname`（≤32 字，非空）, `avatar`（≤4 字符 emoji/首字，或 `/uploads/...` 路径） | 更新后的 `profile` |
|  | `POST /users/{id}/avatar` | **上传头像图片（v2.3.7 新增）**：multipart，Pillow 居中裁 256×256 JPEG(q86)，存 `backend/uploads/avatars/{uid}_{ts}.jpg`，返回相对路径 | `file`（≤3MB，JPG/PNG/WebP） | `{"avatar": "/uploads/avatars/..."}` |
|  | `PUT /users/{id}/preferences` | 更新基因、预算与忌口胶囊 | `base_vector`, `default_budget`, `veto_tags[]` | 更新后的 `user_preferences` |
|  | `POST /users/{id}/red-black-list` | 增删美食红榜(收藏)或黑榜(拉黑) | `target_type` (`DISH` \| `RESTAURANT`), `target_id`, `list_type` (`FAV` \| `BLACK`), `action`（`FAV` 仅允许 `DISH`） | 更新后的 `favorite_dish_ids`, `blacklist_dish_ids`, `blacklist_restaurant_ids` |
| **模块2：单人决策** | `GET /context/weather` | 获取顶部环境胶囊实时数据（数据源：高德天气 API，见本章 0） | `city` 或 `lat, lng` | `temp`, `weather_text`, `capsule_tip` |
|  | `POST /recommend/single` | **单人双模式智能推荐核心接口**；外食按 `campus` 过滤，下厨共享 | `user_id`, `mode_type`, `budget`, `bubbles[]`, `combo_mode`, `override_params`, `campus`（外食必填） | `recommendations[]`（含 `total_score`, `radar_5d`, `explain_reason`） |
| **模块3：虚拟冰箱** | `GET /fridge/{user_id}` | 获取冰箱库存（临期置顶） | `user_id` | `items[]`（含 `is_expiring_soon`：未过期且实际剩余 ≤48h；已过期项 `expire_days=0`、`is_expiring_soon=false`，仍返回供删除） |
|  | `POST /fridge/{user_id}` | 录入/删除冰箱食材（同名再次 `ADD` 视为重新入库，重置 `created_at`） | `ingredient_name`, `category`, `expire_days` | 更新后的库存列表 |
|  | `POST /fridge/shopping-list` | 多菜谱智能合并买菜清单（过期库存不计「已有」） | `user_id`, `dish_ids[]` | `owned_ingredients[]`, `to_buy_ingredients[]` |
| **模块4：多人房间** | `POST /rooms/create` | 创建多人干饭房间（房主自动成为首位成员，写入 `member_user_ids`）；必须指定校区；按房主与校区初筛 10 道候选；冻结有效 ω | `host_user_id`, `mode_type`, `budget`, `campus（必填）`, `override_params.omega_group` | `room_code` (6位码), `candidate_dishes[]`, `campus`, `omega_group` |
|  | `POST /rooms/{room_code}/join` | **扫码/输码进房（成员落库的唯一入口）**：校验房间存在、`WAITING`、请求 `campus` 与房间一致；新成员入组后用全员约束重算候选；将 `user_id` 幂等写入 `member_user_ids`，落库后才允许 WS | `user_id`, `campus（必填）` | 房间详情、`members[]`、最新 `candidates[]`；跨校区 409 |
|  | `GET /rooms/{room_code}` | 获取房间状态与共识揭晓报告 | `room_code` | 房间详情、`members[]`、`winner_dish`、`consensus_report` |
| **模块5：饮食足迹** | `POST /logs/checkin` | 点击“就吃这个”一键打卡 | `user_id`, `dish_id`, `mode_type`, `bubbles[]` | `log_id`, `new_decay_weight` |
|  | `GET /logs/timeline/{user_id}` | **足迹时间线（v2.3.7 新增）**：倒序流水，含每条的评价状态；评价一次批量查出，禁止逐条查（N+1） | `limit`（默认 20，上限 100） | `items[]`（`log_id`, `dish_id`, `dish_name`, `rating`（0=未评价）, `eaten_at`…） |
|  | `POST /logs/{log_id}/feedback` | **满意度反馈（v2.3.7 新增）**：`3`=好吃 `2`=一般 `1`=踩雷；同一 `log_id` 重复提交按更新处理；他人记录返回 403 | `rating`（1–3） | `{"log_id", "rating"}` |
|  | `GET /logs/stats/{user_id}` | 防腻冷却看板与周度干饭报告；打卡结果面板的「本周第几顿 / 本周已花」取自 `meals_this_week` 与 `weekly_expense` | `user_id` | `cooling_dishes[]`, `meals_this_week`, `weekly_expense`, `cuisine_pie_data[]` |
| **模块6&7：管理后台** | `GET /admin/restaurants` | 门店/食堂列表（分页、按 `source_type`/分类筛选） | `page`, `source_type`, `category` | `items[]`, `total` |
|  | `POST /admin/restaurants` | 新增门店/食堂档口 | 门店字段（同第三章） | 新建的餐厅记录 |
|  | `PUT /admin/restaurants/{id}` | 编辑门店/食堂档口 | 待改字段 | 更新后的餐厅记录 |
|  | `DELETE /admin/restaurants/{id}` | 删除门店/食堂档口（其外食菜品一并下架处理） | 无 | 删除结果 |
|  | `GET /admin/dishes` | 菜品/菜谱列表（按 `mode_type`/菜系/角色筛选；v2.3.7 增 `tagging_status` 与 `needs_tag`） | `page`, `mode_type`, `cuisine_type`, `dish_role`, `tagging_status`, `needs_tag` | `items[]`, `total` |
|  | `POST /admin/dishes` | 新增菜品/菜谱 | 菜品字段（同第三章） | 新建的菜品记录 |
|  | `PUT /admin/dishes/{id}` | 编辑菜品/菜谱（含 `feature_vector`、`appliance_tag`） | 待改字段 | 更新后的菜品记录 |
|  | `DELETE /admin/dishes/{id}` | 删除菜品/菜谱 | 无 | 删除结果 |
|  | `POST /admin/llm-tag` | 调用国产模型批量蒸馏8维向量（同步兼容入口，v2.3.7 起前端改用任务队列） | `dish_ids[]` | 生成的 `feature_vector` 数组及入库状态 |
| **模块6.5：后台系统能力（v2.3.7 新增，均需 `role=ADMIN`）** | `GET /admin/users` | 用户列表：昵称/角色/注册时间 + 流水数 + 投票数（子查询计数，避免 N+1） | `page`, `page_size`, `role?`, `keyword?` | `items[]`, `total` |
|  | `PATCH /admin/users/{id}/role` | 角色切换（`USER` ↔ `ADMIN`）；**不允许取消自己的管理员权限**（防自锁），写审计 | `role` | 更新后的用户 |
|  | `GET /admin/users/{id}/overview` | **单用户画像聚合**：偏好向量/预算/忌口/红黑榜计数、流水数与累计花费、菜系 Top6、满意度分布、最近 12 条决策。一次返回，避免画像页连打五六个接口 | `user_id` | `user`, `preference`, `summary`, `cuisine_top[]`, `rating_dist[]`, `recent_logs[]` |
|  | `GET /admin/settings/algo` | 读算法参数：当前生效值 + 默认值 + 是否被覆盖 + 字段中文名 | 无 | `current`, `defaults`, `overridden`, `fields[]` |
|  | `PUT /admin/settings/algo` | 保存算法参数：写 `system_settings` 并**热加载运行期缓存**，推荐接口下一次请求即生效；越界/未知键丢弃 | `lambda_decay`, `omega_group`, `alpha_taste`, `beta_weather`, `gamma_budget`, `delta_status` | 更新后的 `current` |
|  | `POST /admin/tag-jobs` | 创建批量打标任务：立即返回 `job_id`，后台线程逐批推进 | `dish_ids[]` | `job`（`id`, `status`, `total`, `done`, `failed`） |
|  | `GET /admin/tag-jobs` | 任务列表（倒序） | `limit` | `items[]` |
|  | `GET /admin/tag-jobs/{id}` | 单任务进度，供前端 2s 轮询 | `job_id` | `job` |
|  | `POST /admin/import/preview` | 上传 CSV/XLSX 并解析：返回列名、**全量行**（上限 2000）与预览前 8 行、目标字段表 | `file`（≤8MB） | `columns`, `rows`, `preview_rows`, `total_rows`, `target_fields` |
|  | `POST /admin/import/commit` | 按字段映射写库：同名菜品跳过；导入行标 `is_synthetic=1`、`source_dataset=admin_import`、`tagging_status=PENDING` | `mapping`, `rows` | `{"created", "skipped"}` |
|  | `GET /admin/audit-logs` | 后台操作审计（角色变更/参数保存/菜品增删/批量打标），按时间倒序，只读 | `limit`(≤200), `offset`, `action?`, `resource_type?`, `user_id?` | `items[]`, `total` |
|  | `GET /admin/experiments` | 获取算法仿真对比曲线数据（数据源为 `algo_configs.benchmark_json`，结构见第三章） | `lambda_val`, `omega_val` | `duplication_rate_curve`, `group_satisfaction_bars` |
| **模块8：大屏统计（v2.3.1 新增；v2.3.3 共 13 个；v2.3.4 双校区）** | `GET /admin/stats/overview` | 大屏顶部数字带与概览：各表总量、分校区与合计、打标覆盖率；`feature_values_total=8×成功打标菜品数`；`meta.scope` 说明 mode/campus 过滤作用范围 | `mode_type?`, `campus?`（`SIYUAN`/`JIANDA_YANTA`/`ALL`） | `by_campus`, `total`, `feature_values_total`, `logs_total`, `votes_total`, `rooms_total`, `tagging_coverage`, `meta` |
|  | `GET /admin/stats/geo` | POI 地图点位与热力权重（GCJ-02 原样返回，前端不得二次偏移）；rating/cost 缺失保持 NULL；`mode=HOME_COOKING` 不适用 | `mode_type`, `cuisine_type`（可选） | `points[]`（`id`, `name`, `lng`, `lat`, `rating`, `heat`，heat=该店流水出现频次）；不适用时 `applicable:false` |
|  | `GET /admin/stats/calendar` | 日历热力：仿真期每日决策量；Asia/Shanghai 本地日期、默认全库范围 | 无（取 `eating_logs` 全周期） | `daily[]`（`date`, `count`） |
|  | `GET /admin/stats/heatmap` | 星期 × 时段矩阵热力；四档固定为早餐 [05,10)、午餐 [10,15)、晚餐 [15,21)、夜宵 [21,05)，weekday 0=周一 | `mode_type`（可选） | `matrix[]`（`weekday` 0–6, `slot`, `count`） |
|  | `GET /admin/stats/cuisine` | 菜系构成（环形图） | `mode_type`（可选） | `items[]`（`cuisine_type`, `count`, `share`） |
|  | `GET /admin/stats/cuisine-trend` | 菜系决策量按日趋势（堆叠面积） | `mode_type`（可选） | `dates[]`, `series[]`（`cuisine_type`, `data[]`） |
|  | `GET /admin/stats/personas` | 演示角色口味画像雷达（8 维同图对比） | 无 | `personas[]`（`user_id`, `nickname`, `base_vector`） |
|  | `GET /admin/stats/scatter` | 价格 × 评分散点（气泡=出现频次）；数据源为 `restaurants` 全量 + `dishes_and_recipes` 全量；OUT_DINING 用门店真实 rating，HOME_COOKING 无真实 rating 时 `rating=NULL`，不得伪造；评分轴只绘非空点并在 `meta` 报未绘制点数 | `mode_type?`, `campus?` | `points[]`（`name`, `price`, `rating`, `freq`, `entity_id`, `entity_type`）；`meta.not_plotted_no_rating`（整数，rating 为空未绘制的点数） |
|  | `GET /admin/stats/flow` | 决策流向桑基；**守恒单位为“票”**（40,000 票 → 票型 → 赢家/其他/否决/缺席；房间结果另列） | 无 | `nodes[]`, `links[]`（`source`, `target`, `value`） |
|  | `GET /admin/stats/keywords` | 词云：`allergen_tags` + 菜名分词；词频/TopN 规则可复算 | `mode_type`（可选） | `words[]`（`name`, `value`） |
|  | `GET /admin/stats/race` | 动态排序竞赛：菜品热度按周 Top 10 演变；另含 `latest_top10` 供 C08 轮播榜（被选日志+被投票次数降序，VETO 不计） | 无 | `weeks[]`, `series[]`（`dish_id`, `dish_name`, `data[]`）, `latest_top10[]` |
|  | `GET /admin/stats/cooccurrence` | 食材共现关系图：无序主辅料对，次数≥3 入图，`top_n=30`/上限 100，过滤盐/水/油/葱/姜/蒜等通用项 | `top_n`（可选） | `nodes[]`（`name`, `value`）, `links[]`（`source`, `target`, `value`） |
|  | `GET /admin/stats/quality` | 数据质量面板：打标覆盖率、缺失字段 Top、向量越界/异常计数；覆盖率分母=快照 dishes 总数，分子=8 维完整且成功 | 无 | `tagging_coverage`, `missing_fields[]`, `vector_anomalies` |

**模块 8 通用响应（v2.3.3）**：筛选不适用时统一返回 `200`：
`{"applicable": false, "reason": "<说明>", "items": [], "meta": {}}`；不得返回 404/500、不得静默返回全量冒充联动。空结果返回 `200` + 空数组/0 值。模块 8 共 **13** 个接口，`quality` 必须保留。

**双校区筛选（v2.3.4）**：适用 stats 增加可选 `campus`（`SIYUAN`/`JIANDA_YANTA`/`ALL`）；`overview` 同时返回 `by_campus` 与 `total`，合计不得掩盖单校区数；固定实验/人设图（C05/C06/C09）为 `scope=GLOBAL`，campus 筛选返回 `applicable:false`；下厨共享数据标 `scope=SHARED`。见 §5.5。

### 2. 多人房间 WebSocket 实时协议 (`ws://{host}/ws/room/{room_code}/{user_id}`)

* 前置条件：建立 WebSocket 连接前必须已通过 `POST /rooms/{room_code}/join` 落库为成员，未落库的连接直接拒绝（HTTP 403）；连接本身只订阅与广播，不写入成员。
* `MEMBER_SYNC` (服务端广播): 成员进房（join 落库后触发）/准备状态更新，`members: [{user_id, nickname, avatar, progress}]`；**v2.3.6**：同时下发最新 `candidates[]`，供房主在成员变化后刷新卡组。
* `START_SWIPING` (房主触发 -> 全员广播): 同步开启 15 秒倒计时与探探式划卡堆叠；`candidate_count` 为 0 或房间未绑定校区时拒绝开局（`ERROR`）。
* `SUBMIT_VOTE` (客户端上报): `{"type": "SUBMIT_VOTE", "dish_id": 108, "vote_type": "LIKE"}`；**v2.3.6**：`vote_type` 只接受 `LIKE` / `SUPER_LIKE` / `PASS` / `VETO`，`TIMEOUT` 拒绝；同一成员同一菜品在截止前以最后一次为准。
* `PROGRESS_UPDATE` (服务端广播): 实时同步各室友划卡进度（如 `8/10`）。
* `CONSENSUS_REVEAL` (服务端广播): 全员完成或倒计时结束，广播博弈获胜菜品及各成员妥协照顾度报告，触发全屏礼花。
* `ROOM_STATE` (服务端单发，v2.3.6 明确): 建连后立即下发完整快照（成员、候选、本人票、进度、`deadline_at/remaining_ms`、`campus`、`omega_group`、赢家或无共识、完整报告），用于刷新/断线恢复；SWIPING 时再补发 `START_SWIPING` 并重挂定时器，不依赖是否刚好收到广播。

### 5.5 双校区契约（v2.3.4 新增）

#### 5.5.1 校区注册表

| 校区 | ID | 中心 GCJ-02 | 3km 真实 POI | 合成食堂 | 状态 |
|---|---|---|---:|---:|---|
| 西安思源学院主校区 | `SIYUAN` | `109.078487,34.234818` | **605**（直接 count 600；网格去重 605） | 200 | 已实测 |
| 西安建筑科技大学雁塔校区 | `JIANDA_YANTA` | `108.967153,34.236991` | **6,659**（1,206 次调用；0 未完成） | 200 | 已实测 |
| 草堂校区（预留） | `JIANDA_CAOTANG` | 待确认 | 待确认 | 待确认 | 若高德返回草堂，先停下询问用户 |

- 两校区采样方法完全一致：固定 3km、`types=050000`、网格法、按 `poi.id` 去重、最终 haversine ≤3000m；报实际数，不合成补齐，不假设一定到 1500+。
- 思源与建大的真实 POI、合成食堂分别计数、分别存储，不得混用；`1700` 是原规格总数目标（约 1500+ 真实门店 + 200 食堂窗口），不是实际数；“2km 内不足 1700 再扩 3km”规则作废；`17` 只表示大屏图数量。
- 建大若高德返回**草堂校区**，必须停止后续采集并询问用户；不得把草堂结果冒充雁塔。

#### 5.5.2 数据归属与字段

- `restaurants.campus`（可空）标记门店/档口所属校区；思源、建大分别存储；`source_type` 仍区分 `AMAP_POI`/`CANTEEN`，`is_synthetic` 仍区分真实/合成。
- `group_rooms.campus`（可空）标记房间校区；建房必填写入，join 必须同校区；跨校区不能拼一桌外食。**v2.3.6**：外食候选严格按 `restaurant.campus == room.campus` 过滤，`campus IS NULL` 的门店/菜品排除；历史 `campus IS NULL` 房间仅允许 `WAITING` 首个 join 绑定校区并同事务重算候选，重算 0 道则回滚并拒绝，非 `WAITING` 拒绝绑定，未绑定校区不得开局。
- 下厨菜谱（`HOME_COOKING`）为**共享**数据，不按校区复制；外食菜品通过 `restaurant_id` 关联 `restaurants.campus`。
- `eating_logs`/`room_votes` 不新增 campus 字段：外食日志/票通过 `dish_id→restaurant.campus` 或 `group_rooms.campus` 归属；下厨日志/票为 `SHARED`。
- 用户身份不新增 campus 字段；校区由前端当前选择 + 请求参数决定；`X-User-Id` 仍只表示演示身份。

#### 5.5.3 前端切换与过滤

- 前端顶部/全局提供校区切换（`SIYUAN` / `JIANDA_YANTA`；草堂未开放）；默认思源（两校区均已试抓，仍默认思源）。切换后推荐、POI、统计、大屏同步刷新；不得只切标题不切数据。
- 外食推荐：`POST /recommend/single` 增加 `campus`（外食必填；下厨可忽略/共享）。缺失外食 campus 返回 422，不得默认混算两校区。
- 群组：`POST /rooms/create` 增加 `campus`（必填）；`POST /rooms/{code}/join` 校验同校区，不一致返回 409；WebSocket 只接受已落库成员；跨校区拼桌禁止。**v2.3.6**：前端 S06 只透传默认校区 `SIYUAN`，全局校区切换 UI 留后续专项验收；下厨房间仍须同校区但候选不过滤校区。
- 统计：所有适用 stats 增加可选 `campus`（允许 `ALL`）；`overview` 必须返回 `by_campus` 与 `total`，合计不得掩盖单校区数；固定实验/人设图（C05/C06/C09）为全局仿真，`campus` 筛选返回 `applicable:false`、`meta.scope=GLOBAL`；下厨共享数据标 `scope=SHARED`，不重复计入单校区合计。
- 大屏数字分校区报，也报合计；`C02` 地图按校区分层/分色，思源与建大不得共用同一合成食堂图层。

#### 5.5.4 规模与合成边界

- 思源：真实 POI 605 + 合成食堂 200 = 805；建大：真实 POI 6,659 + 合成食堂 200（单独生成）= 6,859；两校区分别报，不得用 1700 反推或跨校区挪用。
- 菜谱为合成数据，`is_synthetic=1`；思源/建大共享同一套下厨菜谱，不按校区复制；外食菜品按校区人工菜单维护，AMap `tag` 仅补充。
- 食堂窗口先按校区分别合成并标注；实数按校区逐个替换；实数不足 200 按实际数记，不硬凑；思源/建大合成食堂不得混用。
- 特征值仍按“成功打标菜品数 × 8”，不设 60,000+ 硬目标；图/论文报实际数。

---

## 六、 前端 UI/UX 视觉规范、用户主页与 60fps 动效工程

### 1. 全局色彩与视觉质感（v2.3 全面改版，细节以 `MOBILE_VISUAL_SPEC.md` 为准）

* **色彩令牌（黑灰银白单色）**：全局以黑、灰、银、白为唯一色系；深色令牌近黑 `#17171A`、银灰 `#55555E`，浅色令牌白 `#FFFFFF` / 浅灰 `#F4F4F5`。双模式（外食/下厨）**不靠颜色区分**，靠图标 + 文案标签 + 分段开关选中态（深灰实底白字）区分。原暖橙/森林绿/奶油白令牌与 `from-orange-500`、`from-emerald-600` 等渐变类一律禁用。
* **背景分工锁定为 Vue Bits 三背景（v2.3，用户拍板）**，全部为原生 Vue 单文件组件、颜色参数化，严禁施工模型另找或手写背景：
  1. **全局底 `Grainient`（谷物）**：移动端所有页面打底；三色全设银灰（深色版 `#3A3A40 / #17171A / #55555E`），`timeSpeed ≈ 0.2` 接近静止，颗粒细腻低强度；禁用其默认蓝紫配色。内容密集页允许冻结为静态帧或大幅降帧。
  2. **重点区域 `Liquid Chrome`（液态铬）**：仅首页顶部与共识揭晓页；底色保持近黑 `#1A1A1A`（最亮不超 `#222226`）；文字严禁直接压铬面，必须落在玻璃组件上。
  3. **启动/登录页 `Silk`（丝绸）**：银灰色，Speed 由默认 5 降至 1–2；仅限只看几秒的页面，不得作全局底（墨池已用 Silk 作全局背景，两作品须区分）。
* **三层架构（硬约束，v2.3.2 修订）**：第 0 层背景只负责氛围不承载信息；第 1 层悬浮小件玻璃（§2.6，WEATHERPILL_GLASS 配方）；第 2 层内容卡片为**液态玻璃卡（G 方案，v2.3.2 定款）**——折射层 + 半透明填充 + 亮边高光 + 阴影组，白字；可读性靠大 blur 与折射层保证，不靠填实。菜品图片在卡内全彩原样展示（不加磨砂/滤镜），不直接贴动效底。性能分级：一级卡（TOP 1 主卡、卡组顶卡、主页区块卡）开折射，次级小卡用同套高光/阴影的磨砂降级版；`backdrop-filter`/SVG 滤镜不支持时整体降级为高透磨砂。配方细节以 `MOBILE_VISUAL_SPEC.md` §3–§4 为准。
* **背景素材授权备注**：Vue Bits 许可为 MIT + Commons Clause，自用/毕设合规、不得转售其组件本身；原 backgrounds.supply 纹理图方案已作废、不再使用，其 $49 商业授权问题随之消失。
* **卡片规范（v2.3.2 定款）**：Bento Grid 便当盒大圆角布局 (`rounded-3xl`) + **液态玻璃材质**（见上条三层架构第 2 层）+ 单色（银灰/白）图标，不再用双色图标；原「实底卡 + 弥散柔光阴影」规范作废。

### 2. 强制集成的 5 大开源前端动效库规范

1. **`@formkit/auto-animate`（零配置列表自动过渡）**：
* 必须挂载于：**虚拟冰箱食材列表**、**用户主页忌口胶囊与红黑榜列表**、以及**主界面推荐结果列表**。当在右上角“算法调试抽屉”拖动滑块改变参数时，推荐卡片自动产生丝滑的上下浮动换位动画。


2. **`@vueuse/motion`（物理弹簧阻尼引擎）**：
* 用于顶部 `WeatherPill.vue` 灵动岛展开、情绪气泡 `StatusBubbles.vue` 点击时的果冻按压回弹 (`stiffness: 300, damping: 20`)，以及双模式切换滑块的物理惯性过渡。


3. **`Inspira UI / Magic UI` 风格微动效**：
* 推荐匹配度百分比（如 `94.6%`）采用数字滚动牌 (`Number Ticker`) 动效；核心主按钮采用流光扫过特效 (`Shimmer Button`)。


4. **`canvas-confetti` + `Lottie`（氛围粒子与矢量动画）**：
* 在多人房间 `CONSENSUS_REVEAL` 共识揭晓瞬间，调用 `confetti()` 触发全屏彩色礼花庆祝。
* **Lottie（v2.1 补回，原始讨论已定）**：顶部天气胶囊的动态天气图标（晴/雨/雪矢量小动画）、共识揭晓与空状态插画一律使用 Lottie JSON 动画文件播放，严禁使用静态图片或手写 CSS 动画替代；动画文件统一放在前端 `src/assets/lottie/` 下按场景命名。

5. **`gsap` + `Draggable` 插件（划卡拖拽与编排时间线，v2.1 补充修订新增）**：
* **唯一指定用途一：`SwipeCardDeck.vue` 划卡**。拖拽、甩出惯性、倾斜印章、松手阈值判定（拖动 `>60px` 触发 `LIKE / PASS`）一律用 Draggable 实现，严禁用手写 touch 事件或 Swiper 冒充；`onDragEnd` 回调将判定结果映射为 `SUBMIT_VOTE` 的 `vote_type`。
* **唯一指定用途二：共识揭晓与结果弹窗的 Timeline 编排**（倒计时结束 → 卡片翻牌 → 礼花 → 共识报告展开的多段顺序动画），以及匹配度数字滚动的补间。
* **Vue 集成纪律**：GSAP 为命令式 DOM 动画，必须用 `gsap.context()` 包裹并在组件 `onUnmounted` 时 `ctx.revert()` 清理，严禁动画实例泄漏；插件在使用前 `gsap.registerPlugin(Draggable)` 注册一次。
* **不引入的部分**：`Flip` 与 `auto-animate` 功能重叠，默认不装；`ScrollTrigger` 仅 PC 后台与干饭报告页确有滚动叙事需求时再评估，移动端不得预装。

### 2.5 动效参照来源与明确不采用的方案（v2.1 补充修订）

* **动效参照来源锁定为 `60fps.design` 免费浏览层**：划卡 (Swipe / Card Stack)、底部抽屉 (Bottom Sheet)、列表错峰 (Stagger) 等场景，先在该站找到对应参照片段，把其配套 prompt 与规律描述喂给施工模型再写代码；其 PRO 订阅与 MCP 均不购买（MCP 输出为 SwiftUI 代码，与 Vue 技术栈不符）。
* **明确不采用 React 组件库移植**：`21st.dev`、`ui.aceternity.com`、`magicui.design` 均为 React 代码，转写 Vue 后效果与维护均无保证，**不作为本项目的参考与移植来源**；已采用的 `Inspira UI` 系 Magic UI 设计语言的 Vue 社区实现，继续保留，两者不得混为一谈。严禁施工模型将 React 组件代码直接粘贴或机械转译进本项目。



### 2.6 `WeatherPill.vue` 液态玻璃质感施工法（v2.1 补充修订新增）

顶部天气胶囊的毛玻璃/液态玻璃质感**不凭模型想象手写 CSS**。参数已实测提取完毕（v2.3 更新，原「打开 Figma 复制 CSS」流程已完成、废止）：

1. **唯一数值来源**：`WEATHERPILL_GLASS.md`（与本文档同目录）——Apple 官方 Figma「macOS 27」Materials 页 **Liquid Glass - Small（Light 变体）** 的完整参数表（两层填充、3 内阴影 + 4 外阴影、Glass 折射参数）与 Web 生产组合版 CSS（经典材质实测填充/模糊 + 液态玻璃阴影塑形）。施工直接引用该文件，数值不得改动、不得凭想象另写。
2. **适用范围（v2.3.2 修订）**：本节的 WEATHERPILL_GLASS 配方用于小面积悬浮件——`WeatherPill.vue`、顶部导航条、底部 Tab 栏、模式切换器、抽屉把手；**内容卡片另走液态玻璃 G 方案**（折射层结构，见第六章 1 三层架构第 2 层与 `MOBILE_VISUAL_SPEC.md` §4），两套玻璃同源（高光/阴影语言一致）、配方不同，不得混用或互相替代。整页玻璃仍禁止。
3. **禁用路线**：GitHub 上的 Liquid Glass 类开源复刻项目实测效果不佳，不作为实现基础；施工模型不得自行引入此类库。

### 2.7 小控件指定来源：按钮 / 开关 / 滑块 / 气泡（v2.1 补充修订，用户拍板）

按钮、开关等小控件**一律用现成组件设计，严禁施工模型凭想象手写样式**。指定来源如下（均已实地核验为免费）：

**主力来源：`daisyUI`（MIT 免费，Tailwind 纯 CSS 插件，零 JS 依赖，框架无关）**
| 本项目控件 | 指定 daisyUI 组件 | 说明 |
| --- | --- | --- |
| 普通按钮 | `btn` | 主按钮再叠加本项目渐变令牌 |
| 双模式分段开关 `ModeSwitcher` | `filter`（一组 radio，选中高亮） | 语义正对外食/下厨二选一 |
| 开关（Toggle） | `toggle` | 忌口、设置类开关 |
| 预算滑块 / 算法沙盒滑块 | `range` | 轨道与手柄颜色取主题令牌 |
| 状态气泡 `StatusBubbles` | `filter` / `badge` 组合 | 选中态高亮沿用单色令牌（深灰实底白字，v2.3 已无模式色） |
| 卡片与小徽章 | `card` / `badge` | 只用其结构类，圆角阴影仍服从第六章 1 的卡片规范 |

**特效补充来源：`Inspira UI`（Vue 原生，开源免费）**
* 全 App 唯一的主 CTA 按钮（“开始智能决策”）直接使用其 **Shimmer Button**（或 Gradient Button）现成实现，不再手写流光效果。

**呼应规则（硬约束）**：daisyUI 只许通过**一套自定义主题**接入——主题变量按 v2.3 单色令牌定：`primary` = 近黑 `#17171A`、`secondary` = 银灰 `#55555E`、`base` = 白/浅灰（`#FFFFFF` / `#F4F4F5`）；所有控件颜色只能引用主题/令牌变量，**严禁在组件代码里写死任何十六进制颜色**。这样按钮、开关与三层背景天然呼应，后续调色只改主题一处。

**不作指定来源**：`shadcn-vue` 覆盖虽全且换色机制好，但属自建组件库模式、默认风格中性且无现成流光按钮，暂不引入，后续确需无障碍原语时再评估；`uiverse.io` 量大（7400+）但质量参差、颜色逐个写死，只许作单个特效灵感参考，不得整站照搬；`hyperui` / `flowbite-vue` 控件齐全但风格偏朴素后台风，不采用。

### 3. 用户主页 (`Profile.vue`) 四大核心区块规范

1. **顶部人设卡与角色入口（v2.3.7 修订）**：展示当前头像、昵称、饮食人设称号（如“川渝无辣不欢星人”）。右上角为**「编辑」**入口（弹层改昵称与头像，头像支持上传图片，后端裁 256×256 JPEG）。**「🔄 切换室友」只在未登录时出现**：登录后身份锁定，切换账号等于越权查看他人数据；演示切换统一由登录页的快捷账号承担。
2. **我的饮食基因与忌口红线控制台**：八维口味偏好可视化进度条 + 日常默认预算滑块 + 支持随时点击增删的“绝对忌口/过敏原”胶囊管理区（配 `v-auto-animate` 动效）。
3. **美食红黑榜（宝藏收藏夹 vs 踩雷黑名单）**：双 Tab 切换展示两类对象并分别注明口径——**红榜只对菜品**（`favorite_dish_ids`，提示“推荐时享 1.15x 提权”）；**黑榜分菜品与门店两类**（菜品拉黑提示“该菜永久一票否决”，门店拉黑提示“该店全部菜品不再推荐”），支持一键移出。文案严禁再把黑榜笼统写成“黑榜店铺”。
4. **个人干饭成就与战绩概览**：展示累计解决“吃什么”世纪难题次数、本月外食与下厨花费占比环形图、以及历史参与的“多人干饭房间”拼单战绩记录。
5. **背景图（v2.3.7 修订）**：背景存 `localStorage` 的 `eatwhat.v5.background`，由 `MobileShell` **统一渲染**，全部 `/m/*` 页面共享；保存后派发 `eatwhat:background-changed` 事件通知外壳重读。此前只有首页自己读取，导致「换完背景只有首页变」。

### 4. 答辩演示专属组件：`AlgoSandboxDrawer.vue`（右上角算法上帝视角抽屉）

* 移动端右上角常驻 `🛠️ 算法沙盒` 悬浮按钮，拉开后提供 4 个实时滑块：`防腻衰减系数 λ (0.1~2.0)`、`群组折中系数 ω (0.0~1.0)`、`天气权重 β`、`预算权重 γ`。拖动滑块实时重算并触发主界面排名动画与五维雷达图面积变形。

### 5. PC 管理后台与实验大屏规范（v2.3.1 全量扩容，调研依据见 `DASHBOARD_EXPANSION.md`；v2.3.7 改为抽屉式）

**v2.3.7 实际落地结构（取代下述「三屏轮播」版式）**：

- **导航**：大屏不再自建抽屉列，分析主题作为**左侧栏「实验大屏」下的缩进子项**（`AdminShell` 的 `subnav` 插槽），主题为 **数据概览 / 数据质量 / 算法实验** 三个；右侧为单主题内容区。
- **取消轮播**：去掉 12 秒自动轮播与底部圆点，改为点击主题切换（↑↓←→ 亦可切换）。轮播会让每张图只被看 12 秒，且没有「当前在看什么」的锚点。
- **布局基线（1920×1080 实测）**：主题区 `grid-template-rows: 88px minmax(0,1fr)`（概览为 `88px / 1fr / 168px`）；KPI 行 88px 是「标签 + 数字 + 说明」三行的实测下限，压到 78px 会把说明文字裁掉。
- **数据不足的图不上屏**（硬规则）：宁可少一张图，不做无数据支撑的图。已移除项见下。
- **图表实现**：一律 ECharts 手写 option；点阵地图为纯 DOM + `transform` 缩放平移（滚轮 1–8×、拖拽、复位），不引地图引擎。
- **颜色**：沿用浅色后台单色令牌（v2.3 系列「浅色化」后后台为浅色长读界面），**不再使用深色底**；路由切页不得露出深色底（`AppBackdrop` 在 `/admin` 不渲染，`html[data-surface="admin"]` 统一表面色，后台切页 `transition: none`）。

**版式锁定（1920×1080 基准画布，深色版单色令牌；v2.3.7 已浅色化，此段保留为设计依据）**：近黑底 `#17171A`、银灰线、白字；图表色板只许灰阶 + 银色渐变，热力图用单色深浅（深灰→银白），**严禁彩虹色板与蓝绿科技风**（与移动端口径统一）。自上而下：标题栏（右侧放全局筛选器）→ 翻牌数字带 → 三列主体（左：菜系环形 / 时段矩阵热力 / 人设雷达；中：POI 地图 C 位 + 底部横贯日历热力；右：实验一曲线 / 实验二柱状 / 热门菜品轮播榜）→ 其余图表（散点、桑基、趋势、词云、竞赛、关系图、水球）以同页第二屏区或 Tab 分区承载，仍服从「一屏一主题」。

**图表清单（原定 17 项，数据源与接口见第五章模块 8 与 `DASHBOARD_EXPANSION.md` §2；v2.3.7 实际落地 13 项，见下方状态表）**：
- 必备档：①翻牌数字带 ×5（门店/菜品/特征值/流水/投票，数字全部取自实际库，不写死）②POI 地图（气泡散点 + 热力叠加 + 点聚合）③60 天日历热力图 ④星期×时段矩阵热力图 ⑤实验一双曲线（已有）⑥实验二分组柱状（已有）⑦菜系构成环形图 ⑧热门菜品轮播排行榜（由 `eating_logs + room_votes` 聚合，按被选/被投次数降序 Top10；VETO 不计热门）
- 加分档：⑨4 人设 8 维雷达对比 ⑩价格×评分散点（`restaurants`+`dishes` 全量；OUT_DINING 用真实 rating，HOME_COOKING 无真实 rating 时 `rating=NULL`，不得伪造；评分轴只绘非空点，`meta.not_plotted_no_rating` 报未绘制点数）⑪决策流向桑基图（守恒单位为“票”）⑫菜系趋势堆叠面积 ⑬口味标签词云（`allergen_tags` + 菜名分词，`echarts-wordcloud` 扩展）⑭每图导出 PNG 按钮（ECharts `getDataURL`，供论文第五章插图，导出图须带图题与数据口径注脚）
- 进阶档：⑮菜品热度按周动态排序竞赛（bar-race）⑯食材共现关系图（力导向）⑰打标覆盖率水球/环形进度（分母=快照 dishes 总数，分子=8 维完整且成功；亦进 DataManage 质量面板）

**17 项落地状态（v2.3.7 实测，以「有无数据支撑」为准）**：

| 项 | 状态 | 说明 |
|---|---|---|
| ① 数字带 ② POI 点阵 ③ 日历热力 ⑤ 实验一双曲线 ⑥ 实验二分组柱状 ⑦ 菜系构成 ⑧ 热门榜 ⑨ 人设雷达 ⑩ 价格×评分散点 ⑫ 菜系趋势 ⑬ 标签词云 ⑯ 食材共现 ⑰ 打标覆盖率 | **已实现** | 词云在 9.5px 字号下叠字严重，改为**标签频次 Top9 横向条形**（同数据、可读）；⑰ 覆盖率环改**大数字 + 图例**（100% 满环没有信息量） |
| ④ 星期×时段矩阵热力 | **已移除** | 9 条流水全部落在夜宵（周四夜宵 3 次最多），7×4 网格全是 0；用 9 条样本画矩阵热力没有意义，应显示「样本不足」而非画一堆 0 |
| ⑪ 决策流向桑基 | **已移除** | 票数为 0，图永远是空态 |
| ⑮ 热度周竞赛 | **已移除** | 仅 2 周数据且各值恒为 1，动画无信息量 |
| ⑭ 每图导出 PNG | **未实现** | 保留为论文插图需求，待图表稳定后统一加（`getDataURL`，导出须带图题与口径注脚） |

**行为数据现状（v2.3.7 核实，2026-10-31 15:30 实测）**：主库 `eating_logs` **23 条**（其中约 14 条为界面联调时点击「就吃这个」产生）、`room_votes` **0 条**、`dish_feedback` 1 条；两个隔离库 `eating_logs` 各 9 条、`room_votes` 各 392 条。G3 仿真产出过 48,000 条流水与 40,000 票，但**从未入库**，存在 `docs/review/consolidated/G3/data/parallel_full/` 的 JSONL 里。若要恢复 ④⑪⑮ 等图，正确做法是写导入脚本把它灌进独立演示库并打 `is_synthetic` 标记，**不是重新造数据**。

**数据底座实测（同一次核对）**：门店 **7,704** 家、菜品 **6,560** 道（外食 120 / 下厨 6,440，其中 6,400 道标 `is_synthetic`）、用户 7 个、`tagging_status=SUCCESS` **6,560**（已全部打完）、缺 `allergen_tags` **843** 道。

**指标默认口径（v2.3.3；v2.3.4 增补双校区）**：C07 菜系构成按 `dishes_and_recipes` 行数；C12 按 `eating_logs` 决策量；C08/C15 热度=被选日志数+被投票次数，VETO 不计；C04 四档见第五章；所有图按 Asia/Shanghai 本地日期；筛选不适用统一 `200 applicable:false`；地图 PNG 导出在 S17 实现并实测。双校区：适用图增加 `campus`，`overview` 同时报 `by_campus` 与 `total`；C02 按校区分层；C05/C06/C09 为 `scope=GLOBAL`，campus 筛选返回 `applicable:false`；C10 全量 `restaurants+dishes`，HOME 无真实 rating 时 `rating=NULL` 不伪造，评分轴只绘非空点并报 `meta.not_plotted_no_rating`（整数）。

**交互硬约束**：顶部全局筛选器（模式 `mode_type`、菜系 `cuisine_type`）一处切换、全图联动刷新；点地图门店气泡或榜单行可下钻跳 `DataManage.vue` 对应明细；每张图标题写成问题式（如实验一标题「防腻衰减真的降低了重样率吗？」），图下给一句话结论，严禁只写「实验一结果图」式空标题。

**实现路线**：图表一律 ECharts 手写 option（对照官方示例 ID，见 `DASHBOARD_EXPANSION.md` §1.3）；版式与组件语言借鉴 GoView 组件清单与 DataV 边框/翻牌/轮播语言，**不引入 GoView/DataEase 等平台本体**（许可证与体积均不合适，DataV 主仓为 Vue 2、只借视觉语言）。地图层走**高德 JS API**（热力图插件 + 点聚合）；禁用百度地图系示例与插件。

**DataManage 数据质量面板（v2.3.1 新增；v2.3.7 增补）**：`DataManage.vue` 顶部增质量概览区——打标覆盖率（水球/环形）、缺失字段 Top 列表、向量异常计数，数据来自 `GET /admin/stats/quality`；定位为「数据真实性证据」，与原 CRUD 表格同页。

**v2.3.7 增补：两个标签维度必须分开**。`tagging_status`（PENDING/SUCCESS/FAILED，指八维向量是否打标成功）与 `allergen_tags`（过敏原标签是否有值）是**不同维度**：S11 已把 6,560 道全部打完（`tagging_status` 无 PENDING），但仍有 **843 道**缺 `allergen_tags`。因此：
- 列表筛选新增独立取值「待补标签（缺过敏原）」，映射到后端 `needs_tag=1`，**不篡改 `tagging_status` 语义**；
- `needs_tag` 判定必须同时覆盖 `NULL` 与空数组 `[]` 两种存法（只判 `NULL` 会漏掉约三分之二）；PG 的 `json` 类型没有 `=` 运算符，须转文本比较；
- 卡片状态带按「缺过敏原 → 琥珀 / 完全合格 → 绿 / 打标失败 → 红」三色区分，缺失维度在状态带右侧**指名道姓**（「缺 油 烫」而非「缺 2 维」）。

---

## 七、 万级数据工程与仿真实验规范（支撑论文第五章）

1. **双校区真实周边门店 + 合成食堂/菜谱底座 (`fetch_amap_poi.py` & `import_open_recipes.py`)**：
* **校区 A（思源）**：西安思源学院主校区，高德地名搜索实际返回 GCJ-02 `109.078487,34.234818`（2026-10-25T00:24:28+08:00）；固定 3km。S09/r02 实测直接 count=600、网格去重后 **605** 个真实餐饮 POI（另 2 个非餐饮剔除）；原目标约 1500+ 未达成，**D03 已裁决接受实际 605 为样本 A**，不得合成补足或跨校区挪用。
* **校区 B（建大雁塔）**：西安建筑科技大学雁塔校区；高德地名搜索实际返回 GCJ-02 `108.967153,34.236991`（碑林区，雁塔校区，未返回草堂）；固定 3km；实测真实餐饮 POI **6,659**（递归网格、0 未完成），合成食堂 200 单列，合计 **6,859**；目标 1500+ 已满足。
* **分校区存储**：`restaurants.campus`（`SIYUAN`/`JIANDA_YANTA`）分开存真实 POI 与合成食堂；两校区真实 POI 与合成食堂均分列，不得混用、不得相加后冒充某一校区。
* **合成食堂**：每个校区单独生成 200 个目标（思源 200、建大 200，`source_type=CANTEEN`、`is_synthetic=1`、`source_dataset=synthetic_canteen_v1`），不计入真实 POI；实数后按校区逐个替换，不足 200 按实际数记，不硬凑。思源真实 605 + 思源合成 200 = **805**；建大真实 6,659 + 建大合成 200 = **6,859**；不是 1,700。`1700` 只是原规格总数目标，不是实际数。
* **合成菜谱**：导入/生成约 6,300 ~ 8,000 行**共享合成菜谱**，`is_synthetic=1`、`source_dataset=synthetic_recipe_v1`；两校区共享下厨菜谱，不按校区复制；菜谱实体数按行统计，同时单独报告唯一菜名数，不得用重复行凑规模。
* **图片**：菜品图片仅用于本地毕业设计演示，不进入公开发布、APK 公开分发或论文公开素材；来源台账保留并标注“演示示意图”；不得声称已获公开再分发授权。


2. **国产大模型批量特征蒸馏 (`llm_batch_tagger.py`)**：
* 异步批处理脚本每次打包 20 道菜品调用国产大模型 API，自动输出 `dish_role`、8 维 `feature_vector` 与 `allergen_tags`；**特征值总量 = 成功打标菜品数 × 8**。
* 不再固定声称 **60,000+**；若要对外写 60,000+，成功打标菜品数必须 ≥7,500。失败/未完成记录保留 `tagging_status=FAILED`、`tagging_error`、`llm_meta`，不得用默认向量或重复计数凑数。目标菜谱 6,300 行全部成功也只有 50,400 个特征值，必须如实披露。


3. **多智能体仿真实验生成器 (`simulate_personas.py`)**：
* 构建 **200 个不同口味人设的虚拟大学生**，按 **每人每天 2 餐（午餐 + 晚餐）** 模拟连续 **60 天饮食打卡流水（200 × 60 × 2 = 24,000+ 条）** 与 **1,000 场四人寝室拼单投票（1,000 × 4 人 × 10 张卡 = 40,000+ 条）**。论文第五章引用数据规模时必须带上“每人每天 2 餐”口径，严禁只写人数天数。
* **仿真数据写入独立统计库**，不写入演示库；stats/大屏明确指向该统计库。演示库保持 4 角色/20 门店/100 菜/9 演示日志、`group_rooms=0`、`room_votes=0`。
* **双校区仿真**：每个 `group_rooms` 必须带 `campus`；外食推荐/群组按校区过滤，跨校区不得拼桌。建大未确认前只跑思源；建大接入后按校区分别跑或按 S12 开工卡明确的分配执行，不得把两校区混成一个房间/一条曲线。C05/C06 为全局固定实验图，campus 筛选返回 `applicable:false`、`scope=GLOBAL`。
* 自动计算并向 `algo_configs.benchmark_json` 写入两组核心实验数据（供 PC 后台与论文第五章直接出图）：
* **实验一**：本系统艾宾浩斯衰减 (`λ=0.5`) vs 无衰减传统推荐的 **连续 14 天菜系重样率对比曲线**；重复率定义=“相邻餐次同菜系次数 / 累计餐次”，第一餐计入分母但不算重复。
* **实验二**：本系统混合博弈策略 (`ω=0.5`) vs 随机抽签 vs 纯均值策略 (`ω=1.0`) 的 **群组平均满意度与最挑剔成员最低满意度（Least Misery Score）柱状对比图**；random baseline 固定 R=30，保存种子、均值与区间信息。

4. **统计与实验默认口径（v2.3.3）**：
* 不可适用筛选统一 `200 {applicable:false, reason, items:[], meta:{}}`；不得静默返回全量冒充联动。
* 星期×时段 7×4：早餐 [05,10)、午餐 [10,15)、晚餐 [15,21)、夜宵 [21,05)，weekday 0=周一；按 Asia/Shanghai 本地日期、默认全库范围。
* 共现图：无序主辅料对，次数≥3 入图，`top_n=30`、上限 100，过滤盐/水/油/葱/姜/蒜等通用项。
* C07 菜系构成按 `dishes_and_recipes` 行数；C12 按 `eating_logs` 决策量；C08/C15 热度=被选日志数+被投票数，VETO 不计热门；口径全局一致。
* `overview` 必须返回 `meta.scope`，明确 mode 过滤对哪些计数生效；`distance_meters` 为直线距离（保留旧字段名，但明确不是步行距离）。
* 地图 PNG 导出在 S17 实现并实测；S09 不偷渡实现。





---

## 八、 分阶段 AI 指挥开发路线图（5 批次执行，批次 5 为 v2.3 新增）

* **批次 1（后端数据库与算法内核）**：生成 `database.py`、`models.py`（当时 9 张表；v2.3.7 已增至 15 张）、`algorithms/` 四大算法模块，以及内置 100 道真实菜品+门店+4个演示角色的种子脚本 `init_seed_data.py`，通过 FastAPI `/docs` 验证推荐与博弈计算输出。
* **批次 2（移动端单人双模式闭环 + 用户主页 + 算法沙盒抽屉）**：搭建 Vue 3 + Tailwind 工程，实现 `Home.vue`（天气胶囊、双模式切换、情绪气泡、五维雷达图）、`Footprint.vue`（打卡与防腻看板）、`Profile.vue`（角色切换、忌口与红黑榜）及 `AlgoSandboxDrawer.vue`。
* **批次 3（虚拟冰箱 + 多人 WebSocket 干饭房间）**：实现 `Fridge.vue`（余料反推与买菜清单合并）及 `Room.vue`（扫码进房、15秒探探划卡组件与礼花揭晓大屏）。
* **批次 4（万级数据扩充 + PC 管理后台实验大屏 + APK 打包）**：运行高德采集、LLM 批量打标与 200 虚拟人仿真脚本，生成 PC 端 `DataManage.vue` 与 `ExperimentDashboard.vue`，最后通过 Capacitor/HBuilderX 一键打包输出 Android APK。**（v2.3.1 扩容）**：本批次另含——第五章模块 8 的 `/admin/stats/*` 统计接口组（13 个，含 quality）、`ExperimentDashboard.vue` 图表与联动/下钻/导出功能（原定 17 项，v2.3.7 收敛为 13 项，清单与版式见第六章 §5）、`DataManage.vue` 数据质量面板；大屏部分工作量显著大于原口径，须在 BATCH4_PLAN 中单独拆步，不得与数据扩充挤在同一步验收。
* **批次 5（网页展示版 + 移动端真机录屏，v2.3 新增，收尾批次）**：**前置条件：批次 1–4 全部完成、功能冻结后才开工，严禁提前或双线维护。** 在同一 Vue 工程内新增桌面壳路由（如 `/showcase/*`，顶部/侧边导航 + 内容区），聚合移动端全部页面与 PC 后台全部页面供答辩投屏展示：多数移动页面在内容区限宽居中原样呈现，仅首页、共识揭晓、实验大屏做横屏扩展；严禁另起工程复制代码、严禁逐页重排桌面布局。同步录制一份移动端真机使用视频（建房 → 划卡 → 揭晓完整流程）作为移动端效果的答辩交代与兜底。桌面端定位至此定案：**管理后台 + 网页展示版**，不做独立桌面用户端；论文中展示版表述为「答辩演示聚合端」，不得虚构为第三个产品端。实施护栏详见 `MOBILE_VISUAL_SPEC.md` §5.4。

**批次进度快照（2026-10-31 核实，开发方自测，未经独立审查）**：

| 批次 | 状态 | 事实依据 |
|---|---|---|
| 1 后端与算法内核 | **已实现** | 四大算法模块 + 15 张表 + 种子脚本；`pytest -q` 430 passed / 1 skipped |
| 2 移动端单人闭环 | **已实现** | 首页 / 足迹 / 我的 / 冰箱 / 房间五页；打卡结果面板、足迹评价、资料编辑、头像上传已接 |
| 3 冰箱 + 多人房间 | **已实现** | REST + WebSocket、15 秒截止与幂等结算；S06/r02 已获独立 PASS |
| 4 数据扩充 + 后台 + APK | **功能已实现，数据未扩容** | `/admin` 六页（数据管理 / 实验大屏 / 用户 / 参数 / 导入 / 审计）与 13 个 stats 接口已上线；大屏收敛为三主题；`frontend/android/app/build/outputs/apk/debug/app-debug.apk` 已产出（debug）。**万级行为数据未入库**，主库流水仅 9 条 |
| 5 展示壳 + 录屏 | **未开工** | 需批次 1–4 冻结后启动 |

**本快照不构成验收结论**：正式 PASS 仍由统一独立审查出具，见 `docs/review/STAGE_STATUS.md`。

---

## 附录 A、 项目背景、立意与交付形态选型理由（v2.1 新增）

### A.1 项目背景与核心痛点

* **选题来源**：源于日常生活里每天反复出现的真实提问——“中午吃什么”。该问题频率高、共鸣强，且长期无好的数字化解法。
* **深层立意（论文绪论可用）**：困境的本质不是没有选择，而是**选择过载 (Choice Overload)**——周边数千家门店、上万道菜谱同时涌向决策者，叠加预算、天气、身体状态、近期重复、他人忌口等多重隐性约束，导致决策成本极高；多人场景下个体偏好冲突进一步放大为“随便”式决策死锁。本系统要解决的不是“随机选一道菜”，而是**在多维约束下做可解释的智能决策**。
* **与同类简单方案的区别**：随机大转盘无约束、无记忆；普通菜谱应用只有 CRUD，无上下文感知、无防腻、无群组博弈。本系统的差异化即第二至四章的算法引擎。

### A.2 交付形态选型：移动端响应式 Web (H5) + Android APK，不做微信小程序

| 方案 | 结论 | 理由 |
| --- | --- | --- |
| 微信小程序 | ❌ 不采用 | 需 30 元认证费、企业/个体资质与 ICP 备案（周期约半个月至一个月）、平台审核约束多，与毕设周期不匹配 |
| 独立原生 App | ❌ 不采用 | 开发成本高，AI 辅助生成成功率低 |
| **响应式 Web (H5) + Capacitor/HBuilderX 套壳 APK** | ✅ 采用 | AI 写 Web 代码成功率最高、调试最快；H5 扫码即用便于答辩演示；套壳打包零成本生成 APK 便于分发；避开备案与审核 |

---

## 附录 B、 双模型协作开发流程（v2.1 新增）

开发分工锁定为“**强模型 = 总指挥/架构师/审查者，国产模型 = 主力施工者**”，严禁颠倒或混用：

1. **强模型定契约（只出图纸，不写大段业务代码）**：输出目录结构、数据库表设计、API Schema、算法数学伪代码；一切以本文档为准，本文档未定义的命名先回本文档增补再开发。
2. **强模型拆原子级施工单**：把每个模块拆成单文件、单功能的提示词交给国产模型执行，施工单必须写明输入/输出格式、类型注解要求与边界条件（参考口径：“实现 `recommender.py` 的某函数，包含完整类型注解和内置模拟数据”）。
3. **国产模型流水线施工**：在契约锁死的前提下逐文件生成代码，一次通过率目标 90% 以上；不得让国产模型自行改表名、字段名、接口路径。
4. **强模型 Code Review 与疑难排错**：每批次产物必须回强模型审查后才放行下一批次；WebSocket 并发、博弈算法等难点直接由强模型处理。
5. **上下文防丢失纪律**：新开任何 AI 会话，第一件事投喂本文档 (MASTER_SPEC) 再下施工单；文档与代码冲突时以文档为准，先改文档再改代码。

---

## 附录 C、 LLM 批量打标提示词契约（v2.1 补全）

`llm_batch_tagger.py` 每次打包 20 道菜品调用国产大模型 API，System Prompt 锁定如下，后续开发不得自行改写核心约束（输出字段与取值范围）：

```text
你是一个中式餐饮营养学与风味特征工程专家。请根据输入的菜品名称、分类与主辅料，为每道菜评估 8 个维度的标准化特征分值，并判断其套餐搭配角色。
8 个维度键名固定为：spicy_level, oily_level, soup_level, temp_fit, satiety_level, prep_speed, social_fit, comfort_level，取值范围严格在 0.0 到 1.0 之间的小数。
套餐搭配角色 dish_role 只能从 MEAT / VEG / SOUP / ONE_MEAL 中选一。
同时识别并输出该菜品命中的常见过敏原/忌口标签数组 allergen_tags（如：香菜、海鲜、花生、葱姜蒜）。
只输出 JSON 数组，不要输出任何解释文字；数组元素字段固定为：dish_name, dish_role, feature_vector{8个键}, allergen_tags[]。
```

* 输入格式：JSON 数组，每元素含 `name`、`cuisine_type`、`ingredients_main`、`ingredients_aux`。
* 入库校验：返回 JSON 解析失败、键名缺失或数值越界的批次整批重试，最多 3 次，仍失败则记录到失败清单人工处理，严禁用默认值蒙混入库。

---

## 附录 D、 论文章节与答辩亮点映射（v2.1 新增）

| 论文/答辩环节 | 对应本系统内容 |
| --- | --- |
| 绪论/研究背景 | 附录 A：选择过载、多人决策死锁、清库存痛点 |
| 需求分析 | 第一、二章的双模式场景 + “5+2”功能模块全景 |
| 系统设计 | 第一章目录契约、第三章 **15 张表**、第五章接口与 WebSocket 协议（含账号/令牌体系） |
| 核心算法（创新点） | 第四章四大算法：防腻时间衰减、多维上下文效用、Least Misery 群组博弈、组合优化 |
| 实验与结果分析（第五章） | 第七章仿真数据：14 天菜系重样率对比曲线、群组满意度与 Least Misery Score 对比 |
| 答辩演示亮点 | ①算法沙盒抽屉实时调参看排名变化（**v2.3.7 起参数落库并热加载，可现场改 λ/ω 立即生效**） ②多人房间 15 秒划卡 + 共识揭晓 ③登录页快捷账号一键填充（登录后锁定身份） ④八维向量翻译成人话的推荐解释 ⑤（v2.3）网页展示版聚合全部功能投屏演示 + 移动端真机录屏交代移动端效果 ⑥（v2.3.1）实验大屏真实数据可视化；**v2.3.7 收敛为三主题抽屉式**（数据不足的图不上屏） ⑦（v2.3.7）完整行为闭环：推荐 → 打卡 → 结果面板 → 足迹评价 → 用户画像，后台可看单用户偏好与满意度 |
| **待补的证据链（v2.3.7 记录，尚未完成）** | 现有实验只证明「算法 A 优于算法 B」，**未证明「用了系统比不用更好」**。答辩若被问「推荐有没有用」，目前只能答算法内部对比。补强方向：①决策效率对照实验（决策耗时 / 切换次数 / 预算超标率 / 后悔率，真人或反事实模拟）②个性化在线学习（采纳信号回写 `base_vector`，给出「准确率随使用次数上升」曲线）③可独立交付的数据集与消融报告。详见 `docs/AGENT_MEMORY.md` §55。 |
| 开题报告核心亮点口径 | 多维上下文感知（非随机抽签）、群组偏好博弈（非简单均值）、万级多源数据工程（非手工造数）、双模型 AI 协作开发流程（方法论创新） |
