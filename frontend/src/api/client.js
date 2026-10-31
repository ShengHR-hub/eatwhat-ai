/**
 * 唯一的后端出口。路由前缀 /api/v1 由 Vite 代理转发到 127.0.0.1:8000，
 * 前端任何地方都不许再拼后端域名。
 *
 * 身份口径（v2.3.5）：演示级 X-User-Id 请求头，必填；后端对缺失/非法/
 * 未知身份一律 4xx，不会回退用户 1。本地只在首次进入时用演示角色 1。
 * POST /auth/login 已删除，不要复活它。
 */
const API_ORIGIN = (import.meta.env.VITE_API_ORIGIN || '').replace(/\/$/, '')
const BASE = `${API_ORIGIN}/api/v1`
const STORAGE_KEY = 'eatwhat.userId'
const TOKEN_KEY = 'eatwhat.token'

function normalizeUserId(raw, fallback = 1) {
  const value = Number(raw)
  return Number.isInteger(value) && value > 0 ? value : fallback
}

const storedRaw = localStorage.getItem(STORAGE_KEY)
let currentUserId = normalizeUserId(storedRaw)
let currentToken = localStorage.getItem(TOKEN_KEY) || ''
if (storedRaw !== null && String(currentUserId) !== String(storedRaw)) {
  console.warn(`已丢弃非法本地身份 ${storedRaw}，本次演示使用用户 ${currentUserId}`)
  localStorage.setItem(STORAGE_KEY, String(currentUserId))
}

export function setUserId(id) {
  const next = Number(id)
  if (!Number.isInteger(next) || next <= 0) {
    throw new Error(`非法用户身份：${id}`)
  }
  currentUserId = next
  localStorage.setItem(STORAGE_KEY, String(currentUserId))
}

export function getUserId() {
  return currentUserId
}

export function setToken(token) {
  currentToken = String(token || '')
  if (currentToken) localStorage.setItem(TOKEN_KEY, currentToken)
  else localStorage.removeItem(TOKEN_KEY)
}

export function getToken() {
  return currentToken
}

export function clearToken() {
  setToken('')
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request(path, { method = 'GET', body, query } = {}) {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return
      url.searchParams.set(key, String(value))
    })
  }

  const requestUrl = API_ORIGIN ? url.toString() : url.pathname + url.search

  const isFormData = body instanceof FormData
  let response
  try {
    response = await fetch(requestUrl, {
      method,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        'X-User-Id': String(currentUserId),
        ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
      },
      body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
    })
  } catch (err) {
    throw new ApiError('后端没连上，检查 uvicorn 是否在 8000 端口', 0, err?.message)
  }

  const text = await response.text()
  const data = text ? safeParse(text) : null

  if (!response.ok) {
    const detail = data?.detail ?? data ?? `HTTP ${response.status}`
    // S05：5xx 的响应体可能是 "Internal Server Error" 这类原文，不能直接展示给用户。
    // 统一换成可读提示，原始内容只留在 ApiError.detail 里供排查。
    const message =
      response.status >= 500
        ? '服务暂时开小差了，请稍后重试'
        : typeof detail === 'string'
          ? detail
          : '请求没有成功，请检查输入后再试'
    throw new ApiError(message, response.status, detail)
  }
  return data
}

function safeParse(text) {
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export const api = {
  get: (path, query) => request(path, { query }),
  post: (path, body, query) => request(path, { method: 'POST', body, query }),
  // 文件上传走 FormData：request 内部已判断 isFormData，不设 Content-Type 让浏览器带 boundary
  postForm: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  del: (path) => request(path, { method: 'DELETE' }),
}
