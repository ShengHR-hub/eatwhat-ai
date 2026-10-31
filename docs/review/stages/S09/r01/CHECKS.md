# CHECKS —— S09 / r01

- 执行日期：2026-10-24（Asia/Shanghai）
- 工作目录：`D:\EatWhat`；pytest 在 `backend/`。
- 所有网络检查只读；无付费批量调用；无 Key 请求使用空 Key，仅记录错误。
- 日志均在 `logs/`；结构化结果在 `data/`。

| # | 命令 / 动作 | 退出码 | 结果 | 日志 |
|---:|---|---:|---|---|
| 1 | 采集日期/时区/Python/Node/npm/git | 0 | 2026-10-24T23:23:44+0800；Python 3.13.9 / Node v24.19.0 / npm 11.17.0；无 commit | `logs/01_env.log` |
| 2 | `python docs/review/stages/S09/r01/probes/baseline_probe.py` | 0 | env、file_hashes、db_baseline、routes、route_gap、external_deps、assets 全部生成 | `logs/02_baseline.log` |
| 3 | 无 Key 请求 `GET /v3/place/around` 与 `/v3/weather/weatherInfo` | 0 | HTTP 200；`status=0`、`INVALID_USER_KEY`、`infocode=10001` | `logs/03_amap_keyless.log`、`data/amap_keyless_check.json` |
| 4 | 抓取高德搜索/计费/FAQ 官方页面 | 0 | 搜索页 200/366805B；计费页 200/95635B；FAQ 200/121261B | `logs/04_amap_docs.log`、`data/amap_docs_check.json` |
| 5 | 高德官方文本/表格解析 | 0 | 取得 `offset≤25`、`radius 0–50000`、同参数最多 200 条、GCJ-02、个人 5000 次/月 3 QPS | `logs/05_amap_docs_extract.log`、`logs/06_amap_tables.log`、`data/amap_official_facts.json` |
| 6 | GitHub API 检查菜谱仓库与 LICENSE | 0 | HowToCook Unlicense；Ta-da/CookBook-KG 无 license；TheGodOfCookery Apache-2.0 但数据来自 XiaChuFang | `logs/07_recipe_repos.log`、`data/recipe_repos_check.json` |
| 7 | 拉取 README + `git/trees/master?recursive=1` 统计 HowToCook | 0 | 373 个 `dishes/**/*.md`；396 个 md；982 个 tree items | `logs/08_recipe_details.log`、`data/recipe_details.json` |
| 8 | 抓取 OpenDataLab XiaChuFang 页面 | 0 | HTTP 200 但仅 2643B JS 外壳；未能从主许可文本验证；搜索摘要为“仅学术/勿商用” | `logs/09_opendatalab.log`、`data/opendatalab_xiachufang.json` |
| 9 | 抓取 XiaChuFang 数据集主页 | 0 | 1,520,327 条 / 30,060 道；页面无 license 字样 | `logs/10_xiachufang_page.log` |
| 10 | 种子菜名/跨模式重复统计 | 0 | 100 行 / 95 唯一名；5 组跨模式同名；唯一 name+主料 95 | `logs/11_seed_dedup.log` |
| 11 | 有效 8 维向量统计 | 0 | 100/100 有效；当前特征值 800 | `logs/12_feature_baseline.log` |
| 12 | 高德 POI 响应字段表解析 | 0 | 取得 id/name/type/typecode/address/location/distance/tag/biz_ext.rating/cost 等字段 | `logs/13_amap_fields.log` |
| 13 | 数据集指纹 | 0 | `3e24f458071d67f3097d28ffb1d997d7a0188c18b0e28251aca7b7cf0c27625e` | `logs/14_dataset_fingerprint.log`、`data/dataset_fingerprint.json` |
| 14 | 前端依赖许可证读取 | 0 | echarts Apache-2.0；vue/daisyUI/lottie-web/auto-animate/vueuse-motion MIT；GSAP Standard no-charge；canvas-confetti ISC | `logs/15_dep_licenses.log` |
| 15 | `cd backend; python -m pytest -q -p no:cacheprovider --basetemp=D:/EatWhat/.pytest-tmp-s09` | 0 | **161 passed**（S09 未改业务代码，作为起点基线） | `logs/16_pytest_baseline.log` |
| 17 | HowToCook 菜谱去重小样本 | 0 | 373 个 md（含 1 个模板）；**372 个可用**、372 个唯一名、重复名 0；分类计数见 JSON | `logs/18_howtocook_dedup.log`、`data/howtocook_dedup.json` |
| 18 | `python docs/review/stages/S09/r01/probes/validate_evidence.py` | 0 | JSON 全部可解析；基线文件未变；演示库 SHA 未变、`group_rooms=0`、`room_votes=0`；全部证据文件入 index | `logs/17_validate_evidence.log`、`data/validation.json`、`data/evidence_index.json` |

## 未执行项（符合 S09 禁令）

- 未实现/未运行 S10 POI 与菜谱批量导入。
- 未实现/未运行 S11 LLM 打标与查询扩容；未配置 Key、未消耗 tokens。
- 未运行 S12/S13 正式仿真或对照实验。
- 未实现 S14+ CRUD/stats/大屏；未新增后台页面；未修改 `/admin`。
- 未修改核心算法、schema、生产/演示库；未执行 `--force`。
- 未做大范围付费 API 调用；无 Key 请求不产生数据。
- 未创建 `REVIEW.md`，未修改 `STAGE_STATUS.md`，未自签 PASS。

## 环境/证据限制

- OpenDataLab 为 JS 动态页，HTTP 抓取只得到外壳；XiaChuFang 的许可证只能标“未找到明确许可/未从主文本验证”，不能写成“已确认可商用/可再分发”。
- 高德 POI 实际数量无法测：Key 缺失，空 Key 请求只证明“无 Key 不可用”，不是 POI 数量。
- 菜品图为小红书截图，台账无 license；本步只记录风险，不宣称已授权。
- `git status` 内含历史 staged/unstaged/untracked；本包只新增 `docs/review/stages/S09/r01/`，未清理或提交既有变更。
