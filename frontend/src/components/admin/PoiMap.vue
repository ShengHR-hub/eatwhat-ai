<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AdminEmpty from './AdminEmpty.vue'
import { exportElementPng } from './export'
import { chartTokens, isAdminLight, isWall } from '../../utils/theme'

const props = defineProps({
  points: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  applicable: { type: Boolean, default: true },
  reason: { type: String, default: '' },
  note: { type: String, default: 'GCJ-02；点位 + 热度 + 聚合；合成食堂单独标记' },
  /** dark：强制深色底图 + 热力（大屏用）；light：默认底图、只做聚合（后台用） */
  theme: { type: String, default: 'light' },
})
const emit = defineEmits(['drill'])
const container = ref(null)
const exportRoot = ref(null)
const mapError = ref('')
const exporting = ref(false)
const exportError = ref('')
const renderReady = ref(false)
const tilesFailed = ref(false)
const apiKey = import.meta.env.VITE_AMAP_JS_KEY || ''
let map = null
let cluster = null
let heatmap = null
let renderSequence = 0
let resizeObserver = null
const unavailableReason = computed(() => {
  if (!props.applicable) return props.reason || '当前模式没有门店地理点位'
  if (!apiKey) return '未配置 VITE_AMAP_JS_KEY，未加载高德地图，也不使用伪地图替代'
  if (!props.points.length) return '当前筛选没有有效 GCJ-02 点位'
  return ''
})

function loadAmap() {
  if (window.AMap) return Promise.resolve(window.AMap)
  if (!apiKey) return Promise.reject(new Error('缺少高德 JS API Key'))
  if (import.meta.env.VITE_AMAP_JS_SECURITY_CODE) {
    window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_AMAP_JS_SECURITY_CODE }
  }
  return new Promise((resolve, reject) => {
    const existing = document.getElementById('eatwhat-amap-js')
    if (existing) {
      existing.addEventListener('load', () => resolve(window.AMap), { once: true })
      existing.addEventListener('error', () => reject(new Error('高德 JS API 加载失败')), { once: true })
      return
    }
    const script = document.createElement('script')
    script.id = 'eatwhat-amap-js'
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(apiKey)}`
    script.async = true
    script.onload = () => resolve(window.AMap)
    script.onerror = () => reject(new Error('高德 JS API 加载失败，请检查 Key 与网络'))
    document.head.appendChild(script)
  })
}

function destroyMap() {
  cluster?.setMap?.(null)
  heatmap?.setMap?.(null)
  cluster = null
  heatmap = null
  map?.destroy?.()
  map = null
  renderReady.value = false
}

/** 等容器拿到非零尺寸，最多约 1 秒；超时仍继续，交给 ResizeObserver 兜底。 */
function waitForSize(el) {
  return new Promise((resolve) => {
    let frames = 0
    const check = () => {
      if (!el || (el.clientWidth > 0 && el.clientHeight > 0) || frames > 60) {
        resolve(Boolean(el && el.clientWidth > 0))
        return
      }
      frames += 1
      requestAnimationFrame(check)
    }
    check()
  })
}

async function renderMap() {
  const sequence = ++renderSequence
  destroyMap()
  mapError.value = ''
  if (props.loading || props.error || unavailableReason.value) return
  await nextTick()
  try {
    // 大屏的高度由 grid/fr 分配，首帧容器可能还是 0×0；
    // 此时建图会得到一张永不请求瓦片的空白地图，必须先等尺寸落定。
    const sized = await waitForSize(container.value)
    // 尺寸没落定就建图，会得到一张永不请求瓦片的空白地图；
    // 交给 ResizeObserver 在拿到尺寸后重试。
    if (!sized) return
    if (sequence !== renderSequence || !container.value) return
    const AMap = await loadAmap()
    if (sequence !== renderSequence || !container.value) return
    const center = props.points.reduce((acc, point) => [acc[0] + point.lng / props.points.length, acc[1] + point.lat / props.points.length], [0, 0])
    // 深色大屏显式指定 dark；浅色后台不传 mapStyle，用高德默认底图
    // （传 'amap://styles/normal' 实测会得到一张不请求瓦片的空白图）
    const dark = props.theme === 'dark' || isWall()
    const mapOptions = { zoom: 12, center, viewMode: '2D' }
    if (dark) mapOptions.mapStyle = 'amap://styles/dark'
    map = new AMap.Map(container.value, mapOptions)
    // 底图瓦片失败时地图实例照样创建成功，只会剩一张白底；
    // 这里做一次超时探测，把「白屏」变成可见的降级说明。
    tilesFailed.value = false
    let tilesOk = false
    map.on('complete', () => { tilesOk = true })
    setTimeout(() => {
      if (!tilesOk && map) tilesFailed.value = true
    }, 4000)
    await new Promise((resolve, reject) => {
      AMap.plugin(['AMap.HeatMap', 'AMap.MarkerCluster'], () => {
        try {
          // 大屏作用域下把热力渐变换成冷色，避免默认红黄渐变破坏单色体系。
          // 低值必须落到背景色上，否则热力层会把整张底图刷白（实测：高值映射成白 → 中心一片白）。
          const palette = chartTokens()
          const heatOptions = { radius: 24, opacity: [0, 0.62] }
          if (dark) {
            heatOptions.gradient = {
              0: palette.ink,
              0.35: palette.ink,
              0.55: palette.accentDim || palette.accent,
              0.75: palette.accent,
              0.92: palette.accentHi,
              1: palette.accentHi,
            }
          }
          // 浅色底图上热力会糊成一团色块，遮住道路与点位；
          // 后台浅色模式只用点聚合，深色投屏才叠热力。
          if (dark) {
            heatmap = new AMap.HeatMap(map, heatOptions)
            const maxHeat = Math.max(1, ...props.points.map((point) => point.heat || 0))
            heatmap.setDataSet({
              max: maxHeat,
              data: props.points.map((point) => ({ lng: point.lng, lat: point.lat, count: Math.max(1, point.heat || 0) })),
            })
          }
          const markers = props.points.map((point) => {
            const marker = new AMap.Marker({
              position: [point.lng, point.lat],
              title: `${point.name} · ${point.campus || '未归属'} · 热度 ${point.heat}`,
              content: `<span class="admin-map-marker${point.is_synthetic ? ' is-synthetic' : ''}">${point.is_synthetic ? '合' : '实'}</span>`,
              anchor: 'center',
            })
            marker.on('click', () => emit('drill', point))
            return marker
          })
          cluster = new AMap.MarkerCluster(map, markers, { gridSize: 56, maxZoom: 17 })
          map.setFitView(null, false, [56, 56, 56, 56])
          renderReady.value = true
          resolve()
        } catch (error) {
          reject(error)
        }
      })
    })
  } catch (error) {
    if (sequence === renderSequence) mapError.value = error?.message || '高德地图渲染失败'
  }
}

async function exportPng() {
  exporting.value = true
  exportError.value = ''
  try {
    if (!renderReady.value) throw new Error('地图尚未完成真实渲染，不能导出')
    await exportElementPng(exportRoot.value, {
      title: '校区周边餐饮 POI 如何分布？',
      note: props.note,
      filename: 'C02-校区POI地图',
    })
  } catch (error) {
    exportError.value = error?.message || '地图 PNG 导出失败；请检查地图跨域资源'
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  renderMap()
  // 大屏用 grid/fr 分配高度，地图初始化那一刻容器可能还是 0 高，
  // 瓦片就永远不会请求。监听尺寸变化后主动 resize 一次。
  if (typeof ResizeObserver !== 'undefined' && container.value) {
    resizeObserver = new ResizeObserver(() => {
      if (map) {
        map.resize?.()
        return
      }
      // 首次因 0 尺寸放弃建图，这里补一次
      if (container.value && container.value.clientWidth > 0 && container.value.clientHeight > 0) {
        renderMap()
      }
    })
    resizeObserver.observe(container.value)
  }
})
watch(() => [props.points, props.loading, props.error, props.applicable], renderMap, { deep: false })
onBeforeUnmount(() => {
  renderSequence += 1
  resizeObserver?.disconnect()
  resizeObserver = null
  destroyMap()
})
</script>

<template>
  <section class="admin-chart-card admin-map-card">
    <div class="admin-chart-actions">
      <button class="admin-button admin-button--small" type="button" :disabled="!renderReady || exporting" @click="exportPng">
        {{ exporting ? '导出中…' : '导出 PNG' }}
      </button>
    </div>
    <div ref="exportRoot" class="admin-map-export">
      <header class="admin-map-heading">
        <p class="admin-eyebrow">C02 · AMAP / GCJ-02</p>
        <h2>校区周边餐饮 POI 如何分布？</h2>
        <p>{{ note }}</p>
      </header>
      <div class="admin-map-canvas-wrap">
        <div ref="container" class="admin-map-canvas" />
        <div v-if="loading" class="admin-map-overlay admin-empty">正在读取真实 POI…</div>
        <div v-else-if="error || mapError" class="admin-map-overlay">
          <AdminEmpty title="地图读取失败" :reason="error || mapError" />
        </div>
        <div v-else-if="unavailableReason" class="admin-map-overlay">
          <AdminEmpty :reason="unavailableReason" />
        </div>
        <div v-else-if="tilesFailed" class="admin-map-overlay admin-map-overlay--soft">
          <p class="admin-map-fallback">
            底图瓦片未加载（高德样式服务无响应）<br />
            当前仅显示热力分布；点位数据本身是真实 GCJ-02 坐标
          </p>
        </div>
      </div>
      <footer class="admin-map-legend"><span>实 = 真实来源门店</span><span>合 = 显式合成食堂</span><span>点击门店标记下钻</span></footer>
    </div>
    <p v-if="exportError" class="admin-inline-error" role="alert">{{ exportError }}</p>
  </section>
</template>
