# S09 / r04 送审说明（仅 B3 封存修复）

- 日期：2026-10-25（Asia/Shanghai）
- 阶段：**S09 阶段 r04**；不是清账 `clearance-codex-r04-2026-10-24`。
- 受审范围：**只审 B3 manifest 封存是否闭合**；B1/B2/C10/字段/抽查/保护沿用 Codex S09/r03 REVIEW 的 PASS，不重做。
- 台账：未修改；S09 仍 `BLOCKED`，S10 仍 `LOCKED`。
- 开发方不签 PASS；本轮只提交封存证据，是否解封由 Codex/用户判定。

## 1. 本轮只改了什么

1. 把 r02 复核证据、r03 历史证据、r04 PASS/FAIL 原件复制为 `snapshot/` 冻结快照（80 个文件，源/快照 SHA-256 全部匹配）。
2. 把 r02 `validation.json`、r03 `data/r03_evidence.json`、r03 `validation.json` 这三个曾失配的文件改为**快照内固定副本**，不再作为可变引用。
3. 只保留一个只读复核脚本 `probes/verify_sealed.py`；它不写任何文件。旧 r02/r03 写回型探针不进入快照，避免复审时再次改变证据。
4. 先定稿所有证据，再最后生成 `SOURCE_MANIFEST.json`；manifest 生成后不再写包内文件。
5. 文档如实记录：**旧 74 项 manifest 已不存在、r02 历史封存不完整、Codex 已接受 r03 为新受审身份**；不宣称 r02 封存完整。

## 2. 三个历史失配文件的新哈希

| 快照路径 | 字节 | SHA-256 | 验证 |
|---|---:|---|---|
| `snapshot/r02/validation.json` | 5,922 | `f4c6199c62f6e7b97df779d44689de562a1df44bdc06749d997df1655242cfc8` | 快照内一致 |
| `snapshot/r03/data/r03_evidence.json` | 2,578 | `ffd64e29ef9776e0ec926577cfea5de239d622b79b09018eb58f6571350c79d8` | 快照内一致 |
| `snapshot/r03/validation.json` | 3,985 | `24515c3355bf0ef09ac2ea4521e531252783a356cbf48c840cd49ae23ad26e44` | 快照内一致 |

## 3. 送审问题

1. 上述 3 个文件已改为冻结快照；r04 manifest 在全部证据之后生成；`verify_sealed.py` 只读复核。B3 是否闭合？
2. 本轮明确不宣称 r02 旧 74 项 manifest 完整；Codex 已接受 r03 为新身份。r04 是否可作为 B3 的新受审包？
3. 在 B3 闭合后，S09 是否可从 `BLOCKED` 解除？本包不请求 S10；台账由 Codex/用户更新。

## 4. 保护

- 未改业务代码、演示库、`/admin`、台账；未创建/修改 `REVIEW.md`。
- `code_changed=[]`；演示库 SHA 未变；`group_rooms=0`、`room_votes=0`；`admin_routes=[]`。
- 未进入 S10；未签 PASS。

## 5. 文件

- `SEAL.md`：封存方法、失配原因、三个新哈希、边界声明。
- `CHECKS.md`：命令、只读复核结果。
- `EVIDENCE_MAP.md`：B3 证据映射。
- `BASELINE.md`：代码/DB/台账基线。
- `validation.json`、`data/r04_evidence.json`：机器可读判定。
- `SOURCE_MANIFEST.json`：最后生成的完整封存清单。
