# F12 颜色归一：对照表与口径

## 归一前（2026-10-24 15:2x 测量，同一段正则）

    裸色值：157 处 / 21 个文件
    rgb 家族 122 处 | #hex 35 处
    最集中：Profile.vue 27、Room.vue 21、Home.vue 16、Fridge.vue 14、theme.js 12

## 归一后

    scripts/check-colors.mjs → ✓ 31 个文件无裸 hex / rgb / hsl

复算脚本：见 ../logs/gate_pass.log 与 data/after_scan.txt。

## hex → 令牌

| 原值 | 令牌 |
|---|---|
| #17171a / #17171A | ar(--color-ink) |
| #55555e | ar(--color-steel) |
| #f4f4f5 / #e4e4e7 | ar(--color-mist) |
| #ffffff / #fff | ar(--color-white) |
| #d4d4d8 | ar(--color-silver) |
| #3a3a40 | ar(--color-grain-a) |
| #1a1a1a | ar(--color-chrome) |
| #222226 | ar(--color-chrome-max) |
| #121215 | ar(--color-panel) |
| #101013 | ar(--color-sheet) |
| #000 / #000000 | ar(--color-black) |
| #212121 / #a1a1aa | ar(--color-ink) / ar(--color-steel)（就近取） |

## rgb 家族 → 通道令牌

| 原写法 | 新写法 |
|---|---|
| gb(255 255 255 / a) | gb(var(--rgb-white) / a) |
| gb(0 0 0 / a) | gb(var(--rgb-black) / a) |
| gb(23 23 26 / a) | gb(var(--rgb-ink) / a) |
| gb(85 85 94 / a) | gb(var(--rgb-steel) / a) |
| gb(18 18 21 / a) | gb(var(--rgb-panel) / a) |
| gb(16 16 19 / a) | gb(var(--rgb-sheet) / a) |

## 人工处理（脚本不做的部分）

1. Home.vue .toast--warn：暖色 → **反白底 + ink 字**。单色体系下警示靠明度反差，不引入色相。
2. Home.vue 的 @media (max-height: 700px) 里夹着一段重复的 .toast* / .deck-actions（早前 Substring 改 CSS 的遗留），一并删除。
3. Footprint.vue 的 ECharts itemStyle.borderColor：CSS 变量在 canvas 上是非法颜色，改走 lpha(t.ink, 0.55)。

## 门禁规则

- 禁：#hex、数字 gb()/rgba()、hsl()/hsla()
- 放行：ar(--…)、gb(var(--rgb-x) / a)、	ransparent、currentColor
- 豁免目录：src/styles/、src/utils/theme.js、src/components/bits/（Vue Bits 上游原件，shader 颜色不改）
