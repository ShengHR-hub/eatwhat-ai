import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchWeather } from '../api'

/** 双模式：外食 / 下厨。v2.3 起不靠颜色区分，靠图标 + 文案 + 分段开关选中态。 */
export const MODES = {
  OUT_DINING: {
    value: 'OUT_DINING',
    label: '外食',
    icon: '🍜',
    hint: '出去吃',
    desc: '附近门店点单',
  },
  HOME_COOKING: {
    value: 'HOME_COOKING',
    label: '下厨',
    icon: '🍳',
    hint: '自己做',
    desc: '家常菜谱',
  },
}

/**
 * 演示天气三档：高德 Key 未配置时，/context/weather 永远 offline，
 * 答辩需要能演示"雨天想喝热汤"这类上下文，故提供预设。
 */
export const WEATHER_PRESETS = [
  { key: 'sunny', label: '晴 26°', temp: 26, weather: '晴' },
  { key: 'rainy', label: '小雨 12°', temp: 12, weather: '小雨' },
  { key: 'hot', label: '高温 34°', temp: 34, weather: '高温' },
]

export const useModeStore = defineStore('mode', () => {
  const modeType = ref('OUT_DINING')
  // v2.3.6：S06 只透传默认校区，全局校区切换 UI 留后续专项验收。
  const campus = ref('SIYUAN')
  const budget = ref(null)
  // 组合方案（算法 4）：后端一直支持 combo_mode，但前端此前写死 false，功能等于没接
  const comboMode = ref(false)
  const bubbles = ref([])
  const weather = ref(null)
  const weatherOverride = ref(null)
  const weatherLoading = ref(false)
  const weatherError = ref('')

  const isOut = computed(() => modeType.value === 'OUT_DINING')
  const modeMeta = computed(() => MODES[modeType.value])
  const weatherTemp = computed(() => weather.value?.temp ?? 22)
  const weatherText = computed(() => weather.value?.weather_text ?? '晴')
  const weatherTip = computed(() => weather.value?.capsule_tip ?? '')
  const weatherSource = computed(() => weather.value?.source ?? 'offline')

  function setMode(value) {
    if (!MODES[value]) return
    modeType.value = value
    bubbles.value = []
  }

  function toggleBubble(id) {
    const index = bubbles.value.indexOf(id)
    if (index >= 0) bubbles.value.splice(index, 1)
    else bubbles.value.push(id)
  }

  /** 预算滑块：拖到最右（120）视为"不限"，回落成 null 交给后端用偏好默认值 */
  function setBudget(raw) {
    const value = Number(raw)
    budget.value = value >= 120 ? null : value
  }

  async function loadWeather(preset = null) {
    weatherLoading.value = true
    weatherError.value = ''
    weatherOverride.value = preset?.key ?? null
    try {
      const query = preset ? { temp: preset.temp, weather: preset.weather } : {}
      weather.value = await fetchWeather(query)
    } catch (err) {
      weatherError.value = err.message
      // 天气不是关键路径：失败就用离线兜底，不让整页挂掉
      weather.value = { temp: 22, weather_text: '晴', capsule_tip: '天气没拿到，按常温推荐', source: 'offline' }
    } finally {
      weatherLoading.value = false
    }
  }

  return {
    modeType,
    campus,
    budget,
    comboMode,
    bubbles,
    weather,
    weatherOverride,
    weatherLoading,
    weatherError,
    isOut,
    modeMeta,
    weatherTemp,
    weatherText,
    weatherTip,
    weatherSource,
    setMode,
    toggleBubble,
    setBudget,
    loadWeather,
  }
})
