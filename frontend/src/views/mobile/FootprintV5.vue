<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { fetchLogStats, fetchLogTimeline, submitFeedback } from '../../api'
import { usePersonaStore } from '../../stores/persona'
import { bubbleById } from '../../constants/bubbles'

const persona = usePersonaStore()
const stats = ref(null)
const timeline = ref([])
const loading = ref(true)
const error = ref('')
const reportOpen = ref(false)

const meals = computed(() => stats.value?.meals_this_week ?? 0)
const expense = computed(() => Number(stats.value?.weekly_expense ?? 0))
const cooling = computed(() => (stats.value?.cooling_dishes ?? []).filter((d) => d.status === 'WARMING'))
const pie = computed(() => stats.value?.cuisine_pie_data ?? [])
const maxPie = computed(() => Math.max(1, ...pie.value.map((item) => item.value)))

function parseDate(value) {
  if (!value) return new Date()
  const hasZone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

function dayKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatDay(key) {
  const today = dayKey(new Date())
  const yesterday = dayKey(new Date(Date.now() - 86400000))
  if (key === today) return '今天'
  if (key === yesterday) return '昨天'
  const [, month, day] = key.split('-')
  return `${Number(month)} 月 ${Number(day)} 日`
}

function formatTime(value) {
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(parseDate(value))
}

const groups = computed(() => {
  const map = new Map()
  for (const item of timeline.value) {
    const date = parseDate(item.eaten_at)
    const key = dayKey(date)
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(item)
  }
  return [...map.entries()].map(([key, items]) => ({ key, label: formatDay(key), items }))
})

function tagLabel(id) {
  return bubbleById(id)?.short ?? id
}

function modeLabel(mode) {
  if (mode === 'HOME_COOKING') return '下厨'
  if (mode === 'COMBO') return '组合'
  return '外食'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [nextStats, nextTimeline] = await Promise.all([
      fetchLogStats(persona.userId),
      fetchLogTimeline(persona.userId, 80),
    ])
    stats.value = nextStats
    timeline.value = nextTimeline.items ?? []
  } catch (err) {
    error.value = err?.message || '足迹加载失败'
    stats.value = null
    timeline.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => persona.userId, load)

/* ── 吃完之后的评价：打卡页只负责「我要吃」，评价放在这里 ── */
const RATING_OPTIONS = [
  { value: 3, emoji: '😋', label: '好吃' },
  { value: 2, emoji: '😐', label: '一般' },
  { value: 1, emoji: '😞', label: '踩雷' },
]
const RATING_LABEL = { 3: '😋 好吃', 2: '😐 一般', 1: '😞 踩雷' }
const ratingFor = ref(0)
const ratingBusy = ref(false)
// 评价失败时的提示。此前 catch 里直接写 notice.value，但 notice 从未声明，
// 失败时会再抛一个 ReferenceError，用户看不到任何反馈、评分静默丢失。
const notice = ref('')
let noticeTimer = 0
onBeforeUnmount(() => clearTimeout(noticeTimer))

function openRate(logId) {
  ratingFor.value = ratingFor.value === logId ? 0 : logId
}

async function submitRate(item, rating) {
  if (ratingBusy.value) return
  ratingBusy.value = true
  try {
    await submitFeedback(item.log_id, rating)
    item.rating = rating
    ratingFor.value = 0
  } catch (err) {
    notice.value = err?.detail || err?.message || '评价没提交成功'
    clearTimeout(noticeTimer)
    noticeTimer = setTimeout(() => (notice.value = ''), 2400)
  } finally {
    ratingBusy.value = false
  }
}
</script>

<template>
  <div class="fpv5">
    <header class="fp-head">
      <div>
        <p class="fp-eyebrow">FOOTPRINT</p>
        <h1>足迹</h1>
        <p class="fp-sub">从最近一顿往回看</p>
      </div>
      <button type="button" class="fp-report-btn" :aria-expanded="reportOpen" @click="reportOpen = !reportOpen">{{ reportOpen ? '收起周报' : '本周周报 →' }}</button>
    </header>

    <div class="fp-summary">
      <span><b class="tabular">{{ meals }}</b>顿</span>
      <span><b class="tabular">¥{{ expense.toFixed(0) }}</b>花费</span>
      <span><b class="tabular">{{ cooling.length }}</b>道冷却</span>
      <span>{{ timeline.length }} 条记录</span>
    </div>

    <p v-if="error" class="fp-error">{{ error }}</p>
    <div v-else-if="loading" class="fp-skeleton" aria-hidden="true" />

    <template v-else>
      <div v-if="!timeline.length" class="fp-empty">
        <p>还没有足迹。</p>
        <span>在首页点“就吃这个”，这里就会开始记录。</span>
      </div>

      <div v-else class="fp-timeline">
        <section v-for="group in groups" :key="group.key" class="day-group">
          <p class="day-label">{{ group.label }}<span>{{ group.key.slice(5).replace('-', '.') }}</span></p>
          <article v-for="item in group.items" :key="item.log_id" class="entry">
            <span class="entry__time">{{ formatTime(item.eaten_at) }}</span>
            <span class="entry__dot" />
            <div class="entry__body">
              <div class="entry__head"><h2>{{ item.dish_name }}</h2><span>¥{{ Number(item.cost_amount || 0).toFixed(0) }}</span></div>
              <p class="entry__meta">{{ item.restaurant_name || '自己做的' }} · {{ modeLabel(item.mode_type) }}<span v-if="item.weather_snapshot"> · {{ item.weather_snapshot }}</span></p>
              <div v-if="item.status_bubbles?.length" class="entry__tags"><span v-for="tag in item.status_bubbles" :key="tag">{{ tagLabel(tag) }}</span></div>
              <div class="entry__rate">
                <template v-if="item.rating">
                  <span class="entry__rated">{{ RATING_LABEL[item.rating] }}</span>
                  <button type="button" @click="openRate(item.log_id)">改</button>
                </template>
                <button v-else type="button" class="entry__rate-ask" @click="openRate(item.log_id)">吃完了？评价一下</button>
                <div v-if="ratingFor === item.log_id" class="entry__rate-opts">
                  <button v-for="opt in RATING_OPTIONS" :key="opt.value" type="button" :disabled="ratingBusy" @click="submitRate(item, opt.value)">
                    {{ opt.emoji }} {{ opt.label }}
                  </button>
                </div>
              </div>
            </div>
          </article>
        </section>
      </div>

      <section v-if="reportOpen" class="report">
        <div class="report__head"><h2>本周周报</h2><span>10.20 — 10.26</span></div>
        <div class="report__stats"><span><b>{{ meals }}</b>顿</span><span><b>¥{{ expense.toFixed(0) }}</b></span><span><b>{{ cooling.length }}</b>道冷却</span></div>
        <div class="report__block">
          <div class="report__title"><h3>还在冷却</h3><span>防腻权重</span></div>
          <div v-if="!cooling.length" class="report__empty">本周没有需要冷却的菜。</div>
          <div v-for="dish in cooling" :key="dish.dish_id" class="cool-row"><span>{{ dish.name }}</span><div class="cool-track"><i :style="{ width: `${dish.cooling_percent}%` }" /></div><b>{{ dish.cooling_percent.toFixed(0) }}%</b></div>
        </div>
        <div class="report__block">
          <div class="report__title"><h3>口味构成</h3><span>本周 {{ meals }} 顿</span></div>
          <div v-if="!pie.length" class="report__empty">本周还没有打卡。</div>
          <div v-for="item in pie" :key="item.name" class="taste-row"><span>{{ item.name }}</span><div class="taste-track"><i :style="{ width: `${(item.value / maxPie) * 100}%` }" /></div><b>{{ item.value }}</b></div>
        </div>
      </section>
    </template>

    <Transition name="fp-toast">
      <p v-if="notice" class="fp-toast" role="status" aria-live="polite">{{ notice }}</p>
    </Transition>
  </div>
</template>

<style scoped>
.fpv5 { display: flex; flex-direction: column; gap: 14px; padding-bottom: 8px; color: var(--on-glass); }
.fp-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }
.fp-eyebrow { margin: 0 0 4px; font-size: 9px; letter-spacing: .16em; color: var(--on-glass-dim); }
.fp-head h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -.04em; }
.fp-sub { margin: 6px 0 0; font-size: 10px; color: var(--on-glass-soft); }
.fp-report-btn { padding: 0 0 3px; font-size: 10px; color: var(--on-glass-soft); text-decoration: underline; text-underline-offset: 3px; }
.fp-summary { display: flex; gap: 14px; align-items: baseline; padding: 11px 0; border-top: 1px solid rgb(var(--rgb-v5-ink) / .12); border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .12); font-size: 9.5px; color: var(--on-glass-soft); }
.fp-summary b { margin-right: 2px; font-size: 16px; color: var(--on-glass); font-weight: 600; }
.fp-summary span:last-child { margin-left: auto; color: var(--on-glass-dim); }
.fp-error, .fp-empty { margin: 0; padding: 18px; border-radius: 16px; background: rgb(var(--rgb-v5-paper-strong) / .5); font-size: 11px; color: var(--on-glass-soft); }
.fp-empty span { display: block; margin-top: 4px; font-size: 9.5px; color: var(--on-glass-dim); }
.fp-skeleton { height: 220px; border-radius: 18px; background: rgb(var(--rgb-v5-ink) / .05); }
.fp-toast {
  position: fixed; left: 50%; bottom: 96px; transform: translateX(-50%); z-index: 40;
  margin: 0; padding: 9px 15px; border-radius: 999px;
  background: rgb(var(--rgb-v5-ink) / .9); color: var(--v5-paper-strong); font-size: 11px; white-space: nowrap;
  box-shadow: 0 8px 22px rgb(var(--rgb-black) / .24);
}
.fp-toast-enter-active, .fp-toast-leave-active { transition: opacity .18s ease, transform .18s ease; }
.fp-toast-enter-from, .fp-toast-leave-to { opacity: 0; transform: translate(-50%, 6px); }
.fp-timeline { position: relative; padding-top: 2px; }
.fp-timeline::before { content: ""; position: absolute; left: 48px; top: 0; bottom: 8px; width: 1px; background: rgb(var(--rgb-v5-ink) / .14); }
.day-group { margin-bottom: 14px; }
.day-label { margin: 0 0 8px; font-size: 9.5px; color: var(--on-glass-dim); }
.day-label span { margin-left: 5px; opacity: .7; }
.entry { display: grid; grid-template-columns: 38px 12px minmax(0,1fr); gap: 8px; align-items: flex-start; margin-bottom: 12px; }
.entry__time { padding-top: 2px; text-align: right; font-size: 8.5px; color: var(--on-glass-dim); font-variant-numeric: tabular-nums; }
.entry__dot { width: 7px; height: 7px; margin-top: 3px; border-radius: 50%; border: 1.5px solid var(--on-glass); background: var(--v5-paper); }
.entry__body { padding-bottom: 11px; border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .1); min-width: 0; }
.entry__head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.entry__head h2 { margin: 0; font-size: 12.5px; font-weight: 600; }
.entry__head span { font-size: 9.5px; color: var(--on-glass-soft); }
.entry__meta { margin: 3px 0 5px; font-size: 9px; color: var(--on-glass-dim); }
.entry__tags { display: flex; flex-wrap: wrap; gap: 5px; }
.entry__tags span { padding: 3px 6px; border-radius: 6px; background: rgb(var(--rgb-v5-ink) / .055); font-size: 8.5px; color: var(--on-glass-soft); }
.report { padding: 14px; border-radius: 20px; background: rgb(var(--rgb-v5-paper-strong) / .58); border: 1px solid rgb(var(--rgb-white) / .8); }
.report__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.report__head h2 { margin: 0; font-size: 15px; font-weight: 600; }
.report__head span { font-size: 9px; color: var(--on-glass-dim); }
.report__stats { display: flex; gap: 14px; padding: 9px 0; border-top: 1px solid rgb(var(--rgb-v5-ink) / .1); border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .1); font-size: 9px; color: var(--on-glass-soft); }
.report__stats b { margin-right: 2px; font-size: 14px; color: var(--on-glass); }
.report__block { padding-top: 12px; }
.report__title { display: flex; justify-content: space-between; margin-bottom: 8px; }
.report__title h3 { margin: 0; font-size: 11px; font-weight: 600; }
.report__title span { font-size: 8.5px; color: var(--on-glass-dim); }
.report__empty { font-size: 9px; color: var(--on-glass-dim); }
.cool-row, .taste-row { display: grid; grid-template-columns: 72px 1fr 28px; gap: 8px; align-items: center; margin-bottom: 7px; font-size: 9px; color: var(--on-glass-soft); }
.cool-row b, .taste-row b { text-align: right; font-size: 8.5px; color: var(--on-glass-soft); font-weight: 500; }
.cool-track, .taste-track { height: 4px; border-radius: 2px; background: rgb(var(--rgb-v5-ink) / .1); overflow: hidden; }
.cool-track i, .taste-track i { display: block; height: 100%; border-radius: 2px; background: var(--v5-ink); }

/* 吃完后的评价入口 */
.entry__rate { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
.entry__rate-ask {
  padding: 2px 9px;
  border: 1px dashed rgb(var(--rgb-v5-ink) / .22);
  border-radius: 999px;
  background: none;
  color: var(--on-glass-soft, var(--v5-muted));
  font: inherit;
  font-size: 10px;
  cursor: pointer;
}
.entry__rate-ask:hover { border-color: rgb(var(--rgb-v5-ink) / .45); color: var(--on-glass, var(--v5-ink)); }
.entry__rated { color: var(--on-glass, var(--v5-ink)); font-size: 10.5px; }
.entry__rate button:not(.entry__rate-ask) {
  padding: 0;
  border: 0;
  background: none;
  color: var(--on-glass-soft, var(--v5-muted));
  font: inherit;
  font-size: 10px;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
.entry__rate-opts { display: flex; gap: 6px; width: 100%; margin-top: 4px; }
.entry__rate-opts button {
  flex: 1;
  height: 30px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .14) !important;
  border-radius: 9px;
  background: rgb(var(--rgb-v5-paper-strong) / .7) !important;
  color: var(--v5-ink) !important;
  font-size: 10.5px !important;
  text-decoration: none !important;
}
.entry__rate-opts button:hover { border-color: rgb(var(--rgb-v5-ink) / .4) !important; }

/* 吃完后的评价入口 */
.entry__rate { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
.entry__rate-ask {
  padding: 2px 9px;
  border: 1px dashed rgb(var(--rgb-v5-ink) / .22);
  border-radius: 999px;
  background: none;
  color: var(--on-glass-soft, var(--v5-muted));
  font: inherit;
  font-size: 10px;
  cursor: pointer;
}
.entry__rate-ask:hover { border-color: rgb(var(--rgb-v5-ink) / .45); color: var(--on-glass, var(--v5-ink)); }
.entry__rated { color: var(--on-glass, var(--v5-ink)); font-size: 10.5px; }
.entry__rate button:not(.entry__rate-ask) {
  padding: 0;
  border: 0;
  background: none;
  color: var(--on-glass-soft, var(--v5-muted));
  font: inherit;
  font-size: 10px;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
.entry__rate-opts { display: flex; gap: 6px; width: 100%; margin-top: 4px; }
.entry__rate-opts button {
  flex: 1;
  height: 30px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .14) !important;
  border-radius: 9px;
  background: rgb(var(--rgb-v5-paper-strong) / .7) !important;
  color: var(--v5-ink) !important;
  font-size: 10.5px !important;
  text-decoration: none !important;
}
.entry__rate-opts button:hover { border-color: rgb(var(--rgb-v5-ink) / .4) !important; }
</style>
