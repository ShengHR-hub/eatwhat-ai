# S09 / r03 独立复审报告

- 复审日期：2026-10-25（Asia/Shanghai）
- 受审包：`docs/review/stages/S09/r03/`
- 复审方：Codex
- 结论：**FAIL / BLOCKED**
- 台账：未修改；S09 当前保持 `BLOCKED`，S10 保持 `LOCKED`

## 审查方法

本次不采信执行端自报或 r04 总报告的版本标签，直接读取 r03/r02 原件并重新执行：

- `python docs/review/stages/S09/r03/probes/validate_r03.py`
- `python docs/review/stages/S09/r02/probes/validate_evidence.py`
- `python docs/review/stages/S09/r02/probes/doc_sync_check.py`
- 独立 Python 重算两校区 JSONL 的行数、唯一 ID、GCJ-02 3km 距离、合成标记和字段缺失统计
- 独立逐项重算 r03 98 项 SOURCE_MANIFEST 的字节数和 SHA-256
- 直接阅读 PC01/r04、PC02/r02、PC02/r01、PC03/r04 原件及 r04 总报告

## 逐项结论

| 项目 | 结论 | 独立结果 |
|---|---|---|
| B1 双校区补证 | **PASS** | 建大中心 `108.967153,34.236991`，未返回草堂；6,659 行、6,659 唯一 ID、最大距离约 2,999.48m、0 条越界、0 条禁字段；采集 425 格/1,206 调用/0 未完成。契约已写入双校区字段、过滤、前端切换和分校区统计。 |
| 思源 POI | **PASS** | 605 行、605 唯一 ID、最大距离约 2,998.51m、0 条越界、全部真实且有校区。 |
| 合成食堂隔离 | **PASS** | 思源 200、建大 200，分别标记合成；合计分别 805 和 6,859，不用建大补思源。 |
| 字段统计 | **PASS** | 思源 rating 604/1、cost 427/178、tag 309/296；建大 rating 6,652/7、cost 5,411/1,248、tag 3,871/2,788；独立计数一致。 |
| 建大抽查 | **PASS** | 同名同址重复 0 组；同名 50m 内 4 对、100m 内 5 对，作为 S10 人工合并判断保留，当前不构成 S09 失败。 |
| D03 分校区 | **PASS** | r02 DECISIONS.md 明确记录用户正式裁决：思源 605 为样本 A，建大 6,659 为样本 B，分校区报 805/6,859，不按 1,700 合计，不跨校区混算。SSOT 同步。 |
| C10 NULL 口径 | **PASS** | 全量 `restaurants + dishes_and_recipes`；HOME 无 rating 使用 `NULL`；只绘非空 rating；`meta.not_plotted_no_rating` 报整数；不返回 `applicable:false`。本步只验契约，未把未实现的 stats 误报为已实现。 |
| PC01/r04 | **PASS** | 原件结论为 PASS，且明确绑定 PC01/r04 manifest。 |
| PC02 PASS 原件 | **PASS** | 实际 PASS 原件是 `PC02/r02/REVIEW.md`；`PC02/r01/REVIEW.md` 明确为 FAIL。r04 总报告“PC02/R01 维持 PASS”是版本标注错误，但不改变 PC02/r02 原件的有效结论。 |
| PC03/r04 | **PASS** | 原件结论为 PASS，绑定 PC03/r04 manifest。 |
| 代码/数据库/admin 保护 | **PASS** | 独立保护检查返回 `code_changed=[]`、演示库 SHA 前后一致、`group_rooms=0`、`room_votes=0`、`admin_routes=[]`。 |
| 台账状态 | **PASS** | 当前台账仍为 S09 BLOCKED、S10 LOCKED；本次未修改。 |
| B3 证据封存 | **FAIL** | 见下文。 |

## B3 判定和 manifest 裁决

我接受 **S09/r03 作为新的受审身份**。当前解封不需要把 r02 的 74 项历史 manifest 重新伪造或回写；但 r02 提交时的 74 项原件已经不存在，不能声称 r02 历史封存完整。若要关闭“r02 历史 manifest 被重建”的审计缺口，应另存不可变的 74 项快照；它不是当前 r03 通过的替代条件。

当前 r03 自身也尚未达到封存要求。独立重算 98 项 `SOURCE_MANIFEST.json` 时发现 3 项失配：

- `docs/review/stages/S09/r02/validation.json`：记录 5,921 字节，当前 5,922 字节，SHA 不同。
- `docs/review/stages/S09/r03/data/r03_evidence.json`：记录 SHA 与当前文件不同。
- `docs/review/stages/S09/r03/validation.json`：记录 3,984 字节，当前 3,985 字节，SHA 不同。

这说明 r03 生成 manifest 后仍修改过被清单覆盖的文件，当前包不可复核封存。r03 的自校验脚本返回 `ok=true`，但它只验证预设检查，不等价于对 98 项清单逐项核对，因此不能覆盖上述独立发现。

复审还确认 `validate_r03.py` 会写回 `data/r03_evidence.json`，`validate_evidence.py` 会写回 r02 `validation.json`；二者都不是纯只读探针。下一轮应在临时副本运行，或拆分为严格只读校验，避免“验证动作本身”改变 manifest 覆盖的证据。

## 放行结论

**S09/r03 FAIL / BLOCKED。S09 不解封，S10 不开放。**

下一轮验收要求：

1. 新建或修订一个不可变的 r03 证据包；停止所有包内文件修改后重新生成 manifest。
2. 重新核验 98 项（或明确删减后的完整清单）逐项存在、字节数和 SHA-256 一致；manifest 不得遗漏被引用的证据文件。
3. 明确 r02 的 74 项历史 manifest 是否有不可变归档。没有归档时，r03 可作为新身份复审，但必须在报告中继续承认 r02 历史完整性不可恢复。
4. 保持业务代码、数据库、`/admin` 和台账不变，直到新的 r03 复审 PASS。

未修改业务代码、数据库、`/admin` 或 `docs/review/STAGE_STATUS.md`。

