# S09 / r03 基线与保护

- 日期：2026-10-25（Asia/Shanghai）
- 仓库：`D:\EatWhat`；仍无 Git HEAD（`git rev-parse HEAD` 报 unknown revision）。工作区存在历史 staged/untracked 变更，本包不提交、不清理、不覆盖。

## 1. 业务代码基线

- 以 r02 `data/file_hashes.json` 为基线，比较 `backend/`、`frontend/`、`scripts/` 路径：
  - `code_changed=[]`。
- 本轮只改文档与 S09 证据，不改后端/前端业务代码、schema、算法或 `/admin`。

## 2. 演示库基线

```text
db_sha256_before = 775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b
db_sha256_now    = 775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b
group_rooms     = 0
room_votes      = 0
admin_routes    = []
```

- 未写演示库；未导入 POI/合成食堂；未执行 `--force`；未新增 `/admin` 路由。

## 3. 台账基线

- `docs/review/STAGE_STATUS.md` 未改；其 SHA-256 与 r02 manifest 记录一致。
- 当前 S09 行为 **BLOCKED**，S10–S20 为 **LOCKED**。
- 本包只请求解封复核；台账更新由 Codex/用户按流程完成。

## 4. r04 PASS 原件映射

| 项 | 现行 PASS 原件 | 说明 |
|---|---|---|
| PC01/R02 | `docs/review/stages/PC01/r04/REVIEW.md` | r04 PASS；manifest 8 项匹配 |
| PC02/R01 | `docs/review/stages/PC02/r02/REVIEW.md` | **现行 PASS 是 r02**；r01 REVIEW 为 FAIL 历史 |
| PC03/F12 | `docs/review/stages/PC03/r04/REVIEW.md` | r04 PASS；manifest 7 项匹配 |
| r04 总报告 | `docs/review/clearance-codex-r04-2026-10-24/REPORT.md` | 记录 PC01/PC03 PASS、PC02 维持 PASS |

> r04 总报告的“PC02/R01 维持既有 PASS”与实际文件名不一致：现行 PASS 文件是 `PC02/r02/REVIEW.md`。本包按实际 PASS 原件引用，并把该差异列入送审问题。

## 5. 环境

- Python 3.13.9；Node v24.19.0；Windows 10.0.22631；shell 为 Git Bash。
- 高德 Key 只从本地用户环境变量读取；不打印、不写入证据。
- 本包未重新运行 r04 的 pytest/build；r04 报告与 manifest 哈希作为历史基线引用。
