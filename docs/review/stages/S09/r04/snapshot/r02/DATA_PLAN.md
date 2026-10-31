# S09 / r02 数据来源与规模契约

- 日期：2026-10-25（Asia/Shanghai）
- 性质：用户已确认口径 + 真实 API 小样本/全量 3km 只读采集；**不导入数据库**。
- 关联：`DECISIONS.md` D01–D38、`MASTER_SPEC.md` v2.3.5 §3/§5.5/§7。

## 0. 双校区注册表（v2.3.4）

| 校区 | ID | 中心 GCJ-02 | 真实 POI | 合成食堂 | 合计 | 状态 |
|---|---|---|---:|---:|---:|---|
| 西安思源学院主校区 | `SIYUAN` | `109.078487,34.234818` | **605** | 200 | **805** | 已实测 |
| 西安建筑科技大学雁塔校区 | `JIANDA_YANTA` | `108.967153,34.236991` | **6,659** | 200 | **6,859** | 已实测 |
| 草堂校区（预留） | `JIANDA_CAOTANG` | 待确认 | 待确认 | 待确认 | 待确认 | 若高德返回草堂，先停问 |

- 两校区方法一致：固定 3km、`types=050000`、800m 网格 + 递归细分、`poi.id` 去重、最终 haversine ≤3000m；报实际数，不合成补齐，不假设 1500+。思源已用与建大同版递归脚本复跑（2026-10-25T02:25:40+08:00），仍为 605。
- `1700` 是原规格总数目标（约 1500+ 真实门店 + 200 食堂窗口），**不是实际数**；`17` 只是大屏图数量；“2km 不足 1700 再扩 3km”规则作废。
- 思源与建大的真实 POI、合成食堂分别存储、分别计数，不得混用；合计不得掩盖单校区数。
- 建成后 `restaurants.campus`、`group_rooms.campus` 可空字段承接；未回填前 NULL，不参与按校区过滤。


## 1. 校区 A 思源：中心与真实 POI（实测）

| 项 | 实测值 |
|---|---|
| 学校 | 西安思源学院主校区 |
| 高德地名搜索 | `GET https://restapi.amap.com/v3/geocode/geo`，`address=西安思源学院`，`city=西安` |
| 实际返回 | `formatted_address=陕西省西安市灞桥区西安思源学院`，`location=109.078487,34.234818`（GCJ-02），`level=兴趣点`，`adcode=610111` |
| 查询时间 | 2026-10-25T00:24:28+08:00 |
| 3km 直接查询 | `types=050000`，`count=600`；page 1–8 有数据，page 9 起为空 |
| 网格去重采集 | 45 个初始 800m 网格 + 递归细分（61 个处理格），133 次调用，0 错误/0 未完成；原始 2,230，按 `poi.id` 去重 1,258，3km 内 607，扣除非餐饮 2 条 → **605** |
| 真实 POI 目标 | 原目标约 **1500+**；实测 **605**，差额 **895**，`target_1500_met=false`；**D03 已裁决接受 605 为样本 A**，差额不再作为阻塞 |
| 字段完整度 | `rating` 有值 604 / 缺失 1；`cost` 有值 427 / 缺失 178；`tag` 有值 309 / 缺失 296 |
| 分类计数（typecode 前 4 位） | 0500=121、0501=373、0502=3、0503=58、0504=4、0505=11、0506=4、0507=18、0508=12、0509=1 |

证据：`data/amap_geocode.json`、`data/amap_pagination_probe.json`、`data/amap_collection.json`、`data/amap_pois.jsonl`、`logs/01_geocode.log`、`logs/03_pagination_probe.log`、`logs/04_amap_collect.log`。

**口径说明**：直接 `count=600` 是 AMap 自身计数；网格去重后 605 是实际采集/落盘结果；两者都低于 1500+ 原目标。**D03 已裁决接受 605 为样本 A**，不再要求补足；S10 不得合成补足、不得借用建大数据或跨校区混算。

## 1b. 校区 B 建大雁塔（已试抓）

- 学校：西安建筑科技大学雁塔校区。
- 中心：高德地名搜索实际返回 `108.967153,34.236991`（陕西省西安市碑林区西安建筑科技大学雁塔校区，level=兴趣点，adcode=610103）；未返回草堂。
- 采样方法：与思源完全一致（3km、`types=050000`、800m 网格、`poi.id` 去重、haversine ≤3000m）；报实际数，不合成、不假设 1500+。
- 当前状态：**已试抓**。3km、`types=050000`、45 个初始 800m 网格 + 递归细分；425 个网格、1,206 次调用、0 错误/0 未完成；原始 25,857、`poi.id` 去重 12,990、3km 内 6,730、剔除 71 条非餐饮后 **6,659** 条真实餐饮 POI。字段分列：rating 有值 6,652/缺失 7；cost 有值 5,411/缺失 1,248；tag 有值 3,871/缺失 2,788。合成食堂单独 200 目标，不与思源混用。
- 证据：`data/amap_jianda_geocode.json`、`data/amap_jianda_collection.json`、`data/amap_jianda_pois.jsonl`、`data/jianda_poi_spotcheck.json`、`logs/15_jianda_geocode.log`、`logs/16_jianda_collect.log`、`logs/18_sanitize_jianda.log`、`logs/22_jianda_spotcheck.log`。

### 1c. 字段完整度与 C10 未绘制点（2026-10-25）

| 校区 | 总数 | rating 有值 | rating 缺失 | cost 有值 | cost 缺失 | tag 有值 | tag 缺失 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 思源 | 605 | 604 | 1 | 427 | 178 | 309 | 296 |
| 建大雁塔 | 6,659 | 6,652 | 7 | 5,411 | 1,248 | 3,871 | 2,788 |

- 缺失值保持 **NULL**，不填 4.5 / 500 / 空字符串；`data/poi_field_stats.json` 为机器可读证据。
- C10 只绘制 rating 非空点；POI 侧因 rating 为空未绘制数为思源 1、建大 7（`c10_poi_only_not_plotted_no_rating`）。HOME 菜品点若没有真实 rating，同样计入 `meta.not_plotted_no_rating`，不得伪造评分。
- 建大抽查：6,659 行、6,659 个唯一 ID；最远 2,999.5m，**0 条 >3km**；距离分段 0–100m=2、100–300m=22、300–500m=140、500–1,000m=495、1,000–1,500m=635、1,500–2,000m=1,201、2,000–2,500m=2,183、2,500–3,000m=1,981。同名店检查：同名同址重复 0 组；同名且相距 ≤50m 4 对、≤100m 5 对（疑似同店多 ID，S10 导入前需人工裁决），同名远距离组多为连锁分店；同坐标 116 组多为商场/楼宇内不同店，不是同一店。`data/jianda_poi_spotcheck.json` 保留前 20 条与全部检查明细。

## 2. 真实 POI → `restaurants`

| AMap 字段 | `restaurants` 字段 | 规则 |
|---|---|---|
| `id` | `source_record_id` | 唯一；同时 `source_dataset=amap_place_around_20261025` |
| `name` | `name` | 空名拒绝 |
| `type`/`typecode` | `category` | 取小类中文名；原始 typecode 进来源字段/来源表 |
| `location` | `longitude`, `latitude` | GCJ-02 原样；解析失败拒绝 |
| `address` | `address` | 空值 NULL/空串，不编造 |
| `biz_ext.rating` | `rating` | 缺失保持 **NULL**；不得默认 4.5 |
| `biz_ext.cost` | `avg_price` | 缺失保持 **NULL**；不得默认 500/0 |
| `distance` | 不直接使用 | 最终 `distance_meters` 按与中心 haversine **直线距离**计算；字段名保留但契约明确不是步行距离 |
| `tag` | 外食菜品候选 | 仅特色菜字符串，不是完整菜单 |
| — | `is_synthetic=0` | 真实 POI 必填 0 |
| — | `campus` | `SIYUAN` / `JIANDA_YANTA`；按校区存储，不得混用 |
| — | `deleted_at=NULL` | 有效记录 |

**去重**：`poi.id` 唯一；跨格子重复只留一条；3km 内按 haversine ≤3000m 过滤；非餐饮 typecode（不以 05 开头）剔除并单列。失败/拒绝记录单列，不进入最终 605。

**来源字段**：`source_dataset`、`source_record_id`、`source_url`（可空）、`data_version`、`campus`；全部可空，见 SSOT §3/§5.5。

## 3. 按校区合成食堂窗口

- 已确认：**合成**，不是实际采集；`source_type=CANTEEN`、`is_synthetic=1`、`source_dataset=synthetic_canteen_v1`、`campus` 必填。
- 计数：**每个校区单独 200 个目标**（思源 200、建大 200），分别存储、不得混用；不计入真实 POI。思源真实 605 + 思源合成 200 = **805**；建大真实 6,659 + 建大合成 200 = **6,859**；不是 1,700（1,700 只是原规模目标）。
- 命名：每校区 4 个食堂 × 5 个楼层 × 10 个窗口 = 200，如“一食堂·1F·01号窗口”；建大按本校食堂命名，不复用思源名称。
- 坐标：S09 不生成；S10 在用户确认校园边界后，将各校区 200 条坐标落在对应校园多边形内，不得落在周边真实店铺位置。
- 样本与规则：`data/canteen_plan.json`（`PLAN_ONLY_NOT_IMPORTED`，思源样本；建大待建）。
- 与真实校园内 POI 去重：同名/同址/坐标 <30m 时 CANTEEN 优先，AMAP_POI 剔除；按校区分别去重。

## 4. 共享合成菜谱

- 已确认：菜谱使用**合成数据**，不包装成真实采集；两校区**共享**下厨菜谱，不按校区复制；`mode_type` 可含 `HOME_COOKING` 与经人工整理的 `OUT_DINING`。
- 目标：约 **6,300–8,000 行**（合成）；`is_synthetic=1`、`source_dataset=synthetic_recipe_v1`。
- 计数：`dishes_and_recipes` 行数 + 唯一菜名数分别报告；不得用跨模式重复行凑规模。
- 外食菜品：人工整理菜单，AMap `tag` 只作补充；不得把菜谱库菜名任意绑定门店并称为真实菜单。
- 必填/可空：`ingredients_main/aux` 必须有值（可为空数组但需标注）；`price_or_cost`/`cook_minutes` 可空；`feature_vector` 由 S11 打标，未完成留 NULL。
- 失败/未完成：不写占位向量；`tagging_status`/`tagging_error`/`llm_meta` 记录。

## 5. 七个数量逐项对照

| 名称 | 表/公式 | 实测/目标 | 允许合成 | 失败计入 | 来源 |
|---|---|---:|---|---|---|
| 真实 POI（每校区） | `restaurants` where `is_synthetic=0` and `campus=?` | 思源 **605**（原目标 1500+ 未达；D03 已接受实际值）；建大 **6,659**（原目标已满足） | 否 | 否 | AMap `poi.id`+GCJ-02+`campus` |
| 合成食堂（每校区） | `restaurants` where `source_type=CANTEEN` and `campus=?` | 思源 **200**；建大 200 目标 | 是，必须 `is_synthetic=1` | 否 | synthetic_canteen_v1 |
| 单校区合计 | 真实 POI + 合成食堂 | 思源 **805**；建大待定 | 同上 | 否 | 分列；不得把两校区合计掩盖单校区 |
| 合成菜谱行 | `dishes_and_recipes` | 目标 6,300–8,000 | 是，必须标注 | 否 | synthetic_recipe_v1 |
| 唯一菜名 | 唯一 `(name, ingredients_main)` | 与行数分别报告 | 同上 | 否 | 去重后 |
| 成功打标菜品 S | `tagging_status=SUCCESS` 且完整 8 维 | 待 S11 | 否 | **否** | LLM 运行记录 |
| 特征值 | `8 × S` | 待 S11；6,300 全成功也只有 50,400 | 否 | **否** | 每条成功 8 值 |

**硬结论**：若只做 6,300 行且全部成功，特征值 50,400，不能写 60,000+；要写 60,000+，S 必须 ≥7,500。对外数字一律按实际成功数披露。

## 6. 删除、历史与 schema 方案

新增字段全部**可空**、不改变旧字段语义；S09 不执行迁移，S10/S11/S14 幂等实施。

| 对象 | 方案 |
|---|---|
| `restaurants` | 新增 `campus/source_dataset/source_record_id/source_url/data_version/is_synthetic/deleted_at`（均 NULL 可空） |
| `dishes_and_recipes` | `feature_vector` 放宽为 NULL；新增 `allergen_tags/tagging_status/tagging_error/llm_meta/source_dataset/source_record_id/source_url/data_version/is_synthetic/deleted_at`（均 NULL 可空） |
| `group_rooms` | 新增可空 `campus`；建房写入，join 必须同校区；跨校区禁止拼桌 |
| 菜品删除 | 软删除 `deleted_at=now()`；推荐/列表过滤已删除；历史 `eating_logs/room_votes/group_rooms` 仍可联表 |
| 门店下架 | 软删除；其外食菜品不再推荐；历史流水/房间不删除、不改写 |
| 被引用对象 | 不硬删；若后续确需硬删，接口必须 409 并列出引用 |
| `allergen_tags` | 可空 JSON；用于词云/质量面板；不默认加入算法 2 硬过滤 |
| 打标任务 | `tagging_status`/`tagging_error`/`llm_meta` + sidecar manifest；幂等键 `(dish_id, prompt_version, model_version)`；失败不写占位向量 |
| 统计库 | 仿真写独立统计库；演示库保持 4 用户/20 门店/100 菜/9 日志、`group_rooms=0`、`room_votes=0` |

**迁移说明**：先加可空列，再回填可空元数据；历史行 `is_synthetic`、`campus` 未回填前保持 NULL，不得冒充真实/合成或某校区；旧种子数据由 S10 标记合成/校区或替换。`feature_vector` 仅放宽 NULL，成功记录仍必须完整 8 键、有限、0–1。

## 7. 去重与失败计数

- POI：`poi.id` 优先；fallback 名称+地址+坐标；跨网格重复只留一条；CANTEEN/POI 同名同址去重。
- 菜谱：`(normalized_name, sorted(ingredients_main))` 唯一；跨模式同名保留两行时分别计行与唯一名；失败（空名、无主料、不可追溯）不进最终数。
- 重复导入幂等：先查唯一键再插入；日常增量不用 `--force`。
- 失败记录：POI 拒绝原因、菜谱拒绝原因、LLM 失败清单分别保存；不计入规模、不计入特征值。

## 8. 成本、权限与外部依赖

| 项 | 现状/估算 |
|---|---|
| 高德 Key | 已在本地环境变量注入；证据不含 Key。个人 5,000 次/月、3 QPS；本次 133 次调用，0 错误。 |
| 真实 POI 采集 | 思源 605（D03 已裁决接受为样本 A）；建大 6,659（样本 B）；两校区分别计数，不互相补足、不跨校区混算。 |
| 合成食堂/菜谱 | 200 / 6,300–8,000 行；S10 生成，不调用外部付费。 |
| LLM | Key/模型/预算未定；7,500 道/20 道=375 批；建议硬上限 ¥50；S11 BLOCKED。 |
| 仿真 | 独立统计库；r04 单 seed 约 12–16 分钟；S12/S13 重测。 |
| APK | `adb`/`gradle`/Android SDK/Capacitor 缺失；Java 25 可能不兼容 AGP；S18 BLOCKED。 |
| 图片 | 仅本地演示；不公开发布/APK 公开分发/论文公开素材；不声称已授权。 |

## 9. 证据索引

`data/amap_geocode.json`、`data/amap_pagination_probe.json`、`data/amap_collection.json`、`data/amap_pois.jsonl`、`data/canteen_plan.json`、`data/baseline_db.json`、`data/dataset_fingerprint.json`、`logs/01_geocode.log`、`logs/03_pagination_probe.log`、`logs/04_amap_collect.log`、`logs/05_finalize_poi.log`。
