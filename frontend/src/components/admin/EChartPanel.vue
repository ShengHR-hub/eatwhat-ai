<script setup>
import { ref } from 'vue'
import VChart from 'vue-echarts'
import 'echarts'
import 'echarts-wordcloud'
import { chartTokens } from '../../utils/theme'
import { downloadDataUrl } from './export'
import AdminEmpty from './AdminEmpty.vue'

const props = defineProps({
  option: { type: Object, default: null },
  title: { type: String, required: true },
  note: { type: String, default: '' },
  filename: { type: String, default: 'eatwhat-chart' },
  empty: { type: Boolean, default: false },
  emptyReason: { type: String, default: '当前筛选没有可展示的数据' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  height: { type: String, default: '360px' },
  /** 大屏用：不自带卡片外壳，卡片外观由外层 .wall-card 提供 */
  bare: { type: Boolean, default: false },
})

const emit = defineEmits(['drill'])
const chartRef = ref(null)
const exporting = ref(false)
const exportError = ref('')

async function exportPng() {
  exporting.value = true
  exportError.value = ''
  try {
    const chart = chartRef.value?.chart
    if (!chart) throw new Error('图表尚未完成渲染')
    const dataUrl = chart.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: chartTokens().ink,
    })
    downloadDataUrl(dataUrl, props.filename)
  } catch (error) {
    exportError.value = error?.message || 'PNG 导出失败'
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <section :class="bare ? 'wall-chart' : 'admin-chart-card'" :style="{ '--admin-chart-height': height }">
    <div :class="bare ? 'wall-chart__actions' : 'admin-chart-actions'">
      <button
        class="admin-button admin-button--small"
        type="button"
        :disabled="empty || loading || !!error || exporting"
        @click="exportPng"
      >{{ exporting ? '导出中…' : '导出 PNG' }}</button>
    </div>
    <p v-if="exportError" class="admin-inline-error" role="alert">{{ exportError }}</p>
    <div v-if="loading" class="admin-empty" role="status">正在读取真实统计数据…</div>
    <AdminEmpty v-else-if="error" title="统计接口读取失败" :reason="error" />
    <AdminEmpty v-else-if="empty" :reason="emptyReason" />
    <VChart
      v-else-if="option"
      ref="chartRef"
      class="admin-chart"
      :option="option"
      autoresize
      @click="emit('drill', $event)"
    />
    <AdminEmpty v-else reason="图表配置尚未生成" />
  </section>
</template>
