# G2 基线

- 采集日期：2026-10-28（Asia/Shanghai）
- 仓库 `D:\EatWhat`，分支 `master`，无 commit（版本以 `SOURCE_MANIFEST.json` 固定）。
- 环境与 G1 相同：Windows 10.0.22631、Node v24.19.0、npm 11.17.0、Python 3.13.9、Chrome 156。
- 服务：8000 = G1 运行库 `eatwhat_g1_s07_iso.db`（演示用户/日志/库存）；8010 = G2 桥接库 `eatwhat_g2_bridge_iso.db`（只用于边界验证）。
- 外部依赖：`AMAP_API_KEY` 存在（不落盘、不打印）；`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` 均缺失 → S11 BLOCKED。

## 1. 数据库身份

| 库 | 来源/用途 | 关键数量 |
| --- | --- | --- |
| `eatwhat_g2_s10_smoke.db` | 空白 G2 库 + 小样导入 | 60 门店（20+20 POI、10+10 食堂）、60 菜谱 |
| `eatwhat_g2_s10_full.db` | 空白 G2 库 + 全量导入 | 7,664 门店、6,400 菜谱；SHA 见 `data/db_protection.json` |
| `eatwhat_g2_bridge_iso.db` | 复制 G1 运行库 + 导入 S10 门店/菜谱 | 20 历史种子（NULL）+ 20 G1 fixture + 7,264 真实 POI + 400 食堂 + 6,400 菜谱；4 演示用户、9 日志、12 冰箱记录 |

- S10 源输入：`docs/review/stages/S09/r02/data/amap_pois.jsonl`（SHA `5cdf4953…`）、`amap_jianda_pois.jsonl`、`amap_collection.json`、`amap_jianda_collection.json`。
- 桥接源：`backend/eatwhat_batch4.db`（SHA `315eb3da…`，只读 ATTACH）；模板：`backend/eatwhat_g1_s07_iso.db`。
- 回滚：删除三个 `eatwhat_g2_*.db`；受保护库无需恢复。

## 2. 受保护库基线

演示库 `775da775…`、S10 导入库 `315eb3da…`、dev 源库 `b965e73e…`、S05/S06 隔离库（`8179f9fd…` / `521d7380…` / `09db91f8…`）、G1 隔离库 `f63d15a0…`；S09/r04 manifest `7b1d163d…`。全部在 G2 结束后复核未变（`data/db_protection.json`）。

## 3. 数据口径

- POI：高德 `types=050000`、固定 3km、GCJ-02 原样保留；思源 605 / 建大 6,659；rating/价格缺失保持 NULL。
- 食堂：每校区 200 个合成窗口，`source_type=CANTEEN`、`is_synthetic=1`，不进入真实 POI 计数。
- 菜谱：6,400 行确定性合成、6,400 唯一菜名，`tagging_status=PENDING`，向量与过敏原留空给 S11。
- 外食菜单：S10 只导 POI/食堂/菜谱，不生成外食菜品（SSOT：外食菜单人工维护）。
