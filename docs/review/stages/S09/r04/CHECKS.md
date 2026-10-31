# S09 / r04 检查记录（仅 B3 封存）

- 日期：2026-10-25（Asia/Shanghai）
- 本包没有写回型自校验脚本；复审只需运行 `probes/verify_sealed.py`，它不写任何文件。
- 台账未改；S09=`BLOCKED`、S10=`LOCKED`；未签 PASS。

| # | 动作 | 结果 | 证据 |
|---:|---|---|---|
| 1 | 复制 r02 证据、r03 历史证据、r04 PASS/FAIL 原件到 `snapshot/` | 80 个文件；`snapshot/SOURCES.json` 中源/快照 SHA-256 全部 `match=true`；0 失配 | `snapshot/SOURCES.json` |
| 2 | 检查 3 个历史失配文件 | r02 `validation.json` 5,922B / `f4c6199c...`；r03 `data/r03_evidence.json` 2,578B / `ffd64e29...`；r03 `validation.json` 3,985B / `24515c33...`；均与快照一致 | `data/r04_evidence.json`、`SEAL.md` |
| 3 | 生成 `validation.json` 与 `data/r04_evidence.json` | 在快照和文档定稿后生成一次；此后不再修改 | `validation.json`、`data/r04_evidence.json` |
| 4 | 最后生成 `SOURCE_MANIFEST.json` | 在全部证据之后生成；manifest 不包含自身；生成后不再写包内文件 | `SOURCE_MANIFEST.json` |
| 5 | `python docs/review/stages/S09/r04/probes/verify_sealed.py`（只读） | 生成 manifest 后执行；要求 `ok=true`、`mismatches=[]`、`extra_files_not_in_manifest=[]`、`post_seal_writes=[]`；结果见本次复审会话输出 | `probes/verify_sealed.py`、`validation.json` |

## 关键约束

- 只读复核只读 manifest/快照/证据，不生成 `validation.json`、不写 `r04_evidence.json`、不写日志。
- 本包不重新运行 r02 `validate_evidence.py`、r03 `validate_r03.py` 或其他写回型探针；它们已被排除在快照之外，避免复审动作改变证据。
- 三个历史失配文件已改为 `snapshot/` 内冻结副本，不再引用可变的 r02/r03 原路径。
- 旧 74 项 r02 manifest 已不存在；本包不宣称 r02 历史封存完整，也不以 r02 当前 84 项工作 manifest 冒充原始快照。
- 未改业务代码、演示库、`/admin`、台账；未创建/修改 `REVIEW.md`；未进入 S10，未签 PASS。

## 最终只读复核

manifest 生成后的只读校验结果不在本文件预写（否则又会形成“复核写文件、文件改哈希”的循环）；由 `verify_sealed.py` 在冻结后执行并报告。该脚本是纯读取，输出不落盘。
