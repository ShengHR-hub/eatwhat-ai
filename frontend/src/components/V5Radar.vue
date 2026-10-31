<script setup>
import { computed } from 'vue'

const props = defineProps({
  vector: { type: Object, default: null },
})

const AXES = [
  ['spicy_level', '辣'],
  ['oily_level', '油'],
  ['soup_level', '汤'],
  ['temp_fit', '温'],
  ['satiety_level', '饱'],
  ['prep_speed', '快'],
  ['social_fit', '社交'],
  ['comfort_level', '抚慰'],
]

const center = 160
const radius = 106
const angle = (index) => (-90 + index * 45) * Math.PI / 180
const point = (index, ratio) => ({
  x: center + Math.cos(angle(index)) * radius * ratio,
  y: center + Math.sin(angle(index)) * radius * ratio,
})
const polygon = (ratio) => AXES.map((_, index) => {
  const p = point(index, ratio)
  return `${p.x.toFixed(2)},${p.y.toFixed(2)}`
}).join(' ')
const grid = [0.25, 0.5, 0.75, 1].map((ratio) => ({ ratio, points: polygon(ratio) }))
const axes = AXES.map((_, index) => point(index, 1))
const labels = AXES.map(([, label], index) => {
  const p = point(index, 1.36)
  return { label, x: p.x, y: p.y, anchor: p.x < center - 2 ? 'end' : p.x > center + 2 ? 'start' : 'middle' }
})
const shape = computed(() => AXES.map(([key], index) => {
  const raw = Number(props.vector?.[key] ?? 0)
  const value = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0
  const p = point(index, value)
  return `${p.x.toFixed(2)},${p.y.toFixed(2)}`
}).join(' '))
const dots = computed(() => AXES.map(([key], index) => {
  const raw = Number(props.vector?.[key] ?? 0)
  const value = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0
  return point(index, value)
}))
</script>

<template>
  <svg viewBox="0 0 320 320" class="v5-radar-svg" role="img" aria-label="菜品八维风味雷达">
    <defs>
      <filter id="v5-radar-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="5" />
      </filter>
    </defs>
    <circle :cx="center" :cy="center" r="116" fill="none" stroke="rgb(var(--rgb-v5-ink) / .08)" stroke-width="1" />
    <g fill="none" stroke="rgb(var(--rgb-v5-ink) / .13)">
      <polygon v-for="item in grid" :key="item.ratio" :points="item.points" :stroke-width="item.ratio === 1 ? 1.1 : 1" />
    </g>
    <g stroke="rgb(var(--rgb-v5-ink) / .1)" stroke-width="1">
      <line v-for="(p, index) in axes" :key="index" :x1="center" :y1="center" :x2="p.x" :y2="p.y" />
    </g>
    <polygon :points="shape" fill="none" stroke="var(--v5-faint)" stroke-width="7" opacity=".22" filter="url(#v5-radar-glow)" />
    <polygon :points="shape" fill="rgb(var(--rgb-v5-ink) / .075)" stroke="var(--v5-ink)" stroke-width="1.6" stroke-linejoin="round" />
    <circle v-for="(p, index) in dots" :key="`dot-${index}`" :cx="p.x" :cy="p.y" r="2.2" fill="var(--v5-ink)" stroke="rgb(var(--rgb-v5-paper) / .9)" stroke-width="1" />
    <circle :cx="center" :cy="center" r="3.2" fill="var(--v5-ink)" />
    <circle :cx="center" :cy="center" r="8" fill="none" stroke="rgb(var(--rgb-v5-ink) / .16)" stroke-width="1" />
    <g fill="var(--v5-muted)" font-size="11" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif">
      <text v-for="item in labels" :key="item.label" :x="item.x" :y="item.y" :text-anchor="item.anchor" dominant-baseline="middle">{{ item.label }}</text>
    </g>
  </svg>
</template>

<style scoped>
.v5-radar-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}
</style>
