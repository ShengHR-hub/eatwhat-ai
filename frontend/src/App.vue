<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppBackdrop from './components/backdrop/AppBackdrop.vue'
import GlassFilters from './components/GlassFilters.vue'

const route = useRoute()
const isMobile = computed(() => route.path.startsWith('/m'))
// 后台是浅色长读界面：不能再挂深色 Grainient 底，否则路由切换的过渡帧会露黑
const isAdmin = computed(() => route.path.startsWith('/admin'))
</script>

<template>
  <AppBackdrop v-if="!isMobile && !isAdmin" />
  <!-- 液态玻璃卡的 SVG 折射滤镜，全局只挂一份 -->
  <GlassFilters />
  <div class="relative z-10 min-h-dvh" :class="[isMobile ? 'v5-stage' : '', isAdmin ? 'admin-stage' : '']">
    <router-view v-slot="{ Component }">
      <transition :name="isAdmin ? 'admin-swap' : 'fade'" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style scoped>
.v5-stage {
  min-height: 100dvh;
  background: var(--v5-bg);
}

.admin-stage {
  min-height: 100dvh;
  background: var(--admin-bg);
}

/* 后台内部切页不做淡入淡出：过渡帧会露出 body 的深色底 */
.admin-swap-enter-active,
.admin-swap-leave-active { transition: none; }

@media (min-width: 900px) {
  .v5-stage {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
}
</style>
