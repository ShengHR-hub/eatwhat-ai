<script setup>
/**
 * 顶部天气胶囊（灵动岛式）。
 *
 * 视觉来源：WEATHERPILL_GLASS.md §4 的 `.weather-pill` 字面块（styles/glass-tokens.css），
 * 本组件只负责结构与交互，不新写玻璃数值。
 * 动效来源：@vueuse/motion（规范 2.2）负责展开/收起。
 * 图标来源：lottie-web + src/assets/lottie/weather-*.json（规范 2.4 明确禁止用静态图或手写 CSS 动画替代）。
 */
import { computed, ref } from 'vue'
import { useModeStore, WEATHER_PRESETS } from '../stores/mode'
import LottieIcon from './LottieIcon.vue'

const mode = useModeStore()
const expanded = ref(false)

/** 天气文案 → Lottie 素材名（素材见 docs/LOTTIE_SOURCES.md） */
const weatherKey = computed(() => {
  const text = mode.weatherText
  if (text.includes('雨')) return 'weather-rainy'
  if (text.includes('雪')) return 'weather-snowy'
  return 'weather-sunny'
})

function pickPreset(preset) {
  mode.loadWeather(preset)
  expanded.value = false
}
</script>

<template>
  <div class="weather-pill weather-pill--host">
    <button
      type="button"
      class="pill-main"
      :aria-expanded="expanded"
      aria-label="天气与演示天气切换"
      @click="expanded = !expanded"
    >
      <!-- 天气图标：lottie-web + meteocons（MIT）单色素材，缺件时组件内部自带兜底 -->
      <span class="pill-icon">
        <LottieIcon :name="weatherKey" :size="20" />
      </span>

      <span class="pill-temp tabular">{{ Math.round(mode.weatherTemp) }}°</span>
      <span class="pill-text">{{ mode.weatherText }}</span>
      <span v-if="mode.weatherSource === 'override'" class="pill-tag">演示</span>
      <span v-else-if="mode.weatherSource === 'offline'" class="pill-tag pill-tag--muted">离线</span>
    </button>

    <div v-if="expanded" v-motion :initial="{ opacity: 0, y: -6 }" :enter="{ opacity: 1, y: 0 }" class="pill-panel">
      <p class="pill-tip">{{ mode.weatherTip || '天气数据未就绪，按常温推荐' }}</p>
      <div class="preset-row">
        <button
          v-for="preset in WEATHER_PRESETS"
          :key="preset.key"
          type="button"
          class="preset"
          :data-active="mode.weatherOverride === preset.key"
          @click="pickPreset(preset)"
        >
          {{ preset.label }}
        </button>
      </div>
      <!-- TODO(lottie)：weather-sunny/rainy/snowy.json 未接入前，图标是占位描边 -->
    </div>
  </div>
</template>

<style scoped>
/* 结构外包一层：玻璃数值仍取 .weather-pill 字面块，方向改为纵向以便展开 */
.weather-pill--host {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  border-radius: 26px;
  overflow: hidden;
}

.pill-main {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px 5px 8px;
  white-space: nowrap;
  color: var(--color-ink);
}

/* 图标是坑位尺寸；真正的动画由 LottieIcon 自己按 size 渲染 */
.pill-icon {
  display: inline-flex;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  align-items: center;
  justify-content: center;
}

.pill-temp {
  font-size: 13.5px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.pill-text {
  font-size: 12px;
  white-space: nowrap;
  color: var(--color-ink);
}

.pill-tag {
  margin-left: 2px;
  white-space: nowrap;
  border-radius: 999px;
  padding: 1px 7px;
  font-size: 10px;
  letter-spacing: 0.02em;
  background: rgb(var(--rgb-ink) / 0.9);
  color: var(--color-white);
}

.pill-tag--muted {
  background: rgb(var(--rgb-steel) / 0.85);
}

.pill-panel {
  padding: 0 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pill-tip {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-steel);
}

.preset-row {
  display: flex;
  gap: 6px;
}

.preset {
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 11.5px;
  /* 展开面板本身是浅色玻璃，预设胶囊要比它更实，否则和底子糊成一片 */
  background: rgb(var(--rgb-white) / 0.86);
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-ink) / 0.08);
  color: var(--color-steel);
}

.preset[data-active='true'] {
  background: var(--color-ink);
  color: var(--color-white);
}
</style>
