<script setup>
/**
 * Footprint.vue —— 饮食足迹：防腻冷却看板 + 周度干饭报告。
 *
 * 数据只走 GET /logs/stats/{user_id}（第五章模块 5），三个区块：
 *   1. 本周概览（打卡次数 / 花费 / 冷却中的菜）
 *   2. 防腻冷却看板 —— 每道吃过不久的菜一条进度：decay_weight 从 0 爬到 1 的过程
 *   3. 菜系分布环形图 + 本周花费
 * 拿不到数据就显示空态，不编数字。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useAutoAnimate } from '@formkit/auto-animate/vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import { fetchLogStats } from '../../api'
import { usePersonaStore } from '../../stores/persona'
import { alpha, tokens } from '../../utils/theme'

use([PieChart, TooltipComponent, CanvasRenderer])

const persona = usePersonaStore()
const stats = ref(null)
const loading = ref(true)
const error = ref('')
const [listRef] = useAutoAnimate({ duration: 220 })

const cooling = computed(() => stats.value?.cooling_dishes ?? [])
const coolingNow = computed(() => cooling.value.filter((d) => d.status === 'WARMING'))
const pie = computed(() => stats.value?.cuisine_pie_data ?? [])
const meals = computed(() => stats.value?.meals_this_week ?? 0)
const expense = computed(() => Number(stats.value?.weekly_expense ?? 0))

async function load() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await fetchLogStats(persona.userId)
  } catch (e) {
    error.value = e?.message || '足迹数据加载失败'
    stats.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => persona.userId, load)

/** 灰阶梯度：单色体系下用"白 → 银 → 钢灰 → 深灰"四级区分菜系 */
const ramp = computed(() => {
  const t = tokens()
  return [t.ink, t.steel, t.silver, alpha(t.steel, 0.55), alpha(t.steel, 0.32)]
})

const pieOption = computed(() => {
  const t = tokens()
  const colors = ramp.value
  return {
    animationDuration: 560,
    tooltip: {
      trigger: 'item',
      backgroundColor: t.ink,
      borderWidth: 0,
      textStyle: { color: t.white, fontSize: 11 },
      formatter: (p) => `${p.name}<br/>${p.value} 次 · ${p.percent}%`,
    },
    series: [
      {
        type: 'pie',
        radius: ['58%', '82%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        // ECharts 画在 canvas 上，不认 CSS 变量，颜色必须走 theme 令牌（已解析成具体色值）
        itemStyle: { borderColor: alpha(t.mist, 0.9), borderWidth: 2 },
        label: {
          color: t.ink,
          fontSize: 10.5,
          formatter: '{b}',
        },
        labelLine: { lineStyle: { color: alpha(t.ink, 0.25) }, length: 8, length2: 8 },
        data: pie.value.map((item, i) => ({
          name: item.name,
          value: item.value,
          itemStyle: { color: colors[i % colors.length] },
        })),
      },
    ],
  }
})

function statusText(status) {
  if (status === 'READY') return '已解禁'
  if (status === 'HOT') return '刚吃过'
  return '冷却中'
}

function daysText(days) {
  if (days <= 0) return '今天'
  if (days === 1) return '昨天'
  return `${days} 天前`
}
</script>

<template>
  <div class="fp">
    <header class="fp__head">
      <p class="fp__eyebrow">饮食足迹</p>
      <h1 class="fp__title">这周都吃了什么</h1>
    </header>

    <p v-if="error" class="fp__error">{{ error }}</p>

    <div v-else-if="loading" class="fp__skeleton" aria-hidden="true" />

    <template v-else>
      <section class="fp__stats">
        <div class="stat glass-card">
          <span class="stat__label">本周打卡</span>
          <span class="stat__value">
            <span class="stat__num tabular">{{ meals }}</span>
            <span class="stat__unit">次</span>
          </span>
        </div>
        <div class="stat glass-card">
          <span class="stat__label">本周花费</span>
          <span class="stat__value">
            <span class="stat__num tabular">{{ expense.toFixed(0) }}</span>
            <span class="stat__unit">元</span>
          </span>
        </div>
        <div class="stat glass-card">
          <span class="stat__label">还在冷却</span>
          <span class="stat__value">
            <span class="stat__num tabular">{{ coolingNow.length }}</span>
            <span class="stat__unit">道</span>
          </span>
        </div>
      </section>

      <section class="block">
        <div class="block__head">
          <h2 class="block__title">防腻冷却看板</h2>
          <span class="block__hint">吃完越近，权重压得越低</span>
        </div>

        <p v-if="!cooling.length" class="empty">
          还没有打卡记录。在首页点「就吃这个」，这里就会开始记录冷却进度。
        </p>

        <ul v-else ref="listRef" class="cooling">
          <li v-for="dish in cooling" :key="dish.dish_id" class="cool">
            <div class="cool__top">
              <span class="cool__name">{{ dish.name }}</span>
              <span class="cool__badge" :data-status="dish.status">{{ statusText(dish.status) }}</span>
            </div>
            <div class="cool__meter" role="img" :aria-label="`已冷却 ${dish.cooling_percent}%`">
              <span class="cool__fill" :style="{ width: `${Math.max(2, dish.cooling_percent)}%` }" />
            </div>
            <div class="cool__foot">
              <span>{{ daysText(dish.days_since) }} · 权重 {{ dish.decay_weight.toFixed(2) }}</span>
              <span class="tabular">{{ dish.cooling_percent.toFixed(0) }}%</span>
            </div>
          </li>
        </ul>
      </section>

      <section class="block">
        <div class="block__head">
          <h2 class="block__title">菜系分布</h2>
          <span class="block__hint">本周打卡按菜系聚合</span>
        </div>

        <p v-if="!pie.length" class="empty">本周还没有打卡，暂时画不出分布。</p>
        <div v-else class="pie glass-card">
          <VChart class="pie__chart" :option="pieOption" autoresize />
          <ul class="legend">
            <li v-for="(item, i) in pie" :key="item.name" class="legend__row">
              <span class="legend__dot" :style="{ background: ramp[i % ramp.length] }" />
              <span class="legend__name">{{ item.name }}</span>
              <span class="legend__val tabular">{{ item.value }} 次</span>
            </li>
          </ul>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.fp {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 8px;
}

.fp__eyebrow {
  margin: 0 0 4px;
  font-size: 10.5px;
  letter-spacing: 0.08em;
  color: var(--on-glass-soft);
}

.fp__title {
  margin: 0;
  font-size: 20px;
  font-weight: 720;
  color: var(--on-glass);
}

.fp__error {
  margin: 0;
  border-radius: 1rem;
  padding: 12px 14px;
  font-size: 12px;
  color: var(--on-glass);
  background: rgb(var(--rgb-white) / 0.12);
}

.fp__skeleton {
  height: 150px;
  border-radius: 1.25rem;
  background: rgb(var(--rgb-white) / 0.08);
}

.fp__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.stat {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  padding: 10px 12px 11px;
  border-radius: 1.125rem;
}

.stat__label {
  font-size: 10.5px;
  color: var(--on-glass-soft);
}

.stat__value {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.stat__num {
  font-size: 21px;
  font-weight: 700;
  line-height: 1.05;
  color: var(--on-glass);
}

.stat__unit {
  font-size: 10px;
  color: var(--on-glass-dim);
}

.block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.block__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.block__title {
  margin: 0;
  font-size: 14px;
  font-weight: 680;
  color: var(--on-glass);
}

.block__hint {
  font-size: 10.5px;
  color: var(--on-glass-dim);
}

.empty {
  margin: 0;
  border-radius: 1.125rem;
  padding: 18px 14px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--on-glass-soft);
  background: rgb(var(--rgb-white) / 0.07);
}

.cooling {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.cool {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-radius: 1rem;
  padding: 11px 13px;
  background: rgb(var(--rgb-white) / 0.08);
}

.cool__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.cool__name {
  font-size: 13px;
  font-weight: 640;
  color: var(--on-glass);
}

.cool__badge {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 2px 7px;
  font-size: 9.5px;
  color: var(--on-glass-soft);
  background: rgb(var(--rgb-white) / 0.1);
}

.cool__badge[data-status='READY'] {
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.9);
}

.cool__meter {
  position: relative;
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
}

.cool__fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.82);
  transition: width 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.cool__foot {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--on-glass-dim);
}

.pie {
  padding: 12px 14px 14px;
  border-radius: 1.25rem;
}

.pie__chart {
  width: 100%;
  height: 196px;
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}

.legend__row {
  display: grid;
  grid-template-columns: 8px 1fr auto;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--on-glass-soft);
}

.legend__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend__val {
  color: var(--on-glass-dim);
}
</style>
