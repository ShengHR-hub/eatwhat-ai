/**
 * 情绪气泡目录 —— 与后端 `backend/algorithms/vector_spec.py` 的 STATUS_BUBBLE_RULES 一一对应。
 * 只在前端展示用；真正的权重/硬过滤全部由后端执行，前端不许自行算分。
 *
 * modes 决定该气泡在哪个模式下可选：不匹配的会被后端放进 bubble_effects.ignored。
 */
export const BUBBLES = [
  { id: 'exhausted', label: '刚加完班累瘫', modes: ['OUT_DINING', 'HOME_COOKING'], short: '累瘫' },
  { id: 'broke_end_month', label: '月底吃土', modes: ['OUT_DINING'], short: '月底' },
  { id: 'craving_heavy', label: '嘴馋想吃重口', modes: ['OUT_DINING', 'HOME_COOKING'], short: '重口' },
  { id: 'light_healthy', label: '想吃得清淡', modes: ['OUT_DINING', 'HOME_COOKING'], short: '清淡' },
  { id: 'need_hot_soup', label: '想喝口热汤', modes: ['OUT_DINING', 'HOME_COOKING'], short: '热汤' },
  { id: 'lazy_one_pot', label: '只有电饭煲 / 不想洗碗', modes: ['HOME_COOKING'], short: '一锅出' },
]

export const bubbleById = (id) => BUBBLES.find((b) => b.id === id) ?? null

/** 该气泡在当前模式是否可选 */
export const bubbleEnabled = (bubble, modeType) => bubble.modes.includes(modeType)

/** 雷达图五轴：键必须与后端 radar_5d 完全一致 */
export const RADAR_AXES = [
  { key: 'taste', name: '口味契合' },
  { key: 'weather', name: '天气适配' },
  { key: 'budget', name: '预算友好' },
  { key: 'freshness', name: '新鲜度' },
  { key: 'status', name: '状态匹配' },
]
