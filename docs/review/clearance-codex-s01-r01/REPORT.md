# S01/r01 独立复审报告

审查时间：2026-10-26（Asia/Shanghai）  
审查方：Codex  
受审包：`docs/review/stages/S01/r01/`  
受审 manifest：144 项，fingerprint `3caa7db07f0516db1ecbda9e58a7cee35c3832ad235dc74f0f4f9c1002c4ad29`

## 最终结论

**S01/r01：PASS。**

身份出口、资源归属、冲突处理、房间成员边界和前端角色切换均通过独立源码核对、自动化复跑及真实浏览器点击。`S02` 可进入 `READY`；`S07` 继续 `DEFERRED`，`S10` 继续 `LOCKED`，`/admin` 未开放。

## 验收结果

| 条目 | 独立核验 | 结果 |
| --- | --- | --- |
| 版本与清单 | 逐文件重算 `SOURCE_MANIFEST.json` | 144/144 存在，0 失配；fingerprint 一致 |
| 身份依赖层 | 直接检查 `backend/deps.py` 的解析、未知用户、冲突日志、资源/成员校验 | 所有私有入口统一经过 `require_user`；路径资源用 `ensure_self`，房间用 `ensure_member` |
| REST 入口覆盖 | 检查 profile、preferences、红黑榜、recommend、checkin、stats、fridge、shopping-list、rooms create/join/GET | 未发现 body/path 身份绕过；header 缺失/非法不回退用户 1 |
| WebSocket | 检查 `room_socket` 及隔离探针 | 未知用户、非成员、路径/header 冲突均拒绝；成员收到 `MEMBER_SYNC`；非房主开局返回错误 |
| 专项测试 | `python -m pytest -q tests/test_identity_s01.py --basetemp backend/.pytest-s01-rerun` | 35 passed |
| 后端全量 | `python -m pytest -q --basetemp backend/.pytest-s01-rerun` | 210 passed, 1 skipped；skip 为既有 Windows 符号链接权限用例 |
| 前端构建 | `npm run build` | Vite 775 modules transformed，exit 0 |
| 前端门禁 | `home-fit`、`refill-fresh`、`sandbox-sync`、`check-colors` | 390×844/390×667 均 PASS；换批无重叠；沙盒与首页同源；38 文件颜色门禁 PASS |
| 真实浏览器 | 独立 Chrome/CDP 会话，真实鼠标点击角色 1→2，13 次点击 | 切换前请求全为 1，切换后 17 个 API 请求全为 2，错配 0；页面、足迹、偏好、红黑榜、冰箱、建房均可达 |
| HTTP/WS 隔离复验 | 新复制开发库，真实 uvicorn + HTTP/WS 探针 | 19 HTTP + 4 WS 用例符合契约；写入仅发生在隔离副本 |
| 数据库保护 | 复核三份受保护库及旁文件 | 演示库 `775da775…bd3a60b`、S10 库 `315eb3da…6918c28`、开发源库 `b965e73e…706a579` 均未变化；服务已停止、端口已释放 |

## 复审过程注记

- 首次全量 pytest 使用系统临时目录时被 Windows 权限拒绝；改用仓库内的隔离 `--basetemp` 后复跑全量通过。首次失败不是业务测试失败。
- 真实浏览器脚本会把截图和 `browser_evidence.json` 写回受审目录；独立复跑因此刷新了该目录中的浏览器证据。当前 JSON 时间为 `2026-10-25T16:50:38Z`，与 `CHECKS.md` 中原执行时间不同；本报告采用本次 13 次真实点击的结果。`SOURCE_MANIFEST.json` 明确排除 S01/r01 证据目录。
- HTTP/WS 探针脚本固定读取/写入提交包路径。复审中脚本误写后，已用原始 `logs/18_live_identity_probe.log` 恢复 `data/live_identity_probe.json`；临时探针的 before/after 行数不作为证据。独立 HTTP/WS 结论来自响应结果、服务端记录及原提交包恢复后的原始探针记录。
- 144 项 manifest 在台账登记前全部匹配。登记本报告会有意改变被 manifest 引用的 `docs/review/STAGE_STATUS.md`；这是审查状态记录的预期后续变化，不属于业务源码漂移。

## 路径冲突裁决（S01-GAP-01）

`MASTER_SPEC.md §5.0` 明确 header 是操作者身份，body/query 身份冲突按 header 执行并记录。路径参数标识被访问的资源，因此 `GET /fridge/2` 携带 `X-User-Id: 1` 属于跨资源访问，返回 403 并记录 `path_header_mismatch` 是资源授权拒绝，与统一身份出口不冲突。该行为已由专项测试和真实隔离探针验证，S01-GAP-01 关闭。

## 问题与范围

未发现影响 S01 放行的 P0/P1/P2 问题。演示身份仍是 `X-User-Id` 方案，不等同生产鉴权；S07 的真实多人划卡、扫码、断线恢复未在 S01 验收，按台账保持延期。双校区、软删除、NULL 向量等后续契约不在本步关闭范围。

## 放行

S01/r01 满足 `docs/REVIEW_RULES.md` 的独立测试、真实交互、隔离写入和证据一致性要求。登记本报告后：

- S01 → `PASS`
- S02 → `READY`
- S07 → `DEFERRED`
- S10 → `LOCKED`
- `/admin` → 保持未开放

