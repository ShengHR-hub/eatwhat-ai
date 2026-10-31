# S01 / r01 基线

日期：2026-10-26（Asia/Shanghai）
步骤：S01 身份与资源归属（F07）
轮次：r01
前置：[S00/r01 独立复审 PASS](../../../clearance-codex-s00-r01/REPORT.md)，受审 manifest fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0`

## 1. 源码与版本

- 分支：`master`
- HEAD：不存在（仓库无 commit）
- commit 数：0
- staged / unstaged / untracked：280 / 136 / 55（`git status --porcelain`，本包不清理、不覆盖既有变更）
- staged diff SHA-256：`cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb`
- 契约：`MASTER_SPEC.md` v2.3.5
- S01/r01 `SOURCE_MANIFEST.json`：144 项，fingerprint `3caa7db07f0516db1ecbda9e58a7cee35c3832ad235dc74f0f4f9c1002c4ad29`
- 逐文件 diff：`data/changed_files.diff`；相关文件状态：`data/git_status_changed.txt`

## 2. 环境

| 项 | 值 |
| --- | --- |
| OS | Windows 10.0.22631 x64 |
| Python | 3.13.9 |
| Node | v24.19.0 |
| npm | 11.17.0 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Pydantic | 2.13.3 |
| websockets | 16.0 |

## 3. 服务与端口

| 用途 | 地址 / 命令 | 状态 |
| --- | --- | --- |
| 隔离后端 | `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s01_r01_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` | 已停止，端口已释放 |
| 前端 Vite | `cd frontend; npm run dev -- --host 127.0.0.1 --port 5173` | 已停止，端口已释放 |
| 浏览器 | 独立 Chrome 实例，CDP `127.0.0.1:9222`，独立 `--user-data-dir` | 已停止；临时 profile 已删除 |

未启动 `/admin`、S10 导入、LLM、统计大屏或 APK 相关服务。

## 4. 数据库身份与保护

| 库 | 路径 | 基线 SHA-256 | 收尾 SHA-256 | 是否变化 |
| --- | --- | --- | --- | --- |
| 演示库 | `backend/eatwhat.db` | `775da775…bd3a60b` | `775da775…bd3a60b` | 否 |
| S10 导入库 | `backend/eatwhat_batch4.db` | `315eb3da…6918c28` | `315eb3da…6918c28` | 否 |
| 开发源库 | `backend/eatwhat_dev_pre00_r02.db` | `b965e73e…706a579` | `b965e73e…706a579` | 否 |
| 本步隔离副本 | `backend/eatwhat_s01_r01_iso.db` | 从开发源库复制，初值 `b965e73e…706a579` | `b35e8b60…b68884` | 是（仅本副本） |

- 隔离副本来源、schema 指纹、逐表行数与前后哈希：`data/db_protection.json`。
- 隔离副本收尾行数：`group_rooms=2`、`eating_logs=10`、`room_votes=0`；其余表与源库一致。
- 演示库、S10 库、开发源库均未写入；无 `-wal / -journal / -shm` 旁文件。
- 浏览器与 live 探针的所有写入只落在隔离副本。

## 5. 身份行为基线

- S00 只读证据：`X-User-Id: 1` 读取 `/api/v1/fridge/2`、`/api/v1/logs/stats/2` 均返回 200；`/users/2/profile` 路径冲突 403。
- S01 修复前红灯：`test_identity_s01.py` 为 24 failed / 11 passed（`logs/00_red_baseline.log`）。
- S01 修复后：专项 35 passed；后端全量 210 passed / 1 skipped（`logs/20_backend_pytest.log`）。
- 全量 skip 仍为 Windows 符号链接权限用例，未新增 skip、未删除断言、未扩大容差。

## 6. 运行库启动方式

后端必须从仓库根启动（`python -m uvicorn backend.main:app`），并通过 `DATABASE_URL` 指向隔离副本；前端通过 Vite 代理 `/api` 与 `/ws` 到 `127.0.0.1:8000`。演示库不是本步运行库。
