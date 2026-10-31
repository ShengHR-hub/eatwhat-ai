<script setup>
/**
 * L0 全局底：Vue Bits Grainient（银灰三色，timeSpeed ≈ 0.2 接近静止）。
 * 只负责氛围、不承载信息、不接收指针事件；内容层对比度全靠 L2 实底保证。
 *
 * 颜色不写在模板里：shader 只吃 hex，统一从 src/utils/theme.js 读 CSS 变量。
 */
import { computed } from 'vue'
import Grainient from '../bits/Grainient.vue'
import { tokens } from '../../utils/theme'

const colors = computed(() => tokens())
</script>

<template>
  <div class="pointer-events-none fixed inset-0 z-0">
    <Grainient
      :color1="colors.grainA"
      :color2="colors.grainB"
      :color3="colors.grainC"
      :time-speed="0.2"
    />
    <div class="vignette" aria-hidden="true" />
  </div>
</template>

<style scoped>
/* 底部压暗，保证玻璃底栏上的白字可读（不改背景本身色值） */
.vignette {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 55%, rgb(var(--rgb-black) / 0.28) 100%);
}
</style>
