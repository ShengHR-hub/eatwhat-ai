# S09 / r03 解封送审包

- 日期：2026-10-25（Asia/Shanghai）
- 性质：**只请求 Codex 独立复审 S09 解封条件**；不请求 S10，不签 PASS，不修改台账。
- 受审对象：S09/r02 的双校区补证、D03 正式裁决、字段统计、C10 NULL 口径、r02 manifest 84 项；r02 原包保留。
- 当前状态：`S09=BLOCKED`、`S10–S20=LOCKED`；`docs/review/STAGE_STATUS.md` 未改，hash 与 r02 manifest 一致。
- 送审结论由 Codex 签发；本文件不写 PASS，不把“证据成立”写成“已放行”。

## 1. 三条 BLOCKED 的逐条回应

### B1：双校区超出 r02 范围

r02 REVIEW 要求：先确认建大雁塔中心；按思源同一套 3km/`types=050000`/网格/去重采集；建大合成食堂单列；契约明确 `campus`、外食/群组/POI/stats 过滤和前端切换。

现状：

- 建大雁塔高德地名搜索实际返回 GCJ-02 **108.967153,34.236991**（碑林区，未返回草堂）。
- 建大采集：45 个初始 800m 网格 + 递归细分，**425 个处理格 / 1,206 次调用 / 0 错误 / 0 未完成**；原始 25,857 → `poi.id` 去重 12,990 → 3km 内 6,730 → 剔除 71 条非餐饮 → **真实 POI 6,659**。
- 建大合成食堂 200 单独计数，**6,659 + 200 = 6,859**，不与思源混用。
- 思源已用同一版递归脚本复跑：45 初始 / **61 处理格** / 133 调用 / 0 未完成，**605 不变**。
- 契约已覆盖 `restaurants.campus`、`group_rooms.campus`、外食/群组按校区过滤、下厨菜谱共享、前端校区切换、stats `campus` 过滤与 `by_campus + total`；见 `MASTER_SPEC.md` §3/§5.5、r02 `CONTRACT_MATRIX.md` §1.1、`DATA_PLAN.md` §0、`EXPERIMENT_PROTOCOL.md` §1.1。
- 建大抽查：6,659 行/6,659 唯一 ID；最远 2,999.5m，**0 条 >3km**；0 条禁止字段。同名同址重复 0 组；同名 ≤50m 4 对、≤100m 5 对，作为 S10 人工判断项保留原始 ID。

### B2：D03 未裁决

r02 REVIEW 要求：分别报告真实 POI/合成食堂/合计，由用户接受实际数量、修改目标或批准新范围，并更新 SSOT/契约；禁止复制、合成或跨校区补数。

现状（用户 2026-10-25 正式裁决，已写入 r02 `DECISIONS.md` D03）：

- 思源 **605 = 样本 A**，按实际值接受，不再要求补足 1500+；
- 建大 **6,659 = 样本 B**，按实际值接受；
- 分校区报：思源 605+200=**805**；建大 6,659+200=**6,859**；
- 不把 `1700` 当实际总数；建大数据**不得补思源**；两校区**不得跨校区混算/拼桌**；
- 合成食堂仍分别 200 目标、分别标注，不计入真实 POI。
- `MASTER_SPEC.md` 已同步 D03 与 C10 NULL 口径（版本仍标 v2.3.5，未擅自升版）。

### B3：r02 manifest 被提交后文档变更打破

r02 REVIEW 要求：不回写 r02 manifest 掩盖差异；在 r03 重新生成完整 manifest，停止修改后交 Codex 复核。

现状：

- r02 当前工作 manifest 为 **84 项**；本包 `probes/validate_r03.py` 独立重算 **84/84 无差异**。
- r02 原包目录保留；r03 另生成自己的 `SOURCE_MANIFEST.json`，并把 r02 manifest 的哈希、84 项路径与哈希、r04 PASS 原件写入 r03 manifest。
- 需要如实说明：r02 manifest 在 D03/字段补证后由开发方重建为 84 项，因此它**不是 r02 提交时的 74 项原件**；r02 REVIEW 记录的失配仍保留在 r02 `REVIEW.md`。本包请求 Codex 以 **r03** 为复审对象；若 Codex 认为必须保留一个不可变的 r02 旧 manifest 才能闭合 B3，请在复审结论中明确要求的打包方式，开发方不自行回写历史。

## 2. 送审内容

| 内容 | 路径 | 证明 |
|---|---|---|
| 思源同脚本复跑 | `docs/review/stages/S09/r02/logs/20_siyuan_recollect.log`、`data/amap_collection.json`、`data/amap_pois.jsonl` | 45/61 格、133 调用、0 未完成、605 不变 |
| 建大试抓 | `data/amap_jianda_geocode.json`、`data/amap_jianda_collection.json`、`data/amap_jianda_pois.jsonl` | 中心 108.967153,34.236991；6,659；6,859 |
| 字段有值/缺失 | `data/poi_field_stats.json` | rating/cost/tag 分列；缺失保持 NULL |
| C10 NULL 口径 | `MASTER_SPEC.md` §5 模块 8/§6.5、r02 `CONTRACT_MATRIX.md`、`DASHBOARD_EXPANSION.md` | 全量 restaurants+dishes；只绘非空；`meta.not_plotted_no_rating` 为整数；HOME 不返回 `applicable=false` |
| 建大抽查 | `data/jianda_poi_spotcheck.json` | 前 20、类型/距离段、同店多 ID、3km 越界 |
| D03 裁决 | r02 `DECISIONS.md` D03、`MASTER_SPEC.md` | 样本 A=605、样本 B=6,659；分校区 805/6,859；不按 1700 合计 |
| r02 manifest | r02 `SOURCE_MANIFEST.json` | 84 项；r03 独立重算 84/84 |
| PC01 PASS 原件 | `docs/review/stages/PC01/r04/REVIEW.md` | r04 PASS（manifest 8 项匹配） |
| PC02 PASS 原件 | `docs/review/stages/PC02/r02/REVIEW.md` | **现行 PASS 是 r02**；PC02/r01 是 FAIL 历史，不作为 PASS 附上 |
| PC03 PASS 原件 | `docs/review/stages/PC03/r04/REVIEW.md` | r04 PASS（manifest 7 项匹配） |
| r04 总报告 | `docs/review/clearance-codex-r04-2026-10-24/REPORT.md` | PC01/PC03 PASS、PC02 维持 PASS；不把本轮 S09 证据当作 r04 新测试 |
| r03 自校验 | `validation.json`、`data/r03_evidence.json`、`logs/01_validate_r03.log` | 机器可读汇总 |

> 说明：r04 总报告写“PC02/R01 维持既有 PASS”，但仓库中的 `PC02/r01/REVIEW.md` 结论是 **FAIL**，实际现行 PASS 原件是 `PC02/r02/REVIEW.md`。本包按实际文件附 PASS 原件，并把这个命名/版本差异列入送审问题，请 Codex 判定是否影响三项前置条件。

## 3. 送审问题

请 Codex 独立回答：

1. **B1 是否消除？** 建大中心/采集/去重/校区字段/过滤/前端切换/统计分校区证据，是否足以覆盖 r02 REVIEW 对双校区的缺口？
2. **B2 是否消除？** D03 的“样本 A=605、样本 B=6,659、分校区 805/6,859、不按 1700 合计、不得跨校区补数/混算”是否构成用户正式裁决，并已同步 SSOT/契约？
3. **B3 是否消除？** r02 manifest 现为 84 项且本包独立重算 84/84；r03 另生成 manifest。鉴于 r02 旧 74 项 manifest 已被重建，Codex 是否接受 r03 作为新的受审身份？若必须保留旧 manifest，请给出明确打包要求。
4. **S09 是否可从 BLOCKED 解除？** 本包只请求解封复核，不请求 S10；请 Codex/用户按流程更新台账，开发方不自行改台账、不签 PASS。
5. **PC02 PASS 版本差异**：`PC02/r02` 是现行 PASS、`PC02/r01` 是 FAIL；r04 总报告写“PC02/R01 维持 PASS”。请确认三项前置条件的 PASS 绑定是否仍成立。

## 4. 残留说明

- 建大同名/同基名 ≤200m 的 101 对，以及同名 ≤100m 的 5 对，**留待 S10 人工判断**是否同店合并；本包保留原始 `poi.id`，不删除、不合并。
- 建大 `0090汉堡工厂(长安大学本部三楼调剂餐厅店)` 距中心 259.8m，名称含“长安大学”，属高德命名/分店信息，未越界；S10 可按 address 复核。
- 思源 605 是按用户裁决接受的样本 A，不再以 1500+ 作为 S10 阻塞；差额仅作历史记录。
- 本轮未重跑 r04 的 pytest/build；r04 PASS 原件与 manifest 哈希随包引用，不冒充本轮新测试。
- 未改业务代码、演示库、`/admin`；未创建/修改 `docs/review/stages/S09/r03/REVIEW.md`；r02 `REVIEW.md` 未改。

## 5. 保护与验证

- `python docs/review/stages/S09/r03/probes/validate_r03.py`：见 `validation.json`；要求 `ok=true`。
- `python docs/review/stages/S09/r02/probes/validate_evidence.py`：r02 自校验仍为 `ok=true`。
- `python docs/review/stages/S09/r02/probes/doc_sync_check.py`：`live_stale=[]`、`code_changed=[]`、DB SHA 未变、`group_rooms=0`/`room_votes=0`、`admin_routes=[]`。
- r02 manifest：84 项逐项 SHA-256/字节复核；r03 manifest 另列全部受审文件。
- Key 仅从本地环境变量注入，未写入本包任何文档、日志或 JSON。
- **不进入 S10、不签 PASS、不改台账。**
