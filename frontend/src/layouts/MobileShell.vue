<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppTabBar from '../components/AppTabBar.vue'

const route = useRoute()

/*
 * full 布局（首页专用，MOBILE_VISUAL_SPEC §4.3）：
 *   锁 100dvh、禁滚动，内容区自己吃掉剩余高度。
 * 其余页面保持文档流滚动。
 * 底部留出 Tab 栏的真实占位（52px 栏 + 8px 间距 + 安全区），这样页面内容永远不会被 Tab 压住。
 */
const isFull = computed(() => Boolean(route.meta?.full))
const isFlush = computed(() => Boolean(route.meta?.flush))
const savedBg = ref(null)

/**
 * 背景图存在 localStorage，但外壳只在挂载时读一次，
 * 结果在「我的」里换完背景，除了首页以外都不更新。
 * 改成：切页时重读 + 保存时派发事件通知。
 */
function loadBackground() {
  try {
    savedBg.value = JSON.parse(localStorage.getItem('eatwhat.v5.background') || 'null')
  } catch {
    savedBg.value = null
  }
}
loadBackground()

watch(() => route.fullPath, loadBackground)
onMounted(() => window.addEventListener('eatwhat:background-changed', loadBackground))
onBeforeUnmount(() => window.removeEventListener('eatwhat:background-changed', loadBackground))
const globalBgStyle = computed(() => {
  const bg = savedBg.value
  if (!bg || bg.mode !== 'image' || !bg.url) return ''
  return `background-image: url("${bg.url}"); background-size: cover; background-position: center;`
})
const adaptiveTheme = computed(() => {
  const bg = savedBg.value
  if (!bg || bg.mode !== 'image' || !bg.url) {
    return {
      '--v5-text': 'var(--v5-ink)',
      '--v5-muted': 'rgb(var(--rgb-v5-ink) / .68)',
      '--v5-dim': 'rgb(var(--rgb-v5-ink) / .5)',
      '--v5-line': 'rgb(var(--rgb-v5-ink) / .12)',
      '--v5-surface': 'rgb(var(--rgb-v5-paper-strong) / .62)',
      '--v5-surface-strong': 'rgb(var(--rgb-v5-paper-strong) / .8)',
      '--v5-btn-bg': 'var(--v5-ink)',
      '--v5-btn-text': 'var(--v5-paper-strong)',
      '--v5-scrim': 'var(--v5-photo-overlay-light)',
    }
  }
  const lightText = Number(bg.luminance ?? 0.5) < 0.5
  return {
    '--v5-text': lightText ? 'var(--v5-photo-ink)' : 'var(--v5-ink)',
    '--v5-muted': lightText ? 'rgb(var(--rgb-v5-photo-ink) / .72)' : 'rgb(var(--rgb-v5-ink) / .68)',
    '--v5-dim': lightText ? 'rgb(var(--rgb-v5-photo-ink) / .5)' : 'rgb(var(--rgb-v5-ink) / .5)',
    '--v5-line': lightText ? 'rgb(var(--rgb-v5-photo-ink) / .18)' : 'rgb(var(--rgb-v5-ink) / .12)',
    '--v5-surface': lightText ? 'rgb(var(--rgb-v5-shadow) / .58)' : 'rgb(var(--rgb-v5-paper-strong) / .62)',
    '--v5-surface-strong': lightText ? 'rgb(var(--rgb-v5-shadow) / .82)' : 'rgb(var(--rgb-v5-paper-strong) / .82)',
    '--v5-btn-bg': lightText ? 'var(--v5-photo-ink)' : 'var(--v5-ink)',
    '--v5-btn-text': lightText ? 'var(--v5-photo-paper)' : 'var(--v5-paper-strong)',
    '--v5-scrim': lightText ? 'var(--v5-photo-overlay-dark)' : 'var(--v5-photo-overlay-light)',
  }
})
const globalScrimStyle = computed(() => {
  const bg = savedBg.value
  if (!bg || bg.mode !== 'image' || !bg.url) return 'display: none;'
  return `background: ${adaptiveTheme.value['--v5-scrim']}; opacity: ${Math.max(.28, Number(bg.overlay ?? 42) / 100)};`
})
</script>

<template>
  <div class="shell" :class="[isFull ? 'shell--full' : 'shell--flow', isFlush ? 'shell--flush' : '']" :style="adaptiveTheme">
    <div class="v5-global-bg" :style="globalBgStyle"></div>
    <div class="v5-global-scrim" :style="globalScrimStyle"></div>
    <div class="shell__body">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
    <AppTabBar />
  </div>
</template>

<style scoped>
.shell {
  position: relative;
  background: var(--v5-paper);
  margin: 0 auto;
  width: 100%;
  max-width: 390px;
  box-sizing: border-box;
  overflow-x: hidden;
  padding: env(safe-area-inset-top, 0px) 0 0;
}

/* 文档流页面：统一在手机框内滚动，底部给 Tab 栏让位 */
.shell--flow {
  --color-text: var(--v5-text);
  --color-text-soft: var(--v5-muted);
  --color-line: var(--v5-line);
  --on-glass: var(--v5-text);
  --on-glass-soft: var(--v5-muted);
  --on-glass-dim: var(--v5-dim);
  --on-glass-line: var(--v5-line);
  --glass-card-fill: var(--v5-surface);
  --glass-card-fill-matte: var(--v5-surface);
  --glass-card-edge: rgb(var(--rgb-white) / .82);
  --glass-card-inner-top: rgb(var(--rgb-white) / .9);
  --glass-card-inner-bottom: rgb(var(--rgb-white) / .2);
  --glass-card-shadow: 0 12px 30px rgb(var(--rgb-v5-shadow) / .06);
  --glass-bg: rgb(var(--rgb-v5-soft) / .78);
  --glass-shadow: 0 8px 26px rgb(var(--rgb-v5-shadow) / .08);
  background: transparent;
  display: flex;
  height: 100dvh;
  overflow: hidden;
  padding-bottom: 0;
}

.shell--flow .shell__body {
  padding: 12px 22px calc(104px + env(safe-area-inset-bottom, 0px));
  overflow-y: auto;
}

/* 一屏页面：视口高度固定，内容区 flex 分配剩余空间 */
.shell--flush {
  padding: 0;
}

.shell--flush.shell--full {
  padding-bottom: 0;
}

.shell--full .shell__body {
  padding: 0;
}

.shell--full {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  overflow: hidden;
  padding-bottom: 0;
}

.shell--flow :deep(.btn-ink) {
  background: var(--v5-btn-bg) !important;
  color: var(--v5-btn-text) !important;
}

.shell--flow :deep(.member__host) {
  color: var(--v5-paper-strong);
}

.shell--flow :deep(.gene__track) {
  background: rgb(var(--rgb-v5-ink) / .1) !important;
}

.shell--flow :deep(.gene__fill) {
  background: var(--v5-text) !important;
}

.shell--flow :deep(.pick--on),
.shell--flow :deep(.tag--buy),
.shell--flow :deep(.vote--super_like) {
  color: var(--v5-paper-strong) !important;
}

.shell--flow :deep(.vote--super_like small) {
  color: rgb(var(--rgb-v5-paper-strong) / .72) !important;
}

.v5-global-bg,
.v5-global-scrim {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.v5-global-bg { z-index: 0; }
.v5-global-scrim { z-index: 1; }

.shell__body {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
}

@media (min-width: 900px) {
  .shell {
    height: 812px;
    max-height: calc(100dvh - 48px);
    overflow: hidden;
    border: 1px solid rgb(var(--rgb-white) / .72);
    border-radius: 42px;
    background: var(--v5-paper);
    box-shadow: 0 32px 90px rgb(var(--rgb-v5-shadow) / .16), 0 2px 8px rgb(var(--rgb-v5-shadow) / .08);
  }

  .shell--full {
    height: 812px;
  }

  .shell--flow {
    height: 812px;
    overflow-y: auto;
  }
}
</style>
