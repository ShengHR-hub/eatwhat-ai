# S00 / r01 独立复审报告

审查时间：2026-10-25（Asia/Shanghai）  
审查方：Codex  
受审包：`docs/review/stages/S00/r01/`  
受审源码指纹：`SOURCE_MANIFEST.json` 的 143 项、manifest fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0`  
受审前台账 SHA-256：`a4bf33c6e1b80648955aa8aeb786b1cc3f88b657fbab14e62bfb3e6fa8cdf772`

## 最终结论

**S00/r01：PASS。**

S00 的目标是冻结当前版本基线和未验收缺陷，不是关闭这些缺陷。提交包准确保留了当前仍开放的 F07、F08、F09、F11、N02、N03、N04，并将 F01–F13、N01–N05 映射到 S01–S08；没有把历史 PASS、S07 延期或 S10 新功能写成当前通过。

本报告签发后，台账登记：

- S00：`PASS`（受审版本为上述 manifest）
- S01：`READY`
- S07：继续 `DEFERRED`
- S10：继续 `LOCKED`，BRIDGE-10 仍是前置
- `/admin`：未触碰

## 验收结果

| 条目 | 独立核验 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| 证据包身份 | 逐文件读取 `SOURCE_MANIFEST.json`，重算 143 项 SHA 与 fingerprint | 143/143 存在且 0 失配；存储 fingerprint 与重算值均为 `16123ade…5c8a1c0` | PASS |
| S00 范围 | 对照 `PRE_S10_REMEDIATION_PLAN.md`、`BATCH4_PLAN.md`、`REVIEW_RULES.md` | 仅冻结基线/缺陷/矩阵；未实现修复、未签自有 PASS | PASS |
| 后端回归 | 临时目录和隔离 `DATABASE_URL` 下新鲜执行 `python -m pytest -q -p no:cacheprovider` | `175 passed, 1 skipped, 505 warnings`，退出码 0；skip 为 Windows 符号链接权限用例 | PASS |
| 前端构建 | `frontend` 下新鲜执行 `npm run build` | Vite 775 modules transformed，退出码 0 | PASS |
| 颜色静态门禁 | 根目录新鲜执行 `node scripts/check-colors.mjs` | 38 个文件通过，退出码 0 | PASS |
| 接口基线 | 使用 `eatwhat_dev_pre00_r02.db` 启动临时 uvicorn，重复只读请求 | 正常 health、推荐、足迹、冰箱、目录为 200；错误路径/不存在房间保留预期 404；服务无 traceback | PASS |
| 已知残留复现 | `X-User-Id:1` 读取 `/fridge/2`、`/logs/stats/2`；带 `campus` 推荐；OpenAPI 检查 | 跨用户读取仍返回 200；campus 被忽略且不进入 schema；与 FINDINGS 记录一致 | PASS（基线准确） |
| F09 固定时钟 | 独立运行 `probe_fridge_boundary.py` | 3 天库存经过 2.5 天得到 `remaining_days=0`、`is_expired=True`，与清单一致 | PASS（问题准确） |
| 数据库保护 | 服务前后重算三库 SHA、大小、规范化 schema、行数及旁文件 | 演示库 `775da775…bd3a60b`、S10 库 `315eb3da…6918c28`、开发库 `b965e73e…706a579` 全部保持；三库 schema/行数与包内快照一致；无 `-wal/-journal/-shm` | PASS |
| 缺陷清单 | 读取 `data/defects.json`、`FINDINGS.md` | 18 项：F01–F13、N01–N05；每项有源码位置、前置、复现、现状、影响、关闭证据和旧证据局限 | PASS |
| 验证矩阵 | 读取机器矩阵与 Markdown | S01–S08 齐全；S07 明确 `DEFERRED`/未执行；S05/S08 明确真实浏览器两档 viewport、console/network、截图和按钮命中要求 | PASS |
| 边界纪律 | 检查提交说明、日志和工作树 | 未建房、未打卡、未改偏好/库存、未启动真实浏览器；没有把这些未执行项冒充通过 | PASS |

## 源码与数据层面的关键确认

1. F07 的两个明确越权读现象可复现：`backend/routers/fridge.py` 的 `GET /fridge/{user_id}` 与 `backend/routers/eating_log.py` 的 `GET /logs/stats/{user_id}` 没有 `ensure_self`；`group_room.py` 建房仍允许 `payload.host_user_id` 覆盖请求头身份。它们被正确留给 S01，不因本轮回归绿色而关闭。
2. F08 的 `auth_user.py` 仍对 `base_vector` 整体替换；F09 的 `fridge_clock.py` 仍使用 `round`；N02 的推荐/房间 schema 和查询没有 campus 过滤；N03 的查询没有统一 `deleted_at IS NULL`；N04 的 `normalize_vector(None)` 仍返回全 0.5；N05 的默认数据库路径仍是 `backend/eatwhat.db`，`/health` 仍报告 `2.3.2`。这些定位与包内 FINDINGS 一致。
3. 当前开发库的 `deleted_at` 和 NULL 向量计数为 0，故 N03/N04 被正确标为接入 S10 后的潜在缺口，而不是伪造为当前演示已复现。

## 未宣称的范围

- 本轮没有执行真实浏览器点击，因此不签 F06/F10/F13/N01 的 UI 回归；这些仍由 S05/S08 验收。
- 本轮没有执行写库或真实 WS，因此不签 F02–F05、F10 群组链路、F11；S06/S07 按矩阵执行，S07 仍延期。
- PC01/PC02 的 R02/R01 已有独立 PASS 和台账交叉记录，本轮不重跑其业务验收，也不把它们改写成 S00 的新证据。

## P3 文档注记（不阻断 S00）

1. `BATCH4_PLAN.md` 的 S00 检查表还要求对 R01/R02 建立交叉映射；本包没有在 `FINDINGS.md` 中重复该表，但台账和 PC01/PC02 独立 PASS 原件仍保留对应路径。S11/S12 开工卡应继续引用这些原件。
2. F06、F09、F11/N02 的部分行号范围比当前文件末行略长；文件路径、函数/字段名称和行为证据均可直接定位。后续修改相关文件时应刷新行号，避免继续复制旧行号。

## 独立执行记录

- 后端：隔离临时目录，`python -m pytest -q -p no:cacheprovider`，退出码 0。
- 前端：`frontend/npm run build`，退出码 0。
- 静态门禁：`node scripts/check-colors.mjs`，退出码 0。
- 只读 API：临时启动 `DATABASE_URL=sqlite:///D:/EatWhat/backend/eatwhat_dev_pre00_r02.db` 的 uvicorn，验证后停止，端口已释放。
- 保护核验：三库 SHA、大小、规范化 schema/行数和旁文件复核完成；没有业务写入。

## 放行

S00 已满足当前步骤的必需项，允许进入 **S01 身份与资源归属**。S01 必须先提交自己的新轮次验收包并停手；不得把本报告扩大解释为 S01–S08、BRIDGE-10 或 S10 的 PASS。

台账更新后，`docs/review/STAGE_STATUS.md` 的 live SHA 会变化；这是登记本报告造成的预期差异，不改写本次受审包的 manifest，也不使本报告的受审版本漂移。
