import { api } from './client'

const clean = (params = {}) => Object.fromEntries(
  Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
)

export function fetchAdminRestaurants(params = {}) {
  return api.get('/admin/restaurants', clean(params))
}

export function createAdminRestaurant(payload) {
  return api.post('/admin/restaurants', payload)
}

export function updateAdminRestaurant(id, payload) {
  return api.put(`/admin/restaurants/${id}`, payload)
}

export function deleteAdminRestaurant(id) {
  return api.del(`/admin/restaurants/${id}`)
}

export function fetchAdminDishes(params = {}) {
  return api.get('/admin/dishes', clean(params))
}

export function createAdminDish(payload) {
  return api.post('/admin/dishes', payload)
}

export function updateAdminDish(id, payload) {
  return api.put(`/admin/dishes/${id}`, payload)
}

export function deleteAdminDish(id) {
  return api.del(`/admin/dishes/${id}`)
}

export function tagAdminDishes(dishIds) {
  return api.post('/admin/llm-tag', { dish_ids: dishIds })
}

export function fetchAdminExperiments(params = {}) {
  return api.get('/admin/experiments', clean(params))
}

/** G3 仿真底表：只读，数据由 backend/scripts/import_simulation.py 导入 */
export function fetchSimulationRuns() {
  return api.get('/admin/stats/simulation/runs')
}

/** 单次仿真的聚合指标（含 14 天窗口重样与 200 人分布） */
export function fetchSimulationRun(id) {
  return api.get(`/admin/stats/simulation/runs/${id}`)
}

export function fetchAdminStats(path, params = {}) {
  return api.get(`/admin/stats/${path}`, clean(params))
}

export const ADMIN_STATS_PATHS = [
  'overview',
  'geo',
  'calendar',
  'heatmap',
  'cuisine',
  'cuisine-trend',
  'personas',
  'scatter',
  'flow',
  'keywords',
  'race',
  'cooccurrence',
  'quality',
]

/** 审计日志：只读，仅 ADMIN。limit/offset 分页，可按动作、资源类型、操作人过滤。 */
export function fetchAuditLogs(params = {}) {
  return api.get('/admin/audit-logs', clean(params))
}

/* ── 用户管理 ── */
export function fetchAdminUsers(params = {}) {
  return api.get('/admin/users', clean(params))
}

export function updateUserRole(userId, role) {
  return api.patch(`/admin/users/${userId}/role`, { role })
}

/* ── 算法参数 ── */
export function fetchAlgoSettings() {
  return api.get('/admin/settings/algo')
}

export function saveAlgoSettings(values) {
  return api.put('/admin/settings/algo', values)
}

/* ── 打标任务队列 ── */
export function createTagJob(dishIds) {
  return api.post('/admin/tag-jobs', { dish_ids: dishIds })
}

export function fetchTagJobs(limit = 8) {
  return api.get('/admin/tag-jobs', { limit })
}

export function fetchTagJob(jobId) {
  return api.get(`/admin/tag-jobs/${jobId}`)
}

/* ── 数据导入 ── */
export function previewImport(file) {
  const body = new FormData()
  body.append('file', file)
  return api.postForm('/admin/import/preview', body)
}

export function commitImport(payload) {
  return api.post('/admin/import/commit', payload)
}

/** 单个用户画像：偏好向量、预算、菜系分布、满意度与最近决策 */
export function fetchUserOverview(userId) {
  return api.get(`/admin/users/${userId}/overview`)
}
