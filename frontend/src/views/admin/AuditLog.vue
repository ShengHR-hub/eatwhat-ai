<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AdminShell from '../../components/admin/AdminShell.vue'
import AdminEmpty from '../../components/admin/AdminEmpty.vue'
import { fetchAuditLogs } from '../../api/admin'
import { errorText } from '../../utils/errorText'

/**
 * 审计日志（只读）。
 * 后端 GET /admin/audit-logs 只记写操作、不记查询：查询不改数据，逐条记录只会把表撑大。
 * 这里只做展示与过滤，不提供删除/编辑入口——审计记录本身不可被后台改写。
 */
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const limit = 50
const offset = ref(0)
const filters = reactive({ action: '', resource_type: '', user_id: '' })

const ACTION_LABELS = {
  'restaurant.create': '新建门店',
  'restaurant.update': '修改门店',
  'restaurant.delete': '删除门店',
  'dish.create': '新建菜品',
  'dish.update': '修改菜品',
  'dish.delete': '删除菜品',
  'dish.llm_tag': '模型打标',
}

const RESOURCE_LABELS = {
  restaurant: '门店',
  dish: '菜品',
}

const pages = computed(() => Math.max(1, Math.ceil(total.value / limit)))
const currentPage = computed(() => Math.floor(offset.value / limit) + 1)

function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

function resourceLabel(type) {
  return RESOURCE_LABELS[type] || type || '—'
}

function toneOf(action = '') {
  if (action.endsWith('.delete')) return 'bad'
  if (action.endsWith('.create')) return 'ok'
  if (action.endsWith('llm_tag')) return 'warn'
  return 'plain'
}

function detailText(detail) {
  if (!detail || typeof detail !== 'object') return ''
  const entries = Object.entries(detail)
  if (!entries.length) return ''
  return entries
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`)
    .join(' · ')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const body = await fetchAuditLogs({
      limit,
      offset: offset.value,
      action: filters.action,
      resource_type: filters.resource_type,
      user_id: filters.user_id,
    })
    rows.value = body.items || []
    total.value = body.total || 0
  } catch (err) {
    error.value = errorText(err) || '审计日志读取失败'
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  offset.value = 0
  load()
}

function resetFilters() {
  filters.action = ''
  filters.resource_type = ''
  filters.user_id = ''
  offset.value = 0
  load()
}

function changePage(next) {
  if (next < 1 || next > pages.value) return
  offset.value = (next - 1) * limit
  load()
}

onMounted(load)
</script>

<template>
  <AdminShell
    title="审计日志"
    :subtitle="`只记录写操作，共 ${total.toLocaleString()} 条 · 按时间倒序 · 不可在后台改写`"
  >
    <form class="admin-filter-bar" @submit.prevent="applyFilters">
      <label>
        <span>动作</span>
        <select v-model="filters.action">
          <option value="">全部动作</option>
          <option v-for="(label, key) in ACTION_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <label>
        <span>资源类型</span>
        <select v-model="filters.resource_type">
          <option value="">全部资源</option>
          <option value="restaurant">门店</option>
          <option value="dish">菜品</option>
        </select>
      </label>
      <label>
        <span>操作人 ID</span>
        <input v-model="filters.user_id" type="number" min="1" placeholder="留空为全部">
      </label>
      <div class="admin-filter-actions">
        <button class="admin-button admin-button--primary" type="submit">筛选</button>
        <button class="admin-button" type="button" @click="resetFilters">重置</button>
      </div>
    </form>

    <p v-if="error" class="admin-form-error" role="alert">{{ error }}</p>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-empty">正在读取审计日志…</div>
      <AdminEmpty
        v-else-if="!rows.length"
        reason="当前没有审计记录。后台只记录写操作（新建 / 修改 / 删除 / 打标），查询不记录。"
      />
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width: 150px">时间</th>
            <th style="width: 110px">操作人</th>
            <th style="width: 110px">动作</th>
            <th style="width: 120px">资源</th>
            <th>摘要</th>
            <th style="width: 130px">IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td><span class="audit-time">{{ row.created_at?.replace('T', ' ').slice(0, 19) || '—' }}</span></td>
            <td><strong>{{ row.operator }}</strong><small>#{{ row.user_id }}</small></td>
            <td><span class="admin-status" :data-status="toneOf(row.action)">{{ actionLabel(row.action) }}</span></td>
            <td>{{ resourceLabel(row.resource_type) }}<small>#{{ row.resource_id ?? '—' }}</small></td>
            <td>
              <span class="audit-summary">{{ row.summary || '—' }}</span>
              <small v-if="detailText(row.detail)" class="audit-detail">{{ detailText(row.detail) }}</small>
            </td>
            <td><span class="audit-time">{{ row.ip || '—' }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="admin-pagination">
      <span>共 {{ total.toLocaleString() }} 条 · 第 {{ currentPage }}/{{ pages }} 页</span>
      <div>
        <button class="admin-button" type="button" :disabled="offset === 0 || loading" @click="changePage(currentPage - 1)">上一页</button>
        <button class="admin-button" type="button" :disabled="currentPage >= pages || loading" @click="changePage(currentPage + 1)">下一页</button>
      </div>
    </footer>
  </AdminShell>
</template>
