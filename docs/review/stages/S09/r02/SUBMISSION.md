# S09 / r02 提交说明（批次 4 契约修订 + v2.3.4 双校区同步）

- 提交日期：2026-10-25（Asia/Shanghai）
- 当前步骤：S09；台账当前状态 `BLOCKED`（提交时曾为 `REVIEW_PENDING`）；S10–S20 仍 LOCKED。
- 性质：用户已确认口径的 SSOT 修订 + 真实高德 3km POI 只读采集 + 合成食堂/菜谱方案 + 统计/大屏/实验契约 + 双校区文档同步。
- **开发方不签 PASS**；等待 Codex 独立复审。

## 〇、2026-10-25 文档同步（v2.3.4 双校区）

本轮**只同步文档**，不改代码/数据库/`/admin`，不签 PASS，不开 S10。SSOT 从 v2.3.3 升到 v2.3.4，v2.3.3 历史数字保留不改写。

- 新增校区 A 思源 / 校区 B 建大雁塔双校区：A 中心 `109.078487,34.234818`、真实 POI 605、合成食堂 200、合计 805；B 中心 `108.967153,34.236991`、真实 POI **6,659**、合成食堂 200、合计 **6,859**（未返回草堂，目标 1500+ 已满足）。
- `1700` 明确为原规格总数目标，不是实际数；`17` 只是大屏图数量；“2km 不足 1700 再扩 3km”规则作废，两校区固定 3km。
- `restaurants.campus`、`group_rooms.campus` 可空字段；前端校区切换；外食/群组按校区过滤，跨校区不能拼桌；下厨菜谱共享；统计分校区 + 合计。
- C10 改为 `restaurants`+`dishes` 全量，气泡=频次；HOME 无真实 rating 时 NULL，评分轴只绘非空，`meta.not_plotted_no_rating` 报未绘制点数（整数）。
- 菜谱共享合成；食堂按校区分别合成/标注；图片仅本地演示。
- 文档同步不改 S09/r02 状态：当前台账为 `BLOCKED`（r02 独立复审）；S10 仍 LOCKED；r03 历史结论与 r04 后续 PASS 记录均保留。

## 一、本步完成内容

| 交付 | 内容 |
|---|---|
| `MASTER_SPEC.md` v2.3.5 | 13 stats、N/A 响应、C08/C10/C11/C13/C17、合成数据标记、schema 可空字段、独立统计库、实验/统计默认口径、真实 POI 实测与目标差额 |
| `DECISIONS.md` | D01–D38 确认/阻塞状态；D03 已由用户正式裁决（思源 605=样本 A，建大 6,659=样本 B，分校区报，不是 1700 合计） |
| `DATA_PLAN.md` | 中心点、POI 契约/去重、200 合成食堂、合成菜谱、七个数量、schema/软删除、成本 |
| `CONTRACT_MATRIX.md` | 13 个 stats 接口 + 17 项大屏指标；C08/C10/C11/C13/C17；N/A 统一响应 |
| `EXPERIMENT_PROTOCOL.md` | R=30、重复率、7×4、缺席/全否决、展示封顶、独立统计库、合成人设声明 |
| 真实高德证据 | 地名搜索实际坐标、3km 分页、网格去重、API 状态、缺失字段、真实/合成分列 |
| 合成食堂方案 | 200 条目标、`is_synthetic=1`、`PLAN_ONLY_NOT_IMPORTED`、与真实 POI 分列 |
| 验证 | 161 passed、JSON/哈希/DB 保护/Key 不泄漏校验通过 |

## 二、真实高德结果（Key 仅环境变量，不落盘）

- 校区 A 思源：`西安思源学院` → `109.078487,34.234818`（GCJ-02，2026-10-25T00:24:28+08:00）。
- 校区 B 建大雁塔：中心 `108.967153,34.236991`；真实 POI **6,659**（3km/050000/递归网格，0 未完成）；合成食堂 200 单列，合计 **6,859**；未返回草堂，目标 1500+ 已满足。
- 思源 3km 直接查询：`types=050000`、`count=600`；page 1–8 有数据，page 9 起为空（同参数最多 200 条）。
- 思源网格采集：与建大同版递归脚本（2026-10-25T02:25:40+08:00）45 个初始 800m 网格 + 递归细分（61 个处理格）、133 次调用、0 错误/0 未完成；原始 2,230、`poi.id` 去重 1,258、3km 内 607、剔除 2 条非餐饮后 **真实餐饮 POI 605**（复跑不变）。
- 建大 3km 直接查询同样 `count=600`（API 截断值，不能当总量）；递归网格 425 个、1,206 次调用、0 错误/0 未完成；原始 25,857、去重 12,990、3km 内 6,730、剔除 71 条非餐饮后 **真实餐饮 POI 6,659**。
- 去重规则：`poi.id` 唯一；跨格子重复只留一条；最终按中心 haversine ≤3000m；非 05 开头 typecode 剔除。
- 字段完整度（有值/缺失分列）：思源 rating 604/1、cost 427/178、tag 309/296；建大 rating 6,652/7、cost 5,411/1,248、tag 3,871/2,788。缺失值按契约保持 NULL，不填伪默认。
- 分列：思源 605+200=**805**；建大 6,659+200=**6,859**；不按 1,700 合计，不用合计掩盖单校区数。
- **D03 裁决**：思源 605 为样本 A、建大 6,659 为样本 B，均接受实际值；原 1500+ 目标差额保留为历史记录，不再作为 S10 阻塞；**禁止合成补足、建大补思源、跨校区挪用或混算**。
- **建大抽查**：6,659 行/6,659 唯一 ID；最远 2,999.5m，0 条 >3km；同名同址重复 0 组；同名且相距 ≤50m 4 对、≤100m 5 对（疑似同店多 ID，S10 导入前人工裁决）；同坐标 116 组多为商场/楼宇内不同店，不等同于同一店。明细见 `data/jianda_poi_spotcheck.json`。

证据：`data/amap_geocode.json`、`data/amap_pagination_probe.json`、`data/amap_collection.json`、`data/amap_pois.jsonl`、`logs/01_geocode.log`、`logs/03_pagination_probe.log`、`logs/04_amap_collect.log`。

## 三、已确认口径

- 双校区：思源/建大按 `campus` 分开存；外食/群组按校区过滤；下厨共享；前端校区切换；统计分校区+合计。
- 中心点/3km；真实 POI 目标 1500+、禁止合成；食堂按校区分别 200 目标并标记；合成菜谱共享并标记；图片仅本地演示。
- 菜谱行数 + 唯一菜名数分别报告；特征值 = 8×成功打标数；不固定声称 60,000+。
- 13 stats（含 quality）；不删 quality；不新增第 14 个；C08 用 `race.latest_top10`。
- N/A 统一 `200 {applicable:false, reason, items:[], meta:{}}`。
- C10 为 restaurants+dishes 全量，气泡=频次；OUT_DINING 用真实 rating，HOME 无真实 rating 时 NULL，评分轴只绘非空，`meta.not_plotted_no_rating` 报未绘制点数（整数）；C11 单位=票；C13=allergen_tags+菜名分词；C17 分母=快照 dishes 总数、分子=完整成功 8 维。
- POI 缺失 rating/cost 保持 NULL；`distance_meters` 为直线距离；外食菜品人工菜单 + AMap tag 补充。
- R=30；重复率=相邻同菜系/累计餐次；7×4 时段；Asia/Shanghai；全库；共现≥3、top_n=30/上限100、过滤通用调味；C07 dishes 行数、C12 logs 决策量；overview 返回 `meta.scope`。
- 仿真数据写独立统计库，不写演示库。

## 四、Schema 方案（只新增可空字段，不在本步迁移）

- `restaurants`：`campus/source_dataset/source_record_id/source_url/data_version/is_synthetic/deleted_at`（全部可空）。
- `dishes_and_recipes`：`feature_vector` 放宽为 NULL；新增 `allergen_tags/tagging_status/tagging_error/llm_meta/source_dataset/source_record_id/source_url/data_version/is_synthetic/deleted_at`（全部可空）。
- 不改变旧字段语义；软删除用 `deleted_at IS NULL`；历史流水/投票/报告可通过原 ID 联表。
- 迁移由 S10/S11/S14 幂等实施；S09 不改 schema。

## 五、验证与保护

- `pytest` → **161 passed**（`logs/08_pytest.log`）。
- `validation.json` → **ok=true**：JSON 全部可解析；思源 605+200=805、建大 6,659+200=6,859；两校区 POI 文件分别 605/6,659 行、唯一 ID 相等、0 条越界；字段完整度与抽查/字段统计证据可解析；SSOT 含 13 且不含旧计数；S09=BLOCKED、S10=LOCKED；演示库 SHA 未变、`group_rooms=0/room_votes=0`；Key 未出现在任何证据文件。
- 新增证据：`data/poi_field_stats.json`（两校区 rating/cost/tag 有值/缺失）、`data/jianda_poi_spotcheck.json`（前 20 条、类型/距离段、同店/越界检查）、`logs/20_siyuan_recollect.log`（思源同脚本复跑）、`logs/22_jianda_spotcheck.log`、`logs/23_poi_field_stats.log`。
- 未写生产/演示库；未改 schema；未导入批量数据；未实现 `/admin`；未创建/未修改 `REVIEW.md`（r02 下 Codex 已生成的 BLOCKED REVIEW 保持原样）。

## 六、仍阻塞/未解决

1. **D03 已裁决，不再阻塞**：思源 605=样本 A、建大 6,659=样本 B，分校区报；不得合成补足、建大补思源或跨校区混算。
2. **S09 台账**：当前仍为 `BLOCKED`；解封由 Codex/用户按流程处理，开发方不自行改台账、不签 PASS。
3. **S11 LLM**：Key/模型/预算未定；375 批（7,500 道）建议硬上限 ¥50；S11 BLOCKED。
4. **S18 Android/真机**：adb/gradle/Android SDK/Capacitor/设备缺失；S18 BLOCKED。
5. **图片**：仅本地演示；不进入公开发布/APK 公开分发/论文公开素材；未声称已授权。

## 七、结论

r02 已提交，S09 台账当前为 `BLOCKED`（r02 独立复审）；开发方不签 PASS，S10 及后续继续 LOCKED。D03 已由用户裁决并落入 `DECISIONS.md`；台账解封由 Codex/用户按流程处理，开发方不自行修改。
