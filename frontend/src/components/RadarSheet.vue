<script setup>
/**
 * RadarSheet.vue —— 五维雷达弹层（BATCH2_PLAN v1.1：雷达从页面里拆出来，改点击卡面弹出）
 *
 * 数据口径不变：radar_5d 是五个分项分（0–100），与总分封顶无关；
 * 总分 total_score 单独一行展示，避免"雷达轴失效"的误读（用户已裁决）。
 */
import { computed } from 'vue'

import ExplainRadar from './ExplainRadar.vue'
import { RADAR_AXES } from '../constants/bubbles'

const props = defineProps({
  open: { type: Boolean, default: false },
  dish: { type: Object, default: null },
})

const emit = defineEmits(['close'])

const axes = computed(() =>
  RADAR_AXES.map((axis) => ({
    ...axis,
    value: Number(props.dish?.radar_5d?.[axis.key] ?? 0),
  })),
)

const score = computed(() => Number(props.dish?.total_score ?? 0))
</script>

<template>
  <Transition name="radar-fade">
    <div v-if="open && dish" class="radar-mask" role="dialog" aria-modal="true" @click.self="emit('close')">
      <section class="radar-panel">
        <header class="radar-panel__head">
          <div>
            <h2 class="radar-panel__title">{{ dish.name }}</h2>
            <p class="radar-panel__sub">
              五维解释 · {{ dish.restaurant_name || '家常菜谱' }}
            </p>
          </div>
          <button type="button" class="radar-panel__close" aria-label="关闭" @click="emit('close')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
            </svg>
          </button>
        </header>

        <ExplainRadar :data="dish.radar_5d" :height="228" />

        <ul class="radar-panel__axes">
          <li v-for="axis in axes" :key="axis.key" class="axis">
            <span class="axis__name">{{ axis.name }}</span>
            <span class="axis__bar"><i :style="{ width: `${Math.max(0, Math.min(100, axis.value))}%` }" /></span>
            <span class="axis__val tabular">{{ axis.value.toFixed(1) }}</span>
          </li>
        </ul>

        <p class="radar-panel__score">
          综合匹配度 <b class="tabular">{{ score.toFixed(1) }}%</b>
        </p>

        <p v-if="dish.explain_reason" class="radar-panel__reason">{{ dish.explain_reason }}</p>
      </section>
    </div>
  </Transition>
</template>

<style scoped>
.radar-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgb(var(--rgb-black) / 0.52);
  backdrop-filter: blur(2px);
}

.radar-panel {
  width: min(100%, 480px);
  max-height: 88vh;
  overflow-y: auto;
  padding: 18px 18px calc(18px + env(safe-area-inset-bottom));
  border-radius: 26px 26px 0 0;
  background: rgb(var(--rgb-sheet) / 0.97);
  box-shadow: inset 0 1px 0 rgb(var(--rgb-white) / 0.14), 0 -18px 48px rgb(var(--rgb-black) / 0.5);
  color: var(--color-white);
}

.radar-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.radar-panel__title {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
}

.radar-panel__sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-glass-dim);
}

.radar-panel__close {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  border: 0;
  background: rgb(var(--rgb-white) / 0.1);
  color: var(--color-white);
  cursor: pointer;
}

.radar-panel__close svg {
  width: 18px;
  height: 18px;
}

.radar-panel__axes {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.axis {
  display: grid;
  grid-template-columns: 68px 1fr 44px;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.axis__name {
  color: var(--on-glass-soft);
}

.axis__bar {
  height: 5px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
  overflow: hidden;
}

.axis__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-white);
}

.axis__val {
  text-align: right;
  font-weight: 600;
}

.radar-panel__score {
  margin: 16px 0 0;
  font-size: 12.5px;
  color: var(--on-glass-soft);
}

.radar-panel__score b {
  color: var(--color-white);
  font-size: 16px;
}

.radar-panel__reason {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--on-glass-soft);
}

.radar-fade-enter-active,
.radar-fade-leave-active {
  transition: opacity 0.22s ease;
}

.radar-fade-enter-active .radar-panel,
.radar-fade-leave-active .radar-panel {
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.radar-fade-enter-from,
.radar-fade-leave-to {
  opacity: 0;
}

.radar-fade-enter-from .radar-panel,
.radar-fade-leave-to .radar-panel {
  transform: translateY(24px);
}
</style>
