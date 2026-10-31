<script setup>
import { computed } from 'vue'

/**
 * 八维特征雷达（质检卡用）。
 *
 * 轴取自 dishes.feature_vector 的真实 8 键，与 dashboardOptions.FEATURE_LABELS 同源：
 *   辣度 / 油腻 / 汤水 / 温度 / 饱腹 / 速度 / 社交 / 抚慰
 * 设计稿里写的是「酸/甜/苦/辣/咸/鲜/油/烫」，那是视觉占位，库里没有这 8 个字段，
 * 复刻时按真实字段画，否则雷达展示的是不存在的维度。
 */
const props = defineProps({
  vector: { type: Object, default: null },
  index: { type: Number, default: 0 },
})

const AXES = [
  { key: 'spicy_level', label: '辣' },
  { key: 'oily_level', label: '油' },
  { key: 'soup_level', label: '汤' },
  { key: 'temp_fit', label: '温' },
  { key: 'satiety_level', label: '饱' },
  { key: 'prep_speed', label: '速' },
  { key: 'social_fit', label: '社' },
  { key: 'comfort_level', label: '抚' },
]

const S = 132
const CX = 66
const CY = 66
const R = 45
const LR = 62

const values = computed(() => AXES.map((axis) => {
  const raw = props.vector?.[axis.key]
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : null
}))

const missing = computed(() => values.value.map((v, i) => (v == null ? i : -1)).filter((i) => i >= 0))

const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / 8
const point = (i, ratio) => [
  CX + Math.cos(angle(i)) * R * ratio,
  CY + Math.sin(angle(i)) * R * ratio,
]
const polygon = (ratio) => AXES
  .map((_, i) => point(i, ratio).map((n) => n.toFixed(1)).join(','))
  .join(' ')

const rings = [0.33, 0.66, 1].map((ratio) => polygon(ratio))
const spokes = AXES.map((_, i) => {
  const [x, y] = point(i, 1)
  return { x: x.toFixed(1), y: y.toFixed(1), missing: missing.value.includes(i) }
})
const labels = AXES.map((axis, i) => {
  const [x, y] = [
    CX + Math.cos(angle(i)) * LR,
    CY + Math.sin(angle(i)) * LR,
  ]
  return { text: axis.label, x: x.toFixed(1), y: (y + 3.5).toFixed(1) }
})
const shape = computed(() => values.value
  .map((v, i) => point(i, v == null ? 0 : v).map((n) => n.toFixed(1)).join(','))
  .join(' '))
const dots = computed(() => values.value
  .map((v, i) => {
    if (v == null) return null
    const [x, y] = point(i, v)
    return { x: x.toFixed(1), y: y.toFixed(1) }
  })
  .filter(Boolean))
const missingDots = computed(() => missing.value.map((i) => {
  const [x, y] = point(i, 0)
  return { x: x.toFixed(1), y: y.toFixed(1) }
}))
</script>

<template>
  <svg class="dish-radar" viewBox="0 0 132 132" role="img" aria-label="八维特征雷达">
    <defs>
      <linearGradient :id="`dishRadarFill${index}`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--admin-accent)" stop-opacity="0.28" />
        <stop offset="100%" stop-color="var(--admin-accent)" stop-opacity="0.05" />
      </linearGradient>
      <radialGradient :id="`dishRadarGlow${index}`">
        <stop offset="0%" stop-color="var(--admin-accent)" stop-opacity="0.1" />
        <stop offset="62%" stop-color="var(--admin-accent)" stop-opacity="0.05" />
        <stop offset="100%" stop-color="var(--admin-accent)" stop-opacity="0" />
      </radialGradient>
    </defs>

    <circle :cx="CX" :cy="CY" :r="R + 12" :fill="`url(#dishRadarGlow${index})`" />

    <polygon
      v-for="(ring, i) in rings"
      :key="`ring-${i}`"
      :points="ring"
      fill="none"
      stroke="rgb(var(--rgb-admin-ink) / 0.1)"
      stroke-width="1"
    />

    <line
      v-for="(spoke, i) in spokes"
      :key="`spoke-${i}`"
      :x1="CX"
      :y1="CY"
      :x2="spoke.x"
      :y2="spoke.y"
      stroke="rgb(var(--rgb-admin-ink) / 0.08)"
      stroke-width="1"
      :stroke-dasharray="spoke.missing ? '2 3' : undefined"
    />

    <polygon
      :points="shape"
      :fill="`url(#dishRadarFill${index})`"
      stroke="var(--admin-accent)"
      stroke-width="1.6"
      stroke-linejoin="round"
      opacity="0.9"
    />

    <circle
      v-for="(dot, i) in dots"
      :key="`dot-${i}`"
      :cx="dot.x"
      :cy="dot.y"
      r="1.8"
      fill="var(--admin-accent)"
    />

    <circle
      v-for="(dot, i) in missingDots"
      :key="`miss-${i}`"
      :cx="dot.x"
      :cy="dot.y"
      r="2.6"
      fill="var(--admin-bad)"
    />

    <text
      v-for="(label, i) in labels"
      :key="`label-${i}`"
      :x="label.x"
      :y="label.y"
      text-anchor="middle"
      font-size="8.5"
      fill="var(--admin-muted)"
    >{{ label.text }}</text>
  </svg>
</template>

<style scoped>
.dish-radar { display: block; width: 132px; height: 132px; overflow: visible; }
</style>
