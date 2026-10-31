# S09 / r04 B3 封存说明

- 日期：2026-10-25（Asia/Shanghai）
- 阶段：**S09 阶段 r04（仅 B3 manifest 封存修复）**；不是清账 `clearance-codex-r04-2026-10-24`。
- 范围：只修 B3。B1 双校区、B2 D03、C10 NULL、字段统计、建大抽查、保护项沿用 Codex S09/r03 REVIEW 的 PASS，不重做证据。
- 台账：未修改；S09 仍 `BLOCKED`，S10 仍 `LOCKED`。

## 1. Codex r03 结论与本轮前提

Codex S09/r03 REVIEW（`docs/review/stages/S09/r03/REVIEW.md`）结论为 **FAIL / BLOCKED**，仅 B3 未闭合；B1、思源 POI、合成食堂隔离、字段统计、建大抽查、D03、C10、PC01/PC02/PC03 PASS 原件、代码/DB/admin 保护、台账状态均为 PASS。

同时确认：

- Codex 已接受 **S09/r03 作为新的受审身份**；
- **r02 提交时的 74 项旧 manifest 已不存在**，不能声称 r02 历史封存完整；
- 当前 r02 的 84 项 manifest 只是工作清单，不是 r02 原始不可变快照；
- 本轮不尝试伪造/回写旧 74 项 manifest。

## 2. r03 失配原因

r03 manifest 生成后，以下 3 个被清单覆盖的文件又被写入，导致字节/SHA 失配：

| 文件 | 失配原因 |
|---|---|
| `docs/review/stages/S09/r02/validation.json` | `validate_evidence.py` 运行时会写回；Codex 复审运行后字节从 5,921 变为 5,922 |
| `docs/review/stages/S09/r03/data/r03_evidence.json` | `validate_r03.py` 运行时会写回 |
| `docs/review/stages/S09/r03/validation.json` | `validate_r03.py` 运行时会写回 |

r03 的 `validate_r03.py`/`validate_evidence.py` 都不是纯只读探针；因此“验证动作”本身会改变被 manifest 覆盖的证据。

## 3. 本轮封存方法

1. **先冻结**：把 r02 需要复核的证据（data/logs/文档/validation）、r03 的历史证据（validation/data/logs/文档）和 r04 PASS/FAIL 报告原件复制到 `snapshot/`。
   - 快照共 **80 个文件**；`snapshot/SOURCES.json` 记录每个文件的源路径、源 SHA-256、快照 SHA-256 和 `match=true`。
   - r02 的旧 74 项 manifest 不存在；r02 当前 84 项 manifest 不作为权威快照复制。
   - 可执行探针（r02/r03 `probes/`）不进入快照，避免复审时误运行写回脚本；旧探针行为在 r03 REVIEW 中已记录。
2. **再定稿**：在快照和 r04 文档/数据定稿后，生成一次 `validation.json` 与 `data/r04_evidence.json`，此后不再修改。
3. **最后生成 manifest**：`SOURCE_MANIFEST.json` 在所有证据文件之后生成；生成后不再写任何包内文件。
4. **只读复核**：`probes/verify_sealed.py` 只读 manifest/文件，不写任何东西；复审只需运行这一个脚本。

## 4. 三个历史失配文件的新哈希

以下哈希是 r04 冻结快照中的当前值，已由 `data/r04_evidence.json` 记录，并由 `verify_sealed.py` 复核：

| 文件（快照路径） | 字节 | SHA-256 | 结果 |
|---|---:|---|---|
| `snapshot/r02/validation.json` | 5,922 | `f4c6199c62f6e7b97df779d44689de562a1df44bdc06749d997df1655242cfc8` | 与快照一致 |
| `snapshot/r03/data/r03_evidence.json` | 2,578 | `ffd64e29ef9776e0ec926577cfea5de239d622b79b09018eb58f6571350c79d8` | 与快照一致 |
| `snapshot/r03/validation.json` | 3,985 | `24515c3355bf0ef09ac2ea4521e531252783a356cbf48c840cd49ae23ad26e44` | 与快照一致 |

> r04 自身的 `validation.json` 与 `data/r04_evidence.json` 也在 manifest 中冻结；其哈希以 `SOURCE_MANIFEST.json` 为准，不在本文件预写，避免再次形成“文档写哈希、哈希又变更”的循环。

## 5. 边界声明

- **r02 历史封存不完整**：旧 74 项 manifest 已不存在，无法恢复；本包不以 r02 84 项工作 manifest 冒充原始快照。
- **r04 是 S09 阶段的新受审身份**，只审 B3 是否闭合；不重开 B1/B2/C10。
- 未改业务代码、演示库、`/admin`、台账；未创建/修改任何 `REVIEW.md`。
- 未进入 S10，未签 PASS。
