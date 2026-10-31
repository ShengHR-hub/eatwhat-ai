# S09 / r03 检查记录

- 执行日期：2026-10-25（Asia/Shanghai）
- 高德 Key 只从本地环境变量注入；本包未写入 Key。
- 本包只读 r02 证据，不写业务代码、数据库、`/admin`。

| # | 命令/动作 | 退出码 | 实际结果 | 证据 |
|---:|---|---:|---|---|
| 1 | `python docs/review/stages/S09/r03/probes/validate_r03.py` | 0 | `ok=true`；r02 manifest **84/84** 无差异；思源 45/61 格、133 调用、605；建大 425 格、1,206 调用、6,659+200=6,859；D03/C10 文本通过；S09=BLOCKED、S10=LOCKED；`code_changed=[]`、DB SHA 未变、`admin_routes=[]` | `logs/01_validate_r03.log`、`validation.json`、`data/r03_evidence.json` |
| 2 | `python docs/review/stages/S09/r02/probes/validate_evidence.py`（带用户环境变量 Key） | 0 | r02 自校验仍 `ok=true`；84 项 manifest 可用；字段统计、抽查、双校区、台账、DB/代码保护均通过 | `../r02/logs/24_validate_d03_fields.log`、`../r02/validation.json` |
| 3 | `python docs/review/stages/S09/r02/probes/doc_sync_check.py` | 0 | `live_stale_files=[]`；`code_changed=[]`；DB SHA 未变；`group_rooms=0`/`room_votes=0`；`admin_routes=[]`；r01 历史保留 | `../r02/logs/25_doc_sync_check.log`、`../r02/data/doc_sync_check.json` |
| 4 | `python docs/review/stages/S09/r02/probes/poi_field_stats.py` | 0 | 思源 rating 604/1、cost 427/178、tag 309/296；建大 rating 6,652/7、cost 5,411/1,248、tag 3,871/2,788（有值/缺失） | `../r02/logs/23_poi_field_stats.log`、`../r02/data/poi_field_stats.json` |
| 5 | `python docs/review/stages/S09/r02/probes/poi_spotcheck.py ...` | 0 | 建大 6,659 行/6,659 唯一 ID；0 条 >3km；同名同址 0 组；同名 ≤50m 4 对、≤100m 5 对；前 20 条可复核 | `../r02/logs/22_jianda_spotcheck.log`、`../r02/data/jianda_poi_spotcheck.json` |
| 6 | `python docs/review/stages/S09/r03/probes/build_manifest.py` | 0 | 首次输出到 `logs/02_build_manifest.log`；随后无重定向重建一次，固定完成后的日志 hash；r03 manifest 共 98 项（含 r02 84 项引用、r04 PASS 原件） | `logs/02_build_manifest.log`、`SOURCE_MANIFEST.json` |
| 7 | 最终 manifest 复核 | 0 | 98 项全部存在；SHA-256/字节与记录一致；r02 manifest 84 项独立重算无差异 | `SOURCE_MANIFEST.json`、`validation.json` |

## 关键数字

```text
r02_manifest_entries = 84
siyuan_center        = 109.078487,34.234818
siyuan_cells         = 45 planned / 61 processed / 133 calls
siyuan_real_poi      = 605
siyuan_combined      = 805
jianda_center        = 108.967153,34.236991
jianda_cells         = 45 planned / 425 processed / 1206 calls
jianda_real_poi      = 6659
jianda_combined      = 6859
jianda_outside_3km   = 0
jianda_max_distance  = 2999.5m
same_name_50m        = 4 pairs
same_name_100m       = 5 pairs
same_name_addr_dup   = 0 groups
```

## 未执行项

- 未进入 S10；未实现/未运行导入、LLM、正式仿真、`/admin` 或大屏。
- 未改业务代码、演示库、`/admin`；未执行 `--force`。
- 未创建/修改 `docs/review/stages/S09/r03/REVIEW.md`；r02 `REVIEW.md` 未改。
- 未重跑 r04 的 pytest/build；r04 PASS 原件与 manifest 随包引用，不冒充本轮新测试。
- 未签 PASS；S09 仍 `BLOCKED`，等待 Codex 独立复审与台账处理。
