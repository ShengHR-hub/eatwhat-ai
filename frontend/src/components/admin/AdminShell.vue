<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken, getToken } from '../../api/client'
import { fetchMe } from '../../api'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  /** flush：不要页面标题区、主区不滚动，内容自己撑满（大屏用） */
  flush: { type: Boolean, default: false },
})

const router = useRouter()
const logged = computed(() => Boolean(getToken()))
// 以前这里写死「测试账号 / ADMIN」，未登录也这么显示，身份是假的。
// 现在拉一次 /auth/me，显示真实昵称与角色；拉不到就留空，不编。
const me = ref(null)
onMounted(async () => {
  if (!logged.value) return
  try {
    me.value = await fetchMe()
  } catch {
    me.value = null
  }
})

function logout() {
  clearToken()
  router.push('/login')
}
</script>

<template>
  <div class="admin-shell">
    <!-- 侧栏（v7 设计稿：220px，数据 / 分析两组） -->
    <aside class="admin-side">
      <div class="admin-side__brand">
        <span class="admin-side__mark" aria-hidden="true">食</span>
        <span class="admin-side__copy">
          <b>食刻 EatWhat</b>
          <small>ADMIN</small>
        </span>
      </div>

      <nav class="admin-side__nav" aria-label="后台导航">
        <p class="admin-side__label">数据</p>
        <RouterLink to="/admin/data" class="admin-side__item" active-class="is-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h10" />
          </svg>
          数据管理
        </RouterLink>
        <RouterLink to="/admin/audit" class="admin-side__item" active-class="is-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M9 5h9M9 12h9M9 19h9M4 5h1M4 12h1M4 19h1" />
          </svg>
          审计日志
        </RouterLink>

        <p class="admin-side__label">分析</p>
        <RouterLink to="/admin/dashboard" class="admin-side__item" active-class="is-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M4 19V9M10 19V5M16 19v-6M22 19H2" />
          </svg>
          实验大屏
        </RouterLink>
        <!-- 子导航：目前只有大屏用，用来把分析主题收进侧栏 -->
        <slot name="subnav" />

        <p class="admin-side__label">系统</p>
        <RouterLink to="/admin/users" class="admin-side__item" active-class="is-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <circle cx="12" cy="8" r="3.2" />
            <path d="M5 20c0-3.3 3.1-5.5 7-5.5s7 2.2 7 5.5" />
          </svg>
          用户管理
        </RouterLink>
        <RouterLink to="/admin/settings" class="admin-side__item" active-class="is-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6L17 7M7 17l-1.4 1.4" />
          </svg>
          算法参数
        </RouterLink>
        <RouterLink to="/admin/import" class="admin-side__item" active-class="is-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M12 4v10M8 10l4 4 4-4M4 18h16" />
          </svg>
          数据导入
        </RouterLink>
      </nav>

      <div class="admin-side__foot">
        <div class="admin-side__who">
          <span class="admin-side__avatar">{{ (me?.nickname || me?.username || '未').slice(0, 1) }}</span>
          <span class="admin-side__copy">
            <b>{{ me?.nickname || me?.username || (logged ? '加载中' : '未登录') }}</b>
            <small>{{ me?.role || (logged ? '—' : 'GUEST') }}</small>
          </span>
        </div>
        <button v-if="logged" class="admin-side__logout" type="button" @click="logout">退出登录</button>
        <RouterLink v-else class="admin-side__logout" to="/login">登录</RouterLink>
      </div>
    </aside>

    <!-- 工作区：顶栏面包屑 + 页面标题 + 内容 -->
    <div class="admin-workspace">
      <header class="admin-topbar">
        <p class="admin-crumb">后台<span>/</span><b>{{ title }}</b></p>
        <div class="admin-topbar__right">
          <slot name="search" />
        </div>
      </header>

      <main class="admin-main" :class="{ 'admin-main--flush': flush }">
        <div v-if="!flush" class="admin-pagehead">
          <div>
            <h1>{{ title }}</h1>
            <p v-if="subtitle">{{ subtitle }}</p>
          </div>
          <div class="admin-pagehead__actions">
            <slot name="actions" />
          </div>
        </div>
        <slot />
      </main>
    </div>
  </div>
</template>
