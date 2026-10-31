# S00 / r01 提交说明

步骤：S00 基线与缺陷清单冻结
轮次：r01
状态：**SUBMITTED_FOR_REVIEW**
日期：2026-10-25（Asia/Shanghai）
前置：[PRE-00/r02 独立复审 PASS](../../../clearance-codex-pre00-r02/REPORT.md)；台账 S00 为 READY

## 1. 本步范围

只完成 S00：

1. 固定源码、文档、环境、依赖、端口、启动方式、三个数据库与前端构建入口；
2. 保护演示库与 S10 独立库只读，不执行清空/迁移/播种/业务写入；
3. 将 F01–F13、N01 与本轮新发现映射到 S01–S08；
4. 逐条记录源码位置、复现前置、最小复现、当前表现、等级、关闭证据与旧证据局限；
5. 固定首页/足迹/冰箱/角色切换/沙盒的当前入口与接口现状；
6. 为 S01–S08 建立验证矩阵，S05/S08 明确真实浏览器两档 viewport、console/network/截图/按钮命中，S07 保持 DEFERRED。

未修改业务源码、schema、算法、前端组件、接口、`MASTER_SPEC.md`、`docs/review/STAGE_STATUS.md`、演示库、S10 库或 `/admin`；未创建 PASS/REVIEW 结论。

## 2. 交付物

| 文件 | 内容 |
| --- | --- |
| `SUBMISSION.md` | 本说明 |
| `BASELINE.md` | 源码/文档/环境/依赖/端口/三库/前端入口/接口现状 |
| `CHECKS.md` | 命令、退出码、实际结果、失败反例、未执行项 |
| `FINDINGS.md` | 18 条缺陷冻结清单（F01–F13、N01、N02–N05） |
| `VERIFICATION_MATRIX.md` | S01–S08 测试/输入/预期/证据矩阵 |
| `SOURCE_MANIFEST.json` | 143 项逐文件 SHA-256；fingerprint `16123adef28db48d023f746420853bdc70aa4f2c6d51961e34fedb6625c8a1c0` |
| `validation.json` | 机器可读结果，状态 `SUBMITTED_FOR_REVIEW`，`self_signed_pass=false` |
| `data/` | baseline、schema、当前状态、缺陷映射、验证矩阵、DB 保护 |
| `logs/` | 实际命令输出、接口响应、失败反例 |

## 3. 基线摘要

- 分支 `master`，**无 commit**（HEAD 不存在）；staged 280 / unstaged 130 / untracked 53。
- SSOT `MASTER_SPEC.md` v2.3.5；`BATCH4_PLAN.md` v1.1；`REVIEW_RULES.md` v1.1；PRE 计划 v1.0。
- Python 3.13.9、Node v24.19.0、npm 11.17.0；FastAPI 0.115.0、SQLAlchemy 2.0.35、Pydantic 2.13.3。
- 后端开发端口 8000，前端 Vite 5173，`/api` 与 `/ws` 代理到 8000。
- 开发运行库 `backend/eatwhat_dev_pre00_r02.db`，SHA `b965e73e…706a579`，schema 指纹 `82f1b327…ccaeb7`。
- 演示库 `775da775…bd3a60b`、S10 库 `315eb3da…6918c28` 均只读且未变。
- 后端全量 `175 passed, 1 skipped`（skip 为 Windows 符号链接权限）；前端构建成功；颜色门禁 38 文件通过。

## 4. 当前首页/接口状态（只记录，不修复）

- `GET /health`、外食/下厨推荐、足迹、冰箱、天气、目录、角色列表均 200；服务端日志无 500/traceback。
- `GET /api/v1/fridge/2` 与 `/api/v1/logs/stats/2` 携带 `X-User-Id: 1` 仍返回用户 2 数据（200）——F07 残留。
- 外食推荐带 `campus=SIYUAN` 与不带结果完全相同；OpenAPI 无任何 campus 字段——N02。
- `GET /users/2/profile` 头/路径冲突返回 403，与 SSOT『按头解析、冲突记日志』的最终契约仍需 S01 裁决。
- 错误路径 `/api/v1/dishes?ids=24,89` 返回 404，作为反例保留；正确路径为 `/api/v1/catalog/dishes`。
- 页面入口：`/m/home`、`/m/footprint`、`/m/profile`、`/m/fridge`、`/m/room`；角色切换在 Profile，沙盒在 Home。
- S00 未启动 Vite、未做真实浏览器点击；两档 viewport/console/network/截图/按钮命中由 S05/S08 必做。

## 5. 缺陷冻结摘要

18 条：F01–F13、N01，以及本轮新发现 N02–N05。

| 分类 | 条目 | 当前状态 |
| --- | --- | --- |
| 已有补丁、待独立验收 | F01/F02（S04）、F03/F04/F05（S06）、F06/F10/F13（S05）、N01（S05） | 代码存在，自测通过；不等于 PASS |
| 仍有明确残留 | F07 身份（S01）、F08 部分向量（S02）、F09 时效边界（S03）、F11 校区/票型/划卡 UI（S06/S07） | 见 FINDINGS 的具体缺口 |
| 静态已过、视觉待验 | F12（S08） | PC03/r04 只证明静态门禁 |
| 本轮新发现 | N02 campus 缺失、N03 软删除未过滤、N04 NULL 向量默认 0.5、N05 运行库/版本漂移 | 当前演示部分潜伏（deleted/NULL 均为 0）；S10 接线前必须处理 |
| 延期 | S07 多人真实交互/扫码 | **DEFERRED，未执行、未签通过** |

每条均写明当前源码位置、复现前置、最小复现、当前表现、等级、关闭证据与旧证据为什么不能直接视为当前 PASS。旧审查、旧截图、开发方自测均只作线索。

## 6. 数据库保护

S00 只对开发运行库做只读接口探针；启动前后三库 SHA、schema 指纹、行数、旁文件全部一致：

- 演示库：`775da775…bd3a60b`，未变；
- S10 库：`315eb3da…6918c28`，未变；
- 开发库：`b965e73e…706a579`，未变。

未执行任何业务写入；F07 建房身份、F08 部分向量、F02–F05 房间票型、N03/N04 的写型复现均留给对应步骤在隔离库执行。

## 7. 已知限制

1. 仓库无 commit，版本由 143 项逐文件 SHA + staged diff SHA 固定；本包未提交、未清理历史变更。
2. S00 未做真实浏览器与写库复现；当前状态只覆盖只读接口、静态代码与测试基线。
3. 符号链接测试 skip 沿用 PRE-00 的 Windows 权限限制；不是业务跳过。
4. S10 双校区/软删除/NULL 向量尚未接线，相关问题为潜在缺口，不能写成当前演示已复现。
5. 本包不签 PASS、不修改台账、不开放 S01–S08、不实现任何修复。

## 8. 停机声明

**SUBMITTED_FOR_REVIEW，未签 PASS，未改台账，未开始下一步，等待 Codex 独立复审。**
