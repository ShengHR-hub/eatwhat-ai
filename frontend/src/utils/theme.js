/**
 * JS 侧的色值出口。
 *
 * 硬约束：组件 / 页面 / 图表 / 动效里禁止出现裸 hex。
 * ECharts、canvas-confetti、Lottie 拿不到 Tailwind 类，只能从这里读，
 * 而这里又只读 src/styles/main.css 里定义的 CSS 变量 —— 单一出口不破。
 */
function readVar(name, fallback = '#000000') {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

export function tokens() {
  return {
    ink: readVar('--color-ink', '#17171a'),
    steel: readVar('--color-steel', '#55555e'),
    mist: readVar('--color-mist', '#f4f4f5'),
    white: readVar('--color-white', '#ffffff'),
    silver: readVar('--color-silver', '#d4d4d8'),
    // Vue Bits 背景三色（Grainient）与铬底（LiquidChrome）
    grainA: readVar('--color-grain-a', '#3a3a40'),
    grainB: readVar('--color-grain-b', '#17171a'),
    grainC: readVar('--color-grain-c', '#55555e'),
    chrome: readVar('--color-chrome', '#1a1a1a'),
    chromeMax: readVar('--color-chrome-max', '#222226'),
  }
}

/**
 * 管理后台数据大屏（v8 冷色）的令牌组。
 * 键名与 tokens() 对齐，图表配置因此可以整体复用，只换取值出口。
 */
export function wallTokens() {
  return {
    ink: readVar('--wall-bg', '#0b0e14'),
    steel: readVar('--wall-faint', '#69717f'),
    mist: readVar('--wall-text', '#eef1f6'),
    white: readVar('--color-white', '#ffffff'),
    silver: readVar('--wall-muted', '#9aa3b2'),
    accent: readVar('--wall-accent', '#5b8cff'),
    accentHi: readVar('--wall-accent-hi', '#8fb0ff'),
    accentDim: readVar('--wall-accent-dim', '#2f4f9e'),
    ok: readVar('--wall-ok', '#3ddc97'),
    warn: readVar('--wall-warn', '#f0b429'),
    bad: readVar('--wall-bad', '#ff6b6b'),
  }
}

/** 当前页面是否挂在大屏作用域下（由 ExperimentDashboard 挂载时置位）。 */
export function isWall() {
  if (typeof document === 'undefined') return false
  return document.documentElement.dataset.surface === 'wall'
}

/** 当前页面是否挂在后台浅色作用域下（DataManage 挂载时置位）。 */
export function isAdminLight() {
  if (typeof document === 'undefined') return false
  return document.documentElement.dataset.surface === 'admin'
}

/**
 * 后台浅色页面的图表令牌组。
 * 键名同样与 tokens() 对齐，DataManage 的质量图因此能直接复用 qualityOption。
 */
export function adminTokens() {
  return {
    ink: readVar('--admin-surface', '#ffffff'),
    steel: readVar('--admin-faint', '#8d959f'),
    mist: readVar('--admin-ink', '#171a1f'),
    white: readVar('--admin-ink', '#171a1f'),
    silver: readVar('--admin-muted', '#5b636d'),
    accent: readVar('--admin-accent', '#2f6bff'),
    accentHi: readVar('--admin-accent', '#2f6bff'),
    accentDim: readVar('--admin-muted', '#5b636d'),
    ok: readVar('--admin-ok', '#0f7a5a'),
    warn: readVar('--admin-warn', '#9a6a00'),
    bad: readVar('--admin-bad', '#c0392b'),
  }
}

/**
 * 图表配置的统一取色入口：大屏走冷色组、后台浅色走浅色组，其余走 v2.3 单色组。
 * dashboardOptions 只依赖这个函数，因此同一套 option 生成器能同时服务
 * 移动端小图、DataManage 的质量图与大屏的 17 项图表。
 */
export function chartTokens() {
  if (isWall()) return wallTokens()
  if (isAdminLight()) return adminTokens()
  return tokens()
}

/**
 * 单色雷达图的灰阶梯度：v2.3.2 起雷达一律画在液态玻璃卡（深色玻璃）内，
 * 所以线条用白、网格用低透明白，保持"黑灰银白"不引入彩色。
 */
export function radarPalette() {
  const t = tokens()
  return {
    line: t.white,
    area: t.white,
    areaOpacity: 0.16,
    axis: alpha(t.white, 0.28),
    splitLine: alpha(t.white, 0.2),
    label: alpha(t.white, 0.72),
  }
}

function hexToRgb(hex) {
  const clean = String(hex).replace('#', '')
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean
  const num = parseInt(full, 16)
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255]
}

export function alpha(hex, opacity) {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}

/**
 * Vue Bits 背景组件的 shader 只吃 0–1 的三元数组（LiquidChrome.baseColor），
 * 这里负责把 CSS 变量里的 hex 转成它要的形状，避免组件里写死颜色。
 */
export function rgbTriplet(hex) {
  return hexToRgb(hex).map((v) => v / 255)
}
