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
import DishRadar from '../../components/DishRadar.vue'
import RadarSheet from '../../components/RadarSheet.vue'
import LottieIcon from '../../components/LottieIcon.vue'
import AlgoSandboxDrawer from '../../components/AlgoSandboxDrawer.vue'

import { useModeStore } from '../../stores/mode'
import { useAlgoStore } from '../../stores/algo'
import { usePersonaStore } from '../../stores/persona'
import { logDecision } from '../../utils/events'
import { checkin } from '../../api'
import paperGrain from '../../assets/v5/paper-grain.png'
import watercolor from '../../assets/v5/watercolor-ink.png'

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

const ignoredBubbles = computed(() => algo.bubbleEffects.ignored ?? [])

const topDish = computed(() => deck.value[0] ?? null)
const alternatives = computed(() => deck.value.slice(1, 3))
const settingsOpen = ref(false)

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
watch(
  () => algo.reloadTick,
  () => {
    clearTimeout(reloadTimer)
    reloadTimer = setTimeout(() => {
      if (algo.sandboxOpen) loadBatch({ keepSwiped: true })
    }, 320)
  },
)

async function refresh() {
  await loadBatch({ keepSwiped: false })
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
    showToast(`已记入足迹 · 防腻权重降到 ${Number(res.new_decay_weight).toFixed(2)}`)
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
  await mode.loadWeather()
  if (!persona.profile) persona.loadProfile()
  await loadBatch({ keepSwiped: false })
})

/* F10/N01：沙盒改参有 320ms 防抖，toast 也有 3.2s 计时器。
 * 路由离开后这些计时器必须停，否则会在别的页面上补发推荐请求；
 * 沙盒开关存在 Pinia 里，不手动关掉的话下次回到首页会凭空弹出抽屉。 */
onBeforeUnmount(() => {
  window.clearTimeout(reloadTimer)
  window.clearTimeout(toastTimer)
  algo.toggleSandbox(false)
})
</script>

<template>
  <div class="home home--v5" :style="{ '--v5-grain': `url(${paperGrain})` }">
    <div class="v5-ambient" aria-hidden="true"><img :src="watercolor" alt="" /></div>
    <header class="v5-head">
      <div class="v5-head__persona">
        <span class="v5-avatar">{{ (persona.nickname || '食').slice(0, 1) }}</span>
        <div class="v5-head__copy">
        <p class="v5-head__greet">{{ persona.nickname }}</p>
        <p class="v5-head__meta">{{ mode.modeType === 'HOME_COOKING' ? '下厨' : '外食' }} · {{ mode.weatherTemp }}° {{ mode.weatherText }}</p>
        </div>
      </div>
      <div class="v5-head__actions">
        <WeatherPill />
        <button type="button" class="v5-icon" aria-label="打开算法沙盒" title="算法沙盒" @click="settingsOpen = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
            <path d="M4 7h10M18 7h2M4 17h2M10 17h10" stroke-linecap="round" />
            <circle cx="16" cy="7" r="2" />
            <circle cx="8" cy="17" r="2" />
          </svg>
        </button>
      </div>
    </header>

    <div class="v5-context">
      <span>{{ mode.modeType === 'HOME_COOKING' ? '下厨' : '外食' }}</span>
      <i></i>
      <span>预算 {{ mode.budget ? `¥${mode.budget}` : '不限' }}</span>
      <i></i>
      <span>{{ mode.bubbles.length ? mode.bubbles.join(' · ') : '未选择状态' }}</span>
    </div>



    <section v-if="algo.error" class="v5-state glass-card--matte">
      <p class="v5-state__title">没算出来</p>
      <p class="v5-state__body">{{ algo.error }}</p>
      <button type="button" class="v5-state__btn" @click="refresh">重试</button>
    </section>

    <section v-else-if="algo.loading && !topDish" class="v5-state glass-card--matte">
      <div class="v5-skeleton" />
      <div class="v5-skeleton v5-skeleton--short" />
    </section>

    <section v-else-if="topDish" class="v5-decision">
      <div class="v5-decision__head">
        <b class="tabular">{{ Number(topDish.total_score).toFixed(1) }}<small>匹配</small></b>
      </div>
      <div class="v5-radar"><DishRadar :vector="topDish.feature_vector" /></div>
      <h1 class="v5-dish">{{ topDish.name }}</h1>
      <p class="v5-meta">
        <span v-if="topDish.restaurant_name">{{ topDish.restaurant_name }} · </span>
        <span>¥{{ Number(topDish.price).toFixed(0) }}</span>
        <span v-if="topDish.cuisine_type"> · {{ topDish.cuisine_type }}</span>
      </p>
      <p class="v5-reason">{{ topDish.explain_reason }}</p>
      <div class="v5-evidence">
        <span>防腻 <b>{{ topDish.decay_weight?.toFixed(2) ?? '—' }}</b></span>
        <span>角色 <b>{{ topDish.dish_role }}</b></span>
        <span v-if="topDish.is_favorite">红榜</span>
        <button type="button" @click="onTap(topDish)">推荐依据</button>
      </div>
      <div v-if="alternatives.length" class="v5-alts">
        <div class="v5-alts__head"><span>也可以考虑</span><span>点一下切换</span></div>
        <button v-for="dish in alternatives" :key="dish.dish_id" type="button" class="v5-alt" @click="promote(dish)">
          <span>{{ dish.name }}</span>
          <small>¥{{ Number(dish.price).toFixed(0) }} · {{ Number(dish.total_score).toFixed(1) }}</small>
        </button>
      </div>
    </section>

    <section v-else class="v5-state glass-card--matte">
      <LottieIcon name="empty-state" :size="72" :loop="true" />
      <p class="v5-state__title">{{ roundDone ? '本轮推荐已看完' : '这一批划完了' }}</p>
      <button type="button" class="v5-state__btn" @click="roundDone ? resetRound() : refill()">{{ roundDone ? '重置再看一轮' : '换一批' }}</button>
    </section>

    <div v-if="topDish" class="v5-actions">
      <button type="button" class="v5-action v5-action--primary" :disabled="refilling" @click="swipeRight">就吃这个 <span>→</span></button>
      <div class="v5-secondary"><button type="button" :disabled="refilling" @click="swipeLeft">换一个</button><button type="button" @click="showToast('组合方案：切到下厨模式后重算', 'ok')">组合方案</button></div>
    </div>

    <Transition name="toast-fade">
      <p v-if="toast" class="toast glass-card--matte" :class="`toast--${toast.tone}`" role="status" aria-live="polite">{{ toast.text }}</p>
    </Transition>


    <div v-if="settingsOpen" class="v5-overlay" @click="settingsOpen = false"></div>
    <aside v-if="settingsOpen" class="v5-sheet" aria-label="调整这顿">
      <header class="v5-sheet__head"><div><p class="v5-sheet__eyebrow">TUNE THIS MEAL</p><h2>调整这顿</h2></div><button type="button" class="v5-sheet__close" aria-label="关闭" @click="settingsOpen = false">×</button></header>
      <div class="v5-sheet__body">
        <ModeSwitcher />
        <StatusBubbles />
        <p v-if="ignoredBubbles.length" class="ignored">已忽略：{{ ignoredBubbles.join('、') }}</p>
        <div class="runrow">
          <div class="budget">
            <label class="budget__label" for="budget-range">预算</label>
            <input id="budget-range" class="range budget__range slider-ink" type="range" min="10" max="120" step="5" :value="mode.budget ?? 120" @input="mode.setBudget($event.target.value)" />
            <span class="budget__value tabular">{{ mode.budget ? `¥${mode.budget}` : '不限' }}</span>
          </div>
          <button type="button" class="v5-refresh" :disabled="algo.loading" @click="refresh">{{ algo.loading ? '计算中…' : '开始决策' }}</button>
        </div>
        <button type="button" class="v5-sheet__algo" @click="algo.toggleSandbox(true); settingsOpen = false">打开算法沙盒 →</button>
      </div>
    </aside>
    <RadarSheet :open="Boolean(radarDish)" :dish="radarDish" @close="radarDish = null" />
    <AlgoSandboxDrawer />
  </div>
</template>

<style scoped>
/* —— 一屏骨架：flex 纵向分配，页面本身不滚动 —— */
.home {
  position: relative;
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

/* L0 顶部重点区域：只占头部高度，向下渐隐并入全局底 */
.home__chrome {
  position: absolute;
  top: calc(-1 * (env(safe-area-inset-top, 0px) + 12px));
  left: -20px;
  right: -20px;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  border-radius: 0 0 28px 28px;
  /*
   * LiquidChrome 的 shader 是 uBaseColor / abs(sin(...))，分母贴近 0 时约 6.5% 的画面会被钳成纯白，
   * 而规格要求铬底「最亮不超过 var(--color-chrome-max)」。不碰 shader 的前提下唯一无损压法是外层线性缩放：
   * 0.13 × 255 ≈ 33 ≈ var(--color-ink) < var(--color-chrome-max)。这是调用处的视觉约束，不是组件实现改动。
   */
  filter: brightness(0.13);
  mask-image: linear-gradient(to bottom, var(--color-black) 55%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, var(--color-black) 55%, transparent 100%);
}

/* —— 状态行 —— */
.home__head {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 44px;
  align-items: center;
  gap: 8px;
  min-width: 0;
  /* 顶部留一口气，但首屏寸土寸金：卡面要占一半以上，这里只留 14px */
  margin: 14px 0 14px;
}

.home__greet {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  /* 中文的形框比 em 高，行高给到 1.5 再配 2px 内边距，否则 overflow:hidden 会把字头切掉 */
  overflow: hidden;
  padding: 2px 0;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
  color: var(--color-white);
  text-shadow: 0 1px 12px rgb(var(--rgb-black) / 0.35);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home__greet b {
  font-weight: 700;
}

.icon-btn {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  color: var(--color-steel);
}

.icon-btn svg {
  width: 15px;
  height: 15px;
}

/* —— 筛选面板 —— */
.panel {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 10px;
  color: var(--on-glass);
}

.ignored {
  margin: 0;
  font-size: 10px;
  line-height: 1.3;
  color: var(--on-glass-dim);
}

/* 预算滑块 + 主 CTA 同排：省一行，把高度让给卡组 */
.runrow {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 42px;
}

.budget {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.budget__label {
  flex: 0 0 auto;
  font-size: 10.5px;
  letter-spacing: 0.04em;
  color: var(--on-glass-dim);
}

.budget__range {
  flex: 1 1 auto;
  min-width: 0;
  accent-color: var(--color-white);
}

.budget__value {
  flex: 0 0 auto;
  min-width: 30px;
  text-align: right;
  font-size: 11px;
  font-weight: 600;
  color: var(--on-glass);
}

.runrow__cta {
  flex: 0 0 128px;
}

/* —— 结果区：卡面按自身高度排，剩余空白留给页面底部 —— */
.deck-host {
  position: relative;
  z-index: 2;
  display: flex;
  /* 卡组吃掉中间所有剩余高度，再用 max-height 封顶；矮屏收缩时先压卡面而不是压按钮 */
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  margin-top: 12px;
}

.notice {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  border-radius: 20px;
  padding: 16px;
  color: var(--on-glass);
}

/* —— 候选条：一行横滑 —— */
.candidates {
  display: flex;
  flex: 0 0 28px;
  align-items: center;
  gap: 7px;
  margin-top: 8px;
  overflow-x: auto;
  scrollbar-width: none;
}

.candidates::-webkit-scrollbar {
  display: none;
}

.chip {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11.5px;
  color: var(--on-glass);
  white-space: nowrap;
  transition: transform 0.15s ease;
}

.chip:active {
  transform: scale(0.97);
}

.chip--top {
  background: rgb(var(--rgb-white) / 0.92);
  color: var(--color-ink);
  box-shadow: 0 8px 20px rgb(var(--rgb-black) / 0.28);
}

.chip__rank {
  font-size: 9.5px;
  opacity: 0.7;
}

.chip__name {
  max-width: 8em;
  overflow: hidden;
  font-weight: 650;
  text-overflow: ellipsis;
}

.chip__score {
  font-size: 11px;
  opacity: 0.85;
}

.candidates__empty {
  font-size: 11.5px;
  color: var(--on-glass-soft);
}

/* —— 与手势等效的按钮区 —— */
.toast {
  position: fixed;
  left: 50%;
  bottom: calc(104px + env(safe-area-inset-bottom, 0px));
  z-index: 40;
  transform: translateX(-50%);
  max-width: min(86vw, 360px);
  margin: 0;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 12px;
  line-height: 1.4;
  text-align: center;
  color: var(--on-glass);
}

.toast--warn {
  /* 单色体系下警示不靠色相：反白底 + ink 字，与普通 toast 形成明度反差 */
  background: var(--color-white);
  color: var(--color-ink);
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-white) / 0.45), 0 10px 24px rgb(var(--rgb-black) / 0.4);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 6px);
}

.deck-actions {
  display: grid;
  flex: 0 0 44px;
  grid-template-columns: 1fr 1.35fr;
  gap: 10px;
  margin-top: 8px;
  /* 剩余的垂直空间全部落在按钮下方，卡片与候选条紧贴，不留中间空档 */
  margin-bottom: auto;
}

.act {
  border-radius: 999px;
  height: 44px;
  font-size: 12.5px;
  font-weight: 650;
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.act:active:not(:disabled) {
  transform: scale(0.98);
}

.act:disabled {
  opacity: 0.36;
  cursor: not-allowed;
}

.act--ghost {
  border: 1px solid var(--on-glass-line);
  color: var(--on-glass);
  background: transparent;
}

.act--ink {
  background: rgb(var(--rgb-white) / 0.92);
  color: var(--color-ink);
}

/* —— 卡组耗尽 —— */
/* 空态整块居中：一张卡片里只有一个"没有结果"的结论，左对齐会显得散 */
.exhausted {
  align-items: center;
  text-align: center;
}

.exhausted__art {
  margin-bottom: 6px;
  opacity: 0.72;
}

.exhausted__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.exhausted__sub {
  margin: 0 0 4px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--on-glass-soft);
}

.exhausted .act {
  align-self: stretch;
  text-align: center;
}

/* —— 骨架屏 —— */
.skeleton {
  height: 72px;
  border-radius: 16px;
  background: linear-gradient(
    90deg,
    rgb(var(--rgb-white) / 0.07),
    rgb(var(--rgb-white) / 0.16),
    rgb(var(--rgb-white) / 0.07)
  );
  background-size: 200% 100%;
  animation: skeleton-move 1.4s ease-in-out infinite;
}

.skeleton--short {
  height: 44px;
}

@keyframes skeleton-move {
  0% {
    background-position: 120% 0;
  }

  100% {
    background-position: -20% 0;
  }
}

/* —— 错误 —— */
.error-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--on-glass);
}

.error-msg {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--on-glass-soft);
  word-break: break-all;
}

/* —— 矮屏兜底（667 级）：收紧间距、压低图区，仍不滚动 —— */
@media (max-height: 700px) {
  .panel {
    margin-top: 8px;
    padding: 7px 10px;
  }

  .deck-host {
    margin-top: 10px;
  }

  .candidates {
    margin-top: 8px;
  }

  .deck-actions {
    margin-top: 8px;
  }
}

/* —— V5 燕麦暖食作用域：只覆盖首页，不动后台与其他页面 —— */
.home--v5 {
  --color-text: #241e18;
  --color-text-soft: rgba(36, 30, 24, 0.7);
  --color-line: rgba(36, 30, 24, 0.12);
  --on-glass: #241e18;
  --on-glass-soft: rgba(36, 30, 24, 0.68);
  --on-glass-dim: rgba(36, 30, 24, 0.5);
  --on-glass-line: rgba(36, 30, 24, 0.14);
  --glass-card-fill: rgba(255, 253, 248, 0.72);
  --glass-card-fill-matte: rgba(255, 253, 248, 0.55);
  --glass-card-edge: rgba(255, 255, 255, 0.82);
  --glass-card-inner-top: rgba(255, 255, 255, 0.9);
  --glass-card-inner-bottom: rgba(255, 255, 255, 0.25);
  --glass-card-shadow: 0 16px 36px rgba(38, 31, 23, 0.08);
  --glass-bg: rgba(251, 249, 244, 0.74);
  --glass-shadow: 0 8px 26px rgba(38, 31, 23, 0.08);
  background: #f4f1ea;
  color: #241e18;
}

.home--v5 .home__chrome {
  display: none;
}

.home--v5 .home__greet {
  color: #241e18;
  text-shadow: none;
}

.home--v5 .icon-btn {
  color: #6e6256;
}

.home--v5 .budget__range {
  accent-color: #241e18;
}

/* —— V5 决策台 —— */
.home--v5 {
  position: relative;
  padding: 0;
  overflow: hidden;
  background: #f4f1ea;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.home--v5::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background-image: var(--v5-grain);
  background-size: 180px 180px;
  opacity: .52;
  mix-blend-mode: multiply;
}

.v5-ambient {
  position: absolute;
  top: -42px;
  left: -42px;
  right: -42px;
  height: 260px;
  z-index: 0;
  opacity: .2;
  pointer-events: none;
}

.v5-ambient img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.v5-head {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 46px;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.v5-head__persona { display: flex; align-items: center; gap: 9px; min-width: 0; }
.v5-avatar { width: 34px; height: 34px; flex: 0 0 34px; border-radius: 50%; display: grid; place-items: center; background: #241e18; color: #fffdf8; font-size: 12px; font-weight: 600; }
.v5-head__copy { min-width: 0; }
.v5-head__greet { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: -0.02em; color: var(--color-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.v5-head__meta { margin: 2px 0 0; font-size: 9.5px; color: var(--color-steel); }
.v5-head__actions { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
.v5-icon { width: 32px; height: 32px; border-radius: 999px; display: grid; place-items: center; color: var(--color-steel); background: rgba(255, 255, 255, .48); border: 1px solid rgba(36, 30, 24, .1); }
.v5-icon svg { width: 15px; height: 15px; }

.v5-context { position: relative; z-index: 2; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; padding: 8px 0 7px; font-size: 9.5px; color: var(--color-steel); }
.v5-context i { width: 2px; height: 2px; border-radius: 50%; background: rgba(36, 30, 24, .35); }

.v5-panel { flex: 0 0 auto; padding: 9px 10px; border-radius: 18px; }
.v5-panel .ignored { margin: 5px 0 0; }
.v5-refresh { flex: 0 0 104px; height: 34px; border-radius: 999px; background: var(--color-ink); color: #fffdf8; font-size: 11px; font-weight: 600; }

.v5-decision { position: relative; z-index: 2; flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; margin-top: 6px; padding: 12px 14px; border-radius: 24px; background: rgba(255, 253, 248, .34); border: 1px solid rgba(255, 255, 255, .55); box-shadow: 0 10px 28px rgba(38, 31, 23, .05); overflow: hidden; }
.v5-decision__head { display: flex; justify-content: flex-end; align-items: baseline; padding: 0 2px; }
.v5-decision__head b { font-size: 20px; font-weight: 600; letter-spacing: -.04em; color: var(--color-ink); }
.v5-decision__head small { margin-left: 3px; font-size: 8px; font-weight: 400; color: var(--color-steel); }
.v5-radar { flex: 0 0 280px; min-height: 0; display: flex; align-items: center; justify-content: center; margin: 0; }
.v5-radar > * { width: 280px; height: 280px; max-width: 100%; }
.v5-dish { margin: 0 0 3px; font-size: 23px; font-weight: 600; letter-spacing: -.04em; line-height: 1.15; color: var(--color-ink); }
.v5-meta { margin: 0; font-size: 9.5px; color: var(--color-steel); }
.v5-reason { margin: 7px 0 0; font-size: 10.5px; line-height: 1.55; color: var(--color-steel); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.v5-evidence { display: flex; align-items: center; gap: 9px; margin-top: 8px; padding-top: 7px; border-top: 1px solid rgba(36, 30, 24, .1); font-size: 9px; color: var(--color-steel); }
.v5-evidence b { color: var(--color-ink); font-weight: 600; }
.v5-evidence button { margin-left: auto; padding: 0; font-size: 9px; color: var(--color-steel); text-decoration: underline; text-underline-offset: 3px; }
.v5-budget { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; padding: 8px 0; border-top: 1px solid rgba(36, 30, 24, .1); border-bottom: 1px solid rgba(36, 30, 24, .1); }
.v5-budget div { display: flex; flex-direction: column; gap: 2px; }
.v5-budget span { font-size: 8px; color: var(--color-steel); }
.v5-budget b { font-size: 12px; font-weight: 600; color: var(--color-ink); }
.v5-budget b.is-over { color: #a33a2b; }
.v5-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 7px; }
.v5-tags span { padding: 3px 6px; border-radius: 6px; background: rgba(36, 30, 24, .055); font-size: 8.5px; color: var(--color-steel); }
.v5-tags b { color: var(--color-ink); font-weight: 600; }
.v5-alts { margin-top: 7px; padding-top: 7px; border-top: 1px solid rgba(36, 30, 24, .1); }
.v5-alts__head { display: flex; justify-content: space-between; font-size: 8px; color: var(--color-steel); }
.v5-alt { width: 100%; display: flex; justify-content: space-between; align-items: baseline; gap: 10px; padding: 6px 0; border-bottom: 1px solid rgba(36, 30, 24, .08); text-align: left; }
.v5-alt:last-child { border-bottom: 0; }
.v5-alt span { font-size: 10px; color: var(--color-ink); }
.v5-alt small { font-size: 8.5px; color: var(--color-steel); white-space: nowrap; }

.v5-actions { position: relative; z-index: 2; display: flex; flex: 0 0 76px; flex-direction: column; gap: 6px; padding-top: 8px; margin-bottom: 64px; }
.v5-action { height: 44px; border-radius: 14px; font-size: 11.5px; font-weight: 500; }
.v5-action--ghost { border: 1px solid rgba(36, 30, 24, .16); color: var(--color-ink); background: rgba(255, 255, 255, .36); }
.v5-action--primary { width: 100%; display: flex; align-items: center; justify-content: space-between; padding: 0 15px; color: var(--color-ink); background: rgba(255, 255, 255, .62); border: 1px solid rgba(255, 255, 255, .9); box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 8px 22px rgba(38, 31, 23, .1); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
.v5-action--primary span { font-size: 16px; opacity: .7; }
.v5-secondary { display: flex; justify-content: space-between; align-items: center; padding: 0 2px; }
.v5-secondary button { padding: 0; font-size: 9.5px; color: var(--color-steel); text-decoration: underline; text-underline-offset: 3px; }

.v5-state { position: relative; z-index: 2; flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border-radius: 20px; padding: 18px; text-align: center; }
.v5-state__title { margin: 0; font-size: 13px; font-weight: 600; color: var(--color-ink); }
.v5-state__body { margin: 0; font-size: 10px; line-height: 1.5; color: var(--color-steel); word-break: break-all; }
.v5-state__btn { height: 34px; padding: 0 14px; border-radius: 999px; background: var(--color-ink); color: #fffdf8; font-size: 10px; }
.v5-skeleton { width: 78%; height: 80px; border-radius: 14px; background: linear-gradient(90deg, rgba(36,30,24,.05), rgba(36,30,24,.1), rgba(36,30,24,.05)); background-size: 200% 100%; animation: v5-skeleton 1.4s ease-in-out infinite; }
.v5-skeleton--short { height: 34px; width: 52%; }
@keyframes v5-skeleton { 0% { background-position: 120% 0; } 100% { background-position: -20% 0; } }

@media (max-height: 720px) {
  .v5-radar { flex-basis: 220px; }
  .v5-radar > * { width: 220px; height: 220px; }
  .v5-actions { margin-bottom: 16px; }
  .v5-dish { font-size: 21px; }
  .v5-reason { -webkit-line-clamp: 1; }
  .v5-alts { display: none; }
}


.v5-overlay { position: absolute; inset: 0; z-index: 10; background: rgba(20, 18, 15, .25); }
.v5-sheet { position: absolute; left: 0; right: 0; bottom: 0; z-index: 11; max-height: 76%; display: flex; flex-direction: column; padding: 10px 18px calc(16px + env(safe-area-inset-bottom, 0px)); border-radius: 26px 26px 0 0; background: rgba(251, 249, 244, .86); border-top: 1px solid rgba(255,255,255,.9); box-shadow: 0 -20px 60px rgba(38,31,23,.18); backdrop-filter: blur(30px) saturate(1.25); -webkit-backdrop-filter: blur(30px) saturate(1.25); }
.v5-sheet__head { display: flex; justify-content: space-between; align-items: flex-start; padding: 4px 0 12px; }
.v5-sheet__eyebrow { margin: 0 0 3px; font-size: 8.5px; letter-spacing: .16em; color: var(--color-steel); }
.v5-sheet__head h2 { margin: 0; font-size: 19px; font-weight: 600; letter-spacing: -.03em; color: var(--color-ink); }
.v5-sheet__close { width: 30px; height: 30px; border-radius: 50%; background: rgba(36,30,24,.06); color: var(--color-steel); font-size: 17px; }
.v5-sheet__body { display: flex; flex-direction: column; gap: 8px; overflow-y: auto; }
.v5-sheet__algo { margin-top: 4px; padding: 8px 0; text-align: left; font-size: 10px; color: var(--color-steel); text-decoration: underline; text-underline-offset: 3px; }

</style>
