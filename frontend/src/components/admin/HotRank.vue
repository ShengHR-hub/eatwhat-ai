<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AdminEmpty from './AdminEmpty.vue'
import { exportElementPng } from './export'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  note: { type: String, default: 'eating_logs + room_votes；VETO 不计热门' },
})
const emit = defineEmits(['drill'])
const root = ref(null)
const offset = ref(0)
const paused = ref(false)
const exporting = ref(false)
const exportError = ref('')
let timer = null
const visibleItems = computed(() => {
  if (!props.items.length) return []
  return props.items.map((_, index) => {
    const sourceIndex = (index + offset.value) % props.items.length
    return { ...props.items[sourceIndex], rank: sourceIndex + 1 }
  })
})

watch(() => props.items, () => { offset.value = 0 })
timer = window.setInterval(() => {
  if (!paused.value && props.items.length > 1) offset.value = (offset.value + 1) % props.items.length
}, 2800)
onBeforeUnmount(() => window.clearInterval(timer))

async function exportPng() {
  exporting.value = true
  exportError.value = ''
  try {
    await exportElementPng(root.value, {
      title: '哪些菜品真正被反复选择？',
      note: props.note,
      filename: 'C08-热门菜品轮播榜',
    })
  } catch (error) {
    exportError.value = error?.message || 'PNG 导出失败'
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <section class="admin-chart-card admin-rank-card">
    <div class="admin-chart-actions admin-rank-actions">
      <button class="admin-button admin-button--small" type="button" @click="paused = !paused">{{ paused ? '继续轮播' : '暂停轮播' }}</button>
      <button class="admin-button admin-button--small" type="button" :disabled="!items.length || exporting" @click="exportPng">
        {{ exporting ? '导出中…' : '导出 PNG' }}
      </button>
    </div>
    <div ref="root" class="admin-rank-export">
      <header>
        <p class="admin-eyebrow">C08 · POPULARITY</p>
        <h2>哪些菜品真正被反复选择？</h2>
        <p>{{ note }}</p>
      </header>
      <div v-if="loading" class="admin-empty">正在聚合真实热度…</div>
      <AdminEmpty v-else-if="error" title="热度读取失败" :reason="error" />
      <AdminEmpty v-else-if="!items.length" reason="当前筛选没有被选日志或非 VETO 投票" />
      <ol v-else class="admin-rank-list">
        <li v-for="(item, index) in visibleItems" :key="item.dish_id">
          <button type="button" @click="emit('drill', item)">
            <span class="admin-rank-index">{{ String(item.rank).padStart(2, '0') }}</span>
            <span class="admin-rank-name">{{ item.dish_name }}</span>
            <strong>{{ item.value }}</strong>
            <span>次</span>
          </button>
        </li>
      </ol>
    </div>
    <p v-if="exportError" class="admin-inline-error" role="alert">{{ exportError }}</p>
  </section>
</template>
