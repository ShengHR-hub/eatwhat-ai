# S09 / r04 B3 封存独立复审报告

- 复审日期：2026-10-25（Asia/Shanghai）
- 受审包：`docs/review/stages/S09/r04/`
- 范围：仅 B3 manifest/快照封存；不重审上一轮已 PASS 项
- 结论：**B3 PASS**
- 出具时台账未修改；登记本报告后，台账已将 S09 更新为 `PASS`、S10 更新为 `READY`

## 独立只读核验

执行：

`python docs/review/stages/S09/r04/probes/verify_sealed.py`

实际结果：

- `ok=true`
- manifest 条目：90
- SHA/字节失配：0
- manifest 外额外文件：0
- 封存后写入：0
- 80 个 snapshot 源文件与快照：全部匹配
- 三个历史失配文件：全部匹配
- `validation_ok=true`
- `evidence_checks_ok=true`

三个历史文件的新哈希由只读脚本重新核对：

- r02 `validation.json`：5,922 bytes，`f4c619c62f6e7b97df779d44689de562a1df44bdc06749d997df1655242cfc8`
- r03 `data/r03_evidence.json`：2,578 bytes，`ffd64e29ef9776e0ec926577cfea5de239d622b79b09018eb58f6571350c79d8`
- r03 `validation.json`：3,985 bytes，`24515c3355bf0ef09ac2ea4521e531252783a356cbf48c840cd49ae23ad26e44`

r04 自身两份证据文件也在 90 项 manifest 中，完整哈希为：

- `data/r04_evidence.json`：`cfcc329bf900f7e1ac6cf621d87acd50ad70566d5f2976a5949b7ebb18a8c8ae`
- `validation.json`：`88073757117afff4df6206ca65f6fcea644d0f9cb7aad97a03677bf74a83d98a`

## 90 项、80 项与上轮 98 项

90 项由以下部分构成：

- 80 项冻结 snapshot 文件；
- 10 项 r04 自身封存文件：5 个说明文档、`data/r04_evidence.json`、`validation.json`、预封存检查日志、只读 verifier、`snapshot/SOURCES.json`。

r04 不是把上轮 98 项原路径全部复制一遍，而是将需要保留的历史证据改为 `snapshot/` 路径。按 `snapshot/SOURCES.json` 的源路径映射，与 r03 的 98 项比较：

- r03 中未进入 r04 snapshot 的共有 22 项：
  - 12 个旧 `probes/` 脚本；
  - 8 个 backend 源/配置文件：
    `backend/algorithms/group_recommender.py`、
    `backend/algorithms/simulate_personas.py`、
    `backend/algorithms/single_recommender.py`、
    `backend/config.py`、`backend/main.py`、`backend/models.py`、
    `backend/scripts/benchmark_snapshot.py`、`backend/scripts/init_seed_data.py`；
  - 2 个 frontend 文件：
    `frontend/package.json`、`frontend/src/router/index.js`。
- r04 snapshot 新增 4 个 r03 清单未包含的历史证据：
  - `docs/_data/dishes.json`
  - `docs/review/stages/PC02/r01/REVIEW.md`
  - `docs/review/stages/S09/r02/data/evidence_index.json`
  - `docs/review/stages/S09/r03/SOURCE_MANIFEST.json`

因此，差额**不是全部 probes**。上述 10 个 backend/frontend 文件属于上一轮代码保护基线，12 个 probes 属于上一轮可执行探针；它们都不是本轮 B3 封存所需的冻结证据。r04 的范围明确是封存 B3，且未宣称重新封存 r03 的全部 98 项原路径。历史证据已通过 snapshot 路径保留，未发现 B3 所需材料遗漏。

## manifest 自哈希

manifest 不把自身列入 90 项文件清单，避免自包含哈希循环；`verify_sealed.py` 明确跳过 manifest 自身，并独立计算当前 manifest SHA-256：

`7b1d163dffdad256a82186f7c7e7f9f0d1b3d38692c764e5450499919e694a3a`

这是可接受的封存方式。r04 的 `validation.json` 和 `data/r04_evidence.json` 均以完整 SHA/字节写入 manifest，未使用报告中的截断值。

## 历史边界

文档如实声明：

- r02 提交时的旧 74 项 manifest 已不存在；
- r02 历史封存不完整；
- r02 当前 84 项工作 manifest 不冒充原始快照；
- S09/r03 被接受为新的受审身份。

该历史缺口没有被掩盖，也没有被 r04 manifest 伪造为已恢复。

## 解封结论

**B3 PASS。S09 具备解封条件，S10 具备开放条件。**

本次未改台账，因此工作区台账仍显示：

- S09：`BLOCKED`
- S10：`LOCKED`

只有在台账记录本报告并由流程更新状态后，S09 才实际变为 `PASS/READY)，S10 才应改为 `READY)。本次未修改业务代码、数据库、`/admin`、台账或 r03 REVIEW。

