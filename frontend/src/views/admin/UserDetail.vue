<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AdminShell from '../../components/admin/AdminShell.vue'
import AdminEmpty from '../../components/admin/AdminEmpty.vue'
import DishRadar from '../../components/admin/DishRadar.vue'
import { fetchUserOverview } from '../../api/admin'
import { errorText } from '../../utils/errorText'

/**
 * 用户画像。
 * 后台此前只能看聚合统计（多少门店、多少流水），看不到「某个人喜欢什么」。
 * 这里把偏好向量、菜系分布、满意度、最近决策放在一页。
 */
const route = useRoute()
const router = useRouter()
const userId = computed(() => Number(route.params.id))
const body = ref(null)
const loading = ref(false)
const error = ref('')

const MODE_LABEL = { OUT_DINING: '外食', HOME_COOKING: '下厨' }
const RATING_EMOJI = { 3: '😋', 2: '😐', 1: '😞' }

const cuisineMax = computed(() => Math.max(1, ...(body.value?.cuisine_top || []).map((row) => row.count)))
const ratingTotal = computed(() => (body.value?.rating_dist || []).reduce((sum, row) => sum + row.count, 0))

function isImageAvatar(value) {
  return typeof value === 'string' && (value.startsWith('/uploads/') || value.startsWith('http'))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    body.value = await fetchUserOverview(userId.value)
  } catch (err) {
    error.value = errorText(err) || '用户画像读取失败'
    body.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AdminShell
    :title="body ? `${body.user.nickname} 的画像` : '用户画像'"
    subtitle="偏好向量 · 菜系分布 · 满意度 · 最近决策"
  >
    <template #actions>
      <button class="admin-button" type="button" @click="router.push('/admin/users')">返回用户列表</button>
    </template>

    <p v-if="loading" class="admin-empty">正在读取用户数据…</p>
    <p v-else-if="error" class="admin-form-error" role="alert">{{ error }}</p>

    <template v-else-if="body">
      <section class="up-head">
        <img v-if="isImageAvatar(body.user.avatar)" class="up-head__avatar up-head__avatar--img" :src="body.user.avatar" alt="">
        <span v-else class="up-head__avatar">{{ body.user.avatar || '🍚' }}</span>
        <div class="up-head__copy">
          <h2>{{ body.user.nickname }}</h2>
          <p>{{ body.user.username }} · {{ body.user.role === 'ADMIN' ? '管理员' : '普通用户' }}
            <template v-if="body.user.created_at"> · 注册于 {{ body.user.created_at.slice(0, 10) }}</template>
          </p>
        </div>
        <div class="up-head__chips">
          <span>预算 ¥{{ Number(body.preference.default_budget || 0).toFixed(0) }}</span>
          <span v-if="body.preference.veto_tags.length">忌口 {{ body.preference.veto_tags.slice(0, 3).join(' / ') }}</span>
          <span>红榜 {{ body.preference.favorite_count }}</span>
          <span>黑榜 {{ body.preference.blacklist_count }}</span>
        </div>
      </section>

      <section class="up-grid">
        <article class="up-card">
          <div class="up-card__head"><b>口味偏好</b><span>base_vector 0–1</span></div>
          <div class="up-radar">
            <DishRadar :vector="body.preference.base_vector" :index="99" />
          </div>
        </article>

        <article class="up-card">
          <div class="up-card__head"><b>数据概览</b><span>近 50 条流水</span></div>
          <div class="up-stats">
            <div><b>{{ body.summary.logs_total }}</b><span>饮食流水</span></div>
            <div><b>¥{{ body.summary.total_expense.toFixed(0) }}</b><span>累计花费</span></div>
            <div><b>¥{{ body.summary.avg_cost.toFixed(1) }}</b><span>单均价格</span></div>
            <div><b>{{ body.summary.avg_rating || '—' }}</b><span>平均评价</span></div>
          </div>
        </article>

        <article class="up-card">
          <div class="up-card__head"><b>常吃菜系</b><span>按流水条数</span></div>
          <div v-if="body.cuisine_top.length" class="up-bars">
            <div v-for="row in body.cuisine_top" :key="row.name" class="up-bar">
              <span class="up-bar__name">{{ row.name }}</span>
              <i><b :style="{ width: `${Math.round((row.count / cuisineMax) * 100)}%` }" /></i>
              <em>{{ row.count }}</em>
            </div>
          </div>
          <p v-else class="up-empty">还没有饮食流水</p>
        </article>

        <article class="up-card">
          <div class="up-card__head"><b>吃完之后的评价</b><span>共 {{ ratingTotal }} 条</span></div>
          <div v-if="ratingTotal" class="up-ratings">
            <div v-for="row in body.rating_dist" :key="row.rating" class="up-rating">
              <span>{{ RATING_EMOJI[row.rating] }} {{ row.label }}</span>
              <i><b :style="{ width: `${Math.round((row.count / ratingTotal) * 100)}%` }" /></i>
              <em>{{ row.count }}</em>
            </div>
          </div>
          <p v-else class="up-empty">还没有评价记录（评价在移动端「足迹」里提交）</p>
        </article>
      </section>

      <section class="up-card up-recent">
        <div class="up-card__head"><b>最近决策</b><span>最多 12 条</span></div>
        <div v-if="body.recent_logs.length" class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th style="width: 150px">时间</th><th>菜品</th><th style="width: 90px">模式</th><th style="width: 80px">花费</th><th style="width: 90px">评价</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in body.recent_logs" :key="row.log_id">
                <td><span class="audit-time">{{ row.eaten_at ? row.eaten_at.replace('T', ' ').slice(0, 16) : '—' }}</span></td>
                <td><strong>{{ row.dish_name }}</strong></td>
                <td>{{ MODE_LABEL[row.mode_type] || row.mode_type }}</td>
                <td>¥{{ Number(row.cost_amount || 0).toFixed(0) }}</td>
                <td>
                  <span v-if="row.rating">{{ RATING_EMOJI[row.rating] }} {{ ['', '踩雷', '一般', '好吃'][row.rating] }}</span>
                  <span v-else class="up-dim">未评价</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <AdminEmpty v-else reason="这个用户还没有饮食记录" />
      </section>
    </template>
  </AdminShell>
</template>

<style scoped>
.up-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
  padding: 14px 18px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.09);
  border-radius: 14px;
  background: var(--admin-surface);
}
.up-head__avatar {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  background: rgb(var(--rgb-admin-accent) / 0.1);
  color: var(--admin-accent);
  font-size: 22px;
  font-weight: 600;
  overflow: hidden;
}
.up-head__avatar--img { object-fit: cover; background: none; }
.up-head__copy h2 { margin: 0; color: var(--admin-ink); font-size: 17px; font-weight: 600; }
.up-head__copy p { margin: 2px 0 0; color: var(--admin-muted); font-size: 11px; }
.up-head__chips { display: flex; flex-wrap: wrap; gap: 6px; margin-left: auto; }
.up-head__chips span {
  padding: 2px 9px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.1);
  border-radius: 999px;
  color: var(--admin-muted);
  font-size: 10px;
}

.up-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.up-card {
  padding: 14px 16px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.09);
  border-radius: 14px;
  background: var(--admin-surface);
}
.up-card__head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.up-card__head b { color: var(--admin-ink); font-size: 12.5px; font-weight: 600; }
.up-card__head span { margin-left: auto; color: var(--admin-faint); font-size: 10px; }

.up-radar { display: grid; place-items: center; padding: 4px 0 8px; }

.up-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.up-stats div { display: flex; flex-direction: column; gap: 1px; }
.up-stats b { color: var(--admin-ink); font-size: 20px; font-weight: 650; font-variant-numeric: tabular-nums; }
.up-stats span { color: var(--admin-faint); font-size: 9.5px; }

.up-bars, .up-ratings { display: flex; flex-direction: column; gap: 7px; }
.up-bar, .up-rating { display: grid; grid-template-columns: 64px 1fr 34px; align-items: center; gap: 8px; }
.up-bar__name, .up-rating span { color: var(--admin-muted); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.up-bar i, .up-rating i { display: block; height: 6px; border-radius: 3px; background: rgb(var(--rgb-admin-ink) / 0.07); overflow: hidden; }
.up-bar i b { display: block; height: 100%; border-radius: 3px; background: var(--admin-accent); }
.up-rating i b { display: block; height: 100%; border-radius: 3px; background: var(--admin-ok); }
.up-bar em, .up-rating em { color: var(--admin-ink); font-size: 11px; font-style: normal; text-align: right; font-variant-numeric: tabular-nums; }

.up-empty, .up-dim { margin: 0; color: var(--admin-faint); font-size: 11px; }
.up-recent { margin-top: 12px; }
</style>
