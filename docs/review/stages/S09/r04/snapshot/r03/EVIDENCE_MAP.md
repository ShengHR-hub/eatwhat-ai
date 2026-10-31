# S09 / r03 证据映射

| r02 BLOCKED 项 | 证据 | 当前状态 | 请 Codex 判断 |
|---|---|---|---|
| B1 双校区超出范围 | `../r02/data/amap_jianda_geocode.json`、`../r02/data/amap_jianda_collection.json`、`../r02/data/amap_jianda_pois.jsonl`、`../r02/data/jianda_poi_spotcheck.json`、`MASTER_SPEC.md` §5.5、`../r02/CONTRACT_MATRIX.md` §1.1、`../r02/DATA_PLAN.md` §0、`../r02/EXPERIMENT_PROTOCOL.md` §1.1 | 中心 `108.967153,34.236991`；425 格/1,206 调用/6,659 真实；6,859 合计；0 越界；校区字段/过滤/切换/统计契约已落盘 | 是否足以消除 B1 |
| B2 D03 未裁决 | `../r02/DECISIONS.md` D03、`MASTER_SPEC.md`、`../r02/logs/20_siyuan_recollect.log`、`../r02/data/amap_collection.json`、`../r02/data/poi_field_stats.json` | 思源 605=样本 A、建大 6,659=样本 B；分校区 805/6,859；不按 1700 合计；禁跨校区补数/混算 | 是否构成正式裁决并闭合 B2 |
| B3 manifest 失效 | `../r02/SOURCE_MANIFEST.json`、`SOURCE_MANIFEST.json`、`validation.json` | r02 现为 84 项，r03 独立重算 84/84；r03 另建 manifest；r02 原包保留 | 是否接受 r03 作为受审身份；是否需保留旧 74 项 manifest |
| C10 NULL 口径 | `MASTER_SPEC.md` §5/§6.5、`../r02/CONTRACT_MATRIX.md`、`DASHBOARD_EXPANSION.md` | 全量 restaurants+dishes；只绘 rating 非空；`meta.not_plotted_no_rating` 为整数；HOME 无真实 rating 时 NULL，不返回 `applicable=false` | 是否满足“只绘非空、报 not_plotted、不伪造” |
| PC01/02/03 PASS 原件 | `../../PC01/r04/REVIEW.md`、`../../PC02/r02/REVIEW.md`、`../../PC03/r04/REVIEW.md`、`../../../clearance-codex-r04-2026-10-24/REPORT.md` | PC01/PC03 为 r04 PASS；PC02 现行 PASS 为 r02；PC02/r01 是 FAIL 历史 | 三项前置条件是否仍成立 |

## 关键数字

| 项 | 值 |
|---|---:|
| r02 manifest 项数 | 84 |
| 思源真实 POI | 605 |
| 思源合成食堂 | 200 |
| 思源合计 | 805 |
| 建大真实 POI | 6,659 |
| 建大合成食堂 | 200 |
| 建大合计 | 6,859 |
| 建大 >3km | 0 |
| 建大同名 ≤50m | 4 对 |
| 建大同名 ≤100m | 5 对 |
| 建大同名同址重复 | 0 组 |

## 证据哈希

完整 SHA-256/字节清单见 `SOURCE_MANIFEST.json`；机器可读判定见 `validation.json` 与 `data/r03_evidence.json`。本文件不重复哈希，避免与 manifest 双写漂移。
