# S06 / r01 基线

采集时间：2026-10-27 03:08:18（Asia/Shanghai）
采集方式：只读脚本 `data/capture_baseline.py`；完整输出 `logs/00_baseline.log`、`data/baseline.json`。

## 1. 版本与工作树

| 项 | 值 |
| --- | --- |
| SSOT | `MASTER_SPEC.md` **v2.3.6**（S06 小节已写入） |
| 入场须知 | `AGENTS.md` 版本引用同步为 v2.3.6 |
| 仓库提交 | **无 commit**：`git rev-parse HEAD` 返回 128；本轮不新增提交 |
| 工作树 | `git status --short` 356 行（历史 staged/unstaged/untracked 均在，未清空、未重置） |
| 受审源码 | 由 `SOURCE_MANIFEST.json` 固定；不依赖 git HEAD |

环境：

| 项 | 版本 |
| --- | --- |
| Python | 3.13.9 |
| Node | v24.19.0 |
| npm | 11.17.0 |
| pytest | 9.0.3 |
| FastAPI / SQLAlchemy / Pydantic | 0.115.0 / 2.0.35 / 2.13.3 |

应用版本串 `backend/main.py` 与 `/health` 仍为历史 `2.3.2`；SSOT 已 v2.3.6。本轮不改该字符串，作为已知漂移记录。

## 2. 数据库身份与隔离

真实 REST/WS 只写 `backend/eatwhat_s06_r01_iso.db`。该副本由受保护开发源库复制，复制后 SHA 相同；随后加 `room_votes` 唯一索引与 `s06_fixture_v1` 校区 fixture。

| 库 | 角色 | SHA-256 | 行数摘要 |
| --- | --- | --- | --- |
| `backend/eatwhat_dev_pre00_r02.db` | 复制源（只读） | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | users 4 / restaurants 20 / dishes 100 / logs 9 / rooms 0 / votes 0 / config 1 |
| `backend/eatwhat_s06_r01_iso.db` | 唯一写入目标 | 复制时同为 `b965e73e…a579`；最终 `521d73807a2f28768f75924af35c966ffecb07357fcc056058e94ee9f58b48b4` | 最终 restaurants 32（20 NULL + 6 SIYUAN + 6 JIANDA）/ dishes 124 / rooms 9 / votes 51 |
| `backend/eatwhat.db` | 演示库（只读） | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | 20/100/9；rooms 0 / votes 0 |
| `backend/eatwhat_batch4.db` | S10 独立库（只读） | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | restaurants 7,664 / dishes 6,400；rooms 0 / votes 0 |
| `backend/eatwhat_dev_pre00.db` | PRE-00 开发副本（只读） | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | 20/100/9；rooms 0 / votes 0 |
| `backend/eatwhat_s05_r01_iso.db` | S05 证据库（只读） | `8179f9fd2a78c3ee50b9bf6b7bd49a72825db07aabd80d5e5dfa10c4d32833ce` | 20/100/20；rooms 0 / votes 0 |

复制与探针：

- `data/db_provenance.json`：源/目标复制后 SHA 相同，源库复制后未变。
- `data/db_target_probe.json`：启动前 21 项检查全通过，`DATABASE_URL` 指向 S06 隔离库，rooms/votes=0/0。
- `data/db_target_probe_post.json`：运行后仍指向同一库，记录 9 房间/51 票。
- `data/migration.json`：预启动 `room_votes` 行数 0，创建唯一索引。
- `data/fixture.json`：思源/建大各 6 店 12 菜；20 家种子店保持 NULL。
- `data/db_protection.json`：五份受保护库 SHA 前后一致；`group_rooms/room_votes` 仍 0/0。

## 3. fixture 与数据边界

- `source_dataset=s06_fixture_v1`、`is_synthetic=1`；门店地址明确写“非真实采集”。
- 12 道思源菜（ID 101–112）+ 12 道建大菜（ID 113–124）；seed 的 20 家店保持 `campus=NULL`。
- fixture 只存在于 `eatwhat_s06_r01_iso.db`；未写入演示库、S10 库、开发源库或 `init_seed_data.py`。
- 演示版 OUT_DINING 在 S10 回填前 0 候选，是 D1 A′ 的已知数据限制；下厨菜谱共享不受影响。

## 4. 证据包结构

```text
docs/review/stages/S06/r01/
├── SUBMISSION.md
├── BASELINE.md
├── CHECKS.md
├── validation.json
├── SOURCE_MANIFEST.json      # 最后生成
├── logs/                     # 基线、迁移、fixture、目标探针、服务、测试、构建、流程、重启、保护
└── data/                     # baseline / provenance / migration / fixture / probes /
                              # rest_ws_sequence / restart_flow / omega_matrix / db_protection /
                              # command_results / 采集与探针脚本
```

## 5. 复现入口

从仓库根目录按 `CHECKS.md` 的顺序执行；真实服务必须显式设置：

```text
DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s06_r01_iso.db
```

启动前先跑 `probe_db_target.py`；未确认目标前不得启动写测试。演示库、S10 库、开发源库、S05 隔离库均不在本轮写入范围。
