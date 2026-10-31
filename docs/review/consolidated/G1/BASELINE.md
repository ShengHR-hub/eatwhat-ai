# G1 基线

- 采集日期：2026-10-28（Asia/Shanghai）
- 仓库：`D:\EatWhat`，分支 `master`，**尚无任何 commit**（`git log` 报 "does not have any commits yet"）。本轮未提交、未 `git add`，版本以 `SOURCE_MANIFEST.json` 固定。
- 工作树：包含本轮改动的 4 个前端文件、依赖锁文件与 `docs/review/consolidated/G1/**`；后端源码、算法、schema、`/admin` 未改。

## 1. 环境

| 项 | 值 |
| --- | --- |
| OS | Windows 10.0.22631 x64 |
| Node | v24.19.0（`D:\Node\node.exe`） |
| npm | 11.17.0 |
| Python | 3.13.9（`D:\QLDownload\PY\python.exe`） |
| Chrome | 156.0.8078.48（headless，4 个独立实例，端口 9222–9225） |
| 后端 | `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` |
| 前端 | `npm run dev -- --host 0.0.0.0 --port 5173`（`/api`、`/ws` 代理到 8000） |
| 局域网 | `10.235.60.171`（邀请二维码使用） |

浏览器复验脚本均为真实输入事件（`Input.dispatchMouseEvent` 按下/移动/抬起）与真实页面导航；截图用 `Page.captureScreenshot`。`page.evaluate` 只用于读几何/文本、准备独立身份与记录状态，不代替点击或拖拽。

## 2. 数据库

### 2.1 G1 隔离运行库

| 项 | 值 |
| --- | --- |
| 目标 | `backend/eatwhat_g1_s07_iso.db`（新建，唯一写入目标） |
| 来源 | `backend/eatwhat_dev_pre00_r02.db`，SHA-256 `b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579` |
| 创建时 SHA | `d3e5f7954e940d0bb7240876c5baac20cb9c02c591cfd44b35c2f491c502910d` |
| 迁移 | `room_votes (room_code,user_id,dish_id)` 唯一索引（幂等） |
| fixture | `g1_fixture_v1`：SIYUAN / JIANDA_YANTA 各 10 门店 + 30 道外食菜，`is_synthetic=1`，无图片；含海鲜/香菜/折耳根/花生样本与价格阶梯 |
| 测试后状态 | 40 门店（SIYUAN 10 / JIANDA_YANTA 10 / NULL 20）、160 菜、90 房、392 票、12 条冰箱记录；SHA 以 `data/db_protection.json` 为准 |
| 回滚 | 删除该文件即可；受保护库未被写入，无需恢复 |

关键 schema（与 SSOT v2.3.6 一致）：`restaurants.campus/source_dataset/is_synthetic/deleted_at`、`dishes_and_recipes.feature_vector/tagging_status/source_*`、`group_rooms.campus/budget/deadline_at/settled_at/algo_params`、`room_votes` 唯一索引。

### 2.2 受保护库基线（只读）

| 库 | SHA-256（G1 开始/基线） | G1 结束 |
| --- | --- | --- |
| `backend/eatwhat.db`（演示） | `775da775ce8dbd5f…a60b` | 未变 |
| `backend/eatwhat_batch4.db`（S10 导入） | `315eb3da1b7775db…c28` | 未变 |
| `backend/eatwhat_dev_pre00.db` | `b965e73e…a579` | 未变 |
| `backend/eatwhat_dev_pre00_r02.db`（G1 源库） | `b965e73e…a579` | 未变 |
| `backend/eatwhat_s05_r01_iso.db` | `8179f9fd…33ce` | 未变 |
| `backend/eatwhat_s06_r01_iso.db` | `521d7380…b48b4` | 未变 |
| `backend/eatwhat_s06_r02_iso.db` | `09db91f8…1b61` | 未变 |

完整哈希与行数见 `data/db_protection.json`。

## 3. S09 封存证据

- `docs/review/stages/S09/r04/SOURCE_MANIFEST.json` SHA-256 `7b1d163dffdad256a82186f7c7e7f9f0d1b3d38692c764e5450499919e694a3a`。
- 只读运行 `probes/verify_sealed.py`：`validation_ok=true`、`evidence_checks_ok=true`、manifest 哈希一致（`logs/30_s09_seal_verify.log`）。未写入 S09 包。

## 4. 首页默认数据

- 默认外食 + SIYUAN：使用 `g1_fixture_v1` 合成菜，卡面无图（显示「菜品图位」）。
- 下厨：使用种子共享菜谱（含 95 张演示图），素材可见性在此验证。
