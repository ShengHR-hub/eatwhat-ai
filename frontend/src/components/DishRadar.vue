<script setup>
import { computed } from 'vue'

const props = defineProps({
  vector: { type: Object, default: null },
})

const axes = [
  ['spicy_level', '辣'],
  ['oily_level', '油'],
  ['soup_level', '汤'],
  ['temp_fit', '温'],
  ['satiety_level', '饱'],
  ['prep_speed', '快'],
  ['social_fit', '社交'],
  ['comfort_level', '抚慰'],
]

const center = { x: 60, y: 58 }
const radius = 36
const angle = (index) => (-90 + index * 45) * Math.PI / 180
const point = (index, ratio) => ({
  x: center.x + Math.cos(angle(index)) * radius * ratio,
  y: center.y + Math.sin(angle(index)) * radius * ratio,
})
const polygon = (ratio) => axes.map((_, index) => {
  const item = point(index, ratio)
  return `${item.x.toFixed(2)},${item.y.toFixed(2)}`
}).join(' ')

const grid = [0.25, 0.5, 0.75, 1].map(polygon)
const shape = computed(() => axes.map(([key], index) => {
  const raw = Number(props.vector?.[key] ?? 0)
  const value = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0
  const item = point(index, value)
  return `${item.x.toFixed(2)},${item.y.toFixed(2)}`
}).join(' '))
const available = computed(() => axes.every(([key]) => Number.isFinite(Number(props.vector?.[key]))))
const summary = computed(() => axes.map(([key, label]) => `${label}${Math.round(Number(props.vector?.[key] ?? 0) * 100)}`).join(' '))
const labelPoints = axes.map(([, label], index) => {
  const item = point(index, 1.36)
  return { label, ...item, anchor: item.x < center.x - 2 ? 'end' : item.x > center.x + 2 ? 'start' : 'middle' }
})
</script>

<template>
  <div class="dish-radar" role="img" :aria-label="available ? `菜品八维风味：${summary}` : '菜品八维风味未标注'">
    <svg v-if="available" viewBox="0 0 120 116" class="dish-radar__svg">
      <title>菜品八维风味雷达</title>
      <desc>{{ summary }}</desc>
      <polygon v-for="(points, index) in grid" :key="index" :points="points" class="dish-radar__grid" />
      <line
        v-for="(_, index) in axes"
        :key="`axis-${index}`"
        :x1="center.x"
        :y1="center.y"
        :x2="point(index, 1).x"
        :y2="point(index, 1).y"
        class="dish-radar__axis"
      />
      <polygon :points="shape" class="dish-radar__shape" />
      <circle :cx="center.x" :cy="center.y" r="1.5" class="dish-radar__dot" />
      <text
        v-for="item in labelPoints"
        :key="item.label"
        :x="item.x"
        :y="item.y"
        :text-anchor="item.anchor"
        dominant-baseline="middle"
        class="dish-radar__label"
      >{{ item.label }}</text>
    </svg>
    <div v-else class="dish-radar__empty">风味未标注</div>
    <span class="dish-radar__caption">八维风味</span>
  </div>
</template>

<style scoped>
.dish-radar {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(var(--rgb-white) / 0.035);
  overflow: hidden;
}

.dish-radar__svg {
  width: 100%;
  height: 100%;
  padding: 10px 18px 14px;
  box-sizing: border-box;
}

.dish-radar__grid {
  fill: none;
  stroke: rgb(var(--rgb-white) / 0.13);
  stroke-width: 0.7;
}

.dish-radar__axis {
  stroke: rgb(var(--rgb-white) / 0.14);
  stroke-width: 0.7;
}

.dish-radar__shape {
  fill: rgb(var(--rgb-white) / 0.2);
  stroke: var(--on-glass);
  stroke-width: 1.2;
  stroke-linejoin: round;
}

.dish-radar__dot {
  fill: var(--on-glass);
}

.dish-radar__label {
  fill: var(--on-glass-soft);
  font-size: 7px;
  font-family: var(--font-sans);
}

.dish-radar__caption {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--on-glass-dim);
}

.dish-radar__empty {
  font-size: 11px;
  color: var(--on-glass-dim);
}
</style>
