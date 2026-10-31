import { api, getToken } from './client'

/**
 * 接口契约按 MASTER_SPEC v2.3.1 第五章。
 * 只包这一层，页面与 store 不许直接 fetch。
 */

/** GET /context/weather —— temp/weather 走演示覆盖，source=override 时前端显示"演示"角标 */
export function fetchWeather({ city, lat, lng, temp, weather } = {}) {
  return api.get('/context/weather', { city, lat, lng, temp, weather })
}

/** POST /recommend/single */
export function fetchSingleRecommend(payload) {
  return api.post('/recommend/single', payload)
}

/** GET /users/demo-list —— 答辩演示角色一键切换的数据源 */
export function registerAccount(payload) {
  return api.post('/auth/register', payload)
}

export function loginAccount(payload) {
  return api.post('/auth/login', payload)
}

export function fetchMe() {
  return api.get('/auth/me')
}

export function logoutAccount() {
  return api.post('/auth/logout', {})
}

export function fetchDemoUsers() {
  return api.get('/users/demo-list')
}

/** GET /users/{id}/profile */
export function fetchProfile(userId) {
  return api.get(`/users/${userId}/profile`)
}

/** PUT /users/{id}/preferences —— 八维口味 + 预算 + 忌口 */
export function savePreferences(userId, payload) {
  return api.put(`/users/${userId}/preferences`, payload)
}

/** POST /users/{id}/red-black-list —— { target_type, target_id, list_type, action } */
export function updateRedBlackList(userId, payload) {
  return api.post(`/users/${userId}/red-black-list`, payload)
}

/** GET /logs/stats/{id} —— 个人战绩概览 */
export function fetchLogStats(userId) {
  return api.get(`/logs/stats/${userId}`)
}

/** GET /logs/timeline/{user_id} —— 真实足迹时间线 */
export function fetchLogTimeline(userId, limit = 50) {
  // 第二个参数直接是 query 对象（client.js 逐项转 searchParams）。
  // 写成 { params: { limit } } 会发出 ?params=[object Object]，limit 永远不生效。
  return api.get(`/logs/timeline/${userId}`, { limit })
}

/** POST /logs/checkin */
export function checkin(payload) {
  return api.post('/logs/checkin', payload)
}

/**
 * GET /catalog/dishes?ids=1,2,3 —— 只读目录。
 * 红黑榜 / 忌口台只有 id，靠它把 id 翻成名字，避免前端硬编码字典。
 */
export function fetchDishes(ids) {
  const query = Array.isArray(ids) ? ids.join(',') : ids
  return api.get('/catalog/dishes', { ids: query })
}

/** GET /catalog/restaurants?ids=1,2,3 */
export function fetchRestaurants(ids) {
  const query = Array.isArray(ids) ? ids.join(',') : ids
  return api.get('/catalog/restaurants', { ids: query })
}

/** GET /catalog/dishes?mode_type=HOME_COOKING —— 全部下厨菜谱，买菜清单选菜用 */
export function fetchHomeDishes() {
  return api.get("/catalog/dishes", { mode_type: "HOME_COOKING" })
}

/** GET /fridge/{user_id} —— 冰箱库存，临期置顶 */
export function fetchFridge(userId) {
  return api.get(`/fridge/${userId}`)
}

/** POST /fridge/{user_id} —— action: "ADD" | "REMOVE"，返回更新后的整份库存 */
export function upsertFridge(userId, payload) {
  return api.post(`/fridge/${userId}`, payload)
}

/** POST /fridge/scan —— 上传图片调用云端视觉模型，只返回候选，不入库 */
export function scanFridge(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/fridge/scan', form)
}

/** POST /fridge/{user_id}/scan-import —— 批量写入已确认的识别结果 */
export function scanImportFridge(userId, items) {
  return api.post(`/fridge/${userId}/scan-import`, { items })
}

/** POST /fridge/shopping-list —— 多菜谱主辅料并集减冰箱现有（身份只走请求头） */
export function fetchShoppingList(dishIds) {
  return api.post("/fridge/shopping-list", { dish_ids: dishIds })
}

/**
 * POST /rooms/create —— 建房（v2.3.2 契约第 315 行）
 * 传 budget 时后端按预算 1.25 倍做软上限筛候选；返回里带 10 道 candidates。
 * host_user_id 不再放 body：身份只由 client.js 统一注入 X-User-Id。
 */
export function createRoom(modeType, budget = null, overrideParams = null, campus = 'SIYUAN') {
  const payload = { mode_type: modeType, campus }
  if (budget != null) payload.budget = budget
  // F10：沙盒调过的参数随建房一起落库成快照，结算时用快照而不是读 DB
  if (overrideParams && Object.keys(overrideParams).length) {
    payload.override_params = { ...overrideParams }
  }
  return api.post('/rooms/create', payload)
}

/** POST /rooms/{code}/join —— 加入房间（幂等；身份只走请求头；v2.3.6 必带校区） */
export function joinRoom(code, campus = 'SIYUAN') {
  return api.post(`/rooms/${code}/join`, { campus })
}

/** GET /rooms/{code} —— 房间快照 */
export function fetchRoom(code) {
  return api.get(`/rooms/${code}`)
}

/** WebSocket 地址：同一 host，走 Vite 的 /ws 代理。
 *  浏览器 WS 不能设 Authorization 头，所以已登录时把令牌放查询参数，
 *  服务端据此确认"你确实是这个 user_id"，避免知道房间码就能冒充成员投票。
 */
export function roomSocketUrl(code, userId) {
  const token = getToken()
  const query = token ? `?token=${encodeURIComponent(token)}` : ''
  const configured = (import.meta.env.VITE_WS_ORIGIN || '').replace(/\/$/, '')
  if (configured) return `${configured}/ws/room/${code}/${userId}${query}`
  const proto = location.protocol === "https:" ? "wss:" : "ws:"
  return `${proto}//${location.host}/ws/room/${code}/${userId}${query}`
}

/** 改昵称 / 头像（与 preferences 分开，见后端注释） */
export function updateProfileBasic(userId, payload) {
  return api.patch(`/users/${userId}/profile`, payload)
}

/** 上传头像：multipart，后端裁成 256×256 JPEG 并返回相对路径 */
export function uploadAvatar(userId, file) {
  const body = new FormData()
  body.append('file', file)
  return api.postForm(`/users/${userId}/avatar`, body)
}

/** 满意度反馈：3=好吃 2=一般 1=踩雷 */
export function submitFeedback(logId, rating) {
  return api.post(`/logs/${logId}/feedback`, { rating })
}
