<script setup>
/**
 * 主 CTA：Inspira UI「Shimmer Button」的 Vue 移植（MIT）。
 * 规范 2.7：全 App 唯一主 CTA（"开始智能决策"）必须用现成 Shimmer Button，不许手写流光。
 * 移植时只改了配色：银白流光 + 近黑底，符合 v2.3 单色令牌。
 */
defineProps({
  label: { type: String, default: '' },
  block: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
defineEmits(['click'])
</script>

<template>
  <button
    type="button"
    class="shimmer-button"
    :class="{ 'is-block': block, 'is-disabled': disabled || loading }"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <span class="shimmer-button__shine" aria-hidden="true" />
    <span class="shimmer-button__content">
      <span v-if="loading" class="dot-flash" aria-hidden="true" />
      <slot>{{ label }}</slot>
    </span>
  </button>
</template>

<style scoped>
.shimmer-button {
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  /* 紧凑呼吸：CTA 高度 48px（原 ~53px） */
  min-height: 48px;
  padding: 0 24px;
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--color-white);
  background: var(--color-ink);
  box-shadow:
    inset 0 1px 0 rgb(var(--rgb-white) / 0.14),
    0 10px 24px rgb(var(--rgb-black) / 0.22);
  transition: transform 0.16s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}

.shimmer-button:active {
  transform: scale(0.985);
}

.shimmer-button.is-block {
  width: 100%;
}

.shimmer-button.is-disabled {
  opacity: 0.55;
  pointer-events: none;
}

/* 流光：一条柔和的斜向高光带周期性扫过（3.2s）。
 * 边缘必须长渐变过渡：短渐变在深底上会显出直边，像贴了一块灰玻璃。 */
.shimmer-button__shine {
  position: absolute;
  inset: -60% -10%;
  background: linear-gradient(
    100deg,
    transparent 26%,
    rgb(var(--rgb-white) / 0.04) 38%,
    rgb(var(--rgb-white) / 0.18) 46%,
    rgb(var(--rgb-white) / 0.34) 50%,
    rgb(var(--rgb-white) / 0.18) 54%,
    rgb(var(--rgb-white) / 0.04) 62%,
    transparent 74%
  );
  transform: translateX(-120%);
  animation: shimmer-sweep 3.2s ease-in-out infinite;
  pointer-events: none;
}

.shimmer-button__content {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.dot-flash {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.9);
  animation: dot-pulse 1s ease-in-out infinite;
}

@keyframes shimmer-sweep {
  0% {
    transform: translateX(-120%);
  }
  55%,
  100% {
    transform: translateX(120%);
  }
}

@keyframes dot-pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .shimmer-button__shine {
    animation: none;
    opacity: 0.25;
  }
}
</style>
