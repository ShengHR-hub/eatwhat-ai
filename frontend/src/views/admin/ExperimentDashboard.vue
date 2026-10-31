<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AdminShell from '../../components/admin/AdminShell.vue'
import EChartPanel from '../../components/admin/EChartPanel.vue'
import PoiScatter from '../../components/admin/PoiScatter.vue'
import {
  cooccurrenceOption,
  cuisineOption,
  experimentBarsOption,
  personasOption,
  repeatCurveOption,
  repeatDistributionOption,
  scatterOption,
  trendOption,
} from '../../components/admin/dashboardOptions'
import { ADMIN_STATS_PATHS, fetchAdminExperiments, fetchAdminStats, fetchSimulationRun, fetchSimulationRuns } from '../../api/admin'
import { alpha, chartTokens } from '../../utils/theme'

/*
 * 数据大屏 v8（冷色三屏）
 * 设计稿：design/admin-v7/dashboard-v8.html
 *
 * 与旧版差异只在「外壳」：数据仍走同一组 13 个 stats 接口 + G3 实验 JSON，
 * 图表仍由 dashboardOptions 生成，只把 17 项按 总览 / 数据质量 / 算法实验 拆三屏，
 * 色值经 chartTokens() 切到 --wall-* 冷色组（见 src/utils/theme.js）。
 */
if (typeof document !== 'undefined') {
  document.documentElement.dataset.surface = 'admin'
}

const router = useRouter()
const filters = reactive({ campus: 'ALL', mode_type: '', cuisine_type: '' })
const responses = reactive({})
const errors = reactive({})
const loading = ref(false)
const cuisineList = ref([])
const activeTopic = ref('overview')
const clock = ref('')
const hovering = ref(false)
const simRun = ref(null)
const simDetail = ref(null)
const personaScope = ref('demo')
const personaLoading = ref(false)
let sequence = 0
let clockTimer = null

// 左侧抽屉主题：每个主题聚焦一件事，不再靠 12s 轮播串场
const topics = [
  { key: 'overview', label: '数据概览', hint: '底座规模 · 空间分布 · 构成' },
  { key: 'quality', label: '数据质量', hint: '打标覆盖 · 缺口 · 关系' },
  { key: 'experiment', label: '算法实验', hint: 'G3 对照 · 人设 · 趋势' },
]

const data = (path) => responses[path] || null
const error = (path) => errors[path] || ''
const reason = (path, fallback) => data(path)?.reason || data(path)?.meta?.reason || fallback
const has = (path, key) => Boolean(data(path)?.[key]?.length)
const percent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`
const num = (value) => Number(value || 0).toLocaleString('zh-CN')

async function loadDashboard() {
  const current = ++sequence
  loading.value = true
  Object.keys(errors).forEach((key) => delete errors[key])
  const requests = [
    ...ADMIN_STATS_PATHS.map((path) => ({ key: path, promise: fetchAdminStats(path, path === 'personas' ? { ...filters, scope: personaScope.value } : filters) })),
    { key: 'experiments', promise: fetchAdminExperiments(filters) },
    { key: 'simulation', promise: fetchSimulationRuns() },
  ]
  const settled = await Promise.allSettled(requests.map((item) => item.promise))
  if (current !== sequence) return
  settled.forEach((result, index) => {
    const key = requests[index].key
    if (result.status === 'fulfilled') responses[key] = result.value
    else errors[key] = result.reason?.detail || result.reason?.message || '接口读取失败'
  })

  simRun.value = responses.simulation?.items?.[0] || null
  simDetail.value = null
  if (current === sequence && simRun.value) {
    try {
      simDetail.value = await fetchSimulationRun(simRun.value.id)
    } catch (err) {
      errors.simulationDetail = err?.detail || err?.message || '仿真指标读取失败'
    }
  }
  if (current !== sequence) return
  loading.value = false
}

/* ── 大屏化：去掉图内标题、压紧留白、抬字号 ───────────────── */
function wallize(option) {
  if (!option) return option
  const next = { ...option }
  if (next.title) next.title = { ...next.title, show: false }
  if (next.grid) next.grid = { ...next.grid, top: 14, left: 6, right: 10, bottom: 6, containLabel: true }
  if (next.calendar) next.calendar = { ...next.calendar, top: 8, bottom: 46, left: 34, right: 12, cellSize: ['auto', 16] }
  if (Array.isArray(next.series) && next.series[0]?.type === 'sankey') {
    next.series = next.series.map((item) => ({ ...item, top: 6, left: 6, right: 6, bottom: 6 }))
  }
  if (Array.isArray(next.series) && next.series[0]?.type === 'pie') {
    next.series = next.series.map((item) => ({ ...item, center: ['50%', '48%'], radius: ['38%', '62%'] }))
    if (next.legend) next.legend = { ...next.legend, bottom: 0, left: 'center', itemWidth: 8, itemHeight: 8, textStyle: { ...(next.legend.textStyle || {}), fontSize: 11 } }
  } else if (next.legend && !next.radar) {
    next.legend = { ...next.legend, top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { ...(next.legend.textStyle || {}), fontSize: 11 } }
  }
  if (next.xAxis && !Array.isArray(next.xAxis)) {
    next.xAxis = {
      ...next.xAxis,
      axisLabel: { ...(next.xAxis.axisLabel || {}), fontSize: 11, hideOverlap: true },
    }
  }
  if (next.yAxis && !Array.isArray(next.yAxis)) {
    next.yAxis = {
      ...next.yAxis,
      axisLabel: { ...(next.yAxis.axisLabel || {}), fontSize: 11, hideOverlap: true },
    }
  }
  if (next.radar) {
    next.radar = {
      ...next.radar,
      center: ['50%', '52%'],
      radius: '64%',
      axisName: { ...(next.radar.axisName || {}), fontSize: 11 },
    }
  }
  if (next.visualMap && !Array.isArray(next.visualMap)) {
    next.visualMap = { ...next.visualMap, textStyle: { ...(next.visualMap.textStyle || {}), fontSize: 10 } }
  }
  // 词云在小卡片里默认会叠字；共现图节点标签也会糊成一团
  if (Array.isArray(next.series)) {
    next.series = next.series.map((item) => {
      if (item.type === 'wordCloud') {
        return { ...item, gridSize: 8, sizeRange: [11, 26], rotationRange: [0, 0] }
      }
      if (item.type === 'graph') {
        return {
          ...item,
          repulsion: 260,
          label: { ...(item.label || {}), fontSize: 9, show: true },
          lineStyle: { ...(item.lineStyle || {}), opacity: 0.35 },
        }
      }
      return item
    })
  }
  next.textStyle = { ...(next.textStyle || {}), fontSize: 12 }
  return next
}

/* ── 数据 ─────────────────────────────────────────────────── */
const overview = computed(() => data('overview'))
const quality = computed(() => data('quality'))
const experiments = computed(() => data('experiments'))

const kpiCards = computed(() => {
  const o = overview.value || {}
  const q = quality.value || {}
  return [
    { key: 'restaurants', label: '有效门店', value: num(o.restaurants_total), unit: '家', foot: `思源 ${num(o.by_campus?.SIYUAN?.restaurants)} · 建大 ${num(o.by_campus?.JIANDA_YANTA?.restaurants)}`, hero: false },
    { key: 'dishes', label: '菜品与菜谱', value: num(o.dishes_total), unit: '道', foot: `共享下厨 ${num(o.by_campus?.SHARED?.dishes)}`, hero: false },
    { key: 'feature', label: '有效特征值', value: num(o.feature_values_total), unit: '个', foot: '合法八维成功记录 × 8', hero: false },
    { key: 'logs', label: '饮食流水', value: num(o.logs_total), unit: '条', foot: '当前筛选真实流水', hero: true },
    { key: 'votes', label: '真实投票', value: num(o.votes_total), unit: '票', foot: `房间 ${num(o.rooms_total)} 个`, hero: false },
    { key: 'coverage', label: '打标覆盖率', value: q.tagging_coverage === undefined ? '—' : (Number(q.tagging_coverage) * 100).toFixed(1), unit: '%', foot: `${num(q.tagged_dishes)} / ${num(q.total_dishes)} 道`, hero: false },
  ]
})

const campusBars = computed(() => {
  const campus = overview.value?.by_campus || {}
  const rows = [
    { name: '思源', value: campus.SIYUAN?.restaurants || 0 },
    { name: '建大雁塔', value: campus.JIANDA_YANTA?.restaurants || 0 },
    { name: '合成食堂', value: 400 },
  ]
  const max = Math.max(1, ...rows.map((row) => row.value))
  return rows.map((row) => ({ ...row, width: Math.round((row.value / max) * 100) }))
})

const hotList = computed(() => {
  const rows = data('race')?.latest_top10 || []
  if (!rows.length) return []
  const max = Math.max(1, ...rows.map((row) => Number(row.value || 0)))
  return rows.slice(0, 8).map((row, index) => ({
    ...row,
    no: String(index + 1).padStart(2, '0'),
    width: Math.round((Number(row.value || 0) / max) * 100),
  }))
})

const cuisineBars = computed(() => {
  const rows = data('cuisine')?.items || []
  if (!rows.length) return []
  const top = rows.slice(0, 4)
  const max = Math.max(1, ...top.map((row) => row.count))
  return top.map((row) => ({ ...row, width: Math.round((row.count / max) * 100) }))
})

const coverage = computed(() => {
  const q = quality.value
  if (!q) return null
  return {
    percent: Number(q.tagging_coverage || 0) * 100,
    tagged: q.tagged_dishes || 0,
    total: q.total_dishes || 0,
    pending: Math.max(0, (q.total_dishes || 0) - (q.tagged_dishes || 0)),
    anomalies: q.vector_anomalies?.total || 0,
  }
})

const todoList = computed(() => {
  const q = quality.value
  if (!q) return []
  // 缺图片不是缺陷（菜品图不是必需资产），不列进缺口
  const rows = (q.missing_fields || [])
    .filter((item) => item.field !== 'image_url')
    .map((item) => ({
      label: `缺 ${item.field}`,
      value: item.count,
      tone: item.count > 500 ? 'is-warn' : '',
    }))
  rows.push({
    label: '向量异常',
    value: q.vector_anomalies?.total || 0,
    tone: (q.vector_anomalies?.total || 0) > 0 ? 'is-bad' : 'is-ok',
  })
  return rows
})

/* ── 图表 ─────────────────────────────────────────────────── */
/**
 * 词云按设计稿用 HTML 文字云渲染，不用 ECharts wordCloud：
 * 后者在 ~600×250 的卡片里布局失败，文字互相压住（试过 gridSize 3/7/8/10 与多档 sizeRange）。
 */
const cloudWords = computed(() => {
  const words = data('keywords')?.words || []
  if (!words.length) return []
  return words.slice(0, 36).map((word, index) => ({
    name: word.name,
    value: word.value,
    tier: index < 2 ? 1 : index < 6 ? 2 : index < 14 ? 3 : 4,
  }))
})

const cuisineChart = computed(() => wallize(cuisineOption(data('cuisine'), '真实菜品库由哪些菜系构成', cuisineNote.value)))

/**
 * 日历热力在 7 天真实数据下会被 ECharts 拉成整年横条，大屏小容器完全不可读。
 * 这里改用「按日决策量」柱状图，数据来源仍是同一个 calendar 接口。
 */
const dailyChart = computed(() => {
  const daily = data('calendar')?.daily || []
  if (!daily.length) return null
  const t = chartTokens()
  return wallize({
    backgroundColor: 'transparent',
    textStyle: { color: t.mist },
    grid: { top: 14, left: 6, right: 10, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: daily.map((row) => row.date.slice(5)),
      axisLabel: { color: alpha(t.silver, 0.8), fontSize: 11 },
      axisLine: { lineStyle: { color: alpha(t.silver, 0.3) } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: alpha(t.silver, 0.8), fontSize: 11 },
      splitLine: { lineStyle: { color: alpha(t.silver, 0.12) } },
    },
    series: [{
      type: 'bar',
      data: daily.map((row) => row.count),
      barMaxWidth: 30,
      itemStyle: { color: t.accent, borderRadius: [4, 4, 0, 0] },
    }],
  })
})
const heatmapChart = computed(() => wallize(heatmapOption(data('heatmap'), '一周哪些时段最容易产生饮食决策', heatmapNote.value)))
const personasChart = computed(() => wallize(personasOption(data('personas'), personaScope.value === 'real' ? '真实账号的八维口味' : '演示人设的八维口味', personaNote.value)))
const scatterChart = computed(() => {
  const option = wallize(scatterOption(data('scatter'), '价格与真实评分之间存在怎样的分布', scatterNote.value))
  // 价格长尾到 ¥1485（p99 仅 ¥127），不截断会把 99% 的点压成一条竖线
  if (option?.xAxis && !Array.isArray(option.xAxis)) {
    option.xAxis = { ...option.xAxis, max: 200, name: '' }
  }
  return option
})
const flowChart = computed(() => wallize(flowOption(data('flow'), '每张候选票最终流向了哪里', flowNote.value)))
const trendChart = computed(() => {
  const option = wallize(trendOption(data('cuisine-trend'), '各菜系的决策量如何随日期变化', trendNote.value))
  // 日期标签是 YYYY-MM-DD，小容器里会互相压住，只留 MM-DD
  if (option?.xAxis && !Array.isArray(option.xAxis)) {
    option.xAxis = {
      ...option.xAxis,
      axisLabel: { ...(option.xAxis.axisLabel || {}), formatter: (value) => String(value).slice(5) },
    }
  }
  return option
})
const raceChart = computed(() => wallize(raceOption(data('race'), '菜品热度榜按周如何更迭', raceNote.value)))
const cooccurrenceChart = computed(() => wallize(cooccurrenceOption(data('cooccurrence'), '哪些主辅料最常在同一菜谱出现', cooccurrenceNote.value)))
const qualityChart = computed(() => wallize(qualityOption(data('quality'), '多少菜品拥有真实完整的八维向量', qualityNote.value)))
const repeat = computed(() => simDetail.value?.repeat_metrics || null)
const curveChart = computed(() => wallize(repeatCurveOption(repeat.value, '防腻衰减真的降低了同菜重样率', curveNote.value)))
const distributionChart = computed(() => wallize(repeatDistributionOption(repeat.value, '200 人的重样率分布', distributionNote.value)))
const STRATEGY_LABELS = {
  'mixed_omega_0.5': '混合 ω=0.5',
  'average_omega_1.0': '平均分',
  'random': '随机',
}
const barsChart = computed(() => {
  const option = wallize(experimentBarsOption(experiments.value, '混合博弈如何影响群组满意度', barsNote.value))
  // 接口返回的是实验内部策略名（mixed_omega_0.5 等），展示层换成中文
  if (option?.xAxis && !Array.isArray(option.xAxis) && Array.isArray(option.xAxis.data)) {
    option.xAxis = {
      ...option.xAxis,
      data: option.xAxis.data.map((name) => STRATEGY_LABELS[name] || name),
    }
  }
  return option
})

const cuisineNote = computed(() => {
  const rows = data('cuisine')?.items || []
  return rows.length ? `共 ${num(rows.reduce((sum, row) => sum + row.count, 0))} 行 · 首位 ${rows[0].cuisine_type}` : 'dishes 行数占比'
})
const calendarNote = computed(() => {
  const rows = data('calendar')?.daily || []
  return `${rows.length} 天 · 合计 ${num(rows.reduce((sum, row) => sum + row.count, 0))} 次`
})
const heatmapNote = computed(() => {
  const rows = data('heatmap')?.matrix || []
  const peak = [...rows].sort((a, b) => b.count - a.count)[0]
  return peak?.count ? `峰值 周${'一二三四五六日'[peak.weekday]} ${peak.slot} ${peak.count} 次` : '7×4 固定时段'
})
const scatterNote = computed(() => {
  const body = data('scatter')
  const points = body?.points || []
  const plotted = points.filter((row) => row.price !== null && row.rating !== null).length
  const clipped = points.filter((row) => row.price !== null && row.price > 200).length
  return `绘制 ${plotted} 点 · 价格轴截断 ¥200（超出 ${clipped} 点）`
})
const flowNote = computed(() => {
  const meta = data('flow')?.meta || {}
  return `候选 ${num(meta.total_opportunities)} = 实票 ${num(meta.actual_votes)} + 缺席 ${num(meta.absent_votes)}`
})
const trendNote = computed(() => {
  const body = data('cuisine-trend')
  const total = (body?.series || []).reduce((sum, row) => sum + row.data.reduce((part, value) => part + value, 0), 0)
  return `${body?.dates?.length || 0} 天合计 ${num(total)} 次`
})
const keywordsNote = computed(() => {
  const words = data('keywords')?.words || []
  return words.length ? `首位「${words[0].name}」${num(words[0].value)} 次` : 'allergen_tags + 菜名分词'
})
const raceNote = computed(() => `${data('race')?.weeks?.length || 0} 周 · 热度=被选+非 VETO 票`)
const cooccurrenceNote = computed(() => `${data('cooccurrence')?.links?.length || 0} 条食材边 · 阈值≥3`)
const qualityNote = computed(() => {
  const q = quality.value
  return q ? `有效 ${num(q.tagged_dishes)} / ${num(q.total_dishes)} 道` : 'quality 实时聚合'
})
const curveNote = computed(() => {
  const daily = repeat.value?.daily?.arms
  if (!daily?.ours || !daily?.baseline) return '仿真指标尚未导入'
  const last = (repeat.value?.daily?.days?.length || 14) - 1
  const consecutive = experiments.value?.duplication_rate_curve
  const tailText = consecutive?.days?.length
    ? ` · 连续同菜系 ${percent(consecutive['ours_lambda_0.5'][consecutive.days.length - 1])} / ${percent(consecutive.baseline_no_decay[consecutive.days.length - 1])}`
    : ''
  return `D14 同菜 ${percent(daily.ours.same_dish[last])} / ${percent(daily.baseline.same_dish[last])}${tailText}`
})
const personaNote = computed(() => {
  const rows = data('personas')?.personas || []
  if (personaScope.value === 'real') {
    return rows.length ? `${rows.length} 个真实账号` : '还没有真实账号'
  }
  return `${rows.length} 个演示人设`
})
async function switchPersonaScope(scope) {
  if (personaScope.value === scope) return
  personaScope.value = scope
  personaLoading.value = true
  try {
    responses.personas = await fetchAdminStats('personas', { ...filters, scope })
  } catch (err) {
    errors.personas = err?.detail || err?.message || '人设接口读取失败'
  } finally {
    personaLoading.value = false
  }
}
const distributionNote = computed(() => {
  const by = repeat.value?.by_arm
  if (!by?.ours || !by?.baseline) return '每点一个用户'
  return `本系统 ${percent(by.ours.user_rate_mean)} ± ${percent(by.ours.user_rate_sd)} · 基线 ${percent(by.baseline.user_rate_mean)} ± ${percent(by.baseline.user_rate_sd)}`
})
const barsNote = computed(() => {
  const bars = experiments.value?.group_satisfaction_bars
  if (!bars?.strategies?.length) return 'G3 正式输出未完成'
  return `${bars.strategies.length} 种策略 · 平均 / 最低成员`
})
const mapNote = computed(() => `${(data('geo')?.points?.length || 0).toLocaleString()} 个有效 GCJ-02 点 · 本地点阵渲染`)

/* ── 交互 ─────────────────────────────────────────────────── */
function goTopic(key) {
  if (topics.some((item) => item.key === key)) activeTopic.value = key
}
function onKey(event) {
  const index = topics.findIndex((item) => item.key === activeTopic.value)
  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') goTopic(topics[(index + 1) % topics.length].key)
  if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') goTopic(topics[(index - 1 + topics.length) % topics.length].key)
}
function goDish(id, campus) {
  router.push({ path: '/admin/data', query: { tab: 'dishes', dish_id: id, campus: campus === 'SHARED' ? '' : campus || filters.campus } })
}
function goRestaurant(id, campus) {
  router.push({ path: '/admin/data', query: { tab: 'restaurants', restaurant_id: id, campus: campus || filters.campus } })
}
function drillScatter(params) {
  const item = params?.data
  if (item?.entityType === 'RESTAURANT') goRestaurant(item.entityId, item.campus)
  else if (item?.entityType === 'DISH') goDish(item.entityId, item.campus)
}

onMounted(async () => {
  loadDashboard()
  const tick = () => {
    const now = new Date()
    const pad = (value) => String(value).padStart(2, '0')
    clock.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  }
  tick()
  clockTimer = setInterval(tick, 1000)
  window.addEventListener('keydown', onKey)
  try {
    const body = await fetchAdminStats('cuisine')
    cuisineList.value = (body.items || []).map((row) => row.cuisine_type).filter((name) => name !== '未标注')
  } catch {
    cuisineList.value = []
  }
})

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <AdminShell title="实验大屏" flush>
    <template #subnav>
      <button
        v-for="topic in topics"
        :key="topic.key"
        type="button"
        class="admin-side__sub"
        :class="{ 'is-on': activeTopic === topic.key }"
        @click="goTopic(topic.key)"
      >{{ topic.label }}</button>
    </template>
    <div class="admin-wall">
    <!-- 顶栏：只放真实可用的筛选，不做装饰性时间控件 -->
    <header class="wall-top">
      <div class="wall-seg" role="group" aria-label="校区筛选">
        <button v-for="item in [{ v: 'ALL', t: '全部校区' }, { v: 'SIYUAN', t: '思源' }, { v: 'JIANDA_YANTA', t: '建大雁塔' }]"
                :key="item.v" type="button" :class="{ 'is-on': filters.campus === item.v }"
                @click="filters.campus = item.v; loadDashboard()">{{ item.t }}</button>
      </div>

      <div class="wall-pills">
        <button class="wall-pill" :class="{ 'is-on': filters.mode_type === '' }" type="button" @click="filters.mode_type = ''; loadDashboard()">全部模式</button>
        <button class="wall-pill" :class="{ 'is-on': filters.mode_type === 'OUT_DINING' }" type="button" @click="filters.mode_type = 'OUT_DINING'; loadDashboard()">外食</button>
        <button class="wall-pill" :class="{ 'is-on': filters.mode_type === 'HOME_COOKING' }" type="button" @click="filters.mode_type = 'HOME_COOKING'; loadDashboard()">下厨</button>
        <button v-if="filters.cuisine_type" class="wall-pill is-on" type="button" @click="filters.cuisine_type = ''; loadDashboard()">
          {{ filters.cuisine_type }} ✕
        </button>
      </div>

      <div class="wall-top__right">
        <span class="wall-live"><i></i>{{ loading ? '同步中' : '实时同步' }}</span>
        <span class="wall-clock">{{ clock }}<small>CST</small></span>
      </div>
    </header>

    <!-- 三屏 -->
    <div class="wall-workbench">
      <div class="wall-stage">
      <!-- ── 屏 1 · 总览 ── -->
        <section v-show="activeTopic === 'overview'" class="wall-topic wall-topic--overview">
        <div class="wall-kpis wall-kpis--6">
          <article v-for="item in kpiCards" :key="item.key" class="wall-kpi" :class="{ 'wall-kpi--hero': item.hero }">
            <span class="wall-kpi__label">{{ item.label }}</span>
            <span class="wall-kpi__value">{{ item.value }}<em>{{ item.unit }}</em></span>
            <span class="wall-kpi__foot">{{ item.foot }}</span>
          </article>
        </div>

        <div class="wall-body wall-body--overview">
          <div class="wall-card wall-card--map">
            <div class="wall-card__head">
              <span class="wall-card__title">门店 POI 分布 · 双校区 3km 半径</span>
              <span class="wall-card__note">{{ mapNote }}</span>
            </div>
            <div class="wall-map">
              <PoiScatter v-if="has('geo', 'points')" :points="data('geo').points" />
              <p v-else-if="loading && !data('geo')" class="wall-empty">正在读取真实 POI…</p>
              <p v-else class="wall-empty">{{ error('geo') || data('geo')?.reason || '当前筛选没有有效 GCJ-02 点位' }}</p>
            </div>
          </div>

          <div class="wall-side">
            <div class="wall-card">
              <div class="wall-card__head">
                <span class="wall-card__title">校区规模对比</span>
                <span class="wall-card__note">门店 / 菜品</span>
              </div>
              <div class="wall-bars">
                <span class="wall-group-label">门店</span>
                <div v-for="row in campusBars" :key="row.name" class="wall-bar">
                  <span class="wall-bar__name">{{ row.name }}</span>
                  <span class="wall-bar__track"><span class="wall-bar__fill" :class="{ 'wall-bar__fill--hi': row.name === '思源' }" :style="{ width: `${row.width}%` }" /></span>
                  <span class="wall-bar__val">{{ num(row.value) }}</span>
                </div>
                <span class="wall-group-label">菜品</span>
                <div class="wall-bar">
                  <span class="wall-bar__name">共享下厨</span>
                  <span class="wall-bar__track"><span class="wall-bar__fill wall-bar__fill--hi" style="width: 100%" /></span>
                  <span class="wall-bar__val">{{ num(overview?.by_campus?.SHARED?.dishes) }}</span>
                </div>
                <div class="wall-bar">
                  <span class="wall-bar__name">思源外食</span>
                  <span class="wall-bar__track"><span class="wall-bar__fill" :style="{ width: `${Math.round(((overview?.by_campus?.SIYUAN?.dishes || 0) / Math.max(1, overview?.by_campus?.SHARED?.dishes || 1)) * 100)}%` }" /></span>
                  <span class="wall-bar__val">{{ num(overview?.by_campus?.SIYUAN?.dishes) }}</span>
                </div>
              </div>
            </div>

            <div class="wall-card">
              <div class="wall-card__head">
                <span class="wall-card__title">热度榜</span>
                <span class="wall-card__note">TOP 8 · 被选次数</span>
              </div>
              <div v-if="hotList.length" class="wall-rank">
                <div v-for="row in hotList" :key="row.dish_id" class="wall-rank__row">
                  <span class="wall-rank__no">{{ row.no }}</span>
                  <span class="wall-rank__name">{{ row.dish_name }}</span>
                  <span class="wall-rank__track"><i :style="{ width: `${row.width}%` }" /></span>
                  <span class="wall-rank__val">{{ row.value }}</span>
                </div>
              </div>
              <p v-else class="wall-empty">当前筛选没有投票或流水记录<br />热度榜需要 eating_logs 或非 VETO 票</p>
            </div>
          </div>
        </div>

        <div class="wall-body wall-bottom">
          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">真实菜品库由哪些菜系构成</span>
              <span class="wall-card__note">按菜品数 · TOP 6</span>
            </div>
            <div v-if="cuisineBars.length" class="wall-bars">
              <div v-for="(row, index) in cuisineBars" :key="row.cuisine_type" class="wall-bar">
                <span class="wall-bar__name">{{ row.cuisine_type }}</span>
                <span class="wall-bar__track"><span class="wall-bar__fill" :class="{ 'wall-bar__fill--hi': index === 0 }" :style="{ width: `${row.width}%` }" /></span>
                <span class="wall-bar__val">{{ num(row.count) }}</span>
              </div>
            </div>
            <p v-else class="wall-empty">{{ reason('cuisine', '当前筛选没有菜品行') }}</p>
          </div>

          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">多少菜品拥有完整八维向量</span>
              <span class="wall-card__note">{{ num(coverage?.total) }} 道</span>
            </div>
            <div v-if="coverage" class="wall-ringwrap">
              <div class="wall-bignum">
                <b>{{ coverage.percent.toFixed(1) }}<em>%</em></b>
                <span>八维齐全率</span>
              </div>
              <div class="wall-legend">
                <div><i style="background: var(--wall-ok)" />已完成 SUCCESS<b>{{ num(coverage.tagged) }}</b></div>
                <div><i style="background: var(--wall-warn)" />待补字段<b>{{ num(coverage.pending) }}</b></div>
                <div><i style="background: var(--wall-bad)" />向量异常<b>{{ num(coverage.anomalies) }}</b></div>
              </div>
            </div>
            <p v-else class="wall-empty">{{ error('quality') || '质量数据读取中' }}</p>
          </div>

          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">数据缺口</span>
              <span class="wall-card__note">实时</span>
            </div>
            <div v-if="todoList.length" class="wall-list">
              <div v-for="row in todoList" :key="row.label" class="wall-list__row" :class="row.tone">
                <span class="wall-list__dot" />
                <span>{{ row.label }}</span>
                <b>{{ num(row.value) }}</b>
              </div>
            </div>
            <p v-else class="wall-empty">{{ error('quality') || '质量数据读取中' }}</p>
          </div>
        </div>
      </section>

      <!-- ── 屏 2 · 数据质量 ── -->
        <section v-show="activeTopic === 'quality'" class="wall-topic wall-topic--quality">
        <div class="wall-kpis wall-kpis--4">
          <article class="wall-kpi wall-kpi--hero">
            <span class="wall-kpi__label">打标覆盖率</span>
            <span class="wall-kpi__value">{{ coverage ? (coverage.percent).toFixed(1) : '—' }}<em>%</em></span>
            <span class="wall-kpi__foot">{{ num(coverage?.tagged) }} / {{ num(coverage?.total) }} 道</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">向量异常</span>
            <span class="wall-kpi__value" :class="coverage?.anomalies ? 'wall-tone-warn' : 'wall-tone-ok'">{{ num(coverage?.anomalies) }}<em>条</em></span>
            <span class="wall-kpi__foot">完整 8 维且有限、0~1</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">缺失字段</span>
            <span class="wall-kpi__value">{{ num(todoList.length) }}<em>类</em></span>
            <span class="wall-kpi__foot">按影响行数排序</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">外食菜单覆盖</span>
            <span class="wall-kpi__value">{{ num(overview?.by_campus?.SIYUAN?.dishes) }}<em>道 · 思源</em></span>
            <span class="wall-kpi__foot">建大 {{ num(overview?.by_campus?.JIANDA_YANTA?.dishes) }} 道</span>
          </article>
        </div>

        <div class="wall-body wall-body--quality">
          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">仿真期每天发生了多少次饮食决策</span>
              <span class="wall-card__note">{{ calendarNote }}</span>
            </div>
            <EChartPanel bare :option="dailyChart" title="按日决策量" filename="C03-按日决策量"
                          :loading="loading && !data('calendar')" :error="error('calendar')"
                          :empty="!has('calendar', 'daily')" empty-reason="当前筛选没有饮食流水" />
          </div>


          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">菜品标签里哪些词最突出</span>
              <span class="wall-card__note">{{ keywordsNote }}</span>
            </div>
            <div v-if="cloudWords.length" class="wall-bars">
              <div v-for="(word, index) in cloudWords.slice(0, 9)" :key="word.name" class="wall-bar">
                <span class="wall-bar__name">{{ word.name }}</span>
                <span class="wall-bar__track"><span class="wall-bar__fill" :class="{ 'wall-bar__fill--hi': index === 0 }" :style="{ width: `${Math.round((word.value / cloudWords[0].value) * 100)}%` }" /></span>
                <span class="wall-bar__val">{{ word.value.toLocaleString() }}</span>
              </div>
            </div>
            <p v-else class="wall-empty">{{ error('keywords') || '当前筛选没有可用标签或菜名词元' }}</p>
          </div>


          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">哪些主辅料最常同时出现</span>
              <span class="wall-card__note">{{ cooccurrenceNote }}</span>
            </div>
            <EChartPanel bare :option="cooccurrenceChart" title="食材共现关系" filename="C16-食材共现关系"
                          :loading="loading && !data('cooccurrence')" :error="error('cooccurrence')"
                          :empty="data('cooccurrence')?.applicable === false || !has('cooccurrence', 'links')"
                          :empty-reason="reason('cooccurrence', '没有达到次数≥3 的食材边')" />
          </div>

          <div class="wall-card wall-span2">
            <div class="wall-card__head">
              <span class="wall-card__title">价格与真实评分之间存在怎样的分布</span>
              <span class="wall-card__note">{{ scatterNote }}</span>
            </div>
            <EChartPanel bare :option="scatterChart" title="价格评分散点" filename="C10-价格评分散点"
                          :loading="loading && !data('scatter')" :error="error('scatter')"
                          :empty="!(data('scatter')?.points || []).some((row) => row.price !== null && row.rating !== null)"
                          :empty-reason="reason('scatter', '当前数据没有同时具备价格与真实评分的点；NULL 未伪造')"
                          @drill="drillScatter" />
          </div>

          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">八维向量的真实覆盖</span>
              <span class="wall-card__note">{{ qualityNote }}</span>
            </div>
            <div v-if="coverage" class="wall-ringwrap">
              <div class="wall-bignum">
                <b>{{ coverage.percent.toFixed(1) }}<em>%</em></b>
                <span>八维齐全率</span>
              </div>
              <div class="wall-legend">
                <div><i style="background: var(--admin-ok)" />已完成 SUCCESS<b>{{ num(coverage.tagged) }}</b></div>
                <div><i style="background: var(--admin-warn)" />待补字段<b>{{ num(coverage.pending) }}</b></div>
                <div><i style="background: var(--admin-bad)" />向量异常<b>{{ num(coverage.anomalies) }}</b></div>
              </div>
            </div>
            <p v-else class="wall-empty">{{ error('quality') || '质量数据读取中' }}</p>
          </div>
        </div>
      </section>

      <!-- ── 屏 3 · 算法实验 ── -->
        <section v-show="activeTopic === 'experiment'" class="wall-topic wall-topic--experiment">
        <div class="wall-kpis wall-kpis--6">
          <article class="wall-kpi wall-kpi--hero">
            <span class="wall-kpi__label">14 天同菜重样 · 本系统</span>
            <span class="wall-kpi__value wall-tone-ok">{{ percent(repeat?.by_arm?.ours?.same_dish_rate) }}</span>
            <span class="wall-kpi__foot">14 天窗口 · 60 天平均</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">14 天同菜重样 · 无衰减</span>
            <span class="wall-kpi__value wall-tone-bad">{{ percent(repeat?.by_arm?.baseline?.same_dish_rate) }}</span>
            <span class="wall-kpi__foot">14 天窗口 · 60 天平均</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">群组满意度 · 最高策略</span>
            <span class="wall-kpi__value">{{ experiments?.group_satisfaction_bars?.avg_scores?.length ? Math.max(...experiments.group_satisfaction_bars.avg_scores).toFixed(2) : '—' }}<em>分</em></span>
            <span class="wall-kpi__foot">平均满意度</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">Least Misery · 最高策略</span>
            <span class="wall-kpi__value">{{ experiments?.group_satisfaction_bars?.least_misery_scores?.length ? Math.max(...experiments.group_satisfaction_bars.least_misery_scores).toFixed(2) : '—' }}<em>分</em></span>
            <span class="wall-kpi__foot">最挑剔成员满意度</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">仿真规模</span>
            <span class="wall-kpi__value">{{ num((experiments?.sample?.personas || 0) * (experiments?.sample?.days || 0) * (experiments?.sample?.meals_per_day || 0)) }}<em>次</em></span>
            <span class="wall-kpi__foot">{{ experiments?.sample?.personas || 0 }} 人 × {{ experiments?.sample?.days || 0 }} 天 × {{ experiments?.sample?.meals_per_day || 0 }} 餐</span>
          </article>
          <article class="wall-kpi">
            <span class="wall-kpi__label">群组投票</span>
            <span class="wall-kpi__value">{{ num((experiments?.sample?.rooms || 0) * (experiments?.sample?.members_per_room || 0) * 10) }}<em>票</em></span>
            <span class="wall-kpi__foot">{{ experiments?.sample?.rooms || 0 }} 房 × {{ experiments?.sample?.members_per_room || 0 }} 人 × 10 卡</span>
          </article>
        </div>

        <p v-if="simRun" class="wall-card__note" style="margin: 0 4px 8px">
          仿真底表已入库：{{ simRun.name }} · {{ num(simRun.meal_rows) }} 餐 / {{ num(simRun.room_rows) }} 房 / {{ num(simRun.vote_rows) }} 票（ours + baseline 两条 arm）
        </p>

        <div class="wall-body wall-body--experiment">
          <div class="wall-card wall-span2">
            <div class="wall-card__head">
              <span class="wall-card__title">防腻衰减真的降低了同菜重样率</span>
              <span class="wall-card__note">{{ curveNote }}</span>
            </div>
            <EChartPanel bare :option="curveChart" title="14 天同菜重样曲线" filename="C05-同菜重样曲线"
                          :loading="loading && !repeat" :error="error('simulationDetail')"
                          :empty="!repeat" empty-reason="仿真指标尚未导入" />
          </div>

          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">200 人的重样率分布</span>
              <span class="wall-card__note">{{ distributionNote }}</span>
            </div>
            <EChartPanel bare :option="distributionChart" title="用户重样率分布" filename="C07-用户重样分布"
                          :loading="loading && !repeat" :error="error('simulationDetail')"
                          :empty="!repeat" empty-reason="仿真指标尚未导入" />
          </div>

          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">混合博弈如何影响群组满意度</span>
              <span class="wall-card__note">{{ barsNote }}</span>
            </div>
            <EChartPanel bare :option="barsChart" title="群组实验柱状" filename="C06-群组实验柱状"
                          :loading="loading && !experiments" :error="error('experiments')"
                          :empty="!experiments?.available" :empty-reason="reason('experiments', 'G3 正式实验输出尚未生成')" />
          </div>

          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">八维口味画像</span>
              <span class="wall-card__note">{{ personaNote }}</span>
              <div class="wall-scope">
                <button type="button" :class="{ 'is-on': personaScope === 'demo' }" @click="switchPersonaScope('demo')">演示人设</button>
                <button type="button" :class="{ 'is-on': personaScope === 'real' }" @click="switchPersonaScope('real')">真实账号</button>
              </div>
            </div>
            <EChartPanel bare :option="personasChart" title="人设雷达" filename="C09-人设雷达"
                          :loading="personaLoading || (loading && !data('personas'))" :error="error('personas')"
                          :empty="!has('personas', 'personas')"
                          :empty-reason="personaScope === 'real' ? '还没有真实账号设置口味' : '没有演示人设'" />
          </div>


          <div class="wall-card">
            <div class="wall-card__head">
              <span class="wall-card__title">各菜系的决策量如何随日期变化</span>
              <span class="wall-card__note">{{ trendNote }}</span>
            </div>
            <EChartPanel bare :option="trendChart" title="菜系趋势" filename="C12-菜系趋势"
                          :loading="loading && !data('cuisine-trend')" :error="error('cuisine-trend')"
                          :empty="!has('cuisine-trend', 'dates')" empty-reason="当前筛选没有饮食流水" />
          </div>

        </div>
      </section>
    </div>

      </div>
    </div>
  </AdminShell>
</template>
