# S09 / r04 基线与保护

- 日期：2026-10-25（Asia/Shanghai）
- 仓库仍无 Git HEAD；工作区存在历史 staged/untracked 变更，本包不提交、不清理、不覆盖。

## 1. 业务代码 / 数据库 / admin

```text
code_changed   = []
db_sha256      = 775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b
group_rooms    = 0
room_votes     = 0
admin_routes   = []
```

- 以 r02 `data/file_hashes.json` 为代码基线；本轮未改 `backend/`、`frontend/`、`scripts/`。
- 未写演示库；未导入 POI/合成食堂；未改 schema；未新增 `/admin` 路由。

## 2. 台账

- `docs/review/STAGE_STATUS.md` 未改；当前 S09=`BLOCKED`、S10–S20=`LOCKED`。
- 本包只请求 B3 封存复核；台账解封由 Codex/用户处理。

## 3. 历史边界

- r02 提交时的旧 74 项 manifest **已不存在**，无法恢复。
- r02 当前 84 项 manifest 只是工作清单，不作为 r02 原始封存快照。
- Codex 已接受 S09/r03 作为新的受审身份；r04 只审 B3。
- r04 是 S09 阶段 r04，不是清账 `clearance-codex-r04-2026-10-24`。

## 4. 复审入口

- 只运行 `probes/verify_sealed.py`；它只读。
- 不运行 r02/r03 写回型探针；旧探针不进入快照。
- 未创建/修改 `REVIEW.md`；未签 PASS；未进入 S10。
