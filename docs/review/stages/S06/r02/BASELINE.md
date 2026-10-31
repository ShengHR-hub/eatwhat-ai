# S06 / r02 基线

采集时间：2026-10-27 23:24:03（Asia/Shanghai）
采集方式：只读脚本 `data/capture_baseline.py`；输出 `logs/00_baseline.log`、`data/baseline.json`。

## 1. 入场状态

| 项 | 值 |
| --- | --- |
| r01 结论 | **FAIL（CHANGES_REQUIRED）**，P2-S06-01 / P2-S06-02 |
| 本轮范围 | 只修两项 P2 + 回归；r01 包原样保留 |
| SSOT | `MASTER_SPEC.md` **v2.3.6**（r02 两处澄清，不升版本） |
| 仓库提交 | 无 commit；以 `SOURCE_MANIFEST.json` 固定受审源码 |
| 环境 | Python 3.13.9 / Node v24.19.0 / npm 11.17.0 / pytest 9.0.3 |

应用 `/health` 版本串仍为历史 `2.3.2`；SSOT 为 v2.3.6，属已知漂移，不在本轮修改。

## 2. 数据库身份与隔离

r02 使用新的 `backend/eatwhat_s06_r02_iso.db`，不写 r01 隔离库或任何受保护库。

| 库 | 角色 | SHA-256 | 行数摘要 |
| --- | --- | --- | --- |
| `backend/eatwhat_dev_pre00_r02.db` | 复制源（只读） | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | users 4 / restaurants 20 / dishes 100 / logs 9 / rooms 0 / votes 0 |
| `backend/eatwhat_s06_r02_iso.db` | 唯一写入目标 | 复制时同为 `b965e73e…a579`；最终 `09db91f8151badfbc23a755ef9eaa72dd80ed80aa7e5245c2cd74275fc2c1b61` | restaurants 32 / dishes 124 / rooms 32 / votes 151 |
| `backend/eatwhat_s06_r01_iso.db` | r01 证据（只读） | `521d73807a2f28768f75924af35c966ffecb07357fcc056058e94ee9f58b48b4` | 9 房 / 51 票，未变 |
| `backend/eatwhat.db` | 演示库（只读） | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | rooms/votes 0/0 |
| `backend/eatwhat_batch4.db` | S10 库（只读） | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | rooms/votes 0/0 |
| `backend/eatwhat_dev_pre00.db` | PRE-00 副本（只读） | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | rooms/votes 0/0 |
| `backend/eatwhat_s05_r01_iso.db` | S05 证据（只读） | `8179f9fd2a78c3ee50b9bf6b7bd49a72825db07aabd80d5e5dfa10c4d32833ce` | rooms/votes 0/0 |

r02 隔离库的 32 房/151 票包含本轮多次回归、P2 复现与故障注入的隔离房间；最终证据房间在各自 JSON 中绑定（P2-02 `381152`、P2-01 `970002`、重启 `617709` 等）。这些不是演示数据。

## 3. fixture 与边界

- `source_dataset=s06_fixture_v1`、`is_synthetic=1`；思源 6 店 12 菜、建大 6 店 12 菜。
- 20 家种子店保持 `campus=NULL`，用于严格校区过滤的负例。
- fixture 只存在于 r02 隔离库；未写入演示库、S10 库、开发源库或 `init_seed_data.py`。
- 演示版 OUT_DINING 在 S10 回填前 0 候选，是已知数据限制。

## 4. 证据包结构

```text
docs/review/stages/S06/r02/
├── SUBMISSION.md
├── BASELINE.md
├── CHECKS.md
├── validation.json          # 22 项
├── SOURCE_MANIFEST.json     # 最后生成
├── logs/                    # 基线、迁移、fixture、探针、服务、测试、构建、流程、P2、重启、保护
└── data/                    # baseline/provenance/migration/fixture/probes/flow/p2/omega/protection
```

## 5. 复现入口

```text
DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s06_r02_iso.db
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8026
```

启动前先跑 `probe_db_target.py`；真实流程、P2-01、P2-02、重启、保护脚本见 `CHECKS.md`。演示库、S10 库、开发源库、r01 隔离库均不在 r02 写入范围。
