/**
 * 把接口错误转成一句人能读的话。
 *
 * FastAPI 的 422 返回体是 `{detail: [{loc, msg, type}, ...]}`，
 * 直接 `error.value = err.detail` 会渲染成 `[object Object]`。
 * 各页面此前各自写 `err?.detail || err?.message`，遇到数组就露馅。
 */
export function errorText(err) {
  const detail = err?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item) => (item && (item.msg || item.message)) || '')
      .filter(Boolean)
    if (msgs.length) return msgs.join('；')
  }
  if (detail && typeof detail === 'object') {
    const msg = detail.msg || detail.message
    if (msg) return String(msg)
  }
  return err?.message || '请求失败'
}
