# S09 / r01 提交说明（批次 4 契约、数据来源与指标定稿）

- 提交日期：2026-10-24（Asia/Shanghai）
- 当前步骤：S09（READY）；S10–S20、`/admin` 未开工。
- 性质：**设计补充 + 契约矩阵 + 数据来源调研 + 小样本只读验证**。不是导入完成证明，不是 S09 PASS。
- 开发方结论：**S09 暂不能签 PASS**；至少 3 类硬阻塞（数据来源/许可证、规模算术、schema 缺口），另有构建/真机/LLM/图片授权阻塞，需用户先裁决。

## 一、本步做了什么

| 交付 | 内容 |
|---|---|
| `DATA_PLAN.md` | 中心坐标/3km/POI 契约、食堂方案、菜谱源与许可证、表映射、去重、规模算术、失败计数、schema 缺口 |
| `CONTRACT_MATRIX.md` | 13 个 stats 接口逐条矩阵、17 项大屏指标逐项契约、图→端点交叉表、12/13 冲突记录、查询约束 |
| `EXPERIMENT_PROTOCOL.md` | 种子/参数/输入指纹、重复率定义、未投票/全否决、random 重复、展示封顶、公平性限制、结果统计 |
| `DECISIONS.md` | D01–D32 待裁决项，含选项、建议、影响与 SSOT 同步要求 |
| `data/` | 只读基线、文件哈希、DB schema/行数、路由缺口、数据集指纹、高德官方事实/无 Key 实测、菜谱仓库/许可证检查、素材与构建依赖评估 |
| `logs/` | 每条命令的完整输出、退出码；JSON 证据生成脚本在 `probes/` |

## 二、关键事实（实测，不是转述）

1. **高德无 Key**：`AMAP_API_KEY` 缺失；实际请求 `place/around` 与 `weather` 均返回 HTTP 200、`status=0`、`info=INVALID_USER_KEY`、`infocode=10001`。证据：`data/amap_keyless_check.json`、`logs/03_amap_keyless.log`。
2. **高德分页上限**：官方原文“同请求参数翻页查询最多支持获取200条数据”；`offset` 建议 ≤25；个人认证 5,000 次/月、3 QPS。3km 内要 1,500+ 必须按类型/关键词/网格分区，不能只翻页。证据：`data/amap_official_facts.json`、`logs/05_amap_docs_extract.log`、`logs/06_amap_tables.log`。
3. **坐标系**：官方 FAQ 明确 GCJ-02；不是 WGS-84。证据同上。
4. **POI 不提供完整菜单**：`tag` 只给特色菜（如“烤鱼,麻辣香锅”），`biz_ext.rating/cost` 不保证存在。外食菜品来源必须另行定义（D08/D09）。
5. **菜谱源**：
   - `HowToCook`：Unlicense（public domain），实测 373 个菜谱 Markdown（含 1 个模板，实际可用 **372**），规模远不足 6,300。
   - `XiaChuFang Recipe Corpus`：1,520,327 条 / 30,060 道，规模够，但**没有明确许可证**；OpenDataLab 搜索摘要显示“仅用于学术目的，请勿商用”，主页面为 JS 动态页，未能从主许可文本验证。
   - `Ta-da`（12,142 条）与 `CookBook-KG`：无 LICENSE；Ta-da 完整数据未公开。
   - 结论：**没有找到“许可明确 + 规模 ≥6,300 + 中文 + 可再分发”四条件同时满足的公开源**。证据：`data/recipe_source_assessment.json`、`data/recipe_repos_check.json`、`logs/07_recipe_repos.log`、`logs/08_recipe_details.log`。
6. **规模算术**：6,300×8=**50,400**，达不到 60,000+；要 60,000+，成功打标菜品必须 ≥**7,500**。当前种子 100 行/95 唯一名/800 特征值。详见 `DATA_PLAN.md` §6。
7. **schema 缺口**：`allergen_tags` 无字段；`restaurants`/`dishes` 无来源追溯字段；无软删除；`feature_vector NOT NULL`，无法表示未打标/失败；无打标任务表；仿真在隔离库、主库 `room_votes=0`。详见 `DATA_PLAN.md` §9。
8. **统计接口**：SSOT 文字 12、路由表 13（含 `quality`）；当前实际 `/admin/stats/*` 路由 **0** 个。建议保留 13 并同步 SSOT，不删除 quality。详见 `CONTRACT_MATRIX.md` §5。
9. **C08 缺口**：13 个 stats 中没有“热门菜品榜”端点；需扩 `race` 或新增端点，不能用假数组。详见 `CONTRACT_MATRIX.md` §4。
10. **素材授权**：95 张菜品图来自小红书笔记截图，台账无 license；公开再分发/APK/论文附图授权未证明。证据：`data/assets_baseline.json`、`data/dependency_and_license_assessment.json`。
11. **构建工具**：`adb`/`gradle`/Android SDK/Capacitor 配置/依赖均缺失；Java 25.0.2 可能不匹配 Android Gradle Plugin。S18 目前 BLOCKED。
12. **LLM**：Key/模型/单价均未定；按 7,500 道、20 道/批 = 375 批；建议硬上限 ¥50、失败重试 3 次、断点续跑；实际费用待模型报价。S11 目前 BLOCKED。

## 三、未执行（符合 S09 禁令）

- 未实现 POI/菜谱导入（S10）。
- 未实现 LLM 打标/查询扩容（S11）。
- 未运行 S12/S13 正式仿真或对照实验。
- 未实现 S14+ CRUD/stats/大屏；未新增后台页面；未修改 `/admin`。
- 未修改核心算法、数据库 schema、生产/演示库；未执行 `--force`；未发起大规模付费 API 调用。
- 未修改 `docs/review/STAGE_STATUS.md`；未创建 `REVIEW.md`；未自签 PASS。

## 四、回归与保护

- 只读 DB 基线：`python -m pytest -q` → **161 passed**（`logs/16_pytest_baseline.log`；S09 未改业务代码，此日志仅证明起点）。
- 演示库只读：4 用户 / 20 门店 / 100 菜 / 9 日志 / `group_rooms=0` / `room_votes=0`；未写库。
- 自校验：`validate_evidence.py` exit 0；全部证据文件入 `data/evidence_index.json`；基线文件哈希未变，演示库 SHA 与基线相同（`data/validation.json`、`logs/17_validate_evidence.log`）。
- 未改 `backend/eatwhat.db`（SHA 前后对比见 `BASELINE.md` 与 `data/file_hashes.json`）。
- 未改 `MASTER_SPEC.md`、`BATCH4_PLAN.md`、`DASHBOARD_EXPANSION.md`、`STAGE_STATUS.md`；仅在 `docs/review/stages/S09/r01/` 新增本包。

## 五、需要用户先答复的最小集合

1. 实际学校/校区或中心坐标（D01）。
2. 是否提供高德 Key（D02）。
3. 菜谱数据源与许可证（D05）；若没有，接受哪种替代。
4. 200 食堂窗口合成还是实采（D04）。
5. 60,000+ 特征值是否改为“成功打标数×8”（D06）。
6. stats 是否保留 13 个并同步 SSOT（D11）。
7. 是否允许为 allergen_tags/软删除/来源/打标状态修改 schema（D16–D19）。
8. 仿真数据写主库还是独立统计库（D20）。

完整裁决表见 `DECISIONS.md`。

## 六、结论

S09 的图纸、数据来源证据和缺口已经齐备；但 **BLOCKED 项未关闭前不能 PASS，也不能进入 S10**。开发方不签 PASS，提交后停手，等待 Codex 独立审查与用户裁决。

证据包：`docs/review/stages/S09/r01/`。
