# Vue Bits 三个 L0 背景组件接入对照（Grainient / LiquidChrome / Silk）

> 任务授权（用户，2026-10-23）：「自行去 vue-bits.dev 取源文件原件接入，只改 props（颜色、speed），不许改 shader 与内部实现；验收时交与原文件的 diff 对照」。
> 本文即验收用的 diff 对照。原文件已归档在 `docs/vuebits-originals/`，可直接 `git diff --no-index` 复核。

---

## 0. 一句话结论

三个组件**都取到了上游原始 `.vue` 源码**（不是二手改写、不是凭 shader 手搓），落盘到 `frontend/src/components/bits/`。除「去 TypeScript 类型标注」与「props 默认值」这两类改动外，**shader 字符串、渲染循环、几何、uniform 逻辑逐字未动**——可用第 5 节的 diff 直接核对（shader 段落零 hunk 命中）。

| 组件 | 用到页面 | 上游源文件 | 改动 | 状态 |
|---|---|---|---|---|
| `Grainient.vue` | 全局页底 L0 | ✅ 取到原件 | 4 个 props 默认值 + 去类型标注 | ✅ 达标 |
| `LiquidChrome.vue` | 首页顶部 / 揭晓页 | ✅ 取到原件 | 1 个 props 默认值 + 去类型标注 | ⚠️ 差一条：`最亮 ≤ #222226` props 做不到，见 §6.1 |
| `Silk.vue` | 启动 / 登录页 | ✅ 取到原件 | 1 个 props 默认值 + 去类型标注 | ✅ 达标 |

---

## 1. 取件证据（可复现）

- 仓库：`DavidHDev/vue-bits`（vue-bits.dev 的源码仓库，MIT + Commons Clause）
- 抓取时 `main` HEAD commit：**`3766ebeeed37ec35bce29f001b6d101c7b17da35`**（2026-10-19）
- 抓取日期：**2026-10-23**
- 分发方式核实：网站是 shadcn 风格 copy-paste。仓库里既有成品 `.vue`，也有 registry JSON（`public/r/Grainient.json`、`public/r/LiquidChrome.json`，内容 = 同一份源码的 `files[].content` + `dependencies: ["ogl@^1.0.11"]`）。**`public/r/Silk.json` 不存在（404）**，Silk 只有 `src/content/Backgrounds/Silk/Silk.vue` 一份源文件——这点如实记录，不是漏取。

| 文件 | 原始 URL（`https://raw.githubusercontent.com/DavidHDev/vue-bits/main/…`，抓取时） | 原件归档 | 接入后 |
|---|---|---|---|
| Grainient | `src/content/Backgrounds/Grainient/Grainient.vue` | `docs/vuebits-originals/Grainient.vue`<br>8001 B / 285 行<br>sha256 `7026acc4395fcaabd99a86b438118c7aa8e7924048f03963d498c45a71499f7a` | `frontend/src/components/bits/Grainient.vue`<br>8085 B / 264 行<br>sha256 `1d795f7c5f39662048ea2bb79fa4b77cbc50eb611899b1b21f58b97acc96defc` |
| LiquidChrome | `src/content/Backgrounds/LiquidChrome/LiquidChrome.vue` | `docs/vuebits-originals/LiquidChrome.vue`<br>5763 B / 199 行<br>sha256 `13b563b572272798580e692fe5bdcd6d5f469779f929fe124d274aef7e83461f` | `frontend/src/components/bits/LiquidChrome.vue`<br>5812 B / 195 行<br>sha256 `20434f3a8a2d01e109cec2bb9e8e68e507b64928413ad78e7f5d44fdd562ff86` |
| Silk | `src/content/Backgrounds/Silk/Silk.vue` | `docs/vuebits-originals/Silk.vue`<br>6615 B / 273 行<br>sha256 `549f75e49db81e3e0d379128bcaf24cb84e06be195b8efe992c68c462ba1e371` | `frontend/src/components/bits/Silk.vue`<br>6648 B / 268 行<br>sha256 `9d8171f26591231cfe041ca5f677ee0cae8817d7fd65cf9fc742119a6c3439f2` |

复核命令（Windows / PowerShell，项目根目录）：

```powershell
git diff --no-index --no-color docs/vuebits-originals/Grainient.vue      frontend/src/components/bits/Grainient.vue
git diff --no-index --no-color docs/vuebits-originals/LiquidChrome.vue   frontend/src/components/bits/LiquidChrome.vue
git diff --no-index --no-color docs/vuebits-originals/Silk.vue           frontend/src/components/bits/Silk.vue
```

三个文件头部均加了 3 行注释：来源 URL / 抓取日期 / `改动仅限默认 props，见 docs/vuebits-diff.md`。

---

## 2. Grainient.vue

**改的 props 默认值（4 个）**

| prop | 上游默认 | 项目默认 | 依据 |
|---|---|---|---|
| `timeSpeed` | `0.25` | **`0.2`** | MASTER_SPEC v2.3.1：timeSpeed ≈ 0.2 |
| `color1` | `'#48FF28'`（荧光绿） | **`'#3A3A40'`** | 单色体系 |
| `color2` | `'#2c3d32'` | **`'#17171A'`** | 黑 |
| `color3` | `'#65a865'` | **`'#55555E'`** | 银灰 |

其余 19 个 props（`colorBalance 0.0` / `warpStrength 1.0` / `warpFrequency 5.0` / `warpSpeed 2.0` / `warpAmplitude 50.0` / `blendAngle 0.0` / `blendSoftness 0.05` / `rotationAmount 500.0` / `noiseScale 2.0` / `grainAmount 0.1` / `grainScale 2.0` / `grainAnimated false` / `contrast 1.5` / `gamma 1.0` / `saturation 1.0` / `centerX 0.0` / `centerY 0.0` / `zoom 0.9` / `className ''`）**逐字保留**，只把「类型声明」写法换成运行时 `defineProps({ type, default })`，数值不变。

**去类型标注（24 行 interface 删除 + 6 处行内标注）**

`interface GrainientProps {…}` 整块删除（24 行）；`<script setup lang="ts">`→`<script setup>`；`(hex: string): [number, number, number]`→`(hex)`；`useTemplateRef<HTMLDivElement>`→`useTemplateRef`；`let cleanup: (() => void) | null`→`let cleanup`；`gl.canvas as HTMLCanvasElement`→`gl.canvas`；`(program.uniforms.iResolution as { value: Float32Array }).value`→`program.uniforms.iResolution.value`；`(t: number)`→`(t)`；`(program.uniforms.iTime as { value: number }).value`→`program.uniforms.iTime.value`。

**除 props 外无改动**：GLSL `vertex`/`fragment` 模板字符串、WebGL2 `#version 300 es`、`Triangle` 几何、uniform 装配、`ResizeObserver` 尺寸、`requestAnimationFrame` 循环、`watch` 重建逻辑、`<template>` 全部原样。

---

## 3. LiquidChrome.vue

**改的 props 默认值（1 个）**

| prop | 上游默认 | 项目默认 | 说明 |
|---|---|---|---|
| `baseColor` | `() => [0.1, 0.1, 0.1]` | **`() => [26 / 255, 26 / 255, 26 / 255]`** | 见下 |

⚠️ **`baseColor` 不是 hex 字符串，是归一化 float RGB 数组**（上游 API 如此，shader 里 `uniform vec3 uBaseColor` 直接吃 `new Float32Array(props.baseColor)`）。所以 `'#1a1a1a'` 不能字面量塞进去，只能换算：`26/255 = 0.101960784…`。写成 `26 / 255` 而不是 `0.10196` 是为了让「= #1a1a1a」在源码里一眼可验。
顺带一个事实：上游默认 `0.1 × 255 = 25.5`，四舍五入正好也是 **#1A1A1A**——也就是说这一项在视觉上与上游几乎一致，本次改动只是把它钉成精确值。

`speed` 保持上游 `0.2`（MASTER_SPEC 未给 LiquidChrome 指定 speed）；`amplitude 0.5` / `frequencyX 3` / `frequencyY 2` / `interactive true` 全保留。

**去类型标注（8 行 interface 删除 + 10 处行内标注）**

`interface LiquidChromeProps {…}` 删除；`lang="ts"` 去掉；`useTemplateRef<HTMLDivElement>`；`let cleanupAnimation: (() => void) | null`；`program.uniforms.uResolution.value as Float32Array`；`program.uniforms.uMouse.value as Float32Array`（2 处：mouse / touch）；`(event: MouseEvent)`；`(event: TouchEvent)`；`let animationId: number`；`(t: number)`。

**除 props 外无改动**：`vertexShader`/`fragmentShader`（含 `uBaseColor / abs(sin(uTime - uv.y - uv.x))` 这一行）、3×3 超采样循环、`Triangle`、`uResolution` 三元组装配、mouse/touch 监听、rAF 循环、`watch(() => props, deep)` 重建逻辑、`<template>` 全部原样。

---

## 4. Silk.vue

**改的 props 默认值（1 个）**

| prop | 上游默认 | 项目默认 | 依据 |
|---|---|---|---|
| `speed` | `5` | **`1.5`** | MASTER_SPEC：Speed 1~2 |

`scale 1` / `noiseIntensity 1.5` / `rotation 0` / `className ''` / `style () => ({})` 保留。`color` 保留上游 **`'#7B7481'`**（spec 未指定 Silk 色值，不擅自发明；调用处要改直接传 `color`，因为 shader 里 `uColor` 每帧从 `props.color` 取，传了就生效）。

**去类型标注（9 行 interface 删除 + 11 处行内标注）**

`interface SilkProps {…}` 删除；`import { …, type CSSProperties, … }` 去掉 `type CSSProperties`；`useTemplateRef<HTMLDivElement>`；`(hex: string): [number, number, number]`；`let renderer/mesh/program/camera: Xxx | null`（4 行）；`renderer!.setSize(...)` 与 `renderer!.render(...)` 的 TS 非空断言（`!` 在纯 JS 里是语法错误，必须去掉）；`(t: number)`。

**除 props 外无改动**：`vertexShader`/`fragmentShader`（含 `vec4 col = vec4(uColor, 1.0) * vec4(pattern) - rnd / 15.0 * uNoiseIntensity;`）、`Plane` 几何、`Camera(fov 75)`、`mesh.scale` 适配、`uTime += 0.1 * deltaTime` 循环、`<style scoped>` 全部原样。上游末尾那个空实现 `watch(() => [props.speed, …], () => {})` 也**原样保留**（它确实什么都不做，但"内部实现不动"就是不动）。

---

## 5. 完整 diff（原文件 → 接入文件）

```diff
########## Grainient.vue ##########
--- a/docs/vuebits-originals/Grainient.vue
+++ b/frontend/src/components/bits/Grainient.vue
@@ -1,33 +1,12 @@
-<script setup lang="ts">
+<!--
+来源 URL: https://raw.githubusercontent.com/DavidHDev/vue-bits/main/src/content/Backgrounds/Grainient/Grainient.vue
+抓取日期: 2026-10-23
+改动仅限默认 props，见 docs/vuebits-diff.md
+-->
+<script setup>
 import { Mesh, Program, Renderer, Triangle } from 'ogl';
 import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue';
 
-interface GrainientProps {
-  timeSpeed?: number;
-  colorBalance?: number;
-  warpStrength?: number;
-  warpFrequency?: number;
-  warpSpeed?: number;
-  warpAmplitude?: number;
-  blendAngle?: number;
-  blendSoftness?: number;
-  rotationAmount?: number;
-  noiseScale?: number;
-  grainAmount?: number;
-  grainScale?: number;
-  grainAnimated?: boolean;
-  contrast?: number;
-  gamma?: number;
-  saturation?: number;
-  centerX?: number;
-  centerY?: number;
-  zoom?: number;
-  color1?: string;
-  color2?: string;
-  color3?: string;
-  className?: string;
-}
-
-const hexToRgb = (hex: string): [number, number, number] => {
+const hexToRgb = (hex) => {
   const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
   if (!result) return [1, 1, 1];
@@ -126,33 +105,33 @@ void main(){
 `;
 
-const props = withDefaults(defineProps<GrainientProps>(), {
-  timeSpeed: 0.25,
-  colorBalance: 0.0,
-  warpStrength: 1.0,
-  warpFrequency: 5.0,
-  warpSpeed: 2.0,
-  warpAmplitude: 50.0,
-  blendAngle: 0.0,
-  blendSoftness: 0.05,
-  rotationAmount: 500.0,
-  noiseScale: 2.0,
-  grainAmount: 0.1,
-  grainScale: 2.0,
-  grainAnimated: false,
-  contrast: 1.5,
-  gamma: 1.0,
-  saturation: 1.0,
-  centerX: 0.0,
-  centerY: 0.0,
-  zoom: 0.9,
-  color1: '#48FF28',
-  color2: '#2c3d32',
-  color3: '#65a865',
-  className: ''
+const props = defineProps({
+  timeSpeed: { type: Number, default: 0.2 },
+  colorBalance: { type: Number, default: 0.0 },
+  warpStrength: { type: Number, default: 1.0 },
+  warpFrequency: { type: Number, default: 5.0 },
+  warpSpeed: { type: Number, default: 2.0 },
+  warpAmplitude: { type: Number, default: 50.0 },
+  blendAngle: { type: Number, default: 0.0 },
+  blendSoftness: { type: Number, default: 0.05 },
+  rotationAmount: { type: Number, default: 500.0 },
+  noiseScale: { type: Number, default: 2.0 },
+  grainAmount: { type: Number, default: 0.1 },
+  grainScale: { type: Number, default: 2.0 },
+  grainAnimated: { type: Boolean, default: false },
+  contrast: { type: Number, default: 1.5 },
+  gamma: { type: Number, default: 1.0 },
+  saturation: { type: Number, default: 1.0 },
+  centerX: { type: Number, default: 0.0 },
+  centerY: { type: Number, default: 0.0 },
+  zoom: { type: Number, default: 0.9 },
+  color1: { type: String, default: '#3A3A40' },
+  color2: { type: String, default: '#17171A' },
+  color3: { type: String, default: '#55555E' },
+  className: { type: String, default: '' }
 });
 
-const containerRef = useTemplateRef<HTMLDivElement>('containerRef');
+const containerRef = useTemplateRef('containerRef');
 
-let cleanup: (() => void) | null = null;
+let cleanup = null;
 const setup = () => {
   if (!containerRef.value) return;
@@ -166,5 +145,5 @@ const setup = () => {
 
   const gl = renderer.gl;
-  const canvas = gl.canvas as HTMLCanvasElement;
+  const canvas = gl.canvas;
   canvas.style.width = '100%';
   canvas.style.height = '100%';
@@ -212,5 +191,5 @@ const setup = () => {
     const height = Math.max(1, Math.floor(rect.height));
     renderer.setSize(width, height);
-    const res = (program.uniforms.iResolution as { value: Float32Array }).value;
+    const res = program.uniforms.iResolution.value;
     res[0] = gl.drawingBufferWidth;
     res[1] = gl.drawingBufferHeight;
@@ -223,6 +202,6 @@ const setup = () => {
   let raf = 0;
   const t0 = performance.now();
-  const loop = (t: number) => {
-    (program.uniforms.iTime as { value: number }).value = (t - t0) * 0.001;
+  const loop = (t) => {
+    program.uniforms.iTime.value = (t - t0) * 0.001;
     renderer.render({ scene: mesh });
     raf = requestAnimationFrame(loop);
########## LiquidChrome.vue ##########
--- a/docs/vuebits-originals/LiquidChrome.vue
+++ b/frontend/src/components/bits/LiquidChrome.vue
@@ -1,27 +1,23 @@
-<script setup lang="ts">
+<!--
+来源 URL: https://raw.githubusercontent.com/DavidHDev/vue-bits/main/src/content/Backgrounds/LiquidChrome/LiquidChrome.vue
+抓取日期: 2026-10-23
+改动仅限默认 props，见 docs/vuebits-diff.md
+-->
+<script setup>
 import { onMounted, onUnmounted, watch, useTemplateRef } from 'vue';
 import { Renderer, Program, Mesh, Triangle } from 'ogl';
 
-interface LiquidChromeProps {
-  baseColor?: number[];
-  speed?: number;
-  amplitude?: number;
-  frequencyX?: number;
-  frequencyY?: number;
-  interactive?: boolean;
-}
-
-const props = withDefaults(defineProps<LiquidChromeProps>(), {
-  baseColor: () => [0.1, 0.1, 0.1],
-  speed: 0.2,
-  amplitude: 0.5,
-  frequencyX: 3,
-  frequencyY: 2,
-  interactive: true
+const props = defineProps({
+  baseColor: { type: Array, default: () => [26 / 255, 26 / 255, 26 / 255] },
+  speed: { type: Number, default: 0.2 },
+  amplitude: { type: Number, default: 0.5 },
+  frequencyX: { type: Number, default: 3 },
+  frequencyY: { type: Number, default: 2 },
+  interactive: { type: Boolean, default: true }
 });
 
-const containerRef = useTemplateRef<HTMLDivElement>('containerRef');
+const containerRef = useTemplateRef('containerRef');
 
-let cleanupAnimation: (() => void) | null = null;
+let cleanupAnimation = null;
 
 const setupAnimation = () => {
@@ -110,5 +106,5 @@ const setupAnimation = () => {
 
     renderer.setSize(container.offsetWidth * scale, container.offsetHeight * scale);
-    const resUniform = program.uniforms.uResolution.value as Float32Array;
+    const resUniform = program.uniforms.uResolution.value;
     resUniform[0] = gl.canvas.width;
     resUniform[1] = gl.canvas.height;
@@ -118,5 +114,5 @@ const setupAnimation = () => {
   resize();
 
-  function handleMouseMove(event: MouseEvent) {
+  function handleMouseMove(event) {
     if (!container) return;
 
@@ -124,10 +120,10 @@ const setupAnimation = () => {
     const x = (event.clientX - rect.left) / rect.width;
     const y = 1 - (event.clientY - rect.top) / rect.height;
-    const mouseUniform = program.uniforms.uMouse.value as Float32Array;
+    const mouseUniform = program.uniforms.uMouse.value;
     mouseUniform[0] = x;
     mouseUniform[1] = y;
   }
 
-  function handleTouchMove(event: TouchEvent) {
+  function handleTouchMove(event) {
     if (event.touches.length > 0) {
       const touch = event.touches[0];
@@ -137,5 +133,5 @@ const setupAnimation = () => {
       const x = (touch.clientX - rect.left) / rect.width;
       const y = 1 - (touch.clientY - rect.top) / rect.height;
-      const mouseUniform = program.uniforms.uMouse.value as Float32Array;
+      const mouseUniform = program.uniforms.uMouse.value;
       mouseUniform[0] = x;
       mouseUniform[1] = y;
@@ -148,6 +144,6 @@ const setupAnimation = () => {
   }
 
-  let animationId: number;
-  function update(t: number) {
+  let animationId;
+  function update(t) {
     animationId = requestAnimationFrame(update);
     program.uniforms.uTime.value = t * 0.001 * props.speed;
########## Silk.vue ##########
--- a/docs/vuebits-originals/Silk.vue
+++ b/frontend/src/components/bits/Silk.vue
@@ -1,33 +1,28 @@
+<!--
+来源 URL: https://raw.githubusercontent.com/DavidHDev/vue-bits/main/src/content/Backgrounds/Silk/Silk.vue
+抓取日期: 2026-10-23
+改动仅限默认 props，见 docs/vuebits-diff.md
+-->
 <template>
   <div ref="containerRef" :class="className" :style="style" class="w-full h-full"></div>
 </template>
 
-<script setup lang="ts">
-import { onMounted, onUnmounted, watch, type CSSProperties, useTemplateRef } from 'vue';
+<script setup>
+import { onMounted, onUnmounted, watch, useTemplateRef } from 'vue';
 import { Renderer, Program, Mesh, Plane, Camera } from 'ogl';
 
-interface SilkProps {
-  speed?: number;
-  scale?: number;
-  color?: string;
-  noiseIntensity?: number;
-  rotation?: number;
-  className?: string;
-  style?: CSSProperties;
-}
-
-const props = withDefaults(defineProps<SilkProps>(), {
-  speed: 5,
-  scale: 1,
-  color: '#7B7481',
-  noiseIntensity: 1.5,
-  rotation: 0,
-  className: '',
-  style: () => ({})
+const props = defineProps({
+  speed: { type: Number, default: 1.5 },
+  scale: { type: Number, default: 1 },
+  color: { type: String, default: '#7B7481' },
+  noiseIntensity: { type: Number, default: 1.5 },
+  rotation: { type: Number, default: 0 },
+  className: { type: String, default: '' },
+  style: { type: Object, default: () => ({}) }
 });
 
-const containerRef = useTemplateRef<HTMLDivElement>('containerRef');
+const containerRef = useTemplateRef('containerRef');
 
-const hexToNormalizedRGB = (hex: string): [number, number, number] => {
+const hexToNormalizedRGB = (hex) => {
   const clean = hex.replace('#', '');
   const r = parseInt(clean.slice(0, 2), 16) / 255;
@@ -102,8 +97,8 @@ void main() {
 `;
 
-let renderer: Renderer | null = null;
-let mesh: Mesh | null = null;
-let program: Program | null = null;
-let camera: Camera | null = null;
+let renderer = null;
+let mesh = null;
+let program = null;
+let camera = null;
 let animateId = 0;
 
@@ -148,5 +143,5 @@ const initSilk = () => {
     height = Math.max(height, 300);
 
-    renderer!.setSize(width, height);
+    renderer.setSize(width, height);
     camera.perspective({ aspect: width / height });
 
@@ -195,5 +190,5 @@ const initSilk = () => {
 
   let lastTime = 0;
-  const update = (t: number) => {
+  const update = (t) => {
     animateId = requestAnimationFrame(update);
     const deltaTime = (t - lastTime) / 1000;
@@ -207,5 +202,5 @@ const initSilk = () => {
       program.uniforms.uColor.value = hexToNormalizedRGB(props.color);
       program.uniforms.uRotation.value = props.rotation;
-      renderer!.render({ scene: mesh, camera });
+      renderer.render({ scene: mesh, camera });
     }
   };
```

---

## 6. 已知偏差 / 需拍板（不粉饰）

### 6.1 🔴 LiquidChrome 的「最亮不超过 #222226」用 props 做不到

上游 shader 的核心一行是：

```glsl
vec3 color = uBaseColor / abs(sin(uTime - uv.y - uv.x));
```

分母 `abs(sin(...))` 在画面上扫过整个 `[0, 1]` 区间，于是 **只要 `|sin| ≤ baseColor(≈0.102)` 就输出 ≥ 1.0 并被钳到纯白**。按相位比例算，约 `2·asin(0.102)/π ≈ 6.5%` 的画面会是死白高光——这是液态铬的"金属反光"本体，不是 bug。

结论：**只要不碰 shader，就没有任何 prop 能把最亮压到 #222226**（`baseColor` 调到 0 会让整屏全黑，高光依旧是 1.0）。这与"不许改 shader"的授权直接冲突，所以我没有偷偷改 shader，也没有假装达标。三条出路，请你拍板：

1. **（推荐，零组件改动）调用处做一层色调映射**：给包裹容器加 `style="filter: brightness(0.13)"`。`filter` 是逐像素线性缩放，白 1.0 → 0.13 = **#212121 < #222226** ✅，且完全在 L0 容器上，不在组件里。
2. 调用处叠一层 `bg-[#17171A]/85` 遮罩（简单但会糊掉铬面纹理）。
3. 授权我在组件里加一个 `maxLuminance` prop 并在 shader 末尾加一行 `col = min(col, uMaxLuminance)` —— 这是**改 shader**，需要你重新授权。

在拍板前，`/m` 首页顶部与揭晓页**先别上线 LiquidChrome**，否则满屏白色高光会直接违反"文字不许压在铬面上""L2 实底"的观感契约。

### 6.2 🟡 三个文件里有裸 hex（与 AGENTS.md 红线冲突，但是被授权的例外）

AGENTS.md：「颜色只有一个出口……组件、页面、图表、动效里禁止出现裸 hex」。而本任务的授权恰好是「只改 props 默认值」——props 默认值只能是字面量，没法引 CSS 变量（`getComputedStyle` 在模块求值期也拿不到）。现状：`#3A3A40 / #17171A / #55555E / #1a1a1a` 以默认值形式硬编码在 `.vue` 里，`Silk` 还留着上游的 `#7B7481`。这是**授权范围内的例外**，记在此处以免后面被当成违规返工；若要彻底消除，需要改成"调用处从 `src/utils/theme.js` 读变量再传入"，组件里默认值仍会是字面量（fallback）。

### 6.3 🟡 WebGL 后端不一致

`Grainient` 用 **WebGL2**（`#version 300 es` + `Renderer({ webgl: 2 })`），`LiquidChrome` / `Silk` 用 WebGL1（`gl_FragColor`、`attribute/varying`）。Capacitor 打包的 Android WebView 若 WebGL2 不可用，`Grainient` 会静默黑屏（上游没有降级分支）。本次范围不含降级，记 TODO。

### 6.4 🟢 新依赖

上游 registry 声明的唯一依赖是 `ogl@^1.0.11`，本项目原先**没有**。已安装：`frontend/package.json` → `"ogl": "^1.0.11"`，`npm install` 输出 `added 1 package in 14s`（只多 1 个包）。没有引入 `typescript`，没有引入 `three`。

---

## 7. 验证记录（真实输出）

**A. 单文件编译（项目自带的 `@vue/compiler-sfc`，parse + compileScript + compileTemplate）**

```
Grainient.vue: OK  script lang=js  props=23  templateCode=392b
LiquidChrome.vue: OK  script lang=js  props=6  templateCode=354b
Silk.vue: OK  script lang=js  props=7  templateCode=451b
exit=0
```

**B. 三个组件真正过 Vite/Rollup（临时 smoke 入口，验证 `ogl` 能解析、SFC 能进 bundle；验完即删）**

```
vite v6.4.5 building for production...
✓ 75 modules transformed.
_smoke/dist/smoke.js   237.84 kB │ gzip: 67.32 kB
✓ built in 1.45s
```

**C. 项目完整构建 `cd frontend; npm run build`**

```
vite v6.4.5 building for production...
✓ 749 modules transformed.
dist/assets/index-CqHnGVXK.js          84.29 kB │ gzip:  28.83 kB
dist/assets/motion-BDWugTm1.js        451.49 kB │ gzip: 126.82 kB
✓ built in 17.51s
exit=0
```

（注：跑 C 时三个组件尚未被任何页面 import，所以 C 只证明"工程整体可构建"；组件本身的编译证据是 A + B。）

**C′. 收尾复跑（同日，`Home`/`Footprint`/`Profile` 等页面已由并行的同伴落盘之后）**

```
> eatwhat-frontend@2.1.1 build
> vite build

vite v6.4.5 building for production...
transforming...
✓ 749 modules transformed.
node_modules/lottie-web/build/player/lottie.js (14422:32): Use of eval in "node_modules/lottie-web/build/player/lottie.js" is strongly discouraged as it poses security risks and may cause issues with minification.
rendering chunks...
computing gzip size...
dist/index.html                         0.72 kB │ gzip:   0.45 kB
dist/assets/Home-DmIM2GnC.css          13.13 kB │ gzip:   2.98 kB
dist/assets/index-B8x3656m.css         44.86 kB │ gzip:   8.35 kB
dist/assets/Home-B7UxEopd.js           35.10 kB │ gzip:  13.96 kB
dist/assets/index-BKvVE6da.js          85.26 kB │ gzip:  29.24 kB
dist/assets/echarts-CGxHXyfs.js       418.74 kB │ gzip: 141.77 kB
dist/assets/motion-BDWugTm1.js        451.49 kB │ gzip: 126.82 kB
✓ built in 5.51s
EXIT=0
```

`lottie-web` 的 eval 警告是上游包自带的，与本次改动无关（改动前就存在）。
