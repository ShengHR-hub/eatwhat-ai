# scripts/ 脚本目录

临时脚本不许留在这里（要留就写清楚用途、标上「一次性」）。全部在仓库根目录执行。

## 颜色与清账

| 脚本 | 作用 | 用法 |
|---|---|---|
| `normalize_colors.py` | 把裸 hex / 数字 rgb 机械搬移到设计令牌（`--write` 才落盘） | `python scripts/normalize_colors.py`（干跑看清单） |
| `check-colors.mjs` | 门禁：`frontend/src/**/*.{vue,js}` 出现裸色值即 `exit 1` | `node scripts/check-colors.mjs` |
| `backend/scripts/measure_recommend_sql.py` | 数一次推荐请求打了多少条 SQL，`--legacy` 跑旧实现对照 | `python -m backend.scripts.measure_recommend_sql --user 2 --mode HOME_COOKING` |
| `backend/algorithms/simulate_personas.py` | R02 仿真：200 人 × 60 天 + 1000 场群组，产出 benchmark | `python -m backend.algorithms.simulate_personas --seed 20261024 --write` |

## 截图与交互验收（Node，需 CDP）

先起 headless Chrome：

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --remote-debugging-port=9222 --user-data-dir=D:\EatWhat\.chrome-profile
```

| 脚本 | 用途 |
|---|---|
| `shot.mjs <url> <w> <h> <out.png> [preShotJs] [waitMs]` | 单张截图 + 横向溢出体检；`FULL=1` 出整页长图 |
| `record.mjs [url] [outDir]` | 划卡三动作逐帧（左划/右划确认/点开雷达），帧存 `docs/review/deck-gesture/` |
| `exhaust.mjs` | 连划 24 张 → 空态 → 换一批 → 重置，并写 `refill-evidence.json` |
| `tap-probe.mjs` | 真触摸 tap（`Input.dispatchTouchEvent`），验证点卡片能开五维弹层 |
| `swipe-probe.mjs` | 真触摸左划，验证出牌且不误开弹层 |
| `room-demo.mjs` | 双标签页跑完多人房间：建房 → 加入 → 开团 → 投票 → 揭晓 |

## 菜品图流水线（Python）

| 脚本 | 用途 |
|---|---|
| `dump_dishes.py` | 导出 100 条种子菜到 `docs/_data/dishes.json` |
| `make_dish_table.py` | 生成清单表 `docs/_data/dishes_table.md` |
| `insert_dish_table.py` | 把清单表插进 `docs/DISH_IMAGES_PLAN.md`（幂等） |
| `fetch_dish_images.py` | Commons 检索 + 打分 + 下载 + 裁 800×450，写 `_data/image_ledger.json` |
| `apply_picks.py` | 按 `PICKS` 精确取件 / 按 `DROP` 退回缺失（`--drop` 只删不取） |
| `recover_missing.py` | 对缺失菜换叫法再试 |
| `contact_sheet.py` | 拼接触印样到 `docs/review/dishes/` |
| `build_dish_image_map.py` | **按菜品 id** 重建 `backend/scripts/dish_images.py`（文件名 `<id>-<slug>.jpg`，同名菜共用一张） |
| `render_image_ledger_from_sources.py` | 从 `docs/DISH_IMAGES_SOURCES_RAW.md` 生成台账与缺失清单 |
| `gen_dish_image_map.py` | 旧版：读 `DISH_IMAGES_PLAN.md` 清单表按菜名映射（已被 `build_dish_image_map.py` 取代） |
| `render_image_docs.py` | 生成 `DISH_IMAGES_LEDGER.md` + `DISH_IMAGES_MISSING.md` |
| `make_dish_todo.py` | 生成交办清单 `docs/DISH_IMAGES_TODO.md` |
| `repick.py` | 打印某道菜的候选标题（人工挑图用） |

## Lottie

| 脚本 | 用途 |
|---|---|
| `make_empty_state_lottie.py` | 生成空态自绘碗 `empty-state.json` |
| `make_reveal_lottie.py` | 生成揭晓插画 `reveal.json`（**注意：`lottie_light` 渲染不出来，见 AGENT_MEMORY §10.4**） |
| `peek_lottie.py`、`lottie_fills.py`、`check_lottie_colors.py` | 排查素材层面的颜色/图层数，换素材时复核用 |

## 约定

- 中间数据只写 `docs/_data/`，验收图只写 `docs/review/<页面>/`。
- 脚本里不要写死 `D:/EatWhat`（`room-demo.mjs` 目前是唯一例外，改路径时记得同步）。

### 颜色与清账（r03 之后）

| 脚本 | 作用 |
| --- | --- |
| `check-colors.mjs` | 颜色门禁。扫 `frontend/src/**/*.{vue,js,css}`，禁裸 `#hex` / `rgb()` / `hsl()`；注释与自定义属性值按**词法范围**豁免（`stripComments` + `maskTokenDeclarations`），非主题出口文件里的「带裸色的自定义属性」记 `token-literal`。白名单是三个精确的 Vue Bits 文件 + `utils/theme.js`。 |
| `gate_probes.py` | 门禁自检：造六类样本（通配选择器 / 注释后代码 / 令牌声明后代码 / 组件本地造色 / 多行注释后代码 / 合法别名），断言前五类被拦、末一类放行，最后清理探针并回到基线。 |
| `normalize_colors.py` | 一次性机械搬移（hex/rgb → 令牌）。`--write` 才落盘，默认干跑。 |
| `measure_recommend_sql.py` | 用 SQLAlchemy 事件数语句，`--legacy` 走旧逐菜实现做对照。 |
| `simulate_personas.py`（`backend/algorithms/`） | 仿真。真调 `recommend_single` / `shortlist_candidates` / `compute_group_consensus`，调用计数写进存档 JSON；主规模 40,000 票满额，缺席实验走 `run_absence_experiment` 另列。 |
