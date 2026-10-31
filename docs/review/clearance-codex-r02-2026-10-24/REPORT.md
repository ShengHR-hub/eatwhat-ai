# 清账第二轮 r02 独立复审报告

审查方：Codex。审查日期：2026-10-24（Asia/Shanghai），本轮取证始于18:02；最终归档时间见 `evidence-index.json`。

**结论：PC01 / R02 FAIL；PC02 / R01 PASS；PC03 / F12 FAIL。S09 与批次 4 主线继续 LOCKED，`/admin` 未操作。**

本报告是新一轮结论，不覆盖 `docs/review/clearance-codex-2026-10-24/REPORT.md` 或三份 r01 REVIEW。业务源码未修改；新增的是本目录审查脚本、隔离数据和报告，并更新审查台账/工程记忆。前端构建产生的 dist 属生成物。开发方自报只用作核验线索。

## 1. 依据、版本与数据保护

- 依据：`MASTER_SPEC.md` v2.3.2、`docs/REVIEW_RULES.md`、r01 独立审查报告、`D:/谷歌/BATCH4_REWORK_ROUND2.md`、本次用户明确的核验要求。根目录不存在同名返工指令，实际读取的是上述外部文件；文档内容作为审查依据，不额外授予改业务代码或放行权限。
- 当前三包 manifest 中的全部 15 条文件记录均与源码 SHA-256 相符。核验结果见 `baseline.json`；额外相关源码的审前摘要见 `source-before.json`。

| 受审包 | SOURCE_MANIFEST.json SHA-256 |
| --- | --- |
| PC01/r02 | `55d23a6d8b2af25b0566db1aab343a5da14d9d69a5a81acafe79ac174a5cae0d` |
| PC02/r02 | `671ccd00883179312f9e951b2ae815051288090d52ce920eb0fabdc43db5b5a2` |
| PC03/r02 | `e38cd93ebcecc699bbf5aa3fb6b4a4c84720e880deda348f2d3cda533f949113` |

演示库 `backend/eatwhat.db` 用 SQLite `mode=ro` 读取；在读事务中计算逻辑 dump SHA-256 和逐表行数，不使用仅主文件哈希代替逻辑状态。审前/后均为：

```text
logical_sha256 = 02ad8560b6268c22684cc4ec2cb08a4c8afdf504f3a58b22e395bdc5368b4d3f
journal_mode = delete
users=4, user_preferences=4, restaurants=20, dishes_and_recipes=100,
eating_logs=9, fridge_inventory=12, algo_configs=1, group_rooms=0, room_votes=0
```

`final-protection.json` 记录审查前已有源码内容无变化、演示库逻辑状态无变化。仿真、播种、真实 API、SQL 扩容、写回验证全部在本目录隔离库中进行；原提交数据库只读。未运行真实演示库的 `--force` 或 `--write`。

## 2. R02 / PC01：FAIL

### 2.1 独立核验结果

| 验收项 | 本轮实际方法及结果 | 判定 |
| --- | --- | --- |
| 生产函数实际调用 >0 | 完整独立跑默认 200 人×60 天×2 餐，两臂各 24,000 条；在真实函数入口计数，不采信脚本 CALLS 自报 | PASS |
| 默认曲线、柱图复现 | 新建 `simulation-default/` 重跑；sample、14 点双曲线、三策略柱图全部与提交一致 | PASS |
| 换种子/参数复跑 | seed=7、λ=.8：独立重跑每臂 200×14×2 餐和 1,000 房间；覆盖全部对外 14 点曲线/柱图，结果一致；提交库的 60 天日志另全部只读复算 | PASS（明示范围） |
| 三策略同场景 | 逐场捕获两次生产 consensus 的成员、卡、票矩阵哈希，1,000 对全部相等；random 在同一 cards 上用 `Random(seed+1)` 抽取、复用同一 report | PASS（输入配对） |
| 投票真实落库与规模 | 两个提交库均 1,000 房间、每房 4 个不同成员和 10 张不同卡，无越界或重复票；默认实际票 37,999，缺席 2,001 | 实际落库 PASS；40,000 条规模 FAIL，见 R2-03 |
| 演示库不被仿真污染 | 演示库 group_rooms=0、room_votes=0，审前后不变 | PASS |
| 存档→快照→库逐点一致 | 演示库 benchmark、快照与默认存档去 params 后四键完全相等；两 seed 原始吃饭日志重建曲线相等，生产重算所有 2,000 个提交房间 stored consensus 全相等 | PASS（存储一致性） |
| 真实写回函数 | 在独立空库调用 `write_benchmark()` 两次，仍仅 1 条配置，四键和独立生成 payload 完全一致 | PASS |
| `--force` 刷新快照的代码保障 | 完全相同 SHA 的播种脚本副本接受陈旧快照，且覆盖隔离库中的较新 benchmark | FAIL，见 R2-01 |
| 群组平均/最低满意度口径 | random 抽到被否决菜时，否决成员的 0 分没有进入其平均数/最低数 | FAIL，见 R2-02 |

真实入口计数如下（`simulation-verification.json`）：

| 函数 | 独立入口计数 |
| --- | ---: |
| recommend_single | 48,000 |
| compute_decay_weights | 48,000 |
| shortlist_candidates | 1,000 |
| member_prior_scores | 3,000 |
| compute_group_consensus | 2,000 |

脚本 params 仅统计外层 48,000+1,000+1,000+2,000，**合计 52,000，不是自报 51,000**。两次 consensus 内部各会调用 prior，故完整入口 prior=3,000；单人内部 decay=48,000。完整表累计 102,000 是不同层级函数入口之和，不能当作 102,000 次独立推荐。这个计数说明错误是非阻断文档项，本轮“生产调用为 0”的旧问题已关闭。

### 2.2 R2-01 / P2：强制播种仍可静默回退到旧快照

**位置**：`backend/scripts/init_seed_data.py:249–268, 469–471`；快照在模块导入时读取到 `BENCHMARK_JSON`，`main()` 的 `--force` 分支直接清表后 `seed_all()`，没有刷新/验证上游结果步骤。

独立复现使用与源码 SHA-256 完全相同的脚本副本和独立快照/数据库：

1. 快照写入 `generated_at=STALE_REVIEW_SENTINEL`、d14=.1234。
2. 先在隔离库写入 `NEWER_GOOD_REVIEW_SENTINEL`、d14=.0091。
3. 对副本实际执行 `python init_seed_data.py --force`，exit 0。
4. 库中较新 benchmark 被替换为 `STALE_REVIEW_SENTINEL`、d14=.1234。没有报错或重新生成。

**判断**：当前快照内容确实正确，但“先手工刷新再播种”的纪律没有锁进代码。下次操作仍能覆盖正确结果。证据：`seed-guard-results.json`、`write-check-results.json`、`seed-guard-cli.log`。

**下一轮验收**：在任何清库之前，由受控入口完成刷新和来源/参数/数据身份校验，再在播种时读取本次结果，不能继续依赖模块级旧值；刷新失败必须在破坏旧数据前中止。至少交“陈旧快照＋较新库”、“缺快照”、“刷新失败”、“连续执行”四类隔离反例，证明无法静默回退。本项修改前按项目规则说明后端改动范围；本次审查未替开发方实现。

### 2.3 R2-02 / P1：随机策略删掉了最不满意成员，群组柱图指标失真

**位置**：`backend/algorithms/simulate_personas.py:347–361, 487–495`；来源契约在 `backend/algorithms/group_recommender.py:178–200`。

生产共识函数对 VETO 成员在 `members` 中记录 satisfaction=0，但不将其加入 `satisfaction_values`，随后把该菜 `group_score` 置 0 并移出可胜出集合。对生产 winner，这个内部行为不会让被否决菜胜出。

仿真 random 却从**所有** card_ids 抽一张，随后把该报告内部的 `mean_satisfaction/least_misery` 直接当作全组四人的平均/最低满意度。被否决者恰恰在这些字段的聚合样本之外。

可直接定位默认房间 `000001`，random 抽 dish 52：四人分数为 `[0, 67.58, 97.82, 107.70]`；报告拿到 **mean=91.03、least=67.58**，全四人的均值应约 68.275、最低值 **0**。这不是封顶或四舍五入造成的差异。

| seed | random 抽中被否决菜的房间 | 当前 random 均值/最低柱 | 纳入四人成员的 0 分后均值/最低柱 |
| --- | ---: | --- | --- |
| 20261024 | 331 / 1,000 | 81.13 / 61.76 | 73.43 / 40.37 |
| 7 | 326 / 1,000 | 80.36 / 60.99 | 72.86 / 40.30 |

右列是依据存档成员分数精度重建、沿用当前“聚合后封顶 100”的诊断值，不是审查方替项目批准的新实验数据。详见 `random-metric-results.json`（含具体房间、票型、分数）与 `random_metric.py`。

**判断**：三策略输入配对已修复，但“同一四人群体的满意度”仍没有统一。当前 mixed/average 的赢家无 VETO，random 中的被否决成员却被删掉，不能据此宣称实验二已验收。问题根源是仿真消费了只适合共识排序的内部聚合字段，而非要求审查时重写生产共识。

**下一轮验收**：冻结并说明三策略共同的指标定义与可行候选约束。若 random 仍允许抽到否决菜，必须在统一的四人成员集合上计平均/最低，0 分不能被排除；若把 random 限制到可行集合，须明确这是受相同否决约束的随机基线并重跑全部柱图。两种设计不能混写。加固定四人样本：无否决、单人否决、多人否决、全否决、缺席；由独立参考计算断言成员分母与最小值，提交新原始数据、报告、快照和库逐点一致证明。

### 2.4 R2-03 / P2：40,000 是计划票格数，实际投票数据仍不够规格规模

**位置**：`backend/algorithms/simulate_personas.py:422–425`（5% 超时直接 continue），对照 `MASTER_SPEC.md:17, 468` 的 1,000×4×10=40,000+ 条投票口径。

本轮确认 37,999 张票是真数据，没有造假、没有跨房间/成员/卡的坏票；其余 2,001 格由真实生产共识按缺席 TIMEOUT 处理。这是合法的超时场景，但 **40,000 次计划机会不等于已落库 40,000 条票**。seed7 实际 38,043 张，同样不足。提交材料已披露实际数，不能再把规模验收写为完成 40,000 张真实投票。

**下一轮验收**：保留本轮超时实验作为独立场景；主规模验收运行在 1,000 房×4 人×10 卡上完整生成 40,000 张合法枚举投票，并逐房验证 40 张、不重不漏。不要为了凑数往四枚举表塞伪 TIMEOUT、复制票或混入演示库。若希望将“计划机会含缺席”正式作为规模口径，必须先获用户批准并同步 SSOT；审查方本轮不自行降低要求。

### 2.5 对用户指定两处方法学问题的判断

**无衰减基线：当前代码范围内可接受，但名称应准确。**

审查在默认相同目录/人设上重建 16 个固定历史场景（第 1/7/14/60 天、四个用户、两模式），比较：①当前查询时钟+15 天；②原时点仅将衰减权重固定为 1 的独立控制。16 次**完整推荐响应全部相等**，不只 top3；当前 `now` 仅用于 decay 查询。故时钟偏移在现有实现中等价于禁用历史衰减，没有发现额外有利条件。它仍保留用户向量/预算，并非完整产品意义的“全新用户冷启动”；论文宜称“保持其余输入一致的无历史衰减基线”。以后若 now 参与天气、库存、预算或其它时效逻辑，必须重审这份等价性，不能沿用结论。证据：`baseline-controls.json`。

**排名票型：可以作为显式的合成行为假设，不能当作真人规律。**

按同一先验加噪声后排名、再映射固定票型，对三策略是同一份冻结票矩阵，因此这一改动本身不破坏策略输入公平性。相对选择也有合理用途。但“前两张一定爱爆、末两张各半否决”是作者设定，不是测得的用户行为；全体先验都很差或相等时仍强制产生爱爆，`baseline-controls.json` 附平坦先验探针。源码“真人一定如此”的表述没有证据。不能因为绝对阈值出现天花板、相对模型差距更明显，就把后者当作已证实更真实。论文须公开模型、噪声、超时与票型分布；S13 正式实验应补固定 seed 的票型/噪声敏感性，保留不显著或不利结果。本条是解释/外推限制，不单独作为本轮返工的 P1/P2。

**d14 从 .1696 变成 .0091：算得出来，不能称为同实验下算法提升。**

- 默认原始日志前 14 天共 5,600 餐：ours 重复 **51** 次，baseline **1,639** 次，按当前定义得到 .0091/.2927；两个库逐点与存档相等，独立完整重跑也相等。
- 这是“截至第 d 天累计的相邻餐次同菜系次数 / 累计餐次”，不是第 d 天的单日率，也不是 14 天内只要再吃过一次就算重复。每人第一餐也在分母内；按已定义的相邻转移作分母，d14 为 .0094/.3035。论文要写清统计定义，不能混用。
- 200 人的每餐模式被固定交替为外食/下厨；目录下厨 40 菜仅 3 类，其中家常菜 33 个，外食 60 菜有 15 类。生产算法按同菜系/共主料和同日历史衰减，再从 top10 以 `total_score^3` 加权抽取，确实会强烈回避上一餐相关菜系。默认 60 天 ours 的 OUT_DINING 餐次同菜系重复为 0，不能把本场景直接外推成真实学生 0.91% 的重复率。
- 首轮是已被退回的另一套简化模型，本轮替换为真实生产链，并改变了选择过程/统计上下文；.1696 与 .0091 不是同一受控实验的前后改进。群组 rank 票型在两臂完成后才运行、使用单独 RNG，**不是单人 d14 下降的原因**。

因此：新数值在这套明确的仿真假设下是真实可复现的；不因数值漂亮判造假，也不把旧模型与新模型差值当作系统提升证据。实验二仍须修复 R2-02。

## 3. R01 / PC02：PASS（绑定本次版本）

### 3.1 干净环境与实现约束

在启动 pytest 前设置 `DATABASE_URL` 指向本目录**不存在**的 `must-not-exist.sqlite`，实际运行 `python -m pytest tests/test_query_budget.py -q`：**6 passed**，退出 0；结束后该文件仍不存在。测试使用 fixture 内存数据库，不再读现有全局数据库。全量后端为 **131 passed**、退出 0。

源码比较还原结果见 `r01-source-control.json`：从当前 `single_recommender.py` 只移除本轮 R02 的 now 参数、导入、注释和透传后，CRLF 字节 SHA-256 **精确匹配 r01 的 `8d17bf949434bbc1fa7abb3bbb359050161dab761299f31aefadef52aa1f874f`**。说明原 N+1 优化实现未被本轮改写；时钟适配属于 R02。测量工具的 SHA 也与 r01 相同。

### 3.2 真对照与查询数量

测试对照不再只是同一函数调两次：存在独立逐菜库存参考实现；pipeline monkeypatch 在逐菜环节真实重新发库存 SELECT。**但 monkeypatch/CLI legacy 仍复用了批量评分算术且保留一次循环外预取，并非旧版源码的精确复刻。** 这不会使性能改善消失，但 37/32 不能标作真实旧版的精确查询计数。

本轮另外运行独立表达的逐菜参考，移除循环外预取，通过实际 FastAPI `POST /api/v1/recommend/single` 捕获整个请求 SQL，并真实扩增隔离目录至 400 道下厨菜，核对完整 JSON 响应相等（非仅 top3）。

| 下厨目录 | 模式 | CLI legacy 总/库存 SELECT | 独立逐菜 API 参考 总/库存 SELECT | 批量实现 总/库存 SELECT | 响应/条数 |
| --- | --- | --- | --- | --- | --- |
| 40 | HOME_COOKING | 37 / 32 | 36 / 31 | 6 / 1 | CLI top3/count 相同；API 全响应相同，31 条 |
| 400 | HOME_COOKING | 316 / 311 | 315 / 310 | 6 / 1 | CLI top3/count 相同；API 全响应相同，limit100 返回100条 |
| 40 / 400 | OUT_DINING | 6 / 0 | 6 / 0 | 6 / 0 | CLI top3/count、API 全响应相同，46条 |

总查询断言已为 `HOME_SQL_BUDGET=9`、库存 `FRIDGE_SQL_BUDGET=1`。独立 API 探针另外核验无主料、无匹配、普通库存、临期双倍、过期不计分的固定期望：0/0/33.33/66.67/0/100 均通过。

7 次交替调用的下厨中位耗时：40 菜逐菜 21.174ms → 批量 9.335ms；400 菜 150.546ms → 33.713ms。它们与后台仿真并行，属本机观察值，不宣称稳定性能 SLO。SQL 数和语义等价是本轮验收依据。

**非阻断维护项**：`test_recommend_query_budget_with_expanded_candidates` 只是提高 limit，没有向 fixture 增加到 400 道菜；本轮由独立真实扩容探针补验，正式 S11 应把真实扩容保留为自动化。独立库存参考使用列表而生产主料去重，重复主料的完整语义可在 S11 继续补测；本轮固定样本和既有目录结果不受影响。CLI legacy 额外一次预取及“旧版”命名应在材料中准确标注。

证据：`query-pytest.log`、`pytest.log`、`r01-results.json`、`cli-results.json`、`api_probe.py`、`controls.py`、逐次 `sql-*.json`。

**本项 PASS 不授予 S09/批次4许可，也不意味着所有移动端/多人专项通过。**

## 4. F12 / PC03：FAIL

### 4.1 已证实修复的部分

- 原报告点名的 **10 条业务 CSS 声明**逐项匹配；以 PostCSS 解析 `.css` 和 `.vue` style，排除自定义属性声明后，实际业务裸 hex/rgb/hsl **0 条**。
- 新增五个通道令牌真实为 fill `246 246 246`、shade `40 40 40`、highlight `230 230 230`、edge `208 208 208`、ring `232 232 232`。
- 对 10 条原始声明逐项解析 var，再把新旧 rgb/rgba 归一为通道+alpha 后比对，**10/10 数值完全一致**。WeatherPill 七层阴影、填充 alpha=.48、blur60px，磨砂卡三层阴影等未发现数值改变。这里只证明对应 CSS 数值，不冒称已做新一轮像素/浏览器回归。
- 原 checker 实际运行：**34 文件、exit 0**；扩展名含 `.vue/.js/.css`，RGB/HSLA 大小写测试通过，非上游 `bits/BusinessCard.vue` 的普通裸色被拦，文件白名单已精确到三个上游组件与 theme.js。
- `npm run build` 实际退出 0，775 modules，6.69s。

### 4.2 R2-04 / P2：按整行跳过注释/令牌，仍漏掉有效业务声明

**位置**：`scripts/check-colors.mjs:76–94`。

在本轮隔离目录复制**同一个 checker**，保持相同相对布局，逐个写入并删除探针，以真实 Node 子进程核对退出码；未改受审业务源码。

| 反例（合法 CSS 中的违规色值） | 期望退出 | 实际退出 |
| --- | ---: | ---: |
| `* { color: #ff0000; }` | 1 | **0** |
| `/* normal comment */ .x { color: #ff0000; }` | 1 | **0** |
| 声明行 `--approved: #fff; color: #ff0000;` | 1 | **0** |

原因分别为 `trimmed.startsWith('*')` 把通配选择器当注释、注释起始行整行返回、令牌声明行整行返回。它们都是常见 CSS 写法，不属于运行时拼接或刻意编码绕过。

**下一轮验收**：按语法/词法范围识别真正的注释与自定义属性值，只豁免该范围，不整行丢弃其它代码。三例必须 exit1；另测多行注释结束后的同一行业务、多行令牌结束后的同一行业务、正常合法注释/令牌消费不误报。可复用现有 PostCSS 能力；审查方不限定具体实现。

### 4.3 R2-05 / P2：组件本地定义裸色仍被当成合法主题出口

**位置**：`scripts/check-colors.mjs:37, 92–94`；对照项目“颜色出口仅 tailwind 主题令牌 + src/styles CSS 变量”的红线。

在 `components/bits/BusinessCard.vue` 写入：

```vue
<style scoped>
.x {
  --local-red: #ff0000;
  color: var(--local-red);
}
</style>
```

实际 **exit0**。虽然 bits 白名单已收窄，但 `TOKEN_DECL` 对任何文件的任意 `--*` 声明均免检，这使业务组件可以自行造色而“通过令牌”绕过主题出口。

**下一轮验收**：将裸色令牌定义限定到批准的主题定义文件/位置；组件可定义引用全局令牌的别名，但不能自行写裸色。在普通 Vue、非上游 bits Vue、业务 JS/CSS 分别验证本地造色 exit1；合法集中主题定义/消费 exit0。不要恢复整个 styles/bits 目录豁免。

### 4.4 正反例结果与浏览器范围（浏览器补验前记录）

本轮 13 个独立探针：普通大写 hex、RGB、HSLA、JS、Vue、非上游 bits 六类违规均 exit1；三类合法输入均 exit0；上述四个漏检探针均错误 exit0。探针文件用 finally 清理，隔离扫描清理后 exit0；生产目录未注入测试文件。全部输入与输出在 `color-results.json`，代码在 `color_audit.mjs`。

**本轮未启动浏览器、未独立复跑 home-fit，不能采信自报双屏 PASS 为本轮独立 PASS。** 工具清单没有自动审批服务余额查询接口，已向用户发起“是否确认余额充足”的异步问题；报告落盘时未收到确认。遵守用户先确认余额的条件，没有绕过审批改用 CDP/终端浏览器。本轮静态/运行反例已经足以判 FAIL，无须为得出退回结论继续消耗浏览器。开发方截图/日志保留为待复验材料，不记入独立通过证据。下一轮 F12 修复后仍须确认余额并真实点击 Home/足迹/我的、390×667和390×844布局与命中，检查 console/network。

## 5. 本轮命令与证据

以下命令均已实际执行；长任务均已取回最终完成状态。cwd 未标注者为 `D:/EatWhat`，环境/完整重跑入口见脚本。

| 命令 | 实际结果 | 原始日志/结构化结果 |
| --- | --- | --- |
| `python .../audit.py baseline` | exit0，15项 manifest 一致，源/演示库摘要 | `baseline.log/json`, `source-before.json` |
| `python -u .../audit.py simulate` | exit0，完整默认 60天、真实入口计数、1,000对输入哈希、结果全等 | `simulation.log`, `simulation-independent.json`, `simulation-verification.json`, `simulation-default/` |
| `python -u .../data_audit.py repeat_seed` | exit0，seed7/λ.8，对外14点与1,000房间结果全等 | `seed7.log`, `seed7-independent.json`, `seed7-verification.json` |
| `python .../data_audit.py archived` | exit0，两 seed 四个60天单人库和两个群组库只读复算 | `archived-data.log`, `archived-data-results.json` |
| `python .../data_audit.py seed_guard` | 探针 exit0，证明陈旧快照被接受；不是业务验收通过 | `seed-guard.log`, `seed-guard-results.json` |
| `python .../write_checks.py` | 探针 exit0，真实写回幂等；旧快照覆盖较新库已复现 | `write-check.log`, `write-check-results.json` |
| `python .../controls.py baseline` | exit0，16/16 时钟基线完整响应等价，重样次数独立重建 | `baseline-controls.log/json` |
| `python .../random_metric.py` | 探针 exit0，证明 random 的四人聚合错误 | `random-metric.log`, `random-metric-results.json` |
| `DATABASE_URL=不存在库; python -m pytest tests/test_query_budget.py -q`（cwd backend） | exit0，6 passed，文件未生成 | `query-pytest.log` |
| 同一隔离环境 `python -m pytest -q`（cwd backend） | exit0，131 passed，506 warnings | `pytest.log` |
| `python .../api_probe.py` | exit0，真实 API、40/400目录、全响应对照、SQL及7次交替计时 | `api-probe.log`, `r01-results.json`, `sql-*.json` |
| `python .../controls.py cli` | exit0，8个真实 CLI 子进程，top3/count相等 | `cli.log`, `cli-results.json`, `cli-*.log` |
| `python .../source_control.py` | exit0，还原精确匹配r01算法文件哈希 | `r01-source-control.json` |
| `node .../color_audit.mjs` | 探针 exit0，发现4个应拒未拒；不是门禁验收通过 | `color.log`, `color-results.json` |
| `npm run build`（cwd frontend） | exit0，775模块，6.69s | `build.log` |
| `python .../audit.py final` | exit0，原有源码与演示库逻辑摘要不变 | `final-protection.log/json` |

现有警告：requests 依赖版本兼容提示；`datetime.utcnow()` 弃用；pytest cache 目录权限导致缓存无法写入。均保留原始输出，未隐藏、未放宽断言；本轮没有测试失败。不把这些既有环境警告误记为上述算法/门禁反例的原因。PowerShell 中一次内联源码比较因转义失败未执行，改用 `source_control.py` 后成功；未因该失败变更业务文件。

## 6. 下一轮提交和许可

1. **PC01/R02 返工**：关闭 R2-01（代码保障快照刷新）、R2-02（统一四人满意度/基线硬约束）、R2-03（实投规模）。保留本轮与 r01 原始证据，交 `PC01/r03`；新旧数值变化按方法变更解释，不能手工修柱图。
2. **PC02/R01 本版本 PASS**：不为凑工作量重写优化；若 R02 后续改变共享推荐逻辑/fixture/时钟语义，按依赖重新验证，本次 PASS 不自动覆盖未来修改。
3. **PC03/F12 返工**：关闭 R2-04、R2-05，交 `PC03/r03`，包含全部反例和真实界面回归；10条已清理声明/玻璃数值作为保留回归，不要再次改材质。
4. **S09、批次4仍 LOCKED**，没有“基本通过”或条件放行；不碰 `/admin`。只有三项均获独立 PASS 后才讨论后续许可。台账在 `docs/review/STAGE_STATUS.md`，各项签署在对应 `r02/REVIEW.md`。

## 7. 用户确认余额后的真实浏览器补验（20:36–20:54）

§4.4保留报告首次落盘时的事实；用户随后明确确认余额充足，已补做独立真实浏览器测试。新增完整报告：[浏览器补验报告](browser-supplement/REPORT.md)，原始动作/截图/几何/console/network及最终保护证明均在该目录，不覆盖旧证据。

- **本次浏览器范围PASS**：390×844和390×667均实际点击足迹/我的并核对目标页内容，未复现旧跳转故障；冰箱列表/返回、房间入口、切换室友、下厨决策、稳定换卡、五维说明和沙盒开关正常。
- **双屏布局**：页面分别390×844、390×667，无整页滚动；顶卡422px（50.0%）、261px（39.1%），操作行与底栏均间隔8px；两尺寸外食6个关键按钮/底栏中心命中均成功。小屏下厨同样无滚动且完成真实点击。不是复用开发方home-fit自报。
- **真实用餐**：隔离库新增user2/dish74/HOME_COOKING/7元一条日志；足迹显示洋葱炒蛋，2次/31元→3次/38元。演示库未写入。
- **异常观察**：123条响应全200，0请求失败、0未捕获异常、console error为0；保留5条ECharts alignTicks刻度可读性warning。未宣称覆盖多人WS/完整划卡、APK、真实外网天气或/admin。
- **保护/清理**：审后源码无改动、演示库逻辑摘要不变；viewport已重置、自建tab关闭、测试端口5182/8022关闭，`browser-supplement/final_verify.py` exit0。

补验关闭的是浏览器证据空缺；R2-01～05仍未关闭，三包总评仍**FAIL/PASS/FAIL**，S09与批次4仍LOCKED。后续r03修改后仍须做对应回归，本次结果不自动覆盖未来版本。
