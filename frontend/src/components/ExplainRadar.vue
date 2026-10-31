<script setup>
/**
 * 五维雷达图（口味 / 天气 / 预算 / 新鲜度 / 状态），对应后端 radar_5d。
 * 数据口径：五轴各自 0–100 的分项分，与总分封顶 100 无关（用户已裁决）。
 * 配色只取 src/utils/theme.js → CSS 变量，禁止在这里出现 hex。
 */
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import { RADAR_AXES } from '../constants/bubbles'
import { alpha, radarPalette } from '../utils/theme'

use([RadarChart, TooltipComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Object, default: null },
  height: { type: Number, default: 210 },
  showLabels: { type: Boolean, default: true },
})

const palette = computed(() => radarPalette())

const option = computed(() => {
  const values = RADAR_AXES.map((axis) => Number(props.data?.[axis.key] ?? 0))
  const p = palette.value
  return {
    animationDuration: 520,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'item',
      backgroundColor: p.line,
      borderWidth: 0,
      textStyle: { color: 'var(--color-white)', fontSize: 11 },
      formatter: () =>
        RADAR_AXES.map((axis, i) => `${axis.name} ${values[i].toFixed(1)}`).join('<br/>'),
    },
    radar: {
      radius: props.showLabels ? '64%' : '72%',
      center: ['50%', '52%'],
      splitNumber: 4,
      axisName: {
        show: props.showLabels,
        color: p.label,
        fontSize: 10.5,
      },
      axisLine: { lineStyle: { color: p.splitLine, width: 1 } },
      splitLine: { lineStyle: { color: p.splitLine, width: 1 } },
      splitArea: { show: false },
      indicator: RADAR_AXES.map((axis) => ({ name: axis.name, max: 100, min: 0 })),
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: p.line, width: 1.6 },
        itemStyle: { color: p.line },
        areaStyle: { color: alpha(p.area, p.areaOpacity) },
        data: [{ value: values, name: '五维得分' }],
      },
    ],
  }
})
</script>

<template>
  <div class="radar-wrap" :style="{ height: `${height}px` }">
    <VChart v-if="data" class="radar" :option="option" autoresize />
    <p v-else class="radar-empty">暂无雷达数据</p>
  </div>
</template>

<style scoped>
.radar-wrap {
  position: relative;
  width: 100%;
}

.radar {
  width: 100%;
  height: 100%;
}

.radar-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  font-size: 12px;
  color: var(--color-text-soft);
}
</style>
