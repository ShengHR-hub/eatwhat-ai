# S05/r01 独立复审报告

审查时间：2026-10-27（Asia/Shanghai）
审查方：Codex
受审版本：docs/review/stages/S05/r01/SOURCE_MANIFEST.json，154 项，fingerprint 92ccd30d34e2a28210dc3bb78dd048185756f2aebd8d4d8fb6b031976d7cc5f9
证据清单：119 项
最终结论：PASS（用户手测替代本轮 Codex 自动化点击）

## 结论

源码 manifest 154 项和证据清单 119 项均为 0 失配。后端全量测试、前端构建、颜色门禁通过，三份受保护数据库哈希与提交基线一致。本轮静态核读 Home.vue 的卸载清理、client.js 的 5xx 用户提示，以及 sandbox-sync.mjs 的同源断言，未发现新的源码阻断问题。

用户最初选择不启用 Chrome 远程调试，因此 Codex 未运行自动化鼠标点击，初审报告曾记为 BLOCKED。用户随后亲自操作已启动的本地页面并反馈“没有问题”，同时明确表示这些基本浏览器点击由用户完成即可，要求没有其他问题时放行。按用户明确调整的验收方式，本轮接受该手测作为 S05 交互验收。报告不声称 Codex 独立完成了浏览器点击。

## 验收结果

| 项目 | 独立核验 | 结果 |
| --- | --- | --- |
| 开工前置 | 初审台账为 S04/r03 PASS、S05 READY、S06 LOCKED | PASS |
| 源码版本 | SOURCE_MANIFEST.json 154 项 SHA-256 逐项匹配，失配 0 | PASS |
| 证据完整性 | evidence_inventory.json 119 项 SHA-256 逐项匹配，失配 0 | PASS |
| 静态代码核读 | Home 卸载时清 timer/关闭沙盒；5xx 文案统一且保留原始 detail；沙盒门禁核验实际权重、候选 ID 和 Top5 同源 | PASS |
| 后端回归 | backend 下 python -m pytest -q --basetemp=$env:TEMP\eatwhat-s05-review-final-20261027 | PASS：365 passed, 1 skipped；退出码 0 |
| 前端构建 | frontend 下 npm run build | PASS：775 modules transformed，构建成功，退出码 0 |
| 颜色门禁 | 仓库根目录 node scripts/check-colors.mjs | PASS：38 个文件通过，退出码 0 |
| 用户页面手测 | 用户在本地页面手测并明确反馈无问题；运行日志记录推荐、角色、足迹、冰箱、打卡请求 | PASS（用户执行） |
| 数据隔离 | 手测写入只出现在 S05 隔离库；演示库、S10 库、开发源库哈希不变 | PASS |
| 服务收尾 | 本轮启动的服务已停止，8000/5173 无监听 | PASS |

后端测试输出包含 62 条 warning：datetime.utcnow 弃用警告、requests 依赖版本提示及 pytest 缓存目录权限警告；测试退出码为 0。颜色门禁第一次从 frontend 子目录误启动并因脚本路径不存在退出 1，随后从仓库根目录正确重跑通过。

## 手测与数据记录

用户在本地 /m/home 页面进行手动浏览器检查并确认没有问题。服务运行日志显示用户 1/2 的推荐、足迹、冰箱及打卡请求。S05 隔离库提交时 eating_logs 为 16，用户测试后为 20；group_rooms=0、room_votes=0。用户手测写入保留，不回滚。

当前隔离库 SHA-256：8179f9fd2a78c3ee50b9bf6b7bd49a72825db07aabd80d5e5dfa10c4d32833ce。

受保护库哈希仍与提交基线一致：

- backend/eatwhat.db：775da775ce8dbd5f078d61d5c05db175d8f10d4224fd41755435ac864bd3a60b
- backend/eatwhat_batch4.db：315eb3da1b7775db6fdfc4f6ed72c304de15b66e78c97e843005528976918c28
- backend/eatwhat_dev_pre00_r02.db：b965e73ee318a2b07e89f08eac8aa7bd7cfacf84b87f5c4446c1938bf706a579

## 后续 UI 优化建议

用户建议将足迹页的“防腻冷却看板”改成可展开/收起，以减少页面纵向占用、改善观感。实现位置为 frontend/src/views/mobile/Footprint.vue。本轮不实施；记录为后续 S08 UI 工作项，由执行 AI 开发并在 S08 页面/视口回归中验收。该建议不阻断 S05 或 S06。

## 最终判定

S05/r01：PASS，绑定 manifest fingerprint 92ccd30d34e2a28210dc3bb78dd048185756f2aebd8d4d8fb6b031976d7cc5f9。

S06：READY，可提交开工卡并开始本步骤。S07 保持 DEFERRED，S08 与其后步骤状态不变。
