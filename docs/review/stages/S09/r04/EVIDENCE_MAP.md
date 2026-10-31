# S09 / r04 B3 证据映射

本包只处理 B3；B1/B2/C10 的 PASS 依据沿用 Codex S09/r03 REVIEW，不在此重做。

| B3 要求 | 证据 | 状态 |
|---|---|---|
| 先冻结证据 | `snapshot/` 共 80 个文件；`snapshot/SOURCES.json` 记录源/快照 SHA-256 与 `match=true` | 已冻结 |
| r02 不再作可变引用 | `snapshot/r02/validation.json`（5,922B，`f4c6199c...`）；r02 data/logs/文档均复制入快照 | 已切断 |
| r03 历史失配文件固定 | `snapshot/r03/data/r03_evidence.json`（2,578B，`ffd64e29...`）；`snapshot/r03/validation.json`（3,985B，`24515c33...`） | 已固定 |
| 不再用写回型自校验 | 只保留 `probes/verify_sealed.py`；旧 r02/r03 `probes/` 不进入快照 | 已隔离 |
| manifest 最后生成 | `SOURCE_MANIFEST.json` 在全部证据之后生成；生成后不再写包内文件 | 已按顺序执行 |
| 只读复核 | `verify_sealed.py` 只读 manifest 与文件，不写盘；检查失配/额外文件/封存后写入 | 待本次运行报告 |
| r02 历史完整性 | 文档明确旧 74 项 manifest 已不存在、r02 历史封存不完整 | 已如实声明 |
| S09 阶段 r04 命名 | 本目录；不是 `clearance-codex-r04-2026-10-24` | 已区分 |

## r04 PASS/FAIL 原件快照

- `snapshot/r04_reports/clearance-r04-REPORT.md`
- `snapshot/r04_reports/PC01-r04-PASS.md`
- `snapshot/r04_reports/PC02-r02-PASS.md`
- `snapshot/r04_reports/PC03-r04-PASS.md`
- `snapshot/r04_reports/PC02-r01-FAIL.md`（历史 FAIL；不是 PASS 原件）

## 三个历史失配文件

| 文件 | 新哈希 |
|---|---|
| `snapshot/r02/validation.json` | `f4c6199c62f6e7b97df779d44689de562a1df44bdc06749d997df1655242cfc8` |
| `snapshot/r03/data/r03_evidence.json` | `ffd64e29ef9776e0ec926577cfea5de239d622b79b09018eb58f6571350c79d8` |
| `snapshot/r03/validation.json` | `24515c3355bf0ef09ac2ea4521e531252783a356cbf48c840cd49ae23ad26e44` |

完整清单与字节数见 `SOURCE_MANIFEST.json`；机器可读结果见 `validation.json` 与 `data/r04_evidence.json`。
