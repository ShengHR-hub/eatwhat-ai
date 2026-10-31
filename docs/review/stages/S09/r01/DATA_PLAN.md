# S09 数据来源与规模契约

- 日期：2026-10-24（Asia/Shanghai）
- 性质：**数据方案，不是导入完成证明**。S09 不执行 POI/菜谱批量导入，不写生产/演示库。
- 关联决策：`DECISIONS.md` D01–D10、D16–D20、D25、D27。
- 结论：**POI、菜谱、食堂三类来源均未达到可施工状态**；本文件把可行路径、算术和缺口写清，等待用户裁决。

## 1. 当前只读基线（实测）

数据来源：`backend/eatwhat.db`，SQLite `mode=ro`。证据：`data/db_baseline.json`、`logs/02_baseline.log`。

| 项 | 当前值 |
|---|---:|
| `users` | 4 |
| `restaurants` | 20（AMAP_POI 10 / CANTEEN 10） |
| `dishes_and_recipes` | 100（OUT_DINING 60 / HOME_COOKING 40） |
| 唯一菜名 | 95；跨模式同名 5 组（回锅肉、宫保鸡丁、白灼虾、紫菜蛋花汤、麻婆豆腐） |
| 唯一 `(name, ingredients_main)` | 95 |
| 有效 8 维向量 | 100 / 100 |
| 当前特征值总数（有效向量×8） | **800** |
| `eating_logs` | 9 |
| `group_rooms` / `room_votes` | 0 / 0 |
| 数据集指纹 | `3e24f458071d67f3097d28ffb1d997d7a0188c18b0e28251aca7b7cf0c27625e` |

当前 20 家门店与 100 道菜是**种子数据**，不是真实采集结果。现有种子坐标 `108.9301,34.2402` 仅用于演示，不能当作实际学校中心。

## 2. 中心坐标与 3km 查询包络

### 2.1 待用户提供

- 实际学校/校区名称，或直接给 **GCJ-02** 经纬度（D01）。
- 高德 Web 服务 Key 与账号等级（D02）。当前环境变量 `AMAP_API_KEY` 缺失；实际请求返回：

```text
HTTP 200
{"status":"0","info":"INVALID_USER_KEY","infocode":"10001"}
```

证据：`data/amap_keyless_check.json`、`logs/03_amap_keyless.log`。

### 2.2 官方约束（已核验）

来源：高德官方搜索 POI 文档与计费页（`data/amap_official_facts.json`）。

- 周边搜索：`GET https://restapi.amap.com/v3/place/around`
- 必填：`key`、`location`（经度,纬度；小数点后不超过 6 位）。
- `radius`：0–50,000 米，默认 5,000；本项目固定 **3,000 米**。
- `offset`：官方强烈建议 ≤25。
- **同请求参数翻页最多 200 条**：官方原文“目前搜索是不支持返回全量数据的，同请求参数翻页查询最多支持获取200条数据”。
- 个人认证开发者：关键字/周边搜索 **5,000 次/月、3 QPS**；未认证为 0。
- 坐标系：**GCJ-02**；官方 FAQ 明确“高德开放平台服务用的是国测局规定的GCJ-02坐标系”。

### 2.3 查询分区方案（建议，待 Key 实测）

因为单组参数最多 200 条，不能只靠 `page` 翻页拿 1,500+。建议：

1. 以中心点画 3km 圆，再切成互相重叠的 1km 网格（重叠 200m，避免边界漏店）。
2. 每个网格先查 `types=050000`（餐饮服务）。
3. 若某网格 `count` 接近/达到 200，按官方 POI 子类（中餐厅/快餐厅/咖啡厅/茶饮/甜品等）或关键词再分片。
4. 每片最多翻 8 页（25×8=200）；记录 `count` 与实收数，差异即截断风险。
5. 以 `poi.id` 去重；跨网格重复由 `id` 消解。
6. 任何一片出现 `count > 200` 且无法再分片，必须记录为“未采全”，不能把 200 当作该片真实总量。

预计调用量（估算，待实测）：1,500 条 / 每片最多 200 条 → 至少 8 个满片；考虑网格与分类冗余，约 50–300 次请求，在个人 5,000 次/月内。**未拿到 Key 前不承诺。**

## 3. POI → `restaurants` 契约

| 高德字段 | `restaurants` 字段 | 处理 |
|---|---|---|
| `id` | 无对应列 | **schema 缺口**：需 `source_record_id`/`source_dataset` 或来源表（D19） |
| `name` | `name` | 原样；空名拒绝 |
| `type` / `typecode` | `category` | 取小类中文名；保留原始 `typecode` 到来源表 |
| `location` | `longitude`, `latitude` | GCJ-02 原样；解析失败拒绝 |
| `address` | `address` | 空值保持 NULL/空串，不编造 |
| `biz_ext.rating` | `rating` | **缺失保持 NULL**；不得默认 4.5 冒充真实（D09） |
| `biz_ext.cost` | `avg_price` | **缺失保持 NULL**；不得默认 500/0 冒充真实（D09） |
| `distance` | `distance_meters` | 高德周边搜索返回的“离中心点距离”单位为米；若为空，按中心点计算，但需标注距离类型（D10） |
| `tag` | 外食菜品候选 | 特色菜字符串（如“烤鱼,麻辣香锅”），**不是完整菜单**；只作候选，需人工/LLM 清洗 |
| `source_type` | `AMAP_POI` | 固定；食堂另走 CANTEEN |
| `pname/adname/business_area` | 无对应列 | 需要时进来源表；不塞进 `address` 冒充 |

**去重规则（建议）**：

1. 首选 `poi.id` 唯一。
2. 无 `id` 时用 `(normalized_name, normalized_address, round(lng,6), round(lat,6))`。
3. 同名同址但坐标相差 <30m 视为重复；保留字段更全、`typecode` 更具体的一条。
4. 校园内部食堂 POI 若与合成 CANTEEN 重复，CANTEEN 优先，AMAP_POI 剔除，避免重复计数。
5. 失败/拒绝记录单列原因（无坐标、非餐饮、重复、越界、字段非法），**不计入最终 POI 数**。

**数量状态**：`measured_poi_count = null`。在 D01/D02 未解决前，**不得对外写“1500+ POI 已可得”**；只能写“目标 1500+，待实测”。

## 4. 200 个食堂窗口契约

SSOT 原文：抓取周边餐饮 POI“及 200 个校园食堂窗口”；脚本说明为“校园食堂档口生成”。当前数据库只有 10 条 `CANTEEN` 种子，**没有 200 条实际采集数据，也没有采集脚本**。

| 方案 | 内容 | 优点 | 风险 |
|---|---|---|---|
| A 合成（建议） | 按校内食堂/楼层/窗口生成 200 条，`source_type=CANTEEN`，名称标注“模拟档口” | 可复现、无需外部数据、与 POI 分表分源 | 不能宣称真实采集；论文必须写明 |
| B 实采 | 用户提供校内档口清单/照片/坐标/价格 | 真实性最高 | 工作量大、隐私/授权、坐标需实测 |
| C 缩减 | 只保留现有 10 条或按实际可得数量 | 诚实 | 与 SSOT 200 不符，需用户批准 |

无论 A/B/C：

- 食堂不进入 `AMAP_POI` 计数；`restaurants_total` 可含两类，但必须能按 `source_type` 拆分。
- 合成窗口的坐标只能落在校园范围内，不得伪造成周边真实店铺。
- 与真实校园 POI 去重（见 §3）。
- 200 这个数字需用户确认（D04）。

## 5. 菜谱来源契约

### 5.1 已核验候选（详见 `data/recipe_source_assessment.json`）

| 来源 | 规模（实测/公开） | 许可证 | 可再分发 | 结论 |
|---|---|---|---|---|
| `Anduin2017/HowToCook` | **373** 个菜谱 Markdown（含 1 个模板，实际可用 **372**） | **Unlicense**（public domain） | 是 | 许可证最干净，但规模远不足 6300 |
| XiaChuFang Recipe Corpus | 1,520,327 条 / 30,060 道 | 未找到明确许可证；搜索摘要显示“仅用于学术目的，请勿商用” | **未证明** | 规模够，许可不清 |
| `Eimo-Bai/Ta-da-recipe-dataset` | 12,142 条（完整数据未公开） | 无 LICENSE | 否 | 不可用 |
| `ngl567/CookBook-KG` | 未给可核验总量 | 无 LICENSE | 否 | 不可用 |
| `SmartFlowAI/TheGodOfCookery` | 代码 Apache-2.0；数据来自 XiaChuFang | 代码许可不覆盖数据 | 未证明 | 不能据此给数据换许可 |
| RecipeNLG / Recipe1M+ / Food.com | 百万级英文菜谱 | 语言/领域不匹配 | — | 不作为中文菜谱来源 |

### 5.2 结论

**没有找到“许可证明确 + 规模 ≥6,300 + 中文菜谱 + 可再分发”四个条件同时满足的公开数据源。** 这是 S09 的硬阻塞（D05）。

可选路径（需用户选一）：

1. 用户提供有明确许可的菜谱数据集/采购授权。
2. 书面确认 XiaChuFang 仅学术使用、不分发原始语料；项目只保存必要字段与派生 8 维向量，并在论文/仓库标注来源与限制。
3. 以 HowToCook（Unlicense）为底座，补充人工整理/自有菜谱，接受规模下调。
4. 合成菜谱并明确标注（不得写成真实采集）。

### 5.3 `dishes_and_recipes` 映射

| 来源字段 | 目标字段 | 处理 |
|---|---|---|
| 菜名 | `name` | 去重/规范化后写入 |
| 家常/外食 | `mode_type` | 来源为菜谱时默认 HOME_COOKING；外食需 D08 单独定义 |
| 菜系 | `cuisine_type` | 来源缺失时需人工/规则映射；不得瞎猜 |
| 角色 | `dish_role` | 优先来源字段；否则 LLM/人工；`MEAT/VEG/SOUP/ONE_MEAL` |
| 价格/成本 | `price_or_cost` | 来源有则用；无则 NULL，不编造 |
| 时长 | `cook_minutes` | 来源有则用；无则按 SSOT 默认 15 **仅作展示兜底**并标注 |
| 厨具 | `appliance_tag` | 来源有则用；无则默认 `["炒锅"]` 需标注 |
| 主料/辅料 | `ingredients_main/aux` | 必需；空数组需标注，不能假装完整 |
| 步骤 | `recipe_steps` | 来源有则用；空则占位并标注 |
| 向量 | `feature_vector` | 由 S11 打标；**不在导入时填默认值** |
| 过敏原 | `allergen_tags` | **无字段**（D16）；暂不落库 |
| 来源 | 无字段 | **schema 缺口**（D19） |

### 5.4 外食菜品来源（D08）

高德 POI 只给 `tag` 特色菜（且不保证有），不提供菜单、主辅料、价格。当前 60 道 OUT_DINING 是种子菜。S10 不能把菜谱库中的菜随机绑定到门店并称为真实菜单。建议：

- 外食菜品：人工整理的门店菜单/招牌菜 + AMap `tag` 候选；每条记录保留“来源=人工/AMap tag”的标记（需 D19 字段）。
- 下厨菜品：来自批准的菜谱数据集。
- 若无法获得真实菜单，OUT_DINING 数量不扩张，只扩张 HOME_COOKING；论文如实说明。

## 6. 规模口径与算术

### 6.1 定义

| 名称 | 定义 | 是否允许合成 | 来源要求 |
|---|---|---|---|
| POI | `restaurants.source_type=AMAP_POI` 的行 | 否 | 高德可追溯 ID/坐标 |
| 食堂窗口 | `restaurants.source_type=CANTEEN` 的行 | **待定（D04）**；若合成必须标注 | 实采清单或合成规则 |
| 菜谱 | `dishes_and_recipes` 中 `HOME_COOKING`（及批准的外食菜）行 | **不允许把合成写成真实**（D05） | 数据集/人工整理可追溯 |
| 菜品实体 | `dishes_and_recipes` 总行数 | 取决于上两项 | 行级来源 |
| 唯一菜谱 | 唯一 `(normalized_name, ingredients_main)` | — | 与行数分开报 |
| 基础实体 | `restaurants` 行数 + `dishes_and_recipes` 行数 | 取决于上两项 | 分表统计 |
| 成功打标菜品 | `feature_vector` 为合法 8 键、有限、0–1 的行 | 用真实 LLM 输出 | 失败不计 |
| 特征值总数 | `8 × 成功打标菜品数` | 否 | 不得用行数×8 含失败 |

### 6.1.1 七个数量逐项对照（不得混用）

| 名称 | 表 / 公式 | 当前 | 目标 | 允许合成 | 失败是否计入 | 来源要求 |
|---|---|---:|---:|---|---|---|
| 1500+ POI | `restaurants where source_type='AMAP_POI'` | 10 | 1,500+（待实测） | **否** | 否 | 高德 `poi.id` + GCJ-02 |
| 200 食堂窗口 | `restaurants where source_type='CANTEEN'` | 10 | 200（D04） | **待定**；合成必须标注 | 否 | 实采清单或合成规则 |
| 6300–8000 菜谱 | `dishes_and_recipes` 行（历史口径） | 100 行 / 95 唯一名 | 6,300–8,000 | **不得把合成写成真实** | 否 | 数据集/人工整理可追溯 |
| 8000–9700+ 基础实体 | `count(restaurants) + count(dishes)` | 120 | 8,000–9,700+ | 取决于上两行 | 否 | 分表统计，不合并成 dishes |
| dishes 表实际条数 | `count(dishes_and_recipes)` | 100 | 6,300–8,000 | 取决于来源 | 否 | 行级来源 |
| 成功打标菜品数 S | `feature_vector` 为合法 8 键的行数 | 100 | **≥7,500**（若要 60,000+） | 否 | **否** | LLM 运行记录 |
| 60000+ 特征值 | `8 × S` | 800 | 60,000+ | 否 | **否** | 每条成功记录 8 个值 |

> 注意：`restaurants_total` 含 POI + 食堂；`dishes_total` 只含菜品/菜谱。论文和接口不得把 1,700 门店 + 菜品加总后称为“菜品数”。

### 6.2 目标算术

| 组合 | 计算 | 结果 |
|---|---|---:|
| 1,500 POI + 200 食堂 | 1,500 + 200 | 1,700 门店 |
| 基础实体（菜谱 6,300） | 1,700 + 6,300 | 8,000 |
| 基础实体（菜谱 8,000） | 1,700 + 8,000 | 9,700 |
| 特征值（6,300 道全部成功） | 6,300 × 8 | **50,400** |
| 特征值（7,500 道全部成功） | 7,500 × 8 | **60,000** |
| 特征值（8,000 道全部成功） | 8,000 × 8 | 64,000 |

**硬结论**：若只导入 6,300 道且全部成功，最多 50,400 个特征值，达不到 60,000+。要写 60,000+，成功打标菜品数必须 ≥7,500；否则只能写“按实际成功数 8×S”，不能四舍五入/重复计数（D06）。

### 6.3 当前种子与目标的差距

| 项 | 当前 | 目标 | 差距 |
|---|---:|---:|---:|
| 门店 | 20 | 1,700 | 1,680 |
| 菜品行 | 100 | 6,300–8,000 | 6,200–7,900 |
| 特征值 | 800 | 60,000 | 59,200 |
| 日志 | 9 | 24,000（S12） | 23,991 |
| 房间/票 | 0 / 0 | 1,000 / 40,000（S12） | 全部 |

## 7. 去重规则（建议，待确认）

### 7.1 POI

见 §3：`poi.id` 优先；fallback 名称+地址+坐标；校园内 CANTEEN 与 AMAP_POI 去重；同名连锁店保留不同 `id`/地址。

### 7.2 菜谱

1. 规范化菜名：去空格、全半角统一、去括号修饰；但“番茄炒蛋/西红柿炒蛋”这类近义不自动合并，需别名表。
2. 以 `(normalized_name, sorted(ingredients_main))` 为唯一键；同键不同步骤保留来源更完整的一条。
3. **跨模式同名**（如麻婆豆腐同时存在外食/下厨）不是自动重复：若两个实体确实分别属于门店菜单与家常菜，保留两行，但必须在统计中同时报“行数/唯一菜谱数”，且特征值按行计，不得把两行说成两道不同菜（D07）。
4. 同一数据集重复导入必须幂等：先按唯一键查重，再插入；`--force` 不用于日常增量导入。
5. 失败/拒绝记录（无主料、无步骤、名称空、来源不可追溯）单列，不进入最终菜谱数。

## 8. 数据不足时的调整方案（需用户批准）

按优先级：

1. **延长/扩大 POI 查询**：3km → 5km，或增加分类分片；必须重新实测，不直接写 1500+。
2. **降低 POI 目标**：按实测可采数写论文；不要伪造。
3. **菜谱规模**：若拿不到 ≥7,500 道可打标菜谱，把“60,000+”改为“8×实际成功数”，或降低菜品总量目标。
4. **食堂**：合成 200 或按实采数写；不得把合成包装成真实采集。
5. **外食菜品**：若拿不到真实菜单，减少 OUT_DINING 扩张，只扩 HOME_COOKING，并说明。
6. **任何调整**都要更新 SSOT 第七章与论文口径，不能只在代码里悄悄改。

## 9. schema 缺口（本步不修，先报）

| 缺口 | 现状 | 影响 | 建议（需 SSOT） |
|---|---|---|---|
| `allergen_tags` | 附录 C 有输出，核心表无列 | 词云/质量面板无来源；不能落库 | 新增 nullable JSON 列或独立表（D16） |
| 来源追溯 | `restaurants`/`dishes` 无 source id/dataset/url/version | 无法证明 30 条抽检来自哪里 | 新增来源列或 `data_sources` 表（D19） |
| 软删除 | 无 `is_active`/`deleted_at` | 删除菜品/门店会破坏历史流水/投票 | 软删除 + active 过滤（D17） |
| `feature_vector` | `NOT NULL` | 无法表示未打标/失败；默认值蒙混被禁止 | 改 nullable + `tagging_status`/`llm_meta`（D18） |
| 打标任务 | 无任务/失败表 | 断点续跑、重试、幂等无落点 | 任务表或 sidecar manifest（D18） |
| 仿真数据 | 隔离库，主库 `room_votes=0` | stats 看不到 24,000/40,000 | 明确统计库/主库策略（D20） |

以上任何一项都不能在 S09 直接改代码/迁移；必须先由用户确认并更新 SSOT，再在 S10/S11/S14 实施。

### 9.1 历史数据与删除策略（设计建议，待 D17/D16/D18 确认）

| 对象/动作 | 建议 | 历史记录行为 | 需要的 schema/约束 |
|---|---|---|---|
| 菜品删除 | **软删除** `is_active=false`（或 `deleted_at`） | `eating_logs.dish_id`、`room_votes.dish_id`、`group_rooms.candidate_dish_ids/winner_dish_id` 仍可联表；历史可读 | 需加 `is_active`/`deleted_at`，所有推荐/列表查询过滤 active |
| 门店下架 | **软删除/下架** `is_active=false` | 其外食菜品不再推荐；历史流水/房间不删除、不改写 | 同上；不级联删菜品历史 |
| 历史打卡 | 保留 `dish_id`；若要求不可变快照，另存 `dish_name/cuisine/price` 快照 | 软删除下可直接 join；硬删除会悬空 | 快照字段是 schema 变更，需用户决定 |
| 历史投票/推荐 | `group_rooms.consensus_report` 已有报告；保留 `candidate_dish_ids/winner_dish_id` | 软删除下可复算/展示；硬删除会破坏报告 | 若硬删除，必须禁止删除仍被引用的菜品 |
| 删除被引用对象 | 软删除优先；若坚持硬删除，接口应返回 409 并列出引用 | 不允许静默悬空 | S14 删除接口契约 |
| `allergen_tags` | 建议 nullable JSON 列或独立表；**只用于词云/质量面板** | 不改变历史流水 | 不要把它加入算法 2 硬过滤，除非 SSOT 明确改算法 |
| LLM 批任务 | sidecar manifest + `tagging_status`；幂等键 `(dish_id, prompt_version, model_version)` | 失败不写占位向量；成功记录可重跑跳过 | 需 `tagging_status/llm_meta` 或独立任务表（D18） |
| 断点/重试 | 每批提交；失败清单；最多 3 次；恢复从 manifest 续跑 | 不重复收费/覆盖成功记录 | 任务日志 + 状态字段 |

**结论**：现行 schema 没有软删除、来源、allergen_tags、打标状态；在用户确认并同步 SSOT 前，S14 的删除接口和 S10/S11 的导入/打标都不能按“已定”施工。

## 10. S10/S11 数据质量门禁（供后续验收）

- 原始数量 → 去重后 → 有效 → 入库 → 拒绝，五段都要有数，按 `source_type`/`mode_type` 分桶。
- 每条 POI/菜谱保留来源键；抽检至少 30 条 POI、30 条菜谱能回到原始记录。
- 重复导入同批次不增加行数；同一 `poi.id`/菜谱唯一键不重复。
- 枚举/外键/坐标范围/8 维向量合法性校验；失败记录可查。
- 统计口径以本文件 §6 为准；论文数字必须能从数据库查询复算。

## 11. 证据

- `data/db_baseline.json`：表结构、行数、source/mode 分布。
- `data/dataset_fingerprint.json`：当前库表级指纹。
- `data/amap_official_facts.json`、`data/amap_keyless_check.json`、`logs/03_amap_keyless.log`、`logs/05_amap_docs_extract.log`、`logs/06_amap_tables.log`。
- `data/recipe_source_assessment.json`、`data/recipe_repos_check.json`、`data/recipe_details.json`、`logs/07_recipe_repos.log`、`logs/08_recipe_details.log`。
- `data/assets_baseline.json`、`data/dependency_and_license_assessment.json`。
- `data/git_status_short.txt`、`data/file_hashes.json`、`data/routes.json`。

## 12. 成本、权限与外部依赖

> 以下为预算/条件清单，不是已发生费用。未确认前不发起批量付费调用。

| 项 | 现状 | 估算/上限 | 状态 |
|---|---|---|---|
| 高德 Key | 缺失；空 Key 实测 `INVALID_USER_KEY` | 个人认证 5,000 次/月、3 QPS；3km 分区预计 50–300 次，免费额度内 | **BLOCKED**（D02） |
| AMap POI 执行时间 | 未执行 | 50–300 次 / 3 QPS，正常 <5 分钟（不含限流/重试） | 待 Key |
| LLM Key/模型 | 缺失；模型未选 | 7,500 道 / 20 道每批 = 375 批；按 2k 输入 + 2k 输出/批估算约 1.5M tokens | **BLOCKED**（D27） |
| LLM 费用上限 | 未定 | 建议硬上限 **¥50**，超过即停并报告；实际以选定模型单价为准 | 待用户确认 |
| LLM 执行时间 | 未执行 | 375 批 × 5–15 秒，2–4 并发 + 3 次重试，约 20–60 分钟 | 待模型 |
| 仿真 | r04 实测单 seed 约 12–16 分钟 | 两 seed 约 30 分钟；S12/S13 若数据扩容需重测 | 可执行（S12 前需 D20） |
| APK 构建 | `java/javac 25.0.2` 有；`adb`/`gradle`/Android SDK/Capacitor 配置均缺失 | 需 JDK 17/21 + Android SDK + Capacitor 工程；Java 25 可能不兼容 AGP | **BLOCKED**（D26） |
| 真机 | 未确认 | 需要 Android 设备/系统版本/网络 | **BLOCKED** |
| 菜品图 | 95 张小红书截图 | 公开再分发/APK/论文附图授权未证明 | **BLOCKED**（D25） |
| Lottie/前端库 | MIT/ISC/Apache/Standard no-charge 等 | 已在 `data/dependency_and_license_assessment.json` 记录 | 可用（Vue Bits 受 Commons Clause 限制） |
| 高德 JS API 地图 | 需 Key | 与 POI 共用 Key；页面使用条款需在 S17 记录 | **BLOCKED**（D02） |

**费用纪律**：S09 只做空 Key 探测，未产生付费调用；S10/S11 的任何批量调用必须先报预算、先小样本、再全量，失败/超限立即停。
