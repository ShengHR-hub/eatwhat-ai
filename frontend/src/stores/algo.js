import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchSingleRecommend } from '../api'
import { useModeStore } from './mode'
import { usePersonaStore } from './persona'

/**
 * 算法沙盒 + 单菜推荐结果。
 *
 * 后端 PARAM_KEYS 六个（lambda_decay / omega_group / alpha_taste / beta_weather /
 * gamma_budget / delta_status），沙盒按 v2.3.1 第六章 §4 只暴露 4 个滑块：
 * λ 防腻衰减、ω 群组折中、β 天气权重、γ 预算权重。
 * 拖动滑块 = 写 override_params → 实时重算（后端再把四权重归一化到和 1）。
 */
export const BATCH_SIZE = 24

export const SANDBOX_PARAMS = [
  { key: 'lambda_decay', label: '防腻衰减 λ', min: 0.1, max: 2.0, step: 0.1, hint: '越大越不容易重复吃同一道' },
  { key: 'omega_group', label: '群组折中 ω', min: 0, max: 1, step: 0.05, hint: '多人房里对妥协者的照顾力度' },
  { key: 'beta_weather', label: '天气权重 β', min: 0, max: 1, step: 0.05, hint: '天冷天热对推荐的影响' },
  { key: 'gamma_budget', label: '预算权重 γ', min: 0, max: 0.9, step: 0.05, hint: '月底吃土时更看重价格' },
]

export const useAlgoStore = defineStore('algo', () => {
  const overrides = ref({
    lambda_decay: 0.5,
    omega_group: 0.5,
    beta_weather: 0.25,
    gamma_budget: 0.2,
  })
  const dirty = ref(false)
  const sandboxOpen = ref(false)
  // 审查 F10：沙盒滑块与首页卡组必须同源。任何参数变化只在这里加一，
  // 由持有卡组的页面（Home）统一重取，避免抽屉自己 refresh(10) 把卡组打成 10 张。
  const reloadTick = ref(0)

  const result = ref(null)
  const loading = ref(false)
  const error = ref('')
  const stamp = ref(0)

  const recommendations = computed(() => result.value?.recommendations ?? [])
  const top = computed(() => recommendations.value[0] ?? null)
  const others = computed(() => recommendations.value.slice(1))
  const paramsUsed = computed(() => result.value?.params_used ?? {})
  const bubbleEffects = computed(() => result.value?.bubble_effects ?? { applied: [], ignored: [] })
  const combo = computed(() => result.value?.combo ?? null)

  function setParam(key, value) {
    overrides.value = { ...overrides.value, [key]: Number(value) }
    dirty.value = true
    reloadTick.value += 1
  }

  function resetParams() {
    overrides.value = { lambda_decay: 0.5, omega_group: 0.5, beta_weather: 0.25, gamma_budget: 0.2 }
    dirty.value = false
    reloadTick.value += 1
  }

  function toggleSandbox(force) {
    sandboxOpen.value = force === undefined ? !sandboxOpen.value : Boolean(force)
  }

  // 请求序号：切模式 / 切气泡 / 拖沙盒 / 天气变化会并行发出多条推荐请求，
  // 旧批次后到会把新结果覆盖回去（persona.js 有 profileToken，这里之前没有）。
  // 只接受最后一次发出的请求结果。
  let requestSeq = 0

  async function refresh(limit = BATCH_SIZE, exclude = []) {
    const mode = useModeStore()
    const persona = usePersonaStore()
    const token = ++requestSeq
    loading.value = true
    error.value = ''
    try {
      const payload = {
        mode_type: mode.modeType,
        // v2.3.4 §5.5.3：外食必须带校区；下厨共享，后端会忽略
        campus: mode.campus,
        bubbles: [...mode.bubbles],
        weather_temp: mode.weatherTemp,
        weather_text: mode.weatherText,
        limit: Math.max(1, Number(limit) || 10),
        combo_mode: Boolean(mode.comboMode) && mode.modeType === 'HOME_COOKING',
      }
      if (mode.budget != null) payload.budget = Number(mode.budget)
      // 审查 F13：把已经划过的菜交给后端排掉，换一批才是真的新候选
      if (exclude.length) payload.exclude_dish_ids = [...exclude]
      if (dirty.value) payload.override_params = { ...overrides.value }

      const data = await fetchSingleRecommend(payload)
      if (token !== requestSeq) return // 已被更新的请求取代，丢弃这次结果
      result.value = data
      stamp.value += 1
      // 后端会把四权重归一化后回传，沙盒初始值以第一次真实回传为准
      if (!dirty.value && result.value?.params_used) {
        const used = result.value.params_used
        overrides.value = {
          lambda_decay: used.lambda_decay ?? overrides.value.lambda_decay,
          omega_group: used.omega_group ?? overrides.value.omega_group,
          beta_weather: used.beta_weather ?? overrides.value.beta_weather,
          gamma_budget: used.gamma_budget ?? overrides.value.gamma_budget,
        }
      }
      if (!persona.profile) persona.loadProfile()
    } catch (err) {
      if (token !== requestSeq) return
      error.value = err.message
      result.value = null
    } finally {
      // 只有最新那次请求才有权关掉 loading，否则先完成的旧请求会提前收掉转圈
      if (token === requestSeq) loading.value = false
    }
  }

  return {
    reloadTick,
    overrides,
    dirty,
    sandboxOpen,
    result,
    loading,
    error,
    stamp,
    recommendations,
    top,
    others,
    paramsUsed,
    bubbleEffects,
    combo,
    setParam,
    resetParams,
    toggleSandbox,
    refresh,
  }
})
