# Lottie 素材来源与授权

本文件记录 `frontend/src/assets/lottie/` 下五个 JSON 的出处、授权与校验值。改素材时同步更新本表。

## 1. 天气三件：@meteocons/lottie（monochrome）

- 上游仓库：<https://github.com/basmilius/meteocons>（作者 Bas Milius）
- 取件地址：`https://unpkg.com/@meteocons/lottie/monochrome/<slug>.json`
- 授权：**MIT License**（动画取自 Bas Milius 的 Meteocons；上游对动画文件按 MIT 释出，仓库内保留本说明）
- 风格：`monochrome` 单色版，与 v2.3 单色体系一致；素材内部填充为纯黑 `[0,0,0,1]`，在深色底上由组件 `filter: invert(1)` 反白使用，**未修改 JSON 内容**。

| 本地文件 | 上游 slug | 字节 | sha256[:16] |
|---|---|---|---|
| `weather-sunny.json` | `clear-day` | 4852 | `6d71975a8c9a1214` |
| `weather-rainy.json` | `rain` | 11826 | `86c6e752aa445c38` |
| `weather-snowy.json` | `snow` | 28667 | `eb633df978d52efa` |

## 2. 空状态：本项目自绘

| 本地文件 | 来源 | 字节 | sha256[:16] |
|---|---|---|---|
| `empty-state.json` | 本仓库脚本生成，版权随仓库（MIT） | 3620 | `647952e33db6b120` |

- 生成脚本：`scripts/make_empty_state_lottie.py`（空碗轮廓 + 碗沿 + 三个上浮小圆点，128×128，60 帧 / 30fps，循环）
- 为什么不从 LottieFiles 取：LottieFiles 站点由 Cloudflare 托管，程序化访问返回 403 挑战页，`/api/v1/search` 亦 404，无法在构建流程里稳定取件；且其免费区素材授权逐条不同，批量落地需逐个人工核，反而不可复现。气象三件改用 meteocons 是"授权明确 + 可脚本取件 + 风格统一"三者同时满足的方案。

## 3. 多人揭晓：本项目自绘

| 本地文件 | 来源 | 字节 | sha256[:16] |
|---|---|---|---|
| `reveal.json` | 本仓库脚本生成，版权随仓库（MIT） | 7636 | `c92890cc8c888bbd` |

- 生成脚本：`scripts/make_reveal_lottie.py`（中心圆点 + 外圈 8 点，128×128，60 帧 / 30fps，依次淡入后保持）。
- 圆点使用静态坐标，只对透明度做关键帧动画；多段位置轨道在当前 `lottie_light` 下会把图层移到 `-999999`，不能再用“SVG/path 节点存在”代替可见性验收。
- 消费位置：`frontend/src/views/mobile/Room.vue` 通过 `LottieIcon name="reveal"` 单次播放；GSAP 仍负责揭晓时间线，confetti 仍负责粒子。

## 4. 渲染方式

- `frontend/src/components/LottieIcon.vue`：`import.meta.glob('../assets/lottie/*.json', { eager: true, import: 'default' })` 打包全部 JSON。
- 播放器按需动态 `import('lottie-web/build/player/lottie_light')`（约 170 KB，gzip 48.6 KB），不用全量包。
- 缺件时渲染中性描边方块兜底（`data-missing="true"`），不静默空屏。

## 5. 复购/替换流程

1. 把新 JSON 放到 `frontend/src/assets/lottie/`，文件名保持 `weather-sunny|weather-rainy|weather-snowy|empty-state|reveal.json`。
2. 若是黑白稿且底色深，确认组件里 `invert` 是否需要；彩色素材要在 `LottieIcon.vue` 里关掉反白。
3. 更新本表（来源页、授权、字节、sha256）。
4. `npm run build` 并截图确认（玻璃参数与素材替换都要附对照截图）；Lottie 还需断言路径矩形位于组件可视区域内。
