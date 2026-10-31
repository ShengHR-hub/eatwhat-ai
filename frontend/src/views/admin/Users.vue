<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AdminShell from '../../components/admin/AdminShell.vue'
import AdminEmpty from '../../components/admin/AdminEmpty.vue'
import { useRouter } from 'vue-router'
import { fetchAdminUsers, updateUserRole } from '../../api/admin'
import { errorText } from '../../utils/errorText'

/**
 * 用户管理。
 * 移动端注册写的是同一张 users 表，这里把「谁注册了、各自多少数据」显性化；
 * 角色切换走后端 PATCH，前端不做本地伪造。
 */
const router = useRouter()
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const saving = ref(0)
const pageSize = 20
const page = ref(1)
const filters = reactive({ keyword: '', role: '' })

const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const body = await fetchAdminUsers({ ...filters, page: page.value, page_size: pageSize })
    rows.value = body.items || []
    total.value = body.total || 0
  } catch (err) {
    error.value = errorText(err) || '用户列表读取失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.keyword = ''
  filters.role = ''
  page.value = 1
  load()
}

function changePage(next) {
  if (next < 1 || next > pages.value) return
  page.value = next
  load()
}

async function toggleRole(row) {
  const next = row.role === 'ADMIN' ? 'USER' : 'ADMIN'
  const label = next === 'ADMIN' ? '管理员' : '普通用户'
  if (!window.confirm(`把「${row.nickname}」改为${label}？`)) return
  saving.value = row.user_id
  notice.value = ''
  try {
    await updateUserRole(row.user_id, next)
    row.role = next
    notice.value = `${row.nickname} 已改为${label}`
  } catch (err) {
    error.value = errorText(err) || '角色修改失败'
  } finally {
    saving.value = 0
  }
}

onMounted(load)
</script>

<template>
  <AdminShell title="用户管理" :subtitle="`共 ${total.toLocaleString()} 个账号 · 移动端注册与演示身份共用一张 users 表`">
    <form class="admin-filter-bar" @submit.prevent="applyFilters">
      <label>
        <span>关键词</span>
        <input v-model="filters.keyword" placeholder="昵称或用户名">
      </label>
      <label>
        <span>角色</span>
        <select v-model="filters.role">
          <option value="">全部角色</option>
          <option value="ADMIN">管理员</option>
          <option value="USER">普通用户</option>
        </select>
      </label>
      <div class="admin-filter-actions">
        <button class="admin-button admin-button--primary" type="submit">筛选</button>
        <button class="admin-button" type="button" @click="resetFilters">重置</button>
      </div>
    </form>

    <p v-if="notice" class="admin-notice" role="status">{{ notice }}</p>
    <p v-if="error" class="admin-form-error" role="alert">{{ error }}</p>

    <div class="admin-table-wrap">
      <div v-if="loading" class="admin-empty">正在读取用户…</div>
      <AdminEmpty v-else-if="!rows.length" reason="当前筛选没有账号" />
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th style="width: 60px">ID</th>
            <th>昵称 / 用户名</th>
            <th style="width: 110px">角色</th>
            <th style="width: 90px">饮食流水</th>
            <th style="width: 90px">房间投票</th>
            <th style="width: 150px">注册时间</th>
            <th style="width: 170px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.user_id">
            <td><span class="cell-id">#{{ row.user_id }}</span></td>
            <td>
              <strong>{{ row.nickname }}</strong>
              <small>{{ row.username }}<template v-if="row.is_demo_persona"> · 演示人设</template></small>
            </td>
            <td>
              <span class="admin-status" :data-status="row.role === 'ADMIN' ? 'SUCCESS' : 'PENDING'">
                {{ row.role === 'ADMIN' ? '管理员' : '普通用户' }}
              </span>
            </td>
            <td>{{ row.logs }}</td>
            <td>{{ row.votes }}</td>
            <td><span class="audit-time">{{ row.created_at ? row.created_at.replace('T', ' ').slice(0, 16) : '—' }}</span></td>
            <td>
              <div class="user-ops">
                <button class="admin-button admin-button--small" type="button" @click="router.push(`/admin/users/${row.user_id}`)">画像</button>
                <button class="admin-button admin-button--small" type="button" :disabled="saving === row.user_id" @click="toggleRole(row)">
                  {{ saving === row.user_id ? '处理中…' : row.role === 'ADMIN' ? '降为普通' : '设为管理员' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="admin-pagination">
      <span>共 {{ total.toLocaleString() }} 个账号 · 第 {{ page }}/{{ pages }} 页</span>
      <div>
        <button class="admin-button" type="button" :disabled="page <= 1 || loading" @click="changePage(page - 1)">上一页</button>
        <button class="admin-button" type="button" :disabled="page >= pages || loading" @click="changePage(page + 1)">下一页</button>
      </div>
    </footer>
  </AdminShell>
</template>