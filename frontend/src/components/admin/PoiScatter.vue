<script setup>
import { computed, ref } from 'vue'

/**
 * POI 分布点阵（真实 GCJ-02 坐标，纯本地渲染）。
 *
 * 为什么不用高德 JS API：底图瓦片在该 Key 下反复加载失败，只剩热力层，
 * 地图块变成一块白/黑斑。这里把真实经纬度直接投影成点位，
 * 不依赖任何外部瓦片服务，同时保留「两个校区 3km 半径」的空间关系。
 */
const props = defineProps({
  points: { type: Array, default: () => [] },
  maxDots: { type: Number, default: 1400 },
})

/* ── 缩放与平移：点阵是纯 DOM，用 transform 即可，不需要地图引擎 ── */
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
let dragging = false
let originX = 0
let originY = 0
let startX = 0
let startY = 0

const layerStyle = computed(() => ({
  transform: `translate(${tx.value}px, ${ty.value}px) scale(${scale.value})`,
  transformOrigin: '50% 50%',
}))

function onWheel(event) {
  event.preventDefault()
  const next = scale.value * (event.deltaY > 0 ? 0.88 : 1.12)
  scale.value = Math.min(8, Math.max(1, Number(next.toFixed(2))))
  if (scale.value === 1) {
    tx.value = 0
    ty.value = 0
  }
}

function onPointerDown(event) {
  dragging = true
  startX = event.clientX - tx.value
  startY = event.clientY - ty.value
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function onPointerMove(event) {
  if (!dragging) return
  tx.value = event.clientX - startX
  ty.value = event.clientY - startY
}

function onPointerUp() {
  dragging = false
}

function resetView() {
  scale.value = 1
  tx.value = 0
  ty.value = 0
}

const projected = computed(() => {
  const source = props.points.filter((p) => Number.isFinite(p.lng) && Number.isFinite(p.lat))
  if (!source.length) return { dots: [], pins: [], bounds: null }

  const lngs = source.map((p) => p.lng)
  const lats = source.map((p) => p.lat)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const spanLng = Math.max(0.001, maxLng - minLng)
  const spanLat = Math.max(0.001, maxLat - minLat)

  const project = (lng, lat) => ({
    x: ((lng - minLng) / spanLng) * 100,
    y: (1 - (lat - minLat) / spanLat) * 100,
  })

  // 点位太多会拖垮 DOM：按固定步长均匀采样，保持空间分布形态
  const step = Math.max(1, Math.ceil(source.length / props.maxDots))
  const dots = []
  for (let i = 0; i < source.length; i += step) {
    const point = source[i]
    const { x, y } = project(point.lng, point.lat)
    dots.push({
      key: `${point.id ?? i}`,
      x: x.toFixed(2),
      y: y.toFixed(2),
      synthetic: Boolean(point.is_synthetic),
      size: point.heat > 1 ? 3.5 : 2.6,
      title: `${point.name || 'POI'}${point.campus ? ` · ${point.campus}` : ''}`,
    })
  }

  // 校区锚点：按 campus 求质心
  const groups = new Map()
  source.forEach((point) => {
    if (!point.campus) return
    const bucket = groups.get(point.campus) || { lng: 0, lat: 0, n: 0 }
    bucket.lng += point.lng
    bucket.lat += point.lat
    bucket.n += 1
    groups.set(point.campus, bucket)
  })
  const pins = [...groups.entries()].map(([campus, bucket]) => {
    const { x, y } = project(bucket.lng / bucket.n, bucket.lat / bucket.n)
    return {
      campus,
      label: campus === 'SIYUAN' ? '思源校区' : campus === 'JIANDA_YANTA' ? '建大雁塔' : campus,
      x: x.toFixed(2),
      y: y.toFixed(2),
      count: bucket.n,
    }
  })

  return {
    dots,
    pins,
    bounds: { minLng, maxLng, minLat, maxLat },
    total: source.length,
    sampled: dots.length,
  }
})
</script>

<template>
  <div
    class="poi-scatter"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointerleave="onPointerUp"
  >
    <div class="poi-scatter__layer" :style="layerStyle">
      <div class="poi-scatter__grid" aria-hidden="true" />

      <span
        v-for="dot in projected.dots"
        :key="dot.key"
        class="poi-scatter__dot"
        :class="{ 'is-synthetic': dot.synthetic }"
        :style="{ left: `${dot.x}%`, top: `${dot.y}%`, width: `${dot.size}px`, height: `${dot.size}px` }"
        :title="dot.title"
      />

      <span
        v-for="pin in projected.pins"
        :key="pin.campus"
        class="poi-scatter__pin"
        :style="{ left: `${pin.x}%`, top: `${pin.y}%` }"
      >
        <b />
        <em>{{ pin.label }} · {{ pin.count.toLocaleString() }}</em>
      </span>
    </div>

    <button class="poi-scatter__reset" type="button" @click.stop="resetView">
      {{ scale > 1 ? `${scale.toFixed(1)}× · 复位` : '滚轮缩放 · 拖拽平移' }}
    </button>

    <div class="poi-scatter__legend">
      <span><i class="is-real" />真实 POI</span>
      <span><i class="is-syn" />合成食堂</span>
      <span class="poi-scatter__meta">
        采样 {{ projected.sampled?.toLocaleString() || 0 }} / {{ projected.total?.toLocaleString() || 0 }} 点
      </span>
    </div>

    <p v-if="projected.bounds" class="poi-scatter__bounds">
      {{ projected.bounds.minLng.toFixed(3) }}–{{ projected.bounds.maxLng.toFixed(3) }}°E ·
      {{ projected.bounds.minLat.toFixed(3) }}–{{ projected.bounds.maxLat.toFixed(3) }}°N · GCJ-02
    </p>
  </div>
</template>

<style scoped>
.poi-scatter {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.08);
  border-radius: 10px;
  background:
    radial-gradient(70% 60% at 30% 40%, rgb(var(--rgb-admin-accent) / 0.06), transparent 70%),
    var(--admin-surface-2);
}

.poi-scatter { cursor: grab; touch-action: none; }
.poi-scatter:active { cursor: grabbing; }

.poi-scatter__layer {
  position: absolute;
  inset: 0;
  transition: transform 0.12s ease-out;
}

.poi-scatter__reset {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.12);
  border-radius: 6px;
  background: rgb(var(--rgb-admin-surface) / 0.9);
  color: var(--admin-muted);
  font: inherit;
  font-size: 9.5px;
  cursor: pointer;
  z-index: 2;
}
.poi-scatter__reset:hover { color: var(--admin-ink); border-color: rgb(var(--rgb-admin-ink) / 0.28); }

.poi-scatter { cursor: grab; touch-action: none; }
.poi-scatter:active { cursor: grabbing; }

.poi-scatter__layer {
  position: absolute;
  inset: 0;
  transition: transform 0.12s ease-out;
}

.poi-scatter__reset {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.12);
  border-radius: 6px;
  background: rgb(var(--rgb-admin-surface) / 0.9);
  color: var(--admin-muted);
  font: inherit;
  font-size: 9.5px;
  cursor: pointer;
  z-index: 2;
}
.poi-scatter__reset:hover { color: var(--admin-ink); border-color: rgb(var(--rgb-admin-ink) / 0.28); }

.poi-scatter__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgb(var(--rgb-admin-ink) / 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgb(var(--rgb-admin-ink) / 0.045) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(72% 72% at 50% 50%, var(--admin-ink) 30%, transparent 94%);
}

.poi-scatter__dot {
  position: absolute;
  border-radius: 50%;
  background: var(--admin-accent);
  opacity: 0.55;
  transform: translate(-50%, -50%);
}
.poi-scatter__dot.is-synthetic { background: var(--admin-ok); opacity: 0.55; }

.poi-scatter__pin {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.poi-scatter__pin b {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--admin-ink);
  box-shadow: 0 0 0 4px rgb(var(--rgb-admin-ink) / 0.1);
}
.poi-scatter__pin em {
  padding: 1px 6px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.1);
  border-radius: 5px;
  background: rgb(var(--rgb-admin-surface) / 0.9);
  color: var(--admin-ink);
  font-size: 9.5px;
  font-style: normal;
  white-space: nowrap;
}

.poi-scatter__legend {
  position: absolute;
  left: 10px;
  bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--admin-muted);
  font-size: 9.5px;
}
.poi-scatter__legend span { display: inline-flex; align-items: center; gap: 5px; }
.poi-scatter__legend i { width: 6px; height: 6px; border-radius: 50%; }
.poi-scatter__legend i.is-real { background: var(--admin-accent); opacity: 0.6; }
.poi-scatter__legend i.is-syn { background: var(--admin-ok); }
.poi-scatter__meta { color: var(--admin-faint); }

.poi-scatter__bounds {
  position: absolute;
  right: 10px;
  bottom: 8px;
  margin: 0;
  color: var(--admin-faint);
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 9px;
}
</style>
