# PC01 / PC02 / PC03 独立审查：三项均退回整改

审查日期：2026-10-24，Asia/Shanghai。审查方：Codex。

**最终判定：PC01/R02 FAIL；PC02/R01 FAIL；PC03/F12 FAIL。S09 及批次 4 主线不开放。**

这不等于三项代码都没有效果：N+1 优化实测有效；首页暖色已替换；仿真 CLI 能跑出可复现结果。退回的原因是实验算法与生产实现不一致、群组对照不公平、查询回归测试依赖外部库、颜色门禁漏检。已证实的问题不需要等待剩余浏览器操作就能判 FAIL。

## 1. 范围与版本

- 依据 `MASTER_SPEC.md` v2.3.2、`BATCH4_PRE_CLEARANCE.md`、`docs/REVIEW_RULES.md` 和当前用户授权。接受三项同轮提交，仍按 R02 → R01 → F12 逐项判断，不因同轮提交直接拒审。
- 只验三项准入与直接回归，不追认 S00–S08、Room 划卡、后台大屏、正式万级数据或 APK。大屏逐点显示验证仍留 S17。
- 三份提交 manifest 的全部文件均与当前源码匹配；独立固定 123 个源码/输入文件，审查结束再次核对，业务源码变动数为 0。

| 步骤 | 开发方 manifest SHA-256 | 文件数 | 结果 |
|---|---|---:|---|
| PC01 | `0f77a4c67e6264d997ed90a3f99da5371c99a8fcb92fbc249d03180b425bcf72` | 15 | 匹配 |
| PC02 | `2eaee6a62d860e51db587d5b1ca4f08fd7d86ae5202058d6b24633ff0859287f` | 7 | 匹配 |
| PC03 | `2ab8351e11988de2c4e9503804cbade0d59ef9e9bd65d6eb494d7909313fabf3` | 19 | 匹配 |

证据：`submitted-manifest-check.json`、`SOURCE_MANIFEST.json`、`source-integrity.json`。

## 2. 必须修复的问题

### CLR-01 / P1：单人仿真跑的是另一个推荐模型，不能证明线上算法有效

位置：`backend/algorithms/simulate_personas.py:60–87,106–142,177–195`；对照 `single_recommender.py`、`time_decay.py`、`vector_spec.py`。

实际：仿真自己实现四维余弦、简化预算、固定天气/状态项和衰减；线上是八维匹配、既定预算/天气公式、库存与状态规则。仿真只从线上衰减模块导入 `SAME_DAY_WEIGHT`，并没有复用算法调用链。独立 profile 三轮中，`recommend_single / compute_decay_weights / shortlist_candidates / compute_group_consensus` 调用总数均为 **0**。

差异不是只存在于代码风格：在隔离内存库里，唯一历史为昨天吃过该道菜，线上衰减得到 **0.3935**，仿真得到 **0.2980088529**。原因之一是仿真把同一道菜的历史同时加入相似菜惩罚，而生产实现对 exact match 使用 `continue`。仿真还没有线上 14 天历史截断，不能称“同一套衰减”。

影响：两条曲线虽真实经过计算，但不能作为本项目生产算法的实验结论；未来直接用于大屏/论文会造成方法与实现不一致。

整改及复验：由可控制仿真时钟的生产算法/共享评分内核驱动推荐，不在仿真器另写一套公式；用逐餐历史而非未来历史更新；覆盖 exact、相似菜、跨模式、当天、14 天边界与无衰减对照。增加能证明生产调用或共享内核真正生效的测试。不得为得到更好曲线而改数据或定义。

证据：`r02-results.json`、`r02-semantic-results.json`、`r02_semantic_probe.py`。

### CLR-02 / P1：群组仿真没有生成 40,000 张真实投票，也没有执行生产共识链

位置：`backend/algorithms/simulate_personas.py:221–274,307–309`。

实际：对 4 个成员直接计算四维口味余弦并取均值/最小值，未生成 `vote_type`、未执行 `0.4*prior + 0.6*swipe`、VETO 掩码、超时或无共识处理，也未调用生产候选筛选与共识算法。候选从外食和下厨的全集混抽，独立样本实际同时含两个模式。

`sample.rooms=1000`、`cards_per_room=10` 是常量元信息，不能代替投票明细。完成 CLI 后，隔离库仍为 4 用户、9 条种子流水、0 房间、0 投票；更关键的是源码也没有构造内存投票事件，不能把 4 人×10 菜的相似度计算称为“40,000 票”。单人分支确实每臂计算出 24,000 条内存餐次，但默认调用用 `_` 丢弃明细，只留下汇总。提交说明声称的 `len(meals)` / 票数断言并不存在于当前源码。

整改及复验：生成可追溯的人设、餐次和群组事件明细（允许隔离库或明确的实验文件，不得写演示库）；候选通过同模式的真实生产筛选；记录计划/实际/跳过/无可行解/全否决数量及原因。生成合法投票枚举并调用真实共识算法，按既定范围核算 1,000×4×10；不足候选或无解时如实报告，不造票凑数。保证满意度输出按已批准口径为 0–100，原始 SUPER_LIKE 分值不得偷偷改掉。

证据：`final-validation.json`、`r02-semantic-results.json`、源码及开发方 PC01 `SUBMISSION.md`。

### CLR-03 / P1：群组三策略使用不同成员和候选，策略差异被样本差异混入

位置：`backend/algorithms/simulate_personas.py:307–309`。

实际：同一个 RNG 顺序传入三轮完整生成器；第一轮消耗随机数后，第二、第三轮重新抽成员/菜品。独立记录的三组采样哈希全部不同，首场成员和候选也不同。单人两臂共用随机种子，这一点成立；群组三策略不成立。

反例：把前两轮都设为同一个 `omega=1.0`，仍得到 `(avg=86.23, least=75.66)` 与 `(86.37,75.78)`。两轮相同策略的差别来自样本，不是权重。因此工程账本 §17.1 所称“混合策略以 −0.45 平均分换 +1.22 最差分”目前不能作为因果结论。

整改及复验：先固化同一批房间的成员、合法候选、先验和投票矩阵，再让 mixed / average / random 在同一场景上选胜者。随机选菜使用独立随机流，不能改变后续房间输入。额外验证 mixed 的 ω=1 时与 average 对每场的结果、稳定 tie-break 一致；保存场景摘要和每场结果，由明细独立重算汇总。

证据：`r02-results.json` 的 `groups.sample_hash/first_case`；`r02-semantic-results.json` 的 `same_omega_sequential_control`。

### CLR-04 / P2：N+1 新回归测试绕过 fixture，干净数据库下三条全失败

位置：`backend/tests/test_query_budget.py:12–30,33–71`；现有隔离 fixture 在 `backend/tests/conftest.py`。

实际：新增测试直接导入全局 `SessionLocal/engine`，未用项目 `db/session_factory` fixture，硬依赖数据库里已有 user 2 及种子菜。默认环境会读演示库；把 DATABASE_URL 指到全新隔离文件，三个用例全部因 `no such table` 失败。预先 seed 一个外部库后全量 128 项通过，不代表这些测试能独立建库运行。

等价测试还将 `_fridge_index`、`_fridge_status_from_index` 同样调用两遍，并只取第一道菜，两条路径实际是同一个实现；它不能防止两者共同算错。SQL 断言 `<=10` 也不是“个位数”。

整改及复验：改为 fixture 注入的隔离 session，SQL listener 绑定同一 engine；完整请求或调用链计数，库存 ≤1、SELECT ≤9；使用独立的逐菜参考实现/固定期望值，覆盖多道菜、全部排序与分项、候选扩容、空库存、过期和临期双倍。清空审查专用新库后直接运行测试应可通过，不能要求先初始化用户演示库。保留真实修复后性能证据。

说明：这项是**测试与交付门禁不合格**，不是宣称 N+1 业务优化失效；业务实现已由本轮独立探针验证有效。

证据：`query-budget-clean-db.log`（exit 1 / 3 failed）、`pytest-full.log`（隔离预置库 / 128 passed）、`r01-results.json`。

### CLR-05 / P2：颜色脚本的全目录豁免和扩展名/大小写规则造成实测漏检

位置：`scripts/check-colors.mjs:22–29,36,49`；现存漏项示例：`frontend/src/styles/main.css:145,150,247,260,268,278,282`、`glass-card.css:117`、`glass-tokens.css:36,39`。

实际：脚本只枚举 `.vue/.js`，把整个 `styles/` 和整个 `components/bits/` 豁免，且 RGB/HSL 正则没有忽略大小写。允许 CSS 变量定义出现裸色值，不等于允许这个目录的所有业务选择器、任意新 JS/Vue 文件写裸色。

独立用 PostCSS 解析 CSS 声明，排除所有 `--自定义属性`（包括多行阴影变量）后，仍找到 **10 个直接写色的业务声明**，并非“未归并色值 0”。没把文档、注释或变量定义计为违规。

| 临时样例 | 应有结果 | 真实退出码 |
|---|---|---:|
| 普通组件 `#ff0000` + `rgba(...)` | 拒绝 | 1，正确 |
| `src/styles/` 新 CSS 的 `.x{color:#ff0000}` | 拒绝 | 0，漏检 |
| `src/styles/` 新 JS 的裸 hex | 拒绝 | 0，漏检 |
| `components/bits/` 新增非上游业务 Vue 的裸 hex | 拒绝 | 0，漏检 |
| 普通 Vue 的合法 CSS `RGB(255 0 0)` | 拒绝 | 0，漏检 |
| 正确 `rgb(var(--rgb-white) / .5)` | 放行 | 0，正确 |

整改及复验：扫描实际业务 `.vue/.js/.css`；只允许真实令牌声明，采用精确且可核对的上游文件例外，不能按整个目录放过新业务；支持 CSS 函数大小写并保留正确 token 的正例。把现有 10 个业务声明归并，不改已经锁定的玻璃参数值。为门禁保存自动化正/反例并接入约定的检查入口。再次真实回归两尺寸与相关页面。

临时违规样例已全部移除，业务源码哈希不变；最后原门禁仍 exit 0，这正是“脚本全绿不能证明规则完整”的证据。

证据：`color-results.json`、`css-outside-token-definitions.json`、`color_probes.mjs`、`css_scan.mjs`。

## 3. 已独立验证成立的部分

### PC01 / R02

- 实际运行仿真核心三轮：默认 seed 20261024 两次、seed 7 / λ=.8 / ω=.6 一次；同参数除 generated_at 外可复现，换参可变化。
- 每轮两条单人实验臂各 24,000 条内存餐次，200 人、60 天、每天 2 餐；审查探针把返回餐次存为 `meals-*.jsonl.gz` 并独立复算 14 点重复率，相符。
- 另直接执行原 CLI，exit 0：默认第 14 天 `0.1696 / 0.2441`；平均满意度 `[85.92,86.37,73.4]`；最低满意度 `[77.07,75.85,57.15]`。这些只是**待整改简化模型的输出**，不可据此宣称项目算法效果已经成立。
- JSON 四键写库结构、数组长度、隔离库与输出逐点一致均成立；未提前开发 admin。

### PC02 / R01

通过真实 `POST /api/v1/recommend/single` 捕获完整 SELECT；比较保留现有 F09 时效语义的独立逐菜参考实现与当前批量实现。未把开发方 `--legacy`（额外保留一次预取，旧计数偏大）作为独立旧版证据。参考实现属于本轮重建的 N+1 对照，不冒称 Git index 是“恰好优化前版本”；index 较早且缺少现有 F09。

| 场景 | 参考逐菜 SELECT / 库存 | 当前 SELECT / 库存 | 响应等价 | 7 次交替调用中位耗时 ms（前→后） |
|---|---|---|---|---|
| 40 下厨菜，筛后 31 | 36 / 31 | **6 / 1** | 完整 API 响应相等 | 23.569 → 10.694 |
| 400 下厨候选，筛后 310，API 返回上限 100 | 315 / 310 | **6 / 1** | 完整 API 响应相等 | 160.664 → 34.617 |
| 外食，46 结果（40 场景） | 6 / 0 | **6 / 0** | 相等 | 11.875 → 12.312 |
| 外食，46 结果（400 场景） | 6 / 0 | **6 / 0** | 相等 | 12.012 → 12.734 |

400 候选由隔离库复制候选构造，**仅用于证明查询不随候选数线性增长**，不计入真实数据扩容，不代表正式万级数据压测。耗时是本机功能基准，不是吞吐或线上 SLA。库存六个独立断言（空主料、缺料、普通覆盖 33.33、临期覆盖 66.67、过期 0、封顶 100）全部通过。

### PC03 / F12 与浏览器直接回归

- `Home.vue` 暖色替换、组件常见 hex/rgb 替换、Footprint 图表用 theme 解析颜色均有实际改动，构建通过。
- 使用浏览器真实操作，隔离前端 `127.0.0.1:5174` → 隔离后端 `127.0.0.1:8011` → `review-browser.sqlite`。未通过 API 调用冒充点击。
- 两尺寸、外食/下厨分别量测：首页 390×667 的 card 261px / 39.1%，390×844 的 card 422px / 50%；页面 scrollWidth/Height 与视口一致，卡片可见子元素溢出 0，操作行与 Tab 重叠 0，两个按钮中心均命中自身。问候、完整面板、顶卡、露边、候选条、操作行可见。截图已实际打开检查。
- “足迹”“我的”均通过底部链接真实进入，等待页面转场结束并核实 opacity=1；打开沙盒调参后再次导航也成功。**此前页面进不去的症状本轮未复现**。
- 实际切换小赵→阿明、从 Profile 进入冰箱和房间入口；在隔离库实际添加“审查专用食材”成功。Room 只验入口和样式，未扩大为已延期的多人划卡验收。
- 844 屏实际换菜、确认面板及取消均验证；沙盒通过真实键盘 End 改 λ 到 2.00，后端回传生效标签更新，Top5 与首页候选顺序相同，顶卡相同。667 屏“换一个”已点击，但最后结果断言与确认按钮的独立复测未完成，不能记为完整通过。
- 没有直接执行 `home-fit.mjs/refill-fresh.mjs/sandbox-sync.mjs` 的外部 CDP 自动控制脚本。两尺寸布局和沙盒实际重算由受支持浏览器工具复验；本轮未复验完整耗尽/换批，不能宣称 S05/F13 全部通过。

浏览器限制：最后一轮操作被自动审批服务拒绝执行，返回 **403 / Insufficient balance**，不是认定操作不安全。后续小屏按钮结果、最终 console 日志导出、关闭自建 tab 4 和 viewport reset 尚未完成，最后视口为 390×667。未绕过审批改用其他浏览器控制手段。已保存 9 张截图；此限制不改变上述源码和独立运行已证实的 FAIL，但禁止把本轮描述成完整浏览器总验收。

## 4. 命令、数据保护与证据

| 操作 | cwd / 关键参数 | 退出码与结果 | 日志 |
|---|---|---|---|
| 后端全量测试 | `D:\EatWhat\backend`; DATABASE_URL=审查专用已 seed 库 | 0；**128 passed, 133 warnings in 7.40s** | `pytest-full.log` |
| 前端构建 | `D:\EatWhat\frontend`; `npm run build` | 0；**built in 9.45s** | `build.log` |
| 原颜色门禁 | 仓库根；`node scripts/check-colors.mjs` | 0；31 个文件 | `color-current.log` |
| 门禁正反例 | `node docs/review/clearance-codex-2026-10-24/color_probes.mjs` | 驱动器 0；违规样例中 4 类漏拦 | `colors-probe.log` / `color-results.json` |
| 干净库查询测试 | DATABASE_URL=新审查库；`python -m pytest backend/tests/test_query_budget.py -q --tb=short` | 1；**3 failed** | `query-budget-clean-db.log` |
| 仿真审查核心三轮 | `python .../review_harness.py simulation` | 0；调用/样本/明细/复算/写库 | `r02-run.log` / `r02-results.json` |
| 原仿真 CLI | DATABASE_URL=审查库；`python -m backend.algorithms.simulate_personas --seed 20261024 --write --out docs/review/clearance-codex-2026-10-24/benchmark-cli.json` | 0 | `r02-cli.log` |
| 真实接口 SQL/耗时/语义 | `python .../r01_probe.py` | 0；场景与断言见 JSON | `sql-probe.log` / `r01-results.json` / `sql-*.json` |
| 衰减与对照反例 | `python .../r02_semantic_probe.py` | 0；确认差异 | `r02-semantic.log` |

全量测试的警告主要是 `datetime.utcnow()` 弃用与 pytest 缓存目录权限；没有把 warning 改成 error 或删断言求绿。SQL 审查探针最初使用 limit=500 被正确 422 拒绝，随后修正至契约上限 100；另补齐了探针库存 category 必填值后重跑。均为审查夹具问题，不计作业务缺陷。

演示库 `backend/eatwhat.db` 只用 SQLite `mode=ro` + 读事务获取摘要，未用它运行仿真、seed 或写入探针。前后两次逻辑 dump SHA-256 均为：

`3a7fa3f4487c29f3e1f43c09014c1d7a8f4f6261e1ad0dddc06c408cdf5e092f`

两次 journal_mode 均为 delete，所有表行数相同（4 用户、100 菜、9 流水、12 库存、0 房间/投票）；未用仅主文件哈希代替逻辑检查。证据：`demo-before.json`、`demo-after.json`。审查专用数据库与临时样例均未混入用户数据。

## 5. 下一轮提交要求与许可

1. **先整改 PC01 / R02**：关闭 CLR-01/02/03，交 `PC01/r02`，保留 r01 原证据。新的原始事件、生产调用、同场景三策略和复算必须齐全。
2. **PC02 / R01 不重做已有效的优化**：修 CLR-04 测试隔离和独立等价断言，保留本轮 6 SELECT / 1 库存结论作为当前版本证据，变更后复验。
3. **PC03 / F12 不只换一组正则**：关闭 CLR-05 的实际 CSS 残留及所有漏检路径，提交自动化反例和真实界面回归证据。
4. 允许既有三项的整改和重新送审；**不允许 S09 或后续批次 4 开工**。只有三项重新得到独立 PASS 才开放 S09。其他旧专项与延期项不自动关闭。

本轮只新增审查探针/证据/报告并同步审查台账与工程记忆，没有代替开发方修改业务实现。
