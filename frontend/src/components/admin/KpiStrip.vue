<script setup>
import { computed, ref } from 'vue'
import NumberTicker from '../NumberTicker.vue'
import AdminEmpty from './AdminEmpty.vue'
import { exportElementPng } from './export'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  scope: { type: String, default: 'ALL' },
})
const root = ref(null)
const exporting = ref(false)
const exportError = ref('')
const items = computed(() => [
  { key: 'restaurants_total', label: '有效门店', unit: '家' },
  { key: 'dishes_total', label: '菜品 / 菜谱', unit: '道' },
  { key: 'feature_values_total', label: '有效特征值', unit: '个' },
  { key: 'logs_total', label: '饮食流水', unit: '条' },
  { key: 'votes_total', label: '真实投票', unit: '票' },
])

async function exportPng() {
  exporting.value = true
  exportError.value = ''
  try {
    await exportElementPng(root.value, {
      title: '当前数据底座有多大？',
      note: `overview 实时计数；范围 ${props.scope}；特征值=合法成功打标菜品×8`,
      filename: 'C01-数据概览数字带',
    })
  } catch (error) {
    exportError.value = error?.message || 'PNG 导出失败'
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <section class="admin-kpi-section">
    <div class="admin-section-heading">
      <div>
        <p class="admin-eyebrow">C01 · OVERVIEW</p>
        <h2>当前数据底座有多大？</h2>
        <p>口径：当前筛选实时计数；特征值只统计完整合法八维成功记录。</p>
      </div>
      <button class="admin-button admin-button--small" type="button" :disabled="loading || !!error || exporting" @click="exportPng">
        {{ exporting ? '导出中…' : '导出 PNG' }}
      </button>
    </div>
    <p v-if="exportError" class="admin-inline-error" role="alert">{{ exportError }}</p>
    <AdminEmpty v-if="error" title="概览读取失败" :reason="error" />
    <div v-else ref="root" class="admin-kpi-strip">
      <article v-for="item in items" :key="item.key" class="admin-kpi-card">
        <span>{{ item.label }}</span>
        <strong><NumberTicker :value="Number(data?.[item.key] || 0)" :decimals="0" /></strong>
        <small>{{ item.unit }} · {{ data?.meta?.scope || scope }}</small>
      </article>
    </div>
    <div v-if="data?.by_campus" class="admin-campus-summary">
      <span v-for="(row, campus) in data.by_campus" :key="campus">
        {{ campus }}：{{ row.restaurants }} 店 / {{ row.dishes }} 菜 / {{ row.logs }} 流水 / {{ row.votes }} 票
      </span>
    </div>
  </section>
</template>
