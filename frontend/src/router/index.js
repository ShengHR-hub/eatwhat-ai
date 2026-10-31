import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../api/client'

/**
 * 路由分区（v2.3.1 结构）：
 *   /m/*      移动端（Capacitor 打包目标）
 *   /admin/*  PC 管理后台（批次 4，当前未开工）
 * 批次 2：Home / Footprint / Profile / 沙盒抽屉；批次 3：Fridge / Room（多人实时）。
 */
const routes = [
  { path: '/', redirect: '/m/home' },

  {
    path: '/m',
    component: () => import('../layouts/MobileShell.vue'),
    children: [
      { path: '', redirect: '/m/home' },
      {
        path: 'home',
        name: 'home',
        component: () => import('../views/mobile/HomeV5Exact.vue'),
        /* full：首页锁一屏（MOBILE_VISUAL_SPEC §4.3），由 MobileShell 切成 100dvh 禁滚布局 */
        meta: { title: '首页', full: true, flush: true },
      },
      {
        path: 'footprint',
        name: 'footprint',
        component: () => import('../views/mobile/FootprintV5.vue'),
        meta: { title: '足迹' },
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('../views/mobile/Profile.vue'),
        meta: { title: '我的' },
      },
      {
        path: 'fridge',
        name: 'fridge',
        component: () => import('../views/mobile/Fridge.vue'),
        meta: { title: '虚拟冰箱', batch: 3 },
      },
      {
        path: 'room',
        name: 'room',
        component: () => import('../views/mobile/Room.vue'),
        meta: { title: '干饭房', batch: 3 },
      },
    ],
  },

  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },

  { path: '/admin', redirect: '/admin/data' },
  {
    path: '/admin/data',
    name: 'admin-data',
    component: () => import('../views/admin/DataManage.vue'),
    meta: { title: '数据管理' },
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('../views/admin/Users.vue'),
    meta: { title: '用户管理' },
  },
  {
    path: '/admin/users/:id',
    name: 'admin-user-detail',
    component: () => import('../views/admin/UserDetail.vue'),
    meta: { title: '用户画像' },
  },
  {
    path: '/admin/settings',
    name: 'admin-settings',
    component: () => import('../views/admin/Settings.vue'),
    meta: { title: '算法参数' },
  },
  {
    path: '/admin/import',
    name: 'admin-import',
    component: () => import('../views/admin/Import.vue'),
    meta: { title: '数据导入' },
  },
  {
    path: '/admin/audit',
    name: 'admin-audit',
    component: () => import('../views/admin/AuditLog.vue'),
    meta: { title: '审计日志' },
  },
  {
    path: '/admin/dashboard',
    name: 'admin-dashboard',
    component: () => import('../views/admin/ExperimentDashboard.vue'),
    meta: { title: '实验大屏' },
  },

  { path: '/:pathMatch(.*)*', redirect: '/m/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// 后台必须登录才能进：以前没有任何守卫，直接输 /admin 就能看到后台界面
// （数据靠后端 401 兜底，但页面身份与真实用户无关，答辩时容易被问住）。
router.beforeEach((to) => {
  if (!to.path.startsWith('/admin')) return true
  if (getToken()) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · 食刻 EatWhat` : '食刻 EatWhat AI'
})

export default router
