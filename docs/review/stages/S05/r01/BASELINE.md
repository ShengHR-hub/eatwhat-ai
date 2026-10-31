# S05 / r01 基线

步骤：S05 首页与单人闭环
轮次：r01
状态：**已提交待审（SUBMITTED_FOR_REVIEW）**——开发方未签 PASS、未修改台账、未开始 S06
日期：2026-10-27（Asia/Shanghai）
工作目录：`D:\EatWhat`
基线采集：2026-10-27T00:36:26+08:00（`logs/00_baseline.log`、`data/baseline.json`）

## 1. 源码版本

| 项 | 值 |
| --- | --- |
| 分支 | `master` |
| HEAD | 不存在（`git rev-parse HEAD` 退出码 128，0 commit） |
| 工作区 | 采集时 345 条状态（含既有 staged 280 与本次新增，未清理） |
| staged diff SHA-256 | `cbfeb1e84ea5a38053d2b0fa67bd897b69a9aa988e16426e2ccc437e13a630cb` |
| 采集时 unstaged diff SHA-256 | `79516f729cfd31220b88271d35a63b03e29ac801c39fa0d5130bb7e19f611001` |
| 契约版本 | `MASTER_SPEC.md` v2.3.5 |

**与 S04/r03 受审版本的漂移**：逐项重算 S04/r03 `SOURCE_MANIFEST.json` 的 154 项，采集时 **153 项字节一致**；唯一差异是 `docs/review/STAGE_STATUS.md`（Codex 签发 S04/r03 PASS 时更新）。即本轮施工前的后端、前端、脚本源码与 S04/r03 独立复审版本完全相同。

本轮施工后相对 S04/r03 只有 3 个源码文件变化（详见 `SUBMISSION.md` §2）：

- `frontend/src/views/mobile/Home.vue` — `7ded94b886e7bc0cf0705bfff9e195cca5831c5a32da962f5855cbcae60b4563`
- `frontend/src/api/client.js` — `54d56817f34d6a8cdc341547ccb43b5b9024fd8bba59d2e7df1a018e58b570d3`
- `scripts/sandbox-sync.mjs` — `eb15d8054d4b54a5503e3dbc09c74943dfe0d7d93918d57d19063bd6900544b0`

**后端源码本轮未改动**（`backend/` 下无任何文件变化），因此无需报备后端修改，也没有 schema/API 语义变更。

## 2. 运行环境

| 组件 | 版本 |
| --- | --- |
| OS / Shell | Windows 11 10.0.22631 x64 / Git Bash |
| Python | 3.13.9 |
| FastAPI / SQLAlchemy / Pydantic | 0.115.0 / 2.0.35 / 2.13.3 |
| HTTPX / Uvicorn / pytest | 0.28.1 / 0.30.0 / 9.0.3 |
| Node / npm | v24.19.0 / 11.17.0 |
| 浏览器 | Chrome 155.0.8059.86（`--headless=new`，CDP 9222） |
| 前端依赖 | `package.json` `66e99826…48c49b`、`package-lock.json` `adc87fc7…20c297`（与 S04/r03 一致） |
| 后端依赖 | `requirements.txt` `842533ee…0f1c73`、`pytest.ini` `e317b4ea…0f8bb3` |

## 3. 数据库身份与隔离

| 数据库 | 用途 | SHA-256 | 说明 |
| --- | --- | --- | --- |
| `backend/eatwhat.db` | **演示库（只读保护）** | `775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b` | 旧 schema；**无** `allergen_tags` / `deleted_at` / `campus`；4 用户 / 20 门店 / 100 菜 / 9 日志 / 0 房间 / 0 票 |
| `backend/eatwhat_batch4.db` | **S10 独立导入库（只读保护）** | `315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28` | 7,664 门店 / 6,400 菜 / 0 用户 / 0 日志；不得接演示流程 |
| `backend/eatwhat_dev_pre00_r02.db` | PRE-00/r02 开发源库（只读保护） | `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` | 已迁移可空字段；本轮只作复制来源 |
| `backend/eatwhat_s05_r01_iso.db` | **本轮隔离运行库（唯一写入目标）** | 最终 `bdba4e9054e08acc4d581dd761f27e54fe094a6e37d1963fea6f4a39b5d12d07` | 由 dev 源库 **字节一致复制**；本轮全部 API/浏览器写入只落此库；最终 16 条日志（含测试打卡） |

### 3.1 隔离方式

1. `cp backend/eatwhat_dev_pre00_r02.db backend/eatwhat_s05_r01_iso.db`，复制后 SHA 与源库逐字节一致（`logs/02_iso_db_provenance.log`）。
2. 后端以 `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s05_r01_iso.db` 启动；Vite 只代理到 `127.0.0.1:8000`。
3. **哨兵验证**（`logs/05_db_isolation.log`、`data/db_isolation.json`）：直接在 iso 库插入哨兵用户 99，`GET /users/99/profile` 返回哨兵昵称；`POST /logs/checkin` 后 iso `eating_logs` 9→10，`GET /logs/stats/99` 返回 1；哨兵删除后行数回到 4/4/9。演示库、S10 库、dev 源库哈希前后完全一致。
4. 所有浏览器/API 写入测试均在上述哨兵通过之后执行。

### 3.2 三个受保护库的最终状态

最终复核见 `data/db_protection.json` 与 `logs/52_db_protection_final.log`：三库 SHA-256 与基线完全相同；演示库仍 4/20/100/9、`group_rooms=0`、`room_votes=0`；S10 库未变。

## 4. 服务与端口

| 用途 | 地址 | 启动命令 | 日志 |
| --- | --- | --- | --- |
| 后端 | `http://127.0.0.1:8000` | `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_s05_r01_iso.db python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`（仓库根） | `logs/03_backend_start.log` |
| 前端 | `http://127.0.0.1:5173` | `cd frontend && npm run dev` | `logs/04_vite_start.log` |
| 浏览器 | CDP `http://127.0.0.1:9222` | `chrome --headless=new --remote-debugging-port=9222 --user-data-dir=<临时目录>` | `logs/06_chrome_start.log` |

服务在证据采集完成后已全部停止，端口 8000/5173/9222 无监听（`logs/70_service_shutdown.log`）；临时 Chrome profile（190 MB）已删除，截图与日志保留。

## 5. 已知基线风险（未在本步扩大范围）

- **N05**：`backend/eatwhat.db` 仍是旧 schema，直接当运行库会在推荐/足迹 500；`/health` 仍报 `2.3.2`（SSOT v2.3.5）。本步按 PRE-00 约定只使用 `eatwhat_s05_r01_iso.db`，未改默认 `DATABASE_URL`、未改版本号（版本号对齐归 S08）。
- **N02**：双校区 `campus` 契约/过滤未实现（SSOT v2.3.4 要求，主步骤为 S06/BRIDGE-10）；本步外食请求不带 `campus`，未冒充已实现。
- **N03**：软删除 `deleted_at` 尚未在推荐/目录/房间过滤；当前三库 `deleted_at` 非空行均为 0，属 S10 数据接入后的潜在缺口，需要同时覆盖推荐、目录与 S06 房间候选，未在本步做半套修复。
- **天气在线源**：未配置 `AMAP_API_KEY`，`/context/weather` 实测 `source=offline`（22℃/晴）；浏览器截图显示“离线”角标。本包**不声称**在线天气已验收。
