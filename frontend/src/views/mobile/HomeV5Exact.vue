<script setup>
/**
 * Home.vue —— 首页：上下文感知 + 双模式智能决策（批次 2 第一屏）
 *
 * 结构（自上而下，全部服从三层架构，且锁一屏不滚动 —— MOBILE_VISUAL_SPEC §4.3）：
 *   状态行 44  ：问候 + 算法沙盒 + 天气胶囊（一律落在玻璃上）
 *   筛选面板 140：分段开关 40 + 气泡一行 30 + 「预算滑块 + 主 CTA」同排 42
 *   卡组     自适应：吃掉剩余高度（844 下约 470，卡面 446 ≈ 53% 屏高）
 *   候选条   30 ：一行横滑，点任意一条置顶该卡
 *   操作行   44 ：换一个 / 就吃这个（与手势等效）
 * 其余全部进抽屉（算法沙盒）或弹层（雷达），首屏不滚动。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAutoAnimate } from '@formkit/auto-animate/vue'

import WeatherPill from '../../components/WeatherPill.vue'
import ModeSwitcher from '../../components/ModeSwitcher.vue'
import StatusBubbles from '../../components/StatusBubbles.vue'
import V5Radar from '../../components/V5Radar.vue'
import { dishTalk } from '../../utils/dishTalk'
import RadarSheet from '../../components/RadarSheet.vue'
import LottieIcon from '../../components/LottieIcon.vue'
import AlgoSandboxDrawer from '../../components/AlgoSandboxDrawer.vue'

import { useModeStore } from '../../stores/mode'
import { useAlgoStore } from '../../stores/algo'
import { usePersonaStore } from '../../stores/persona'
import { WEATHER_PRESETS } from '../../stores/mode'
import { logDecision } from '../../utils/events'
import { checkin, fetchLogStats } from '../../api'

/** 一次要多少候选：比首屏 10 张多留余量，划完一批还能"换一批" */
const BATCH_LIMIT = 24

const mode = useModeStore()
const algo = useAlgoStore()
const persona = usePersonaStore()

const [candidateRef] = useAutoAnimate({ duration: 240, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)' })

const deckRef = ref(null)
const deck = ref([]) // 卡组：deck[0] 是顶卡
const swiped = ref([]) // 本批次已划过的 dish_id
const roundDone = ref(false) // 换一批后仍为空 → 本轮看完
const refilling = ref(false)
const radarDish = ref(null) // 雷达弹层当前菜品
/** 首次进入（含登录后跳进来）：从第一帧就出骨架屏，不能等 algo.loading 翻上来 */
const booting = ref(true)
/** 首批结果用的是哪一档天气；天气晚到时靠它判断要不要按真实天气重算 */
const bootWeatherKey = ref('')
const weatherKey = () => `${mode.weatherTemp}|${mode.weatherText}`

const ignoredBubbles = computed(() => algo.bubbleEffects.ignored ?? [])

const topDish = computed(() => deck.value[0] ?? null)
const talkLines = computed(() => (topDish.value ? dishTalk(topDish.value, { weatherText: mode.weatherText || '' }) : []))

const alternatives = computed(() => deck.value.slice(1, 3))
const settingsOpen = ref(false)
const weatherOpen = ref(false)
const personaOpen = ref(false)
const candidatesOpen = ref(false)
const filters = ref({ distance: '3', cuisine: 'all', sort: 'match' })
const savedBg = ref(null)
try { savedBg.value = JSON.parse(localStorage.getItem('eatwhat.v5.background') || 'null') } catch {}
const bgTextMode = computed(() => {
  if (!savedBg.value || savedBg.value.mode !== 'image') return 'dark'
  if (savedBg.value.textMode && savedBg.value.textMode !== 'auto') return savedBg.value.textMode
  return Number(savedBg.value.luminance ?? 0.5) < 0.48 ? 'light' : 'dark'
})
const phoneStyle = computed(() => {
  const bg = savedBg.value
  if (!bg || bg.mode !== 'image' || !bg.url) return ''
  const light = bgTextMode.value === 'light'
  return [
    `background-image: url("${bg.url}")`,
    'background-size: cover',
    'background-position: center',
    // 两套主题都走令牌：裸色值只允许出现在 styles/main.css
    `--ink: ${light ? 'var(--v5-photo-ink)' : 'var(--v5-ink)'}`,
    `--muted: ${light ? 'var(--v5-photo-muted)' : 'var(--v5-muted)'}`,
    `--faint: ${light ? 'var(--v5-photo-faint)' : 'var(--v5-faint)'}`,
    `--line: ${light ? 'rgb(var(--rgb-v5-mist) / .18)' : 'rgb(var(--rgb-v5-ink) / .12)'}`,
    `--paper: ${light ? 'var(--v5-photo-paper)' : 'var(--v5-paper)'}`,
    `--paper-strong: ${light ? 'var(--v5-photo-paper)' : 'var(--v5-paper-strong)'}`,
  ].join('; ')
})
const overlayStyle = computed(() => {
  const bg = savedBg.value
  if (!bg || bg.mode !== 'image' || !bg.url) return {}
  return {
    background: bgTextMode.value === 'light' ? 'var(--v5-photo-overlay-dark)' : 'var(--v5-photo-overlay-light)',
    opacity: Number(bg.overlay ?? 42) / 100,
  }
})

/**
 * 取一批候选并装进卡组。
 * keepSwiped = true 时按 dish_id 过滤已划过的（"换一批"语义）；
 * false 时清空已划记录（换模式 / 换气泡 / 重置）。
 */
async function loadBatch({ keepSwiped = true } = {}) {
  const seen = keepSwiped ? new Set(swiped.value) : new Set()
  if (!keepSwiped) swiped.value = []
  // 已划过的菜交给后端排除（F13），本地再过滤一次兜底
  await algo.refresh(BATCH_LIMIT, keepSwiped ? [...seen] : [])
  const fresh = (algo.recommendations ?? []).filter((dish) => !seen.has(dish.dish_id))
  deck.value = fresh
  roundDone.value = fresh.length === 0
}

// 审查 F10：沙盒滑块改动由 store 的 reloadTick 广播，这里统一重取卡组，
// 保证「抽屉里的排名」与「首页卡面」是同一次请求的结果。
let reloadTimer = 0
let weatherTimer = 0
watch(
  () => algo.reloadTick,
  () => {
    clearTimeout(reloadTimer)
    reloadTimer = setTimeout(() => {
      // V5 把沙盒滑块搬进了「调整抽屉」(settingsOpen)，但这里仍只判断
      // algo.sandboxOpen —— 拖完滑块它一直是 false，卡组从不重算，
      // 表现为"调参对首页无效"（门禁 sandbox-sync 报"没有发出新请求"）。
      if (algo.sandboxOpen || settingsOpen.value) loadBatch({ keepSwiped: true })
    }, 320)
  },
)

function pickCandidate(dish) {
  promote(dish)
  candidatesOpen.value = false
}

async function pickPersona(user) {
  if (user.id === persona.userId) { personaOpen.value = false; return }
  await persona.switchUser(user.id)
  personaOpen.value = false
  showToast(`已切换：${user.nickname}`, 'ok')
}

async function refresh() {
  await loadBatch({ keepSwiped: false })
}

/** 组合方案只在下厨模式成立（要凑一餐的菜），外食点它没有意义 */
function toggleCombo() {
  if (mode.modeType !== 'HOME_COOKING') {
    showToast('组合方案只在下厨模式可用，先切到下厨', 'warn')
    return
  }
  // 组合优化按「各角色一道 + 总价不超预算」枚举，没有预算就必然凑不出方案
  if (!mode.budget) {
    showToast('组合方案需要先设置预算，否则凑不出套餐', 'warn')
    return
  }
  mode.comboMode = !mode.comboMode
  algo.refresh(BATCH_LIMIT, [])
}

async function refill() {
  if (refilling.value) return
  refilling.value = true
  try {
    await loadBatch({ keepSwiped: true })
  } finally {
    refilling.value = false
  }
}

async function resetRound() {
  roundDone.value = false
  await loadBatch({ keepSwiped: false })
}

/** 左划 / 换一个：记 PASS 并出牌 */
function onPass(dish) {
  logDecision({ type: 'PASS', dish, modeType: mode.modeType, source: 'swipe-left' })
  swiped.value = [...swiped.value, dish.dish_id]
  deck.value = deck.value.slice(1)
}

/**
 * 右划确认后：先出牌（保证手感），再真落库到 eating_logs。
 * 落库失败不回滚卡组，但必须如实告诉用户"没记上"，不许假装成功。
 */
function onConfirm(dish) {
  logDecision({ type: 'LIKE', dish, modeType: mode.modeType, source: 'swipe-right' })
  swiped.value = [...swiped.value, dish.dish_id]
  deck.value = deck.value.slice(1)
  void writeCheckin(dish)
}

const checkedDishIds = ref([])
const toast = ref(null)
let toastTimer = 0

function showToast(text, tone = 'ok') {
  window.clearTimeout(toastTimer)
  toast.value = { text, tone }
  toastTimer = window.setTimeout(() => {
    toast.value = null
  }, 3200)
}

/* ── 打卡结果页：选完不是「一闪而过的提示」，要给出这顿的上下文 ── */
const result = ref(null)          // { dish, logId, rated }
const resultStats = ref(null)     // { meals_this_week, weekly_expense }

const budgetLeft = computed(() => {
  if (mode.budget == null || !resultStats.value) return null
  return Math.max(0, Number(mode.budget) - Number(resultStats.value.weekly_expense || 0))
})

/** 高德搜店：外食菜有准确店名，下厨菜没有门店所以不显示 */
const amapUrl = computed(() => {
  const name = result.value?.dish?.restaurant_name || ''
  if (!name) return ''
  return `https://uri.amap.com/search?keyword=${encodeURIComponent(name)}&city=${encodeURIComponent('西安')}`
})

const meituanUrl = computed(() => {
  const name = result.value?.dish?.name || ''
  if (!name) return ''
  return `https://i.meituan.com/s/${encodeURIComponent(name)}`
})

async function openResult(dish, logId) {
  result.value = { dish, logId, rated: 0 }
  try {
    resultStats.value = await fetchLogStats(persona.userId)
  } catch {
    resultStats.value = null
  }
}

async function writeCheckin(dish) {
  if (checkedDishIds.value.includes(dish.dish_id)) {
    showToast('这道菜本轮已经记过一次了')
    return
  }
  try {
    const res = await checkin({
      dish_id: dish.dish_id,
      mode_type: mode.modeType,
      bubbles: [...mode.bubbles],
      cost_amount: Number(dish.price) || 0,
      weather_snapshot: `${mode.weatherTemp}°C ${mode.weatherText}`,
    })
    checkedDishIds.value = [...checkedDishIds.value, dish.dish_id]
    await openResult(dish, res.log_id)
  } catch (err) {
    showToast(`没记进足迹：${err.message}`, 'warn')
  }
}

function onTap(dish) {
  radarDish.value = dish
}

/** 点"全部候选"里的任意一条 → 置顶该卡 */
function promote(dish) {
  if (deck.value[0]?.dish_id === dish.dish_id) {
    radarDish.value = dish
    return
  }
  deck.value = [dish, ...deck.value.filter((d) => d.dish_id !== dish.dish_id)]
}

function swipeLeft() {
  if (topDish.value) onPass(topDish.value)
}

function swipeRight() {
  if (topDish.value) onConfirm(topDish.value)
}

/** 换模式 / 换气泡 / 换演示天气 → 清空已划记录并重算（上下文感知的主链路） */
watch(
  () => [mode.modeType, mode.bubbles.slice().sort().join(','), mode.weatherOverride],
  () => {
    radarDish.value = null
    loadBatch({ keepSwiped: false })
  },
)

// 天气变化（自动刷新或预设切换）后，推荐结果跟着重算。
// 首次启动阶段由 onMounted 统一收口（先出结果、天气到位再补算），这里跳过避免重复请求。
watch(
  () => [mode.weatherTemp, mode.weatherText],
  ([nextTemp, nextText], [prevTemp, prevText]) => {
    if (booting.value) return
    if (nextTemp === prevTemp && nextText === prevText) return
    radarDish.value = null
    loadBatch({ keepSwiped: false })
  },
)

/** S01：角色切换后不沿用上一个角色的卡组/已划记录，立即按新身份重取 */
watch(
  () => persona.userId,
  () => {
    radarDish.value = null
    checkedDishIds.value = []
    swiped.value = []
    deck.value = []
    roundDone.value = false
    loadBatch({ keepSwiped: false })
  },
)

onMounted(async () => {
  weatherTimer = window.setInterval(() => mode.loadWeather(), 10 * 60 * 1000)
  if (!persona.profile) persona.loadProfile()
  if (!persona.demoUsers?.length) persona.loadDemoUsers()

  // 天气和推荐并行：天气走公网（首次 1~2 秒），不能让它挡住首屏出菜。
  // 先用当前天气（离线兜底值）出一批结果，天气到位后若真的变了再静默补算一次。
  const weatherTask = mode.loadWeather()
  try {
    await loadBatch({ keepSwiped: false })
    bootWeatherKey.value = weatherKey()
    // 等天气落地再放开 watch，避免天气晚到触发第二次请求（结果一样，白算一遍）
    await weatherTask
    if (weatherKey() !== bootWeatherKey.value) {
      await loadBatch({ keepSwiped: false })
    }
  } finally {
    booting.value = false
  }
})

/* F10/N01：沙盒改参有 320ms 防抖，toast 也有 3.2s 计时器。
 * 路由离开后这些计时器必须停，否则会在别的页面上补发推荐请求；
 * 沙盒开关存在 Pinia 里，不手动关掉的话下次回到首页会凭空弹出抽屉。 */
onBeforeUnmount(() => {
  window.clearTimeout(reloadTimer)
  window.clearTimeout(toastTimer)
  window.clearInterval(weatherTimer)
  algo.toggleSandbox(false)
})
</script>

<template>
  <div class="v5-home">
    <section class="phone" :style="phoneStyle">
      <div class="phone-bg-overlay" :style="overlayStyle"></div>
      <div class="ambient" aria-hidden="true"><img class="ambient__wash" src="/design/v5/assets/watercolor-ink.png" alt="" /></div>

      <div class="statusbar"><span>9:41</span><span class="statusbar__icons"><span class="statusbar__dot"></span><span class="statusbar__dot"></span><span class="statusbar__battery"><i></i></span></span></div>

      <header class="topbar">
        <button class="persona" type="button" aria-label="切换演示角色" @click="personaOpen = true">
          <span class="persona__avatar">{{ (persona.nickname || '食').slice(0, 1) }}</span>
          <span class="persona__copy"><span class="persona__name">{{ persona.nickname }}</span><span class="persona__context">{{ mode.modeType === 'HOME_COOKING' ? '下厨' : '外食' }} · {{ mode.weatherTemp }}° {{ mode.weatherText }}</span></span>
        </button>
        <div class="top-actions">
          <button class="weather-chip" type="button" title="查看实时天气" :aria-expanded="weatherOpen" @click="weatherOpen = !weatherOpen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 15a5 5 0 1 1 10 0"/><path d="M12 4v2M5 7l1.4 1.4M19 7l-1.4 1.4M4 15h16M8 18l-1 2M12 18v2M16 18l1 2"/></svg>
            <span>{{ Math.round(mode.weatherTemp) }}° {{ mode.weatherText }}</span><i aria-hidden="true"></i>
          </button>
          <button class="icon-btn" type="button" aria-label="打开调整抽屉" :aria-expanded="settingsOpen" @click="settingsOpen = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10" stroke-linecap="round"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>
          </button>
        </div>
      </header>

      <div v-if="weatherOpen" class="weather-pop">
        <div class="weather-pop__head"><span>实时天气</span><span>刚刚更新</span></div>
        <div class="weather-pop__main"><b>{{ Math.round(mode.weatherTemp) }}°</b><span>{{ mode.weatherText }}</span></div>
        <div class="weather-pop__grid"><span>体感 {{ Math.round(mode.weatherTemp - 2) }}°</span><span>湿度 —</span><span>风力 —</span></div>
        <p class="weather-pop__tip">{{ mode.weatherTip || '天气数据来自当前定位，失败时按常温推荐。' }}</p>
        <div class="weather-presets"><button v-for="preset in WEATHER_PRESETS" :key="preset.key" type="button" :class="{ 'is-active': mode.weatherOverride === preset.key }" @click="mode.loadWeather(preset)">{{ preset.label }}</button></div>
      </div>

      <div class="content">
        <div class="context-line">
          <div class="context-line__left"><span>{{ mode.modeType === 'HOME_COOKING' ? '下厨' : '外食' }}</span><span class="context-line__dot"></span><span>预算 {{ mode.budget ? `¥${mode.budget}` : '不限' }}</span><span class="context-line__dot"></span><span>{{ mode.bubbles.length ? mode.bubbles.join(' · ') : '未选择状态' }}</span></div>
          <span>{{ mode.campus === 'JIANDA_YANTA' ? '建大' : '思源' }}</span>
        </div>

        <template v-if="topDish">
          <div class="radar-head"><span class="radar-head__label">八维风味</span><span class="radar-head__score"><b class="tabular">{{ Number(topDish.total_score).toFixed(1) }}</b><span>匹配</span></span></div>
          <div class="radar-wrap" aria-hidden="true"><V5Radar :vector="topDish.feature_vector" /></div>

          <div class="dish">
            <h2 class="dish__title">{{ topDish.name }}</h2>
            <p class="dish__meta"><span v-if="topDish.restaurant_name">{{ topDish.restaurant_name }} · </span>¥{{ Number(topDish.price).toFixed(0) }}<span v-if="topDish.cuisine_type"> · {{ topDish.cuisine_type }}</span></p>
            <div class="dish__talk">
              <p v-for="(line, index) in talkLines" :key="index">{{ line }}</p>
            </div>
            <div class="dish__evidence"><span>防腻 <b>{{ topDish.decay_weight?.toFixed(2) ?? '—' }}</b></span><span>角色 <b>{{ topDish.dish_role }}</b></span><span v-if="topDish.is_favorite">红榜</span><button type="button" @click="settingsOpen = true">推荐依据</button><button type="button" class="all-candidates" @click="candidatesOpen = true">全部候选</button></div>
            <div v-if="algo.combo" class="combo">
              <div class="combo__head">
                <span>一餐搭配</span>
                <span class="combo__total">¥{{ Number(algo.combo.total_price).toFixed(0) }}</span>
              </div>
              <ul class="combo__list">
                <li v-for="dish in algo.combo.dishes" :key="dish.dish_id">
                  <span class="combo__role">{{ { MEAT: '荤', VEG: '素', SOUP: '汤' }[dish.dish_role] || dish.dish_role }}</span>
                  <span class="combo__name">{{ dish.name }}</span>
                  <span class="combo__price">¥{{ Number(dish.price).toFixed(0) }}</span>
                </li>
              </ul>
              <p class="combo__note">平均油腻 {{ (Number(algo.combo.avg_oily_level) * 100).toFixed(0) }}% · 各角色一道，总价不超预算</p>
            </div>

            <div v-if="alternatives.length" class="alternatives">
              <div class="alternatives__head"><span>也可以考虑</span><span>点一下切换</span></div>
              <div class="alternatives__list"><button v-for="dish in alternatives" :key="dish.dish_id" :data-dish-id="dish.dish_id" class="alternative" type="button" @click="promote(dish)"><span class="alternative__name">{{ dish.name }}</span><span class="alternative__meta">¥{{ Number(dish.price).toFixed(0) }}</span><span class="alternative__score">{{ Number(dish.total_score).toFixed(1) }}</span></button></div>
            </div>
          </div>

          <div class="actions">
            <button class="primary" type="button" :disabled="refilling" @click="swipeRight"><span>就吃这个</span><span aria-hidden="true">→</span></button>
            <div class="secondary-row"><button class="text-btn" type="button" :disabled="refilling" @click="swipeLeft">换一个</button><button v-if="mode.modeType === 'HOME_COOKING'" class="text-btn" type="button" :class="{ 'is-on': mode.comboMode }" @click="toggleCombo">{{ mode.comboMode ? '组合方案 · 开' : '组合方案' }}</button></div>
          </div>
        </template>

        <section v-else-if="algo.error" class="notice glass-card--matte"><p class="error-title">没算出来</p><p class="error-msg">{{ algo.error }}</p><button type="button" class="act act--ink" @click="refresh">重试</button></section>
        <div v-else-if="booting || algo.loading" class="home-skeleton" aria-busy="true" aria-label="正在计算推荐">
          <div class="home-skeleton__head"><span class="sk-line sk-line--w34"></span><span class="sk-line sk-line--w16"></span></div>
          <div class="sk-radar"><i></i></div>
          <div class="home-skeleton__body">
            <span class="sk-line sk-line--title"></span>
            <span class="sk-line sk-line--w46"></span>
            <span class="sk-line sk-line--w94 sk-line--gap"></span>
            <span class="sk-line sk-line--w82"></span>
          </div>
          <div class="sk-actions"><i class="sk-btn"></i><div class="sk-ghost-row"><i class="sk-ghost"></i><i class="sk-ghost"></i></div></div>
          <p class="sk-hint">正在按你的口味和天气算这一顿…</p>
        </div>
        <section v-else class="notice glass-card--matte"><LottieIcon name="empty-state" :size="72" :loop="true" /><p class="error-title">{{ roundDone ? '本轮推荐已看完' : '这一批划完了' }}</p><button type="button" class="act act--ink" @click="roundDone ? resetRound() : refill()">{{ roundDone ? '重置再看一轮' : '换一批' }}</button></section>
      </div>

      <div v-if="candidatesOpen" class="overlay is-open" @click="candidatesOpen = false"></div>
      <aside v-if="candidatesOpen" class="sheet candidates-sheet is-open" aria-label="全部候选">
        <div class="sheet__handle"></div>
        <header class="sheet__head"><div><p class="sheet__eyebrow">ALL CANDIDATES</p><h2 class="sheet__title">全部候选</h2></div><button class="sheet__close" type="button" @click="candidatesOpen = false">×</button></header>
        <div class="sheet__body">
          <button v-for="(dish, index) in deck" :key="dish.dish_id" type="button" class="candidate-row" :class="{ 'is-top': index === 0 }" @click="pickCandidate(dish)">
            <span class="candidate-row__rank">{{ index + 1 }}</span>
            <span class="candidate-row__copy"><b>{{ dish.name }}</b><small>{{ dish.restaurant_name || '家常菜' }} · ¥{{ Number(dish.price).toFixed(0) }}</small></span>
            <span class="candidate-row__score">{{ Number(dish.total_score).toFixed(1) }}</span>
          </button>
        </div>
      </aside>

      <div v-if="personaOpen" class="overlay is-open" @click="personaOpen = false"></div>
      <aside v-if="personaOpen" class="sheet persona-sheet is-open" aria-label="切换演示角色">
        <div class="sheet__handle"></div>
        <header class="sheet__head"><div><p class="sheet__eyebrow">DEMO PERSONA</p><h2 class="sheet__title">切换演示角色</h2></div><button class="sheet__close" type="button" @click="personaOpen = false">×</button></header>
        <div class="sheet__body">
          <button v-for="user in persona.demoUsers" :key="user.id" type="button" class="persona-option" :class="{ 'is-active': user.id === persona.userId }" @click="pickPersona(user)">
            <span class="persona-option__avatar">{{ user.avatar }}</span>
            <span class="persona-option__copy"><b>{{ user.nickname }}</b><small>{{ user.persona_title }}</small></span>
            <span class="persona-option__mark">{{ user.id === persona.userId ? '当前' : '切换' }}</span>
          </button>
        </div>
      </aside>

      <div class="overlay" :class="{ 'is-open': settingsOpen }" @click="settingsOpen = false"></div>
      <aside class="sheet" :class="{ 'is-open': settingsOpen }" aria-label="调整这顿">
        <div class="sheet__handle"></div>
        <header class="sheet__head"><div><p class="sheet__eyebrow">ADJUST</p><h2 class="sheet__title">调整这顿</h2></div><button class="sheet__close" type="button" aria-label="关闭" @click="settingsOpen = false">×</button></header>
        <div class="sheet__body">
          <section class="section"><div class="section__head"><h3 class="section__title">模式</h3><span class="section__hint">主屏只保留结果</span></div><div class="segmented segmented--two"><button type="button" :class="{ 'is-active': mode.modeType === 'OUT_DINING' }" @click="mode.setMode('OUT_DINING')">外食</button><button type="button" :class="{ 'is-active': mode.modeType === 'HOME_COOKING' }" @click="mode.setMode('HOME_COOKING')">下厨</button></div></section>
          <section class="section"><div class="section__head"><h3 class="section__title">预算</h3><span class="section__hint">{{ mode.budget ? `¥${mode.budget}` : '不限' }}</span></div><div class="slider-row"><input type="range" min="10" max="120" step="5" :value="mode.budget ?? 120" @input="mode.setBudget($event.target.value)" /><span class="slider-value">{{ mode.budget ? `¥${mode.budget}` : '不限' }}</span></div></section>
          <section class="section"><div class="section__head"><h3 class="section__title">现在状态</h3><span class="section__hint">可多选</span></div><StatusBubbles /></section>
          <section class="section"><div class="section__head"><h3 class="section__title">筛选</h3><span class="section__hint">不占主屏</span></div><div class="select-grid"><select class="select-field" :value="mode.campus" @change="mode.campus = $event.target.value; refresh()"><option value="SIYUAN">思源</option><option value="JIANDA_YANTA">建大雁塔</option></select><select v-model="filters.distance" class="select-field"><option value="3">3 公里内</option><option value="1">1 公里内</option><option value="all">不限距离</option></select><select v-model="filters.cuisine" class="select-field"><option value="all">全部菜系</option><option value="川湘菜">川湘菜</option><option value="粤菜">粤菜</option><option value="轻食">轻食</option></select><select v-model="filters.sort" class="select-field"><option value="match">综合匹配</option><option value="distance">距离优先</option><option value="price">价格优先</option></select></div></section>
          <section class="section"><div class="section__head"><h3 class="section__title">算法沙盒</h3><span class="section__hint">现场调参</span></div><div class="slider-row"><span style="width:38px;font-size:10px;color:var(--muted);">λ 防腻</span><input type="range" min="0.1" max="2" step="0.1" :value="algo.overrides.lambda_decay" @input="algo.setParam('lambda_decay', $event.target.value)" /><span class="slider-value">{{ Number(algo.overrides.lambda_decay).toFixed(2) }}</span></div><div class="slider-row" style="margin-top:10px;"><span style="width:38px;font-size:10px;color:var(--muted);">ω 群组</span><input type="range" min="0" max="1" step="0.05" :value="algo.overrides.omega_group" @input="algo.setParam('omega_group', $event.target.value)" /><span class="slider-value">{{ Number(algo.overrides.omega_group).toFixed(2) }}</span></div></section>
        </div>
        <footer class="sheet__footer"><button class="apply" type="button" @click="settingsOpen = false">应用并关闭</button></footer>
      </aside>

      <Transition name="toast-fade"><p v-if="toast" class="toast glass-card--matte" :class="`toast--${toast.tone}`" role="status" aria-live="polite">{{ toast.text }}</p></Transition>
      <RadarSheet :open="Boolean(radarDish)" :dish="radarDish" @close="radarDish = null" />
      <AlgoSandboxDrawer />

      <!-- 打卡结果：给出这顿的上下文，而不是一闪而过的提示 -->
      <div v-if="result" class="rsheet" @click.self="result = null">
        <div class="rsheet__panel">
          <p class="rsheet__ok">✓ 已记入足迹</p>
          <h3 class="rsheet__dish">{{ result.dish.name }}</h3>
          <p class="rsheet__meta">
            <template v-if="result.dish.restaurant_name">{{ result.dish.restaurant_name }} · </template>¥{{ Number(result.dish.price).toFixed(0) }}
          </p>

          <div class="rsheet__stats">
            <div><b>{{ resultStats?.meals_this_week ?? '—' }}</b><span>本周第几顿</span></div>
            <div><b>¥{{ Number(resultStats?.weekly_expense || 0).toFixed(0) }}</b><span>本周已花</span></div>
            <div><b>{{ budgetLeft == null ? '—' : `¥${budgetLeft.toFixed(0)}` }}</b><span>预算剩余</span></div>
          </div>

          <div v-if="amapUrl || meituanUrl" class="rsheet__where">
            <a v-if="amapUrl" :href="amapUrl" target="_blank" rel="noopener">去这家店</a>
            <a v-if="meituanUrl" :href="meituanUrl" target="_blank" rel="noopener">点外卖</a>
          </div>

          <p class="rsheet__hint">吃完可以在「足迹」里给这一顿打个评价</p>
          <button class="rsheet__close" type="button" @click="result = null">继续逛</button>
        </div>
      </div>
    </section>
  </div>
</template>
<style scoped src="../../styles/v5-home-exact.css"></style>
<style scoped>
.weather-presets { display: flex; gap: 5px; margin-top: 9px; }
.weather-presets button { flex: 1; height: 28px; border-radius: 8px; border: 1px solid rgb(var(--rgb-v5-ink) / .14); font-size: 8.5px; color: var(--v5-muted); }
.weather-presets button.is-active { background: var(--v5-ink); color: var(--v5-paper-strong); border-color: var(--v5-ink); }
.persona-option { width: 100%; display: grid; grid-template-columns: 34px 1fr auto; gap: 9px; align-items: center; padding: 9px 0; border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .1); text-align: left; }
.persona-option:last-child { border-bottom: 0; }
.persona-option__avatar { width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 13px; }
.persona-option__copy { display: flex; flex-direction: column; gap: 2px; }
.persona-option__copy b { font-size: 11px; font-weight: 600; color: var(--v5-ink); }
.persona-option__copy small { font-size: 8.5px; color: var(--v5-faint); }
.persona-option__mark { font-size: 8.5px; color: var(--v5-faint); }
.persona-option.is-active .persona-option__mark { color: var(--v5-accent); }


.all-candidates { margin-left: 8px !important; }
.candidate-row { width: 100%; display: grid; grid-template-columns: 22px 1fr 34px; gap: 8px; align-items: center; padding: 9px 0; border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .1); text-align: left; }
.candidate-row:last-child { border-bottom: 0; }
.candidate-row__rank { font-size: 8.5px; color: var(--faint); }
.candidate-row__copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.candidate-row__copy b { font-size: 10.5px; font-weight: 600; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.candidate-row__copy small { font-size: 8.5px; color: var(--muted); }
.candidate-row__score { text-align: right; font-size: 9px; color: var(--muted); }
.candidate-row.is-top .candidate-row__copy b { color: var(--v5-accent); }

/* 首屏骨架：位置与真实版面一致（雷达 → 菜名 → 理由 → 按钮），
 * 颜色一律走 --ink / --line，换背景图后跟着变，不写死暖色。 */
.home-skeleton { flex: 1; min-height: 0; display: flex; flex-direction: column; padding-top: 10px; }
.home-skeleton__head { display: flex; justify-content: space-between; align-items: center; padding: 0 2px; }
.home-skeleton__body { padding: 0 2px; display: flex; flex-direction: column; }
.sk-line { display: block; height: 10px; border-radius: 5px; color: var(--ink); background: currentColor; opacity: .08; animation: sk-breathe 1.6s ease-in-out infinite; }
.home-skeleton__body .sk-line + .sk-line { margin-top: 8px; }
.home-skeleton__body .sk-line--gap { margin-top: 18px; }
.sk-line--w16 { width: 16%; }
.sk-line--w34 { width: 34%; }
.sk-line--w46 { width: 46%; }
.sk-line--w82 { width: 82%; }
.sk-line--w94 { width: 94%; }
.sk-line--title { width: 62%; height: 22px; border-radius: 7px; margin-bottom: 10px; }
.sk-radar { position: relative; height: 266px; display: grid; place-items: center; margin: 6px -4px 4px; }
.sk-radar::before, .sk-radar::after { content: ""; position: absolute; border-radius: 50%; border: 1px solid var(--line); }
.sk-radar::before { width: 244px; height: 244px; }
.sk-radar::after { width: 162px; height: 162px; }
.sk-radar i { width: 244px; height: 244px; border-radius: 50%; background: var(--ink); opacity: .05; animation: sk-breathe 1.6s ease-in-out infinite; }
.sk-actions { margin-top: auto; padding-top: 12px; }
.sk-btn { display: block; height: 50px; border-radius: 16px; background: var(--ink); opacity: .09; animation: sk-breathe 1.6s ease-in-out infinite; }
.sk-ghost-row { display: flex; justify-content: space-between; padding: 13px 3px 2px; }
.sk-ghost { width: 56px; height: 12px; border-radius: 6px; background: var(--ink); opacity: .06; animation: sk-breathe 1.6s ease-in-out infinite .25s; }
.sk-hint { margin: 10px 0 0; text-align: center; font-size: 10px; letter-spacing: .02em; color: var(--muted); }
@keyframes sk-breathe { 0%, 100% { opacity: .06; } 50% { opacity: .16; } }
@media (prefers-reduced-motion: reduce) {
  .sk-line, .sk-radar i, .sk-btn, .sk-ghost { animation: none; opacity: .1; }
}
</style>
