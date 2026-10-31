<script setup>
/**
 * 算法沙盒抽屉（答辩亮点①）。
 * 4 个滑块：λ 防腻衰减 / ω 群组折中 / β 天气权重 / γ 预算权重（v2.3.1 第六章 §4）。
 * 拖动 → 写 override_params → 后端实时重算 → 主界面排名动画 + 雷达面积变形。
 *
 * 抽屉本身是浮层，不是内容卡：内容仍落在实底上，只有把手与悬浮按钮用玻璃。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useAutoAnimate } from '@formkit/auto-animate/vue'

import { SANDBOX_PARAMS, useAlgoStore } from '../stores/algo'

const algo = useAlgoStore()
const [listRef] = useAutoAnimate({ duration: 260, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)' })

// 滑块只改参数（store 里累加 reloadTick），真正的重算由持有卡组的 Home 统一触发，
// 这样抽屉与首页卡组永远是同一次请求的结果（审查 F10）。
function onInput(key, event) {
  algo.setParam(key, event.target.value)
}

function reset() {
  algo.resetParams()
}

function close() {
  algo.toggleSandbox(false)
}

const ranking = computed(() => algo.recommendations.slice(0, 5))

const usedLabel = computed(() => {
  const p = algo.paramsUsed
  if (!p || !Object.keys(p).length) return '—'
  return `λ ${p.lambda_decay?.toFixed(2)} · ω ${p.omega_group?.toFixed(2)} · β ${p.beta_weather?.toFixed(2)} · γ ${p.gamma_budget?.toFixed(2)}`
})

watch(
  () => algo.sandboxOpen,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
  },
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <Transition name="sheet">
    <aside v-if="algo.sandboxOpen" class="sandbox" role="dialog" aria-modal="true" aria-label="算法沙盒">
      <header class="sandbox__head">
        <div>
          <p class="sandbox__title">算法沙盒</p>
          <p class="sandbox__sub">{{ algo.loading ? '重算中…' : '上帝视角调参' }}</p>
        </div>
        <button type="button" class="sandbox__close" aria-label="关闭" @click="close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
          </svg>
        </button>
      </header>

      <div class="sandbox__body">
        <div v-for="param in SANDBOX_PARAMS" :key="param.key" class="param">
          <div class="param__row">
            <span class="param__label">{{ param.label }}</span>
            <span class="param__value tabular">{{ Number(algo.overrides[param.key]).toFixed(2) }}</span>
          </div>
          <input
            class="range range-xs param__range slider-ink"
            type="range"
            :min="param.min"
            :max="param.max"
            :step="param.step"
            :value="algo.overrides[param.key]"
            :aria-label="param.label"
            @input="onInput(param.key, $event)"
          />
          <p class="param__hint">{{ param.hint }}</p>
        </div>

        <div class="used">
          <span class="used__k">本次生效权重</span>
          <span class="used__v tabular">{{ usedLabel }}</span>
        </div>

        <p class="section-title">当前 Top 5（实时重排）</p>
        <ol ref="listRef" class="ranking">
          <li v-for="(item, index) in ranking" :key="item.dish_id" class="ranking__item">
            <span class="ranking__idx tabular">{{ index + 1 }}</span>
            <span class="ranking__name">{{ item.name }}</span>
            <span class="ranking__score tabular">{{ item.total_score.toFixed(1) }}</span>
          </li>
        </ol>

        <button type="button" class="reset" @click="reset">恢复默认参数</button>
        <p class="foot">
          调参只影响本次请求（override_params），不改库里的 algo_configs。确认后点右上角 × 关闭。
        </p>
      </div>
    </aside>
  </Transition>

  <Transition name="fade">
    <div v-if="algo.sandboxOpen" class="backdrop" @click="close" />
  </Transition>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgb(var(--rgb-black) / 0.35);
  backdrop-filter: blur(2px);
}

.sandbox {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  display: flex;
  width: min(360px, 92vw);
  flex-direction: column;
  border-radius: 24px 0 0 24px;
  /* 抽屉是浮层不是内容卡：必须是能压住背景的深色实底，
     直接复用 --color-surface 会拿到半透明玻璃值，字会跟背后的页面糊在一起。 */
  background: rgb(var(--rgb-panel) / 0.96);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow:
    inset 1px 0 0 rgb(var(--rgb-white) / 0.14),
    -18px 0 48px rgb(var(--rgb-black) / 0.45);
  color: var(--color-white);
}

.sandbox__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid rgb(var(--rgb-white) / 0.14);
}

.sandbox__title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.sandbox__sub {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: var(--color-text-soft);
}

.sandbox__close {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.12);
  color: var(--color-white);
}

.sandbox__close svg {
  width: 15px;
  height: 15px;
}

.sandbox__body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px 22px;
}

.param {
  padding: 8px 0 12px;
  border-bottom: 1px dashed rgb(var(--rgb-white) / 0.14);
}

.param__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.param__label {
  font-size: 13px;
  font-weight: 600;
}

.param__value {
  font-size: 12px;
  color: var(--color-text-soft);
}

.param__range {
  width: 100%;
  margin: 8px 0 2px;
  accent-color: var(--color-white);
}

.param__hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--color-text-soft);
}

.used {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin: 14px 0 6px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgb(var(--rgb-white) / 0.08);
}

.used__k {
  font-size: 10.5px;
  color: var(--color-text-soft);
}

.used__v {
  font-size: 11.5px;
  font-weight: 600;
}

.section-title {
  margin: 16px 0 8px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-text-soft);
}

.ranking {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ranking__item {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 12px;
  padding: 8px 10px;
  background: rgb(var(--rgb-white) / 0.08);
  font-size: 12.5px;
}

.ranking__idx {
  width: 14px;
  font-size: 11px;
  color: var(--color-text-soft);
}

.ranking__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ranking__score {
  font-weight: 700;
}

.reset {
  width: 100%;
  margin-top: 16px;
  border-radius: 999px;
  border: 1px solid rgb(var(--rgb-white) / 0.22);
  padding: 10px 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-white);
}

.foot {
  margin: 12px 0 0;
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--color-text-soft);
}
</style>
