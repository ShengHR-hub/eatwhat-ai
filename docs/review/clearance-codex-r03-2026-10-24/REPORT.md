# 清账 r03 独立复审报告

审查日期：2026-10-24（Asia/Shanghai）｜审查方：Codex

## 1. 结论与权限

**PC01 / R02：FAIL；PC02 / R01：维持 PASS；PC03 / F12：FAIL。S09 与批次 4 继续 LOCKED，未授予 `/admin` 开工许可。**

本轮独立读取源码、校验 manifest、实际运行两组完整规模仿真、只读复算存档数据库、执行隔离库真实播种反例、颜色正反例、pytest/build，并进行了真实浏览器点击。没有修改业务源码、主题或生产/演示库。此前 r01/r02 报告及开发方 r03 证据均保留。

| 返工项 | 结论 | 独立结果 |
| --- | --- | --- |
| R2-01 播种前快照守卫 | **FAIL** | 普通旧快照能挡住，但非法时间、带时区的旧时间、非法曲线仍能清库；拒绝刷新时还可能已改快照 |
| R2-02 四人成员满意度 | **FAIL（部分修复）** | VETO 的 0 分已计入，逐人复算一致；另有逐人封顶口径变化、固定样本与归因说明错误，须闭环 |
| R2-03 主规模 40,000 票 | **PASS** | 两 seed 均 1,000 房、每房 40 张唯一合法票；缺席实验独立 |
| R2-04 颜色门禁漏检 | **FAIL** | 旧反例已修复，但合法 JS 正则与 CSS URL 可再次隐藏同行裸色 |
| R2-05 非出口文件自造裸色令牌 | **PASS** | 组件本地 `--local-red:#f00` 被拦，合法变量别名放行；精确上游文件豁免成立 |

## 2. 受审版本与证据位置

- PC01 r03 SOURCE_MANIFEST：SHA256 `6a4e27f582c4378bf7447403395571b758240e6326547fe12843039bc5e978ac`。
- PC03 r03 SOURCE_MANIFEST：SHA256 `73fceda9e24fcd1ba5ed23cc82bb6ffa690994d20e69a4359f2a2ac4a0d199d6`。
- 入场时 13 项 manifest 文件校验全部匹配，详见 [baseline.json](baseline.json)。
- 记忆账本受审原文另存 [AGENT_MEMORY-before-review.md](AGENT_MEMORY-before-review.md)，台账原文另存 [STAGE_STATUS-before-review.md](STAGE_STATUS-before-review.md)。审查方后续追加结论不改变受审业务版本，也不反写 manifest。
- 本轮证据统一保存在本报告目录。业务源码完整性及演示库保护见 [final-protection.json](final-protection.json)。
- 审查交付自校验见 [review-validation.json](review-validation.json)，文件身份与大小见 [evidence-index.json](evidence-index.json)；验证脚本仅校验证据，不代表项目缺陷已经修复。

## 3. R3-01 / P2：播种守卫仍可放行非法或更旧的数据

源码位置：`backend/scripts/init_seed_data.py:284–316`、`:356`、`:363–380`；实际入口守卫位于 `:603`，清库在其后。

已修复的部分：模块导入不再读快照，普通无时区旧快照、缺失快照、曲线长度不足均在清库前失败；正常新快照重复运行成功。因此不能说“完全没做守卫”。

剩余根因：`generated_at` 只检查非空，比较使用 `str(...)`；sample 仅检查字段存在，curve 仅检查长度；刷新目标快照发生在与数据库比较之前。`validate_benchmark` 注释声称检查数值范围，但曲线与 sample 实际没有相应校验。

独立执行真实 `seed.main()` CLI；只把数据库和快照路径导向证据目录中的副本，不替换守卫/清库/播种函数。每例保留运行前后逻辑摘要、快照及输出：[seed-results.json](seed-results.json)、[seed_probe.py](seed_probe.py)、[seed_cli_wrapper.py](seed_cli_wrapper.py)。

| 反例 | 实际结果 | 应有结果 |
| --- | --- | --- |
| `generated_at="zz-not-a-date"` | exit 0，原数据库被清理并重新播种 | 解析失败，DB 与快照均不变 |
| DB `2026-10-24T16:00:00+00:00`；快照 `2026-10-24T23:00:00+08:00` | 快照实际为 15:00 UTC，比 DB 旧一小时，却 exit 0 并重新播种 | 归一化时区比较后拒绝 |
| personas=0、rooms=-1；days=`[14]*14`；ours=`["NOT_A_NUMBER"]*14` | exit 0，非法曲线写入播种结果 | 类型、规模、日序与范围验证失败，保留原数据 |
| 目标快照 00:00、incoming 12:00、DB 20:00 | exit 1、DB 保留，但目标快照已变成 12:00 | 被拒绝的刷新不应先覆盖快照 |

另有工作流缺口：把正常仿真输出（四键 + `params`）原样交给 `--benchmark-from` 会因“必须恰好四键”失败。SSOT 入库四键约束应保持，但 CLI 须提供明确、可执行的提取/导入流程，而不是让使用者猜测。

下一轮验收：

1. 真正解析时间，明确无时区时间的解释，统一到可比较的时间基准；非法时间必须拒绝，不能靠字典序。
2. 校验 JSON 对象、数值类型/有限性/范围、正整数样本规模、14 天正确序列、策略身份与序列长度；拒绝 bool 冒充整数及非法数值。依据现有 SSOT 固定契约，不擅自扩大数据格式。
3. 与当前快照及库内时间的所有检查完成后，再执行持久化/清库；拒绝路径同时保证数据库与快照未变化。
4. 加入上述真实 CLI 反例及正常刷新、重复运行正例；保留前后摘要。`--allow-stale-benchmark` 是显式例外，不能使普通路径或结构校验失效。
5. 证明完整仿真输出经文档化流程可进入四键快照，再经守卫播种；审查只在隔离副本运行。

## 4. R2-02 修复事实及 R3-03 / P2：指标解释尚未闭环

`backend/algorithms/simulate_personas.py:350–375` 现在遍历全体成员，VETO 的 0 分确实进入平均值和最小值。独立参考计算从库内原始向量重算 prior、按票型重算 `0.4*prior+0.6*swipe`，不调用被测 helper；两 seed 主实验及缺席实验均无成员分数或胜出菜差异。该根因修复成立。

但是 `:368` 同时把**每个成员**先 `min(100, satisfaction)` 再取均值。r02 是聚合后展示封顶，这两种运算不可交换。SSOT 的个体 R 公式见 `MASTER_SPEC.md:276`；总分展示封顶文字见 `:267`，不能自动推导“个体 R 在实验统计前封顶”。r03 的 method_notes 虽已写出逐人封顶，提交和账本仍把差异解释成只换票数据，当前证据说明存在实质矛盾。

固定样本 `[0,67.58,97.82,107.70]`：未逐人封顶的四人均值 **68.275**、最低 **0**；当前 r03 helper 实测 **66.35 / 0**，不是自报 **68.28 / 0**。五类测试有独立计算，但采用的也是新逐人封顶定义，不能证明统计口径未变。

提交与 `docs/AGENT_MEMORY.md §19.5` 还把 r03 **mixed 92.0 / 75.37** 与 r02 修正后的 **random 73.43 / 40.37** 比较。这是不同策略，不能用于解释修复前后差异。

同策略、同数据的独立拆分如下，详见 [data-results.json](data-results.json)：

| 数据与统计定义 | random 平均 / 最低 | mixed 平均 / 最低 |
| --- | --- | --- |
| r02 原票，VETO=0，聚合后封顶 | 73.43 / 40.37 | 93.81 / 74.68 |
| r02 原票，VETO=0，逐人封顶 | 72.08 / 40.37 | 91.58 / 74.68 |
| r03 满票，VETO=0，逐人封顶 | 71.39 / 38.82 | 92.00 / 75.37 |
| r03 满票，VETO=0，聚合后封顶 | 72.83 / 38.82 | 94.23 / 75.37 |

VETO 概率仍为 0.5，4,093 vs 3,820 是实际数量变化，不等于参数概率提高。取消缺席抽样也改变后续 RNG 消费，不能把所有数值变化都归因于补齐缺席票；mixed 在相同新口径下反而上升，不能写“两项都让满意度下移”。

下一轮验收：保留 VETO=0，明确原始 R 与展示统计的边界，对逐人封顶这一额外变化与 SSOT 完成对齐；若决定保留新指标，须明确记录其定义及口径变化，不能继续声称统计未变。用包含 R>100 的固定样本锁定定义，修正同策略对照、固定样本结果、提交和账本说明。此项不是“VETO 仍被排除”，也不要求为追求高分而改生产公式。

## 5. 仿真规模、调用、对照及证据完整性

实际重新运行：默认 seed=20261024、λ=0.5、ω=0.5；第二组 seed=7、λ=0.8、ω=0.6。两组都是 200 人 ×60 天 ×2 餐 ×2 arms +1,000 主房 +200 缺席房，全部从新的输出目录起跑，未覆盖开发方数据。

| 每组独立插桩的实际函数调用 | 次数 |
| --- | --- |
| recommend_single | 48,000 |
| compute_decay_weights | 48,000 |
| shortlist_candidates | 1,200 |
| member_prior_scores（含共识内部调用） | 3,600 |
| compute_group_consensus | 2,400 |

不同层级调用不应混加成一个含义不明的“算法次数”。存档 `params.calls` 的 member_prior_scores 是仿真外层调用 1,200，独立统计 3,600 含内部调用，两者作用域不同。

两组 sample、14 点曲线、三策略柱值、主群组摘要与缺席摘要全部与存档一致；每组 1,200 对 mixed/average 的成员/卡片/票矩阵输入 SHA 完全一致，random 从同房卡片抽签，用同份成员和票矩阵统计。证据：[simulation-verification.json](simulation-verification.json)、[seed7-verification.json](seed7-verification.json)，完整执行输出为 [simulation.log](simulation.log)、[seed7.log](seed7.log)。

主规模两 seed 均 1,000 房 /40,000 票 /每房 40 个唯一 `(user_id,dish_id)`，成员 4 人、菜卡 10 张，非法房间 0。默认 SUPER_LIKE=8,000、LIKE=12,000、PASS=15,907、VETO=4,093。缺席另库、200 房（默认 7,614 票；seed7 7,597 票），仅进入 `params.absence`。演示库仍 group_rooms=0 / room_votes=0。

冷启动基线是同一生产算法用错开 15 天的查询时钟消除近 14 天历史，属于**衰减机制消融**，并非独立竞品或全部情境下的性能基线；环境与随机输入应保持配对，结论仅限该仿真。横向 rank 票型能避免人人对高 prior 候选全投高分的天花板，但仍是人为设定、依赖 prior 的偏好模型，不能称真实用户实验，也不能把很小的 mixed/average 差距声称为统计显著优势。r02 关于这两个限定的意见继续有效；当前没有发现三策略偷换房间或票矩阵。

默认 d14=0.0091、base=0.2927 已复现；这不是 r03 再次下降，r02 已有同值。首轮 0.1696 来自不同的旧仿真实现/口径，不能拿来作只改某一参数的效果比较。

**原 stdout 缺口的处置**：开发方 `PC01/r03/logs/01_simulate_seed20261024.log` 确为空，缺口如实保留；本轮完整独立重跑提供了新的执行日志。归档 48,000 行明细与独立生成文件 SHA256 都为 `993976dbc8b5132dbef53c9518625a298cd2dba056678acffc114828a52ccf24`，逐点曲线一致。因此不能仅凭空日志判定数据无效。

**仍应修正证据身份**：`docs/review/simulation/sim_seed20261024_ours.db` 当前只有 8,000 日志 /20 天，baseline 与 seed7 原库完整；它不能继续被标成此次完整 60 天来源。恢复的归档明细是真实完整文件，但没有使那个源 DB 自动恢复。本轮新 `simulation-default/` 两臂各 24,000 日志 /60 天完整保留。下一包列清每个 DB 的行数/日数/哈希，把截断旧库标为废弃证据，不覆盖历史包；可引用此次独立证据，不要求仅为补旧 stdout 无意义重跑。

## 6. R3-02 / P2：词法门禁仍有合法语法漏检

源码：`scripts/check-colors.mjs:52–89`，尤其 `:81–84`。所有语言共用的注释状态机未识别 JS 正则字面量和 CSS 非引号 URL，导致真正的业务声明被当作注释擦除。

独立探针不是插入业务目录：在证据目录的 sandbox 复制 checker，明确指定 sandbox cwd，执行退出码断言。22 例中 19 符合预期，2 个漏检、1 个误报：[color-results.json](color-results.json)、[color_audit.mjs](color_audit.mjs)。

```js
const pattern = /[/*]/; const color = "#ff0000";
```

合法 JS，Node vm 实际执行得到 `color="#ff0000"`；checker 却 exit 0，因为 `/[/*]/` 中的 `/*` 被当成块注释起点，后续裸色消失。

```css
.x{background-image:url(https://example.com//a.png);color:#ff0000;}
```

合法 CSS，PostCSS 解析出 `background-image` 和 `color` 两个声明；checker exit 0，URL 后段 `//` 被当作行注释，同行 color 被吞掉。URL 仅作语法字符串，未访问该远端地址。独立语法证明：[syntax-results.json](syntax-results.json)。

较低优先级误报（P3）：Vue `<template><!-- color:#ff0000 --><p>ok</p></template>` 是注释，仍 exit 1。应在修复时一并增加正例。

下一轮验收：对 JS/Vue script 的正则与字符串、CSS 的 URL/字符串/块注释、Vue template 注释作语言正确处理，或采用已有解析器。新增以上两个漏检反例和 HTML 注释正例，保留原有通配、注释后同行代码、令牌后同行代码、本地裸色令牌、RGB/HSLA 大小写、三种扩展名及 bits 非上游文件覆盖。裸色必须 exit 1 并定位，合法令牌/别名/注释必须 exit 0，不扩大白名单。

已通过的视觉清理事实：当前真实目录扫描 38 文件 exit 0；独立实际业务 CSS/Vue 声明扫描裸色 0；原报告 10 处均已使用令牌，5 个玻璃 RGB 通道与原数值一致。不能把“脚本有漏检”写成“现有页面已经发现裸色”。

## 7. 回归、真实浏览器与边界

| 独立验证 | 结果 |
| --- | --- |
| 后端完整 pytest（工作区 basetemp/cache） | **140 passed，505 warnings，6.78s** |
| R01 定向 `tests/test_query_budget.py` | **6 passed，397 warnings，0.33s**；不存在的 DATABASE_URL 文件仍未生成 |
| 前端 `npm run build` | **775 modules，built in 7.04s，exit 0** |
| 真实目录 check-colors | **38 文件，exit 0**；与上面的反例缺陷并列记录 |
| 390×844 首页 | 卡高 422px /50%；scrollHeight=844；操作行 bottom784，Tab top792；6 个按钮/导航中心命中 |
| 390×667 首页 | 卡高 261px /39.13%；scrollHeight=667；操作行 bottom607，Tab top615；6 个按钮/导航中心命中 |
| 真实点击 | 足迹、我的两页面均能进入并显示真实隔离库数据；沙盒打开关闭，卸载后导航可用；下厨被选中并重新展示下厨菜 |

命令输出：[pytest-workspace-temp.log](pytest-workspace-temp.log)、[query-pytest.log](query-pytest.log)、[build.log](build.log)。首次默认 pytest 有 4 个 tmp_path PermissionError（其余 136 passed），是外部临时目录权限；未修改测试，以工作区临时目录重跑全过，原始失败 [pytest.log](pytest.log) 保留。现有 requests 依赖警告及 datetime.utcnow 弃用警告未隐去。

浏览器在用户明确补充余额后续测，使用独立数据库 `browser-isolated.sqlite`、前端 5183 /后端 8023。两档截图与 geometry、动作/DOM/控制台保存在 [browser/](browser/)。足迹与我的无法进入的问题在本次指定范围未复现。截图：[大屏](browser/home-390x844.jpg)、[小屏](browser/home-390x667.jpg)、[足迹](browser/footprint.jpg)、[我的](browser/profile.jpg)。浏览器截图接口实际返回JPEG，按原字节保存并使用.jpg扩展名；首页两张实际尺寸分别为390×844、390×667。

浏览器限制必须保留：两次 Input.dispatchMouseEvent 工具超时，但后续可见 DOM 分别确认已返回首页、已切到下厨，未当成产品失败或假称命令无异常。关闭沙盒后同调用的立即导航未确认生效，待卸载完成后真实点击并确认足迹正常。控制台本次读取无 warn/error；**CDP 网络事件缓冲已截断，不能据此宣称全程网络零异常**。后端独立 access log 中本次观测到的 21 条 API 响应均为 200；该证据不覆盖所有静态资源。[backend-browser.log](backend-browser.log)、[browser/events.json](browser/events.json)。

没有测试 `/admin`；没有执行完整多人多端 WS 流程、真机 APK、全部 S00–S08 专项。上述成功不等于这些阶段 PASS。临时 viewport 已 reset，自己的测试 tab 已关闭，自己的两个服务已停止。

PC02 共享推荐实现、时钟与 fixture 本轮未改；`_run_group_phase` 是离线实验调用签名变化，不是 R01 查询路径变化。保留 r02 已签 PASS，附本轮干净环境 6 tests；不重复声称本轮重新进行了 r02 的全部 40/400 API 对照。

## 8. 下一轮只准做什么

仅整改 PC01 的 R3-01、R3-03 与证据身份说明，以及 PC03 的 R3-02；新包建议 `PC01/r04/`、`PC03/r04/`，保留本轮历史，不自行签 PASS。提交前写明允许文件与后端改动原因，按范围重跑；新指标定义若影响曲线/柱值，相关实验与快照必须一起重验。

验收是逐项关闭本报告反例、验证无回退，再由 Codex 独立签发 PASS。**三项全 PASS 前，S09 /批次 4 不开放。**
