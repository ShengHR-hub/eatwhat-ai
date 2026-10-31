<script setup>
/**
 * 数字滚动牌（Number Ticker）—— 匹配度百分比用。
 * 参照 Magic UI / Inspira UI 的 NumberTicker 行为：进入视口或数值变化时从旧值滚到新值。
 * 这里用 rAF + easeOutCubic 实现，不占用 gsap（gsap 的用途在规范里锁给划卡与揭晓时间线）。
 */
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  decimals: { type: Number, default: 1 },
  duration: { type: Number, default: 900 },
  suffix: { type: String, default: '' },
})

const shown = ref(0)
let raf = 0

const format = (v) => v.toFixed(props.decimals)

function animateTo(target) {
  cancelAnimationFrame(raf)
  const from = shown.value
  const delta = target - from
  if (!Number.isFinite(delta) || Math.abs(delta) < 0.05) {
    shown.value = target
    return
  }
  const start = performance.now()
  const tick = (now) => {
    const t = Math.min(1, (now - start) / props.duration)
    const eased = 1 - Math.pow(1 - t, 3)
    shown.value = from + delta * eased
    if (t < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

watch(
  () => props.value,
  (v) => animateTo(Number(v) || 0),
  { immediate: true },
)

onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <span class="tabular">{{ format(shown) }}<span v-if="suffix" class="suffix">{{ suffix }}</span></span>
</template>

<style scoped>
.suffix {
  font-size: 0.62em;
  margin-left: 1px;
  color: var(--color-text-soft);
}
</style>
