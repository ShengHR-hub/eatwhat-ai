<script setup>
/**
 * 底部 Tab 栏：小面积悬浮件 → 允许用玻璃（第六章 §2.6 适用范围）。
 * 图标一律单色（currentColor），不出现双色图标。
 */
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { name: '首页', to: '/m/home', key: 'home' },
  { name: '足迹', to: '/m/footprint', key: 'footprint' },
  { name: '冰箱', to: '/m/fridge', key: 'fridge' },
  { name: '房间', to: '/m/room', key: 'room' },
  { name: '我的', to: '/m/profile', key: 'profile' },
]

const isActive = (tab) => route.path.startsWith(tab.to)
</script>

<template>
  <nav class="tabbar-wrap">
    <div class="glass-shell tabbar weather-pill">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.to"
        class="tab"
        :data-active="isActive(tab)"
      >
        <svg v-if="tab.key === 'home'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z" stroke-linejoin="round" />
        </svg>
        <svg v-else-if="tab.key === 'footprint'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <circle cx="8" cy="13" r="4.2" />
          <circle cx="16" cy="11" r="4.2" />
          <path d="M3 20.5c1.6-2.2 3.4-3.2 5-3.2s3.4 1 5 3.2" stroke-linecap="round" />
        </svg>
        <svg v-else-if="tab.key === 'fridge'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <rect x="5" y="3.5" width="14" height="17" rx="3" />
          <path d="M5 10h14M9 6.5v1.8M9 13v2.2" stroke-linecap="round" />
        </svg>
        <svg v-else-if="tab.key === 'room'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <circle cx="9" cy="9" r="3" />
          <circle cx="16.5" cy="10" r="2.3" />
          <path d="M3.8 19c.5-3 2.5-4.5 5.2-4.5s4.7 1.5 5.2 4.5M14 14.8c2.7-.4 5.1.8 6 3.4" stroke-linecap="round" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <circle cx="12" cy="8.5" r="3.6" />
          <path d="M4.5 20c1.3-3.6 4-5.4 7.5-5.4s6.2 1.8 7.5 5.4" stroke-linecap="round" />
        </svg>
        <span class="tab-label">{{ tab.name }}</span>
      </RouterLink>
    </div>
  </nav>
</template>

<style scoped>
.tabbar-wrap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  display: flex;
  justify-content: center;
  padding: 0 16px calc(8px + env(safe-area-inset-bottom, 0px));
}

.tabbar,
.tabbar.glass-shell {
  display: flex;
  width: min(390px, 100%);
  align-items: center;
  justify-content: space-around;
  padding: 6px 8px;
  background: var(--v5-surface-strong, rgb(var(--rgb-v5-soft) / .82)) !important;
  border: 1px solid var(--v5-line, rgb(var(--rgb-white) / .86));
  box-shadow: 0 8px 26px rgb(var(--rgb-v5-shadow) / .1);
  -webkit-backdrop-filter: blur(24px) saturate(1.16);
  backdrop-filter: blur(24px) saturate(1.16);
  /* 一屏口径：栏体 52px（含内边距），加上下方 8px 呼吸，正好对应 MobileShell 预留的 60px */
}

.tab {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  border-radius: 999px;
  padding: 5px 0;
  color: var(--v5-muted, rgb(var(--rgb-v5-ink) / .55)) !important;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.tab svg {
  width: 19px;
  height: 19px;
}

.tab-label {
  font-size: 10px;
  line-height: 1;
  letter-spacing: 0.02em;
}

/* 选中态：深灰实底白字（不靠颜色区分） */
.tab[data-active='true'] {
  color: var(--v5-btn-text, var(--v5-ink)) !important;
  background-color: var(--v5-btn-bg, rgb(var(--rgb-white) / .62));
}
</style>
