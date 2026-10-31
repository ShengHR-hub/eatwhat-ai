<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AdminShell from '../../components/admin/AdminShell.vue'
import AdminEmpty from '../../components/admin/AdminEmpty.vue'
import AdminRecordForm from '../../components/admin/AdminRecordForm.vue'
import DishRadar from '../../components/admin/DishRadar.vue'
import { exportElementPng } from '../../components/admin/export'
import { errorText } from '../../utils/errorText'
import {
  createAdminDish,
  createAdminRestaurant,
  deleteAdminDish,
  deleteAdminRestaurant,
  fetchAdminDishes,
  fetchAdminRestaurants,
  fetchAdminStats,
  createTagJob,
  fetchTagJob,
  updateAdminDish,
  updateAdminRestaurant,
} from '../../api/admin'

// 后台浅色作用域：必须在 setup 同步阶段标记，否则首次 computed 取色时还拿不到作用域。
// 用 'admin' 而不是 'wall'——大屏是深色投屏，后台是浅色长读，两套图表令牌不能混。
if (typeof document !== 'undefined') document.documentElement.dataset.surface = 'admin'

const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab === 'restaurants' ? 'restaurants' : 'dishes')
// 三视图：看板 / 表格 / 质检（对齐 design/admin-v7）。默认质检，与设计稿一致。
const viewMode = ref(route.query.view === 'table' ? 'table' : route.query.view === 'board' ? 'board' : 'grid')
const exporting = ref(false)
const FEATURE_KEYS = ['spicy_level', 'oily_level', 'soup_level', 'temp_fit', 'satiety_level', 'prep_speed', 'social_fit', 'comfort_level']
// 缺维度要指名道姓（缺烫 / 缺油 烫），不能只说「缺 2 维」——设计稿就是这么标的
const FEATURE_LABELS = {
  spicy_level: '辣', oily_level: '油', soup_level: '汤', temp_fit: '温',
  satiety_level: '饱', prep_speed: '速', social_fit: '社', comfort_level: '抚',
}
const STATUS_TONE = { SUCCESS: 'ok', PENDING: 'warn', FAILED: 'bad' }
const filters = reactive({
  mode_type: route.query.mode_type || '', cuisine_type: route.query.cuisine_type || '',
  campus: route.query.campus || '', keyword: route.query.keyword || '',
  source_type: '', category: '', dish_role: '', tagging_status: '',
  dish_id: route.query.dish_id || '', restaurant_id: route.query.restaurant_id || '',
})
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const error = ref('')
const notice = ref('')
const quality = ref(null)
const qualityLoading = ref(false)
const qualityError = ref('')
const selected = ref(new Set())
const tagBusy = ref(false)
const tagResult = ref(null)
const editorOpen = ref(false)
const editorRecord = ref(null)
const saving = ref(false)
const saveError = ref('')
let listSequence = 0
const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const selectedIds = computed(() => [...selected.value])

async function loadQuality() {
  qualityLoading.value = true
  qualityError.value = ''
  try {
    quality.value = await fetchAdminStats('quality', {
      campus: filters.campus,
      mode_type: tab.value === 'dishes' ? filters.mode_type : '',
      cuisine_type: tab.value === 'dishes' ? filters.cuisine_type : '',
    })
  } catch (err) {
    qualityError.value = errorText(err)
  } finally {
    qualityLoading.value = false
  }
}

async function loadItems() {
  const sequence = ++listSequence
  loading.value = true
  error.value = ''
  try {
    const params = { ...filters, page: page.value, page_size: pageSize }
    // 「待补标签」不是 tagging_status 的取值，映射成后端独立参数 needs_tag
    if (params.tagging_status === '__needs_tag') {
      params.tagging_status = ''
      params.needs_tag = 1
    }
    // 热门榜/地图按稳定 ID 下钻时，历史软删除记录也必须能被查看；普通列表仍默认隐藏。
    if (filters.dish_id || filters.restaurant_id) params.include_deleted = true
    const data = tab.value === 'restaurants'
      ? await fetchAdminRestaurants(params)
      : await fetchAdminDishes(params)
    if (sequence !== listSequence) return
    items.value = data.items
    total.value = data.total
    selected.value = new Set()
    if (!data.items.length && page.value > 1 && data.total > 0) {
      page.value = Math.max(1, Math.ceil(data.total / pageSize))
      return loadItems()
    }
  } catch (err) {
    if (sequence === listSequence) error.value = errorText(err)
  } finally {
    if (sequence === listSequence) loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  notice.value = ''
  const query = { tab: tab.value }
  for (const key of ['campus', 'mode_type', 'cuisine_type', 'keyword', 'dish_id', 'restaurant_id']) {
    if (filters[key]) query[key] = filters[key]
  }
  router.replace({ query })
  loadItems()
  loadQuality()
}

function resetFilters() {
  Object.keys(filters).forEach((key) => { filters[key] = '' })
  applyFilters()
}

function switchTab(next) {
  tab.value = next
  filters.dish_id = ''
  filters.restaurant_id = ''
  // 门店没有 feature_vector / tagging_status，看板与质检只对菜品成立
  if (next === 'restaurants') viewMode.value = 'table'
  applyFilters()
}

/** 页面级导出：把当前视图整体截成 PNG，供论文与汇报使用 */
async function exportView() {
  const root = document.querySelector('.admin-main')
  if (!root) return
  exporting.value = true
  try {
    await exportElementPng(root, {
      title: '数据管理',
      note: `视图 ${viewMode.value} · 共 ${total.value} 条 · 打标覆盖 ${quality.value ? ((quality.value.tagging_coverage || 0) * 100).toFixed(1) : '—'}%`,
      filename: `数据管理-${viewMode.value}`,
    })
  } catch (err) {
    notice.value = err?.message || '导出失败'
  } finally {
    exporting.value = false
  }
}

function missingCount(field) {
  const row = (quality.value?.missing_fields || []).find((item) => item.field === field)
  return row ? row.count.toLocaleString() : '0'
}

function toneOf(status) {
  return STATUS_TONE[status] || 'plain'
}

/** 缺过敏原标签的卡片整条状态带换色，比只有一个小角标更显眼 */
function cardTone(item) {
  if (!item?.allergen_tags?.length) return 'tag'
  return toneOf(item.tagging_status)
}

function completeness(item) {
  const vector = item?.feature_vector || {}
  const missing = FEATURE_KEYS
    .filter((key) => !(typeof vector[key] === 'number' && Number.isFinite(vector[key])))
    .map((key) => FEATURE_LABELS[key])
  return missing.length ? `缺 ${missing.join(' ')}` : '8 维齐全'
}

function metaOf(item) {
  if (tab.value === 'restaurants') {
    return [item.campus || '未归属', item.category || '未标注'].join(' · ')
  }
  return [item.restaurant_name || '共享菜谱', item.cuisine_type || '未标注', item.campus || '未归属'].join(' · ')
}

function priceOf(item) {
  const value = tab.value === 'dishes' ? item.price_or_cost : item.avg_price
  return value == null ? '—' : `¥${Math.round(Number(value))}`
}

/** 看板三列：按打标状态分组（只统计当前页，避免为分组再打三次接口） */
const boardColumns = computed(() => [
  { key: 'PENDING', title: '待打标', tone: 'warn' },
  { key: 'SUCCESS', title: '已打标', tone: 'ok' },
  { key: 'FAILED', title: '打标失败', tone: 'bad' },
].map((column) => ({ ...column, items: items.value.filter((row) => row.tagging_status === column.key) })))

function changePage(next) {
  if (next < 1 || next > pages.value) return
  page.value = next
  loadItems()
}

function openCreate() {
  editorRecord.value = null
  saveError.value = ''
  editorOpen.value = true
}

function openEdit(record) {
  editorRecord.value = { ...record }
  saveError.value = ''
  editorOpen.value = true
}

async function saveRecord(payload) {
  saving.value = true
  saveError.value = ''
  try {
    if (tab.value === 'restaurants') {
      if (editorRecord.value) await updateAdminRestaurant(editorRecord.value.id, payload)
      else await createAdminRestaurant(payload)
    } else {
      if (editorRecord.value) await updateAdminDish(editorRecord.value.id, payload)
      else await createAdminDish(payload)
    }
    editorOpen.value = false
    notice.value = '已写入数据库，列表与质量面板已刷新'
    await Promise.all([loadItems(), loadQuality()])
  } catch (err) {
    saveError.value = errorText(err)
  } finally {
    saving.value = false
  }
}

async function removeRecord(record) {
  const target = tab.value === 'restaurants' ? '门店及其有效外食菜品下架' : '菜品软删除'
  if (!window.confirm(`确认将「${record.name}」${target}？历史流水与投票保留原 ID。`)) return
  error.value = ''
  notice.value = ''
  try {
    if (tab.value === 'restaurants') await deleteAdminRestaurant(record.id)
    else await deleteAdminDish(record.id)
    notice.value = '软删除已完成，历史关联未物理删除'
    await Promise.all([loadItems(), loadQuality()])
  } catch (err) {
    error.value = errorText(err)
  }
}

function toggleSelected(id) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function togglePage() {
  const ids = items.value.map((item) => item.id)
  const all = ids.length && ids.every((id) => selected.value.has(id))
  const next = new Set(selected.value)
  ids.forEach((id) => all ? next.delete(id) : next.add(id))
  selected.value = next
}

/**
 * 打标改为任务队列：接口立刻返回 job_id，后台线程逐批推进，
 * 前端每 2 秒轮询一次进度。同步等待几十秒的模型调用会撑爆请求超时。
 */
let jobTimer = null

async function runTagging() {
  if (!selectedIds.value.length || tagBusy.value) return
  tagBusy.value = true
  tagResult.value = null
  error.value = ''
  notice.value = ''
  try {
    const job = await createTagJob(selectedIds.value)
    tagResult.value = { status: job.status, total: job.total, done: job.done, failed: job.failed, message: job.message }
    notice.value = `已创建打标任务 #${job.id}（${job.total} 道），后台执行中`
    pollJob(job.id)
  } catch (err) {
    error.value = errorText(err)
    tagBusy.value = false
  }
}

function pollJob(jobId) {
  clearInterval(jobTimer)
  jobTimer = setInterval(async () => {
    try {
      const job = await fetchTagJob(jobId)
      tagResult.value = { status: job.status, total: job.total, done: job.done, failed: job.failed, message: job.message }
      if (job.status === 'DONE' || job.status === 'FAILED') {
        clearInterval(jobTimer)
        tagBusy.value = false
        notice.value = job.message || `任务 #${job.id} 已结束`
        await Promise.all([loadItems(), loadQuality()])
      }
    } catch (err) {
      // 以前是 catch {} 静默退出：轮询一失败，界面就永远停在最后一次快照，
      // 管理员以为任务还在跑。现在把原因写出来并停掉轮询。
      clearInterval(jobTimer)
      jobTimer = null
      tagBusy.value = false
      error.value = `任务进度查询失败：${errorText(err)}`
    }
  }, 2000)
}

onMounted(() => {
  loadItems()
  loadQuality()
})

// 离开后台后轮询必须停：否则继续每 2 秒请求，并往已卸载的组件里写状态。
onBeforeUnmount(() => {
  if (jobTimer) {
    clearInterval(jobTimer)
    jobTimer = null
  }
})

</script>

<template>
  <AdminShell title="数据管理" :subtitle="`${total.toLocaleString()} 条记录 · ${quality ? ((quality.tagging_coverage || 0) * 100).toFixed(1) : '—'}% 打标覆盖 · 真实 CRUD 与软删除`">
    <template #search>
      <input v-model="filters.keyword" placeholder="搜索菜品名、门店名或 ID" @keyup.enter="applyFilters" />
    </template>
    <template #actions>
      <div class="admin-viewswitch" role="group" aria-label="视图切换">
        <button type="button" :class="{ 'is-on': viewMode === 'board' }" :disabled="tab === 'restaurants'" @click="viewMode = 'board'">看板</button>
        <button type="button" :class="{ 'is-on': viewMode === 'table' }" @click="viewMode = 'table'">表格</button>
        <button type="button" :class="{ 'is-on': viewMode === 'grid' }" :disabled="tab === 'restaurants'" @click="viewMode = 'grid'">质检</button>
      </div>
      <button class="admin-button" type="button" :disabled="exporting || loading" @click="exportView">
        {{ exporting ? '导出中…' : '导出' }}
      </button>
      <button class="admin-button admin-button--primary" type="button" @click="openCreate">新增{{ tab === 'dishes' ? '菜品' : '门店' }}</button>
    </template>
    <!-- 质量统计：只列真正影响算法的指标。缺图片不算缺陷（菜品图不是必需资产），不在这里出现。 -->
    <section class="admin-qstats">
      <div class="admin-qstats__item"><span>在库菜品</span><b>{{ (quality?.total_dishes || 0).toLocaleString() }}</b></div>
      <div class="admin-qstats__item"><span>八维齐全</span><b>{{ (quality?.tagged_dishes || 0).toLocaleString() }}</b></div>
      <div class="admin-qstats__item"><span>向量异常</span><b :class="{ 'is-bad': (quality?.vector_anomalies?.total || 0) > 0 }">{{ quality?.vector_anomalies?.total ?? '—' }}</b></div>
      <div class="admin-qstats__item"><span>缺过敏原标签</span><b>{{ missingCount('allergen_tags') }}</b></div>
      <p class="admin-qstats__note">打标已全部完成；质检重点是向量完整性与标签覆盖，缺图不影响推荐与统计。</p>
    </section>

    <section class="admin-data-section">
      <div class="admin-data-toolbar">
        <div class="admin-tabs" role="tablist">
          <button type="button" :class="{ 'is-active': tab === 'dishes' }" @click="switchTab('dishes')">菜品 / 菜谱</button>
          <button type="button" :class="{ 'is-active': tab === 'restaurants' }" @click="switchTab('restaurants')">门店 / 食堂</button>
        </div>
      </div>

      <form class="admin-filter-bar" @submit.prevent="applyFilters">
        <label><span>关键词</span><input v-model="filters.keyword" placeholder="名称包含"></label>
        <label><span>校区</span><select v-model="filters.campus"><option value="">全部 / 含共享</option><option value="SIYUAN">思源</option><option value="JIANDA_YANTA">建大雁塔</option><option value="SHARED" v-if="tab === 'dishes'">仅共享下厨</option></select></label>
        <template v-if="tab === 'dishes'">
          <label><span>模式</span><select v-model="filters.mode_type"><option value="">全部</option><option value="OUT_DINING">外食</option><option value="HOME_COOKING">下厨</option></select></label>
          <label><span>菜系</span><input v-model="filters.cuisine_type" placeholder="精确匹配"></label>
          <label><span>角色</span><select v-model="filters.dish_role"><option value="">全部</option><option value="MEAT">荤菜</option><option value="VEG">素菜</option><option value="SOUP">汤</option><option value="ONE_MEAL">一餐</option></select></label>
          <label><span>标签状态</span><select v-model="filters.tagging_status"><option value="">全部</option><option value="__needs_tag">待补标签（缺过敏原）</option><option value="PENDING">待打标</option><option value="SUCCESS">成功</option><option value="FAILED">失败</option></select></label>
        </template>
        <template v-else>
          <label><span>来源</span><select v-model="filters.source_type"><option value="">全部</option><option value="AMAP_POI">AMAP_POI</option><option value="CANTEEN">CANTEEN</option></select></label>
          <label><span>分类</span><input v-model="filters.category" placeholder="精确匹配"></label>
        </template>
        <label v-if="filters.dish_id"><span>菜品下钻 ID</span><input v-model="filters.dish_id" type="number" min="1"></label>
        <label v-if="filters.restaurant_id"><span>门店下钻 ID</span><input v-model="filters.restaurant_id" type="number" min="1"></label>
        <div class="admin-filter-actions"><button class="admin-button admin-button--primary" type="submit">筛选</button><button class="admin-button" type="button" @click="resetFilters">重置</button></div>
      </form>

      <div v-if="tab === 'dishes'" class="admin-tag-toolbar">
        <span>已选 {{ selectedIds.length }} 道（每批最多 20）</span>
        <button class="admin-button" type="button" :disabled="!selectedIds.length || selectedIds.length > 20 || tagBusy" @click="runTagging">
          {{ tagBusy ? '正在等待真实模型响应…' : '调用国产模型打标' }}
        </button>
        <span v-if="selectedIds.length > 20" class="admin-inline-error">请减少至 20 道</span>
      </div>
      <p v-if="notice" class="admin-notice" role="status">{{ notice }}</p>
      <p v-if="error" class="admin-form-error" role="alert">{{ error }}</p>
      <div v-if="tagResult" class="admin-tag-result">
        <strong>打标任务 {{ tagResult.status }}</strong>
        <span>{{ tagResult.done }} / {{ tagResult.total }} 道完成<template v-if="tagResult.failed"> · 失败 {{ tagResult.failed }}</template></span>
        <span v-if="tagResult.message">{{ tagResult.message }}</span>
      </div>

      <div v-if="viewMode === 'table'" class="admin-table-wrap">
        <div v-if="loading" class="admin-empty">正在读取数据库…</div>
        <AdminEmpty v-else-if="!items.length" reason="当前筛选没有记录；可重置筛选或新增真实记录" />
        <table v-else class="admin-table">
          <thead>
            <tr v-if="tab === 'dishes'"><th><input type="checkbox" aria-label="选择本页" @change="togglePage"></th><th>ID / 名称</th><th>模式 / 校区</th><th>菜系 / 角色</th><th>价格</th><th>打标</th><th>操作</th></tr>
            <tr v-else><th>ID / 名称</th><th>校区 / 来源</th><th>分类</th><th>均价 / 评分</th><th>GCJ-02</th><th>合成</th><th>操作</th></tr>
          </thead>
          <tbody v-if="tab === 'dishes'">
            <tr v-for="row in items" :key="row.id">
              <td><input type="checkbox" :checked="selected.has(row.id)" :aria-label="`选择 ${row.name}`" @change="toggleSelected(row.id)"></td>
              <td><strong>#{{ row.id }} {{ row.name }}</strong><small>{{ row.restaurant_name || '共享菜谱' }}</small></td>
              <td>{{ row.mode_type }}<small>{{ row.campus }}</small></td>
              <td>{{ row.cuisine_type || '未标注' }}<small>{{ row.dish_role }}</small></td>
              <td>{{ row.price_or_cost ?? 'NULL' }}</td>
              <td><span class="admin-status" :data-status="row.tagging_status">{{ row.tagging_status }}</span><small v-if="row.tagging_error">{{ row.tagging_error }}</small></td>
              <td><div class="admin-row-actions"><button type="button" @click="openEdit(row)">编辑</button><button type="button" @click="removeRecord(row)">软删除</button></div></td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr v-for="row in items" :key="row.id">
              <td><strong>#{{ row.id }} {{ row.name }}</strong><small>{{ row.address || '无地址' }}</small></td>
              <td>{{ row.campus || '未归属' }}<small>{{ row.source_type }}</small></td>
              <td>{{ row.category || '未标注' }}</td>
              <td>{{ row.avg_price ?? 'NULL' }} / {{ row.rating ?? 'NULL' }}</td>
              <td>{{ row.longitude ?? 'NULL' }}, {{ row.latitude ?? 'NULL' }}</td>
              <td>{{ row.is_synthetic === null ? '未知' : row.is_synthetic ? '合成' : '真实' }}</td>
              <td><div class="admin-row-actions"><button type="button" @click="openEdit(row)">编辑</button><button type="button" @click="removeRecord(row)">下架</button></div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="viewMode === 'grid'" class="admin-qgrid">
        <article
          v-for="(item, index) in items"
          :key="item.id"
          class="qcard"
          :data-tone="cardTone(item)"
        >
          <div class="qcard__bar">
            <span class="qcard__dot" />
            {{ item.tagging_status }}
            <span class="qcard__flag">{{ completeness(item) }}</span>
            <span v-if="!item.allergen_tags?.length" class="qcard__badge">缺标签</span>
          </div>
          <div class="qcard__viz">
            <DishRadar :vector="item.feature_vector" :index="index" />
          </div>
          <div class="qcard__body">
            <h3 class="qcard__name">{{ item.name }}</h3>
            <p class="qcard__meta">{{ metaOf(item) }}</p>
            <div class="qcard__row">
              <span class="qcard__price">{{ priceOf(item) }}</span>
              <span class="qcard__ops">
                <button type="button" @click="openEdit(item)">编辑</button>
                <button type="button" class="is-danger" @click="removeRecord(item)">删除</button>
              </span>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="admin-board">
        <div v-for="column in boardColumns" :key="column.key" class="admin-board__col">
          <header class="admin-board__head">
            <span class="admin-board__dot" :data-tone="column.tone" />
            <b>{{ column.title }}</b>
            <span class="admin-board__count">{{ column.items.length }}</span>
          </header>
          <div class="admin-board__body">
            <article v-for="item in column.items" :key="item.id" class="kcard">
              <div class="kcard__name">{{ item.name }}</div>
              <div class="kcard__meta">{{ metaOf(item) }}</div>
              <div class="kcard__foot">
                <span class="kcard__price">{{ priceOf(item) }}</span>
                <span class="kcard__tag">{{ completeness(item) }}</span>
              </div>
            </article>
            <p v-if="!column.items.length" class="admin-board__empty">本页没有{{ column.title }}记录</p>
          </div>
        </div>
      </div>

      <footer class="admin-pagination"><span>共 {{ total }} 条 · 第 {{ page }}/{{ pages }} 页</span><div><button class="admin-button" type="button" :disabled="page <= 1 || loading" @click="changePage(page - 1)">上一页</button><button class="admin-button" type="button" :disabled="page >= pages || loading" @click="changePage(page + 1)">下一页</button></div></footer>
    </section>

    <AdminRecordForm v-if="editorOpen" :kind="tab === 'dishes' ? 'dish' : 'restaurant'" :record="editorRecord" :saving="saving" :error="saveError" @save="saveRecord" @cancel="editorOpen = false" />
  </AdminShell>
</template>
