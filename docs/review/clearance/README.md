# 批次 4 准入清账（R02 / R01 / F12）证据包

依据：`D:\谷歌\BATCH4_PRE_CLEARANCE.md`（用户下发），顺序 R02 → R01 → F12，一次改完统一审查。

> 声明：本目录只放**证据**，不放结论。开发方不自签 PASS、不改 `docs/review/STAGE_STATUS.md`。
> 每项是否能放行，由审查方独立判定。

## 三项的状态

| 项 | 内容 | 证据 | 我的自测结论（不作放行依据） |
|---|---|---|---|
| R02 | `benchmark_json` 改为真跑仿真 | `r02/` | 结构四键、曲线 14 点、可换种子复跑、旧手写键全仓无残留 |
| R01 | 下厨推荐 N+1 消除 | `r01/` | 同一条基准下 SQL 37 → 6（库存 32 → 1），推荐结果等价 |
| F12 | 颜色只有一个出口 | `f12/` | 裸色值 157 → 0，新增门禁 `scripts/check-colors.mjs`，含拦截演示 |

## 复现命令

```powershell
# R02：重跑仿真（不写库，只落存档）
python -m backend.algorithms.simulate_personas --seed 20261024 --lambda-val 0.5 --omega-val 0.5
python -m backend.algorithms.simulate_personas --seed 7 --lambda-val 0.8 --omega-val 0.6
python -m backend.scripts.init_seed_data --force      # 把快照写进 algo_configs

# R01：同一条基准下对比修复前后
python -m backend.scripts.measure_recommend_sql --user 2 --mode HOME_COOKING --legacy
python -m backend.scripts.measure_recommend_sql --user 2 --mode HOME_COOKING

# F12：门禁
node scripts/check-colors.mjs
python scripts/normalize_colors.py        # 干跑：应显示 0 个文件需改写
```

## 目录

```
clearance/
├─ r02/  simulate_seed20261024.log  simulate_seed7.log
│        benchmark_seed20261024.json  benchmark_seed7.json
│        db_benchmark_check.txt  no_legacy_curves.txt
├─ r01/  sql_before_home_cooking.log  sql_after_home_cooking.log
│        sql_after_out_dining.log  before_after_summary.txt
└─ f12/  after_count.txt  gate_pass.txt  gate_pass_again.txt
         gate_block_demo.txt  README.md
```

## 未做/不在本轮

- Room 划卡交互（用户已裁定延期，冻结前补验）。
- 揭晓插画仍为内联 SVG（自绘 Lottie 在 `lottie-web` light 构建下渲染不出，见账本 §10.4）。
- 批次 4 本体（万级数据 / `/admin` 大屏 / APK）未开工。

> **2026-10-24 更新**：本目录已改为「过程留痕」，正式验收包在
> `docs/review/stages/PC01/r01/`、`PC02/r01/`、`PC03/r01/`（按 `REVIEW_RULES.md` §5 结构）。
> 两处内容重复时，以 stage 包为准；本目录保留是为了看「先做证据、后补包」的过程。
