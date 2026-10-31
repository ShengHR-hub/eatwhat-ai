# SUBMISSION —— PC02 / R01（下厨推荐 N+1）

- 步骤：PC02
- 轮次：r02（针对 `REPORT.md` 的 CLR-04）
- 状态：**REVIEW_PENDING**（开发方不自签 PASS）

## 一、这轮改了什么（实现不动，只改测试）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `backend/tests/test_query_budget.py` | 整体重写为 6 条，全部走 `conftest.py` 的 `session_factory` fixture；不再 import 全局 `SessionLocal/engine` |
| 2 | `backend/tests/test_query_budget.py` | 新增**独立参考实现** `_reference_fridge_status()`（逐菜、只用 `ingredients_main`、过期跳过、临期 2.0），与被测批量实现分开写 |
| 3 | `backend/tests/test_query_budget.py` | 等价性改为 `--legacy` 真对照：monkeypatch 把批量函数换成"每道菜单查一次库存"的旧写法，比较完整 top-40 的 `(dish_id, total_score)` 序列 |
| 4 | `backend/scripts/measure_recommend_sql.py` | 保留（上一轮新增），本轮作为两套实现的**同一把尺子**产对照数字 |

`backend/algorithms/single_recommender.py` 的批量实现（`_fridge_index` / `_fridge_status_from_index`）**本轮一行未改**——按指令"实现不动，只改测试"。

## 二、逐条验收自测

| # | 要求（来自 CLR-04 / 返工指令） | 自测结果 | 证据 |
|---|---|---|---|
| 1 | 测试用自建数据、走 conftest fixture | 6/6 使用 `session_factory`，SQL 监听绑在该 fixture 的 engine 上 | `logs/10_clean_db_pytest.log` |
| 2 | 干净库重建后 3 条（现 6 条）全过 | `DATABASE_URL=sqlite:///D:/EatWhat/backend/tmp-clean-r02.db` → **6 passed**，且跑完该文件未生成 | 同上（末行 `db file exists after run: False`） |
| 3 | 等价测试是新实现 vs `--legacy` 旧实现 | 见第 5 条；另 pytest 内用 monkeypatch 调换批量实现，比较完整 top-40 序列一致 | `logs/10_clean_db_pytest.log` 的 `test_batched_pipeline_matches_legacy_pipeline` |
| 4 | SQL 断言收紧到个位数 | `HOME_COOKING` 总语句 **6**（库存查询 **1**），断言 `总 ≤9`、`库存 ≤1` | `logs/11_measure_batched.log`、`data/before_after_summary.txt` |
| 5 | 对照双方必须是不同实现、同一工具 | `measure_recommend_sql.py`：`--legacy` → 37 条（库存 32）；批量 → 6 条（库存 1）；两者返回 31 条、top3 完全一致 | `logs/12_measure_legacy.log` + `logs/11_measure_batched.log` |
| 6 | 候选扩容场景 | `limit=100` 下仍在 `总 ≤9 / 库存 ≤1` 的预算内 | `test_recommend_query_budget_with_expanded_candidates` |
| 7 | 边界覆盖（空库存 / 过期 / 临期双倍 / 多道菜） | 造过期 / 临期 / 正常三种库存，对 12 道下厨菜逐一比对；全部置过期后状态分必须下降 | `test_batched_fridge_score_matches_independent_reference`、`test_expired_stock_does_not_raise_status_score` |

## 三、数字

```
HOME_COOKING  before: statements=37  fridge=32  returned=31
HOME_COOKING  after : statements=6   fridge=1   returned=31
               same top3: True   same count: True
OUT_DINING    before: statements=6   fridge=0   returned=40
OUT_DINING    after : statements=6   fridge=0   returned=40
               same top3: True   same count: True
```

## 四、已知限制

- `OUT_DINING` 前后都是 6 条——因为没有库存读取，N+1 本来就不存在；保留这条是为了证明"修复没有被扩散到别的模式"。
- SQL 预算 `≤9` 是按当前实现的实际值（6）留 3 条余量定的硬阈值，不是拍脑袋的宽松值；
  若将来加一次必要查询会先撞到断言，需要显式改预算并在提交里说明。
