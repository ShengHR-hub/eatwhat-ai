# G1 复验记录（G2 校区接线修复后）

- 日期：2026-10-28 23:20（Asia/Shanghai）
- 原因：G2 修复 `POST /recommend/single` 校区契约，共享调用方 `frontend/src/stores/algo.js` 与 `Home.vue` 的请求体变化，影响 G1 的首页与角色切换证据。
- 复验范围：首页两档几何、角色切换后的推荐/足迹/冰箱/偏好/建房请求头、空态/4xx/5xx/断网恢复。
- 结果：`browser/s08_regression.json` 已用修复后版本重新生成；`identity` 仍全部为 2，两档布局仍不滚动/不溢出/无重叠，console 与异常为空。S07 房间链路不经过单人推荐，未重跑。
- 同轮复跑：`pytest` 396 passed / 1 skipped；`home-fit`/`refill-fresh`/`sandbox-sync`/`npm run build`/`check-colors` 全部 exit 0（日志在 `docs/review/consolidated/G2/logs/30–36`）。
- 本轮没有改动 G1 的历史结论；`SUBMISSION.md` 关于 S08 的原始描述仍成立，具体数字以新 JSON 为准。
