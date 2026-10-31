<script setup>
/**
 * 状态/情绪气泡。规范 2.7：`filter` / `badge` 组合，选中态深灰实底白字。
 * 点击回弹用 @vueuse/motion 的 tapped 变体（stiffness 300 / damping 20）。
 *
 * 气泡与模式的匹配规则由后端裁决：不匹配的会被塞进 bubble_effects.ignored，
 * 这里只负责"当前模式下不可点"的视觉提示，不做过滤逻辑。
 */
import { computed } from 'vue'
import { BUBBLES } from '../constants/bubbles'
import { useModeStore } from '../stores/mode'

const mode = useModeStore()

const bubbles = computed(() =>
  BUBBLES.map((b) => ({
    ...b,
    enabled: b.modes.includes(mode.modeType),
    active: mode.bubbles.includes(b.id),
  })),
)
</script>

<template>
  <div class="bubble-row" role="group" aria-label="此刻的状态">
    <button
      v-for="bubble in bubbles"
      :key="bubble.id"
      v-motion
      type="button"
      class="bubble"
      :data-active="bubble.active"
      :data-disabled="!bubble.enabled"
      :aria-pressed="bubble.active"
      :aria-disabled="!bubble.enabled"
      :disabled="!bubble.enabled"
      :initial="{ scale: 1 }"
      :tapped="{ scale: [0.94, 1] }"
      :transition="{ type: 'spring', stiffness: 300, damping: 20 }"
      :title="bubble.enabled ? bubble.label : `当前模式不可用：${bubble.label}`"
      @click="mode.toggleBubble(bubble.id)"
    >
      <span class="bubble-text">{{ bubble.short }}</span>
    </button>
  </div>
</template>

<style scoped>
.bubble-row {
  /* 单行六列：紧凑呼吸原则（MOBILE_VISUAL_SPEC 增补）—— 高度 30px、字号 12px。
     6 个气泡一行铺满，面板整体高度因此少一整行。 */
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 5px;
}

.bubble {
  border-radius: 999px;
  /* 深色玻璃口径：默认是"玻璃小片"，选中态才填实白 */
  border: 1px solid var(--on-glass-line);
  background: rgb(var(--rgb-white) / 0.08);
  height: 30px;
  padding: 0 2px;
  font-size: 11.5px;
  font-weight: 550;
  letter-spacing: -0.01em;
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--on-glass-soft);
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease;
}

.bubble[data-active='true'] {
  background: rgb(var(--rgb-white) / 0.92);
  border-color: rgb(var(--rgb-white) / 0.92);
  color: var(--color-ink);
  font-weight: 650;
}

.bubble[data-disabled='true'] {
  opacity: 0.28;
  cursor: not-allowed;
  text-decoration: line-through;
}
</style>
