# WeatherPill 玻璃材质开发包（Apple 官方 Figma 实测提取）

> 用途：食刻 EatWhat 的 WeatherPill 天气胶囊及同类悬浮玻璃组件的开发依据。
> 来源：Apple 官方 Figma 社区文件「macOS 27」→ Materials 页。
> 副本（用户 Drafts，未动原文件）：https://www.figma.com/design/yA920qghWCjvGJstC2o0Co/macOS-27--Community-
> 提取日期：2026-10-23。文中标「原值」者为 Figma 右侧面板实测数值；标「转写/组合」者为据原值整理的可落地代码。

---

## 1. 首选样本

- 路径：Materials 页 > 组件 **Liquid Glass - Small** > 变体 **Mode=Light, Active=True, State=Default**
- 结构：两层 48×48 Frame 叠放，圆角 1000（全圆角，CSS 用 999px），下层叫 Fill + Shadow，上层叫 Glass Effect
- 该样本没有独立的 Background Blur、没有 Saturate 参数：背景雾化由 Glass 效果的 Frost 承担

### 参数表 A：下层 Fill + Shadow（不透明度 100%，无描边）

填充（自上而下 4 层叠放）：
- `#F8F8F8` · 20%
- `#444444` · 60%
- `#FFFFFF` · 25%
- `#000000` · 25%

外阴影 Drop shadow（4 个）：
| X | Y | Blur | Spread | 颜色 |
|---|---|------|--------|------|
| 1.25 | 0 | 0 | −0.75 | #D0D0D0 · 100% |
| −1.25 | 0 | 0 | −0.75 | #D0D0D0 · 100% |
| 0 | 0 | 0 | 0.5 | #E8E8E8 · 100% |
| 0 | 8 | 15 | 0 | #000000 · 2%（唯一柔和投影） |

### 参数表 B：上层 Glass Effect（填充 #FFFFFF · 100%，无描边）

内阴影 Inner shadow（3 个）：
| X | Y | Blur | Spread | 颜色 |
|---|---|------|--------|------|
| 0 | 40 | 10 | −40 | #282828 · 100% |
| 0 | −40 | 10 | −40 | #282828 · 100% |
| 0 | 40 | 30 | −40 | #E6E6E6 · 100% |

Glass 效果（Figma/系统级液态玻璃渲染参数，CSS 无等价属性，只能作设计参照）：
- Light Angle 0° / Light Intensity（Opacity）25%
- Refraction 70 / Depth 30 / Dispersion 20 / Frost 6 / Splay 20

---

## 2. 转写 CSS（据上表原值 1:1 转写，非 Figma 复制原文）

说明：Figma 的 CSS 原文未能取得——Dev Mode 代码面板需 Professional 付费版（未购买），Design 模式 Copy as CSS 只进剪贴板、浏览器环境读不回。以下为按面板原值转写的等价实现，数值未做任何改动；多层填充用同色 linear-gradient 叠写以保证 CSS 合法。

```css
.weather-pill {
  border-radius: 999px;
  /* 下层 4 层填充（自上而下） */
  background:
    linear-gradient(rgba(248, 248, 248, 0.20), rgba(248, 248, 248, 0.20)),
    linear-gradient(rgba(68, 68, 68, 0.60), rgba(68, 68, 68, 0.60)),
    linear-gradient(rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.25)),
    linear-gradient(rgba(0, 0, 0, 0.25), rgba(0, 0, 0, 0.25));
  box-shadow:
    /* 上层 3 个内阴影 */
    inset 0 40px 10px -40px rgba(40, 40, 40, 1),
    inset 0 -40px 10px -40px rgba(40, 40, 40, 1),
    inset 0 40px 30px -40px rgba(230, 230, 230, 1),
    /* 下层 4 个外阴影 */
    1.25px 0 0 -0.75px rgba(208, 208, 208, 1),
    -1.25px 0 0 -0.75px rgba(208, 208, 208, 1),
    0 0 0 0.5px rgba(232, 232, 232, 1),
    0 8px 15px rgba(0, 0, 0, 0.02);
}
```

注意：此版只有填充与阴影，没有背景模糊（Glass 的折射/雾化 CSS 表达不了）。单独用它，透底感弱于 Figma 预览，属预期。

---

## 3. 次选样本：经典材质（可直接用 backdrop-filter 落地）

- 路径：Materials 页 > 组件 Materials 的 Light 变体（或 Materials - Light 画板）
- 三档同色 `#F6F6F6`、Background Blur 均为 60、无描边无阴影，仅不透明度不同：
  - Ultrathin 36%（最透）/ Thin 48% / Medium 60%

```css
.weather-pill-fallback {
  background: rgba(246, 246, 246, 0.48); /* Thin；Ultrathin 改 0.36，Medium 改 0.60 */
  backdrop-filter: blur(60px);
  -webkit-backdrop-filter: blur(60px);
  border-radius: 999px;
}
```

Figma 未给 saturate 值；如开发中自行加 `saturate()`，属自选参数、非 Apple 原值，须在代码注释中注明。

---

## 4. Web 生产组合版（推荐实际开发用）

思路：用次选经典材质的填充+模糊做「透底」，叠上首选样本的内/外阴影做「塑形」，是 Web 端最接近原样本的组合。数值全部来自上面两表，未发明新值（blur 的量纲来自经典材质，与 Glass 的 Frost=6 不是同一量纲，此处仅作近似）。

```css
.weather-pill {
  border-radius: 999px;
  background: rgba(246, 246, 246, 0.48);
  backdrop-filter: blur(60px);
  -webkit-backdrop-filter: blur(60px);
  box-shadow:
    inset 0 40px 10px -40px rgba(40, 40, 40, 1),
    inset 0 -40px 10px -40px rgba(40, 40, 40, 1),
    inset 0 40px 30px -40px rgba(230, 230, 230, 1),
    1.25px 0 0 -0.75px rgba(208, 208, 208, 1),
    -1.25px 0 0 -0.75px rgba(208, 208, 208, 1),
    0 0 0 0.5px rgba(232, 232, 232, 1),
    0 8px 15px rgba(0, 0, 0, 0.02);
}
```

使用约束：
- 只用于小面积悬浮元素（WeatherPill、顶部条、抽屉把手等），不做大面积卡片与整页背景
- 背景为深色（Grainient 深灰底 / Liquid Chrome）时，本浅色玻璃仍可读；若后续要 Dark 变体数值，需另行进副本提取（本次未取）
- `backdrop-filter` 不支持时降级为 `rgba(246,246,246,0.85)` 实底填充
