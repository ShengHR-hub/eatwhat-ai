# G1 提交说明（S07 多人真实交互 + S08 移动端总回归）

- 日期：2026-10-28（Asia/Shanghai）
- 状态：**开发方自测完成并封存，等待五组完成后 Codex 统一独立复审**。
- 开发方**未签 PASS**、未创建 `REVIEW.md`、未修改 `STAGE_STATUS.md` 或任何正式审查结论。
- 本包只覆盖 G1；未进入 G2，未碰 `/admin`、S14–S17。

## 1. 范围与改动

| 文件 | 改动 | 原因 |
| --- | --- | --- |
| `frontend/src/components/SwipeCardDeck.vue` | 新增 `variant="room"`：四方向真实拖拽（左 PASS / 右 LIKE / 上 SUPER_LIKE / 下 VETO），60px 阈值、未达阈值回弹；新增卡片插槽与 4 个印章；`castVote`/`reset` 暴露给按钮与恢复逻辑 | S07 要求真实拖拽划卡并覆盖四种票型；首页单人行为保持不变 |
| `frontend/src/views/mobile/Room.vue` | 划卡区改用 `SwipeCardDeck`；新增邀请面板（二维码 + 复制链接，编码局域网地址）；刷新/重进走 `GET /rooms` 恢复；断线退避重连；后台切回刷新快照；重连不清空本人票；结算/超时后禁止拖拽与按钮；揭晓动效只播放一次 | S07 交互、扫码入口与恢复要求 |
| `frontend/vite.config.js` | dev-only `/__lan` 端点，返回本机非回环 IPv4 | 二维码不能用 localhost 编码 |
| `frontend/package.json` / `package-lock.json` | 新增 `qrcode@1.5.4` | 客户端生成邀请二维码 |
| `docs/review/consolidated/G1/**` | 证据与复验脚本 | 本轮交付 |

后端、算法、数据库 schema、`/admin` 均未改动。S09 封存包只读复核，未写入（见 `logs/30_s09_seal_verify.log`）。

## 2. S07 自测结果

| 验收条目 | 方法 | 结果 | 证据 |
| --- | --- | --- | --- |
| 两独立身份建房/加入/成员同步/房主开局/投票/揭晓 | 两个独立 Chrome（独立 user-data-dir，非同一 profile 标签）；A 建房，B 打开邀请链接加入 | 通过；成员 `[1,2]`，X-User-Id 分别 1/2，双方揭晓一致 | `browser/s07_two_identity.json`、`shots/a01–a07` |
| 四身份房间 | 四个独立 Chrome | 通过；成员 `[1,2,3,4]`，仅房主有开局按钮 | `browser/s07_four_identity.json`、`shots/b01–b04` |
| 三种偏好冲突 | ① 忌口：u1+u2 与 u3+u4 候选差异；② 预算：同一校区 budget 12 vs 30；③ 口味：u1 SUPER_LIKE 与 u2 VETO 同菜 | ① u1+u2 候选不含海鲜/香菜/折耳根，u3+u4 不含海鲜/花生；② 12 元房 5 道（最高 ¥9.5），30 元房 10 道（最高 ¥37.5）；③ 该菜被 VETO 掩码（`masked_by_veto=true`，报告 `vetoed_dish_ids=[104,105]`） | 同上 |
| 真实拖拽 >60px 触发、未达阈值回弹、GSAP Draggable | CDP `Input.dispatchMouseEvent` 按下/分步移动/抬起 | 40px 拖动：进度 0→0、卡名不变；≥130px：票型按方向写入 | `s07_two_identity.json.belowThreshold`、`dragResults` |
| 四种票型 | 两个身份分别用真实拖拽发出 | `SUPER_LIKE / VETO / LIKE / PASS` 全部出现，WS 帧与服务端进度一致 | `s07_two_identity.json.voteFrames*` |
| 15 秒倒计时、超时结算、全否决、无共识、截止后拒投 | 无人投票等超时；两身份各 10 张全部下划；结算后拖拽与 WS 补票 | 超时正常结算；全否决 `has_consensus=false`、`winner_dish_id=null`、UI「这局没有结果」；结算后 WS 补票返回 ERROR「这一局已经结束了，不能再改票」 | `s07_negative.json` |
| 刷新恢复 | SWIPING 中 `Page.reload` | 恢复：状态 SWIPING、候选 10、本人票 1 条、成员进度一致、剩余 12s→7s | `s07_recovery.json.reloadPreserved` |
| 断线/重连 | 停掉 Vite 代理进程再重启（CDP offline 不会断开已建立的 WS） | 断开期间显示「实时连接断了，正在重连…」，attempts=2；代理恢复后 socket=open、错误清空并恢复现场 | `browser/reconnect_step1.json`、`reconnect_step2.json` |
| 后台切回 | 真实新建标签并切换焦点，`visibilityState` 记录 hidden→visible | 状态、进度、卡名、成员进度保持一致；切回后重新拉取房间快照 | `s07_recovery.json.background` |
| 重复 join / 房间不存在 / 非成员 WS / 非房主开局 / 跨校区 | REST + 真实 WS 协议 | 重复 join 200 且成员仍 1；不存在房间有可见文案；非成员 WS 握手拒绝；非房主 START 返回「只有房主能开团」；跨校区 join 409 | `s07_negative.json` |
| 邀请/扫码入口 | 二维码载荷 + 局域网地址可访问 + 第二浏览器打开链接进房 | 载荷为 `http://10.235.60.171:5173/m/room?code=…`（非 localhost），LAN 地址 HTTP 200，链接可进房 | `s07_two_identity.json.qrPayload/lanCheck` |
| 揭晓动效 | GSAP 时间线 + canvas-confetti 实际渲染 | confetti canvas 存在且截图可见粒子；揭晓卡与排行可见 | `shots/a06/a07`、`s07_two_identity.json.c…` |

### S07 明确未通过/BLOCKED 的条目

1. **真机扫码：BLOCKED**。本轮没有可操作的第二台设备/相机入口，未执行手机扫码。二维码编码的是局域网地址而非 localhost，且该地址可访问、链接可进房；但「手机相机扫码成功」未经实测，不记为通过。
2. **Lottie 揭晓动画：BLOCKED**。仓库自绘 `reveal.json` 在 `lottie-web` light 构建下渲染不出图形（`docs/AGENT_MEMORY.md` §10.4），当前揭晓使用内联 SVG + 锁定的 GSAP/confetti，未改用其他动效库；不声称 Lottie 揭晓已实现。
3. 最终源码版本的两身份一局在 15 秒内完成 7/6 票后按超时结算（四种票型均已覆盖、双方揭晓一致）；早期中间版本曾达到双方 10/10 提前结算，但**不作为最终源码证据引用**。
4. 四身份一局同样在 15 秒超时结算，未划完全部候选；四端赢家与报告一致，偏好冲突证据独立成立。

## 3. S08 自测结果

| 验收条目 | 方法 | 结果 | 证据 |
| --- | --- | --- | --- |
| 五个页面真实浏览器检查 | 底部 Tab 与「我的」二级入口真实点击 | `/m/home`、`/m/footprint`、`/m/profile`、`/m/fridge`、`/m/room` 均可进入；横向溢出 0 | `browser/s08_regression.json.nav`、`shots/s08_*` |
| 底部导航 / 返回路径 | 切换 Tab；二级页 `history.back()` | 首页↔足迹↔我的正常；冰箱/房间返回均回到 `/m/profile` | `s08_addendum.json` |
| 首页 390×844 / 390×667 | 真实视口 + 几何探针 | 无滚动、无横向溢出、操作行与底栏无重叠、按钮中心命中自身；问候/面板/顶卡/露边/候选条/操作行/Tab 同屏；卡面 50% / 39% 屏高 | `s08_regression.json.layouts`、`shots/s08_home_*` |
| 角色切换 | 我的 → 切换室友 → 选第二个角色 | 切换后 profile GET、足迹 stats、冰箱 GET、推荐 POST、偏好 PUT、建房 POST 的 X-User-Id 全部为 2 | `s08_regression.json.identity` |
| 正常 / 空态 / 4xx / 5xx / 断网恢复 | 真实点击触发；空态与 4xx/5xx 用浏览器级 Fetch 拦截，断网用 Network 离线 | 空态：推荐「本轮推荐已看完」、足迹/冰箱空态文案；422 显示「参数不合法」；500 显示统一文案；断网显示「后端没连上…」，恢复后卡组重新出现 | `s08_regression.json.states`、`shots/s08_home_422/500/offline` |
| 颜色 / 玻璃分级 | `check-colors` + DOM 计数 | 38 文件无裸色值；首页折射只开顶卡（`.deck__top .dishcard.glass-card`），露边卡为 `.glass-card--matte`；一级 2 / 磨砂 25 | `logs/23_gate_check_colors.log`、`s08_regression.json.homeVisual` |
| 动效库分工 | 代码 + 运行证据 | GSAP 划卡（拖拽生效）、vueuse/motion 模式滑块位移、Lottie 天气/空态实际渲染（paths 2 / 5）、canvas-confetti 揭晓可见 | `s08_addendum.json.modeThumb`、`s08_regression.json.states.lottieStatus`、S07 截图 |
| 素材真实可见 | 下厨模式（共享菜谱）顶卡图片 | `naturalWidth=669`，图片真实渲染；外食 fixture 本身无图，显示占位，不伪装 | `s08_regression.json.homeVisual.imgs` |
| 门禁 | pytest / build / 4 条界面门禁 | 全部 exit 0 | `logs/20–25` |

### S08 复验说明（2026-10-28 23:20）

G2 修复单人推荐校区契约后，首页请求体新增 `campus`，S08 已用修复后版本重跑：两档布局、角色切换（推荐/足迹/冰箱/偏好/建房请求头均为 2）、空态/422/500/断网恢复全部通过，console 与异常为空。详见 `RECHECK_AFTER_G2_CAMPUS_FIX.md` 与更新后的 `browser/s08_regression.json`。

### S08 说明

- 首页默认外食模式使用 G1 隔离库的**合成校区 fixture**，条目没有图片，卡面显示「菜品图位」占位；素材可见性改在下厨共享菜谱验证，未把占位说成有图。
- 冰箱隔离数据均处于已到期状态，页面如实显示「已到期」，未修改数据迁就展示。

## 4. 数据库与保护

- 所有写入只落在 `backend/eatwhat_g1_s07_iso.db`（新建、明确命名）。来源 `eatwhat_dev_pre00_r02.db`，来源 SHA `b965e73e…a579`；创建后立即加 `room_votes` 唯一索引并写入 `g1_fixture_v1`（思源/建大各 10 门店 30 菜，合成、无图）。
- 演示库、S10 导入库、PRE-00 源库、S05/S06 历史隔离库 SHA 全部未变（`data/db_protection.json`）。
- 隔离库现状（测试写入后）：40 门店（SIYUAN 10 / JIANDA_YANTA 10 / NULL 20）、160 菜、90 房、392 票、12 条冰箱记录。回滚：删除 `backend/eatwhat_g1_s07_iso.db` 即可，受保护库无需恢复。

## 5. 已知观察（不作为本组通过项）

- 揭晓卡「群组满意度」可显示 100.77 / 108.64（原始分未截断）。这是既有群组结算展示口径，S06 已通过该响应结构；若统一审查认为展示需封顶到 100，应在对应步骤裁决，G1 未擅自改动算法。
- 四身份房间中「u3+u4 候选包含香菜」未出现，原因是该菜在均值排序中未进前 10，不是过滤错误；证据里保留原始候选名单，避免把排序结果误读成筛选缺陷。

## 6. 交付物

`SUBMISSION.md`、`BASELINE.md`、`CHECKS.md`、`SOURCE_MANIFEST.json`、`validation.json`、`logs/`、`browser/`（含 `shots/` 与复验脚本）、`data/`。
