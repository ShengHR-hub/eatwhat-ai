<script setup>
/**
 * 双模式分段开关。规范 2.7 指定来源：daisyUI `filter`（一组 radio）。
 * v2.3 起双模式不靠颜色区分 —— 选中态是深灰实底 + 白字 + 图标/文案。
 *
 * 滑块惯性：用 @vueuse/motion 的 useMotion().apply() 驱动指示块位移
 * （spring stiffness 300 / damping 20，与规范 2.2 一致）。
 * 注意两个坑（都在 2.2.6 上踩过）：
 *   1. `v-motion` 指令没有 `:animate` 变体，合法变体只有
 *      initial / enter / leave / visible / visible-once / hovered / tapped / focused，
 *      写 `:animate="{ x: ... }"` 是无效代码，滑块永远停在 0。
 *   2. `useSpring()` 返回的是 `{ values, stop, set }`，不是 Ref，
 *      拿它当 `ref.value` 用会得到 NaN（浏览器丢弃该 transform 声明）。
 * 因此这里用 `useMotion(thumbRef).apply({ x: px, transition })`，
 * apply 接受对象字面量，正好能传动态像素值。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMotion } from '@vueuse/motion'

import { useModeStore, MODES } from '../stores/mode'

const mode = useModeStore()

const items = [MODES.OUT_DINING, MODES.HOME_COOKING]
const activeIndex = computed(() => items.findIndex((m) => m.value === mode.modeType))

/*
 * 指示块位移必须给像素值（'100%' 在 transform 里按元素自身宽度算，对不上轨道）。
 * 这里量轨道宽度，换算成 (宽 / 2 - 4px)；窗口尺寸变化时重测。
 */
const trackRef = ref(null)
const thumbOffset = ref(0)

function measure() {
  const el = trackRef.value
  if (!el) return
  thumbOffset.value = Math.max(0, Math.round(el.clientWidth / 2 - 4))
}
let observer = null
onMounted(() => {
  measure()
  if (typeof ResizeObserver !== 'undefined' && trackRef.value) {
    observer = new ResizeObserver(measure)
    observer.observe(trackRef.value)
  }
})
onBeforeUnmount(() => observer?.disconnect())

const thumbRef = ref(null)
const { apply } = useMotion(thumbRef, { initial: { x: 0 } })

watch(
  [activeIndex, thumbOffset],
  ([index, offset]) => {
    if (!thumbRef.value) return
    apply({
      x: index * offset,
      transition: { type: 'spring', stiffness: 300, damping: 20 },
    })
  },
  { flush: 'post' },
)
</script>

<template>
  <div ref="trackRef" class="filter mode-switch" role="radiogroup" aria-label="外食 / 下厨">
    <div ref="thumbRef" class="switch-thumb" aria-hidden="true" />

    <label
      v-for="item in items"
      :key="item.value"
      class="switch-item"
      :data-active="item.value === mode.modeType"
      :title="item.desc"
    >
      <input
        class="sr-only"
        type="radio"
        name="eatwhat-mode"
        :value="item.value"
        :checked="item.value === mode.modeType"
        @change="mode.setMode(item.value)"
      />
      <span class="switch-icon" aria-hidden="true">{{ item.icon }}</span>
      <!-- 一屏口径：只留模式名，副标题降级为 title / aria-label，整条压到 40px -->
      <span class="switch-text">
        <b>{{ item.label }}</b>
      </span>
    </label>
  </div>
</template>

<style scoped>
.mode-switch {
  position: relative;
  display: flex;
  width: 100%;
  /* 一屏口径：总高 40px（轨道 3 + 34 + 3） */
  padding: 3px;
  border-radius: 999px;
  /* 深色玻璃口径：轨道是"凹槽"，用极淡白 + 内描边，靠 thumb 的实底表达选中 */
  background: rgb(var(--rgb-white) / 0.06);
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-white) / 0.12);
}

/* 指示块宽度 = 一半，位移用百分比，切换时由 v-motion 做弹簧过渡 */
.switch-thumb {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc(50% - 3px);
  border-radius: 999px;
  background: var(--color-ink);
  box-shadow: 0 4px 14px rgb(var(--rgb-black) / 0.18);
}

.switch-item {
  position: relative;
  z-index: 1;
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  border-radius: 999px;
  padding: 0 6px;
  color: var(--color-text-soft);
  cursor: pointer;
  transition: color 0.22s ease;
}

.switch-item[data-active='true'] {
  color: var(--color-white);
}

.switch-icon {
  font-size: 14px;
  line-height: 1;
  filter: grayscale(1);
}

.switch-item[data-active='true'] .switch-icon {
  filter: none;
}

.switch-text {
  display: flex;
  align-items: baseline;
  gap: 5px;
  line-height: 1.15;
}

.switch-text b {
  font-size: 13px;
  font-weight: 650;
}


</style>
