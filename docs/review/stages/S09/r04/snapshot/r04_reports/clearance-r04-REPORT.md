# r04 独立复审报告

审查日期：2026-10-24（Asia/Shanghai）  
范围：PC01/R02 r04、PC03/F12 r04；PC02/R01 维持既有 PASS。  
限制：未修改业务代码，未触碰 `/admin`、S09 数据或演示库业务数据。

## 结论

**PC01/R02：PASS。PC02/R01：维持 PASS。PC03/F12：PASS。**

r04 关闭了上一轮报告中的 R3-01、R3-02、R3-03。S09 可以进入下一步准备；批次 4 的实际开发仍须遵守台账中的逐步验收，不因本轮清账 PASS 自动通过后续 S10–S20。

## 证据身份

PC01/r04 与 PC03/r04 的 `SOURCE_MANIFEST.json` 所列文件逐一计算 SHA256，均与 manifest 一致（PC01 8 项、PC03 7 项）。本报告不把开发方自报当作唯一依据，所有关键结论均有下列独立复验支撑。

## PC01 / R02

### R3-01 播种守卫：PASS

源码位置为 `backend/scripts/init_seed_data.py:281-561`，破坏性入口在 `:780-795`：`ensure_benchmark_ready()` 完成后才调用 `_clear_all()`。独立运行 `docs/review/stages/PC01/r04/probes/seed_probe.py`，9 个真实 CLI 用例全部符合预期：非法 ISO 时间、跨时区旧时间、非法 sample/curve/策略/柱值、缺失快照、拒绝 incoming 后的保留行为均以 exit 1 结束，数据库逻辑摘要和目标快照保持不变；完整仿真输出带 `params` 的导入 exit 0，落盘仅保留 SSOT 四键；重复执行和显式 `--allow-stale-benchmark` 正例通过。

源码层面确认：`datetime.fromisoformat()` 后统一到 UTC；JSON `NaN`、`Infinity`、重复键拒绝；bool 不被当作整数；曲线日序、长度、有限范围、策略身份和柱值范围均有检查；incoming 与当前快照、库内时间的比较在临时文件写入之前完成，临时文件回读成功后才替换目标。

### R3-03 满意度口径：PASS

`backend/algorithms/simulate_personas.py:353-380` 当前逐人读取原始 `satisfaction`，VETO 取 0、缺席由生产报告给出 TIMEOUT 分，四人均值/最低值完成后统一 `min(100, value)`。独立固定样本 `[0, 67.58, 97.82, 107.70]` 得到 **68.28 / 0**，逐人封顶的 66.35 已不再使用。

两组隔离仿真和存档复算逐点一致：

| seed | avg（mixed / average / random） | least（mixed / average / random） | d14 ours / base |
| --- | --- | --- | --- |
| 20261024 | 94.23 / 94.49 / 72.83 | 75.37 / 74.77 / 38.82 | 0.0091 / 0.2927 |
| 7 | 93.94 / 94.06 / 72.57 | 73.62 / 73.02 / 38.46 | 0.0098 / 0.2746 |

独立查询确认每个群组库为 1000 个房间、40000 张票、每房 40 张，唯一 `(user_id, dish_id)` 无重复；演示库 `group_rooms=0`、`room_votes=0`。票型计数与存档一致。两策略使用同一房间、成员、候选卡和票矩阵，random 只在同一报告的卡片集合上抽签。

基线定义是同一生产推荐器、同一人设和数据，只将查询时钟推后 `LOOKBACK_DAYS + 1` 天，作为“无近期历史/冷启动”的衰减消融，方法上公平但不等同于所有产品维度的全新用户基线。横向 rank 票型是透明的合成压力测试，能避免所有成员只给高先验卡高分，但不能当作真人投票分布。d14 与首轮 0.1696 的差异来自仿真实现、票型、满票和 RNG 口径已变化，不能宣称由单一改动造成；当前 r04 的同策略复算与快照一致。

### 回归

- `backend` 独立 pytest：**161 passed**（工作区 basetemp，505 warnings）。
- `python docs/review/stages/PC01/r04/probes/seed_probe.py`：exit 0，9 例 PASS。
- `metric_probe.py`、`recompute_bars.py`：exit 0，固定样本和两 seed 柱值逐点一致。

## PC03 / F12

### R3-02 颜色门禁：PASS

`scripts/check-colors.mjs:65-344` 按 JS、CSS、Vue template 分开处理：JS 正则/字符串/模板字符串与注释，CSS 字符串、`url(...)` 与块注释，Vue 的 `<script>`/`<style>` 分段及 HTML 注释。主题令牌和精确上游文件白名单保持原约束，非上游 `components/bits/` 业务文件的裸色仍被拦截。

独立运行 `python scripts/gate_probes.py`：23 个隔离探针和 sandbox baseline 全部 PASS；此前两个漏检反例（`/[/*]/` 后裸色、CSS `url(https://...//...)` 后裸色）现在均 exit 1 且定位，Vue HTML 注释正例 exit 0，大写 HEX/RGB/HSLA、注释后同行代码、令牌后同行代码、非上游 bits 和本地裸色 token 也均符合预期。真实目录 `node scripts/check-colors.mjs` 扫描 38 文件 exit 0。

### 回归与浏览器范围

`frontend` `npm run build` exit 0（775 modules，约 7 秒）。r04 只修改门禁脚本和探针，没有修改 `.vue` 业务页面、主题样式、路由或接口契约，因此本轮不需要重复真实浏览器点击；r03 的浏览器证据继续作为既有 UI 证据，但不冒充 r04 新测试。若后续批次修改页面或接口，仍须按台账单独做真实浏览器验收。

## 残余边界

本报告没有验收 `/admin`、完整多人 WS、APK 真机或 S00–S08 专项；这些仍由台账中的后续步骤控制。PC01 的仿真仍是合成人设实验，论文应保留票型、缺席和冷启动基线的限定。

## 复审依据

- `docs/review/stages/PC01/r04/SUBMISSION.md`
- `docs/review/stages/PC01/r04/data/seed-results.json`
- `docs/review/stages/PC01/r04/data/fixed_samples.json`
- `docs/review/stages/PC01/r04/data/db_inventory.json`
- `docs/review/stages/PC01/r04/data/db_benchmark_check.json`
- `docs/review/stages/PC03/r04/logs/gate_probes.json`
- `docs/review/stages/PC03/r04/logs/20_check_colors_real.log`
- `docs/review/stages/PC03/r04/logs/20_build.log`
