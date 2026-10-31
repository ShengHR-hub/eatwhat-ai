// 卡组耗尽 → 换一批 的请求/响应对照（验收证据）
// 用法：node scripts/exhaust.mjs [url] [outDir]
// 做法：包一层 window.fetch 记账，逐张"换一个"划到底，再点"换一批"，
//       打印两次请求体 + 返回的 dish_id 列表 + 过滤后剩余数。
import { mkdirSync, writeFileSync } from 'node:fs'

const url = process.argv[2] || 'http://127.0.0.1:5173/m/home'
const outDir = process.argv[3] || 'docs/review/deck-gesture'
const width = 390
const height = 844

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(outDir, { recursive: true })

async function wsUrl() {
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/version')
      const json = await res.json()
      if (json.webSocketDebuggerUrl) return json.webSocketDebuggerUrl
    } catch {
      /* Chrome 未就绪 */
    }
    await sleep(250)
  }
  throw new Error('连不上 9222')
}

const ws = new WebSocket(await wsUrl())
let seq = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data)
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id)
    pending.delete(msg.id)
    msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result)
  }
})
await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true })
  ws.addEventListener('error', reject, { once: true })
})

function send(method, params = {}, sessionId) {
  const id = ++seq
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    ws.send(JSON.stringify({ id, method, params, sessionId }))
  })
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })
await send('Page.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 2, mobile: true }, sessionId)
await send('Runtime.enable', {}, sessionId)
await send('Page.navigate', { url }, sessionId)
await sleep(5000)

const evaluate = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId)
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text)
  return r.result?.value
}

let frame = 0
async function shoot(label) {
  frame += 1
  const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, sessionId)
  const name = `${outDir}/${String(frame).padStart(2, '0')}-${label}.png`
  writeFileSync(name, Buffer.from(data, 'base64'))
  console.log('frame', name)
}

// —— 网络记账：只记 /recommend/single ——
await evaluate(`(() => {
  window.__calls = []
  const raw = window.fetch
  window.fetch = async (input, init) => {
    const res = await raw(input, init)
    try {
      const url = typeof input === 'string' ? input : input.url
      if (url.includes('/recommend/single')) {
        const body = init && init.body ? JSON.parse(init.body) : null
        const clone = await res.clone().json()
        window.__calls.push({
          at: new Date().toISOString(),
          body,
          count: clone.recommendations ? clone.recommendations.length : 0,
          ids: clone.recommendations ? clone.recommendations.map((d) => d.dish_id) : [],
          top: clone.recommendations && clone.recommendations[0] ? clone.recommendations[0].name : null,
        })
      }
    } catch (err) {
      console.warn('record fail', err)
    }
    return res
  }
  return 'hooked'
})()`)

await evaluate(`window.scrollTo(0, 520)`)
await sleep(500)
await shoot('deck-before-exhaust')
const batch1 = await evaluate(
  "[...document.querySelectorAll('.chip')].map((c) => Number(c.dataset.dishId))",
)
console.log('batch1 ids:', batch1.length)

// —— 逐张"换一个"划到底（按钮与手势等价，走同一 flyAway） ——
let guard = 0
for (;;) {
  const left = await evaluate(`document.querySelectorAll('.deck__top').length`)
  if (!left) break
  const clicked = await evaluate(`(() => {
    const b = [...document.querySelectorAll('.deck-actions .act')].find((n) => n.textContent.includes('换一个'))
    if (!b || b.disabled) return 'blocked'
    b.click()
    return 'ok'
  })()`)
  if (clicked !== 'ok') break
  await sleep(560)
  guard += 1
  if (guard > 60) break
}
console.log('swiped cards:', guard)
await sleep(500)
await shoot('deck-exhausted')

const emptyText = await evaluate(`document.querySelector('.exhausted__title')?.textContent || ''`)
console.log('empty state:', emptyText)

// —— 换一批：重新请求并按 dish_id 过滤 ——
const refill = await evaluate(`(() => {
  const b = [...document.querySelectorAll('.exhausted .act')].find((n) => n.textContent.includes('换一批'))
  if (!b) return 'no-refill-button'
  b.click()
  return 'clicked'
})()`)
console.log('refill:', refill)
await sleep(2200)
await shoot('deck-round-done')

const after = await evaluate(`({
  emptyText: document.querySelector('.exhausted__title')?.textContent || '',
  sub: document.querySelector('.exhausted__sub')?.textContent || '',
  deckCards: document.querySelectorAll('.deck__top').length,
  calls: window.__calls,
})`)
const calls = after.calls || []
const last = calls[calls.length - 1] || null
const seen = new Set(batch1)
const overlap = last ? last.ids.filter((id) => seen.has(id)).length : 0
const remaining = last ? last.ids.filter((id) => !seen.has(id)).length : 0
const evidence = {
  batch1: { count: batch1.length, ids: batch1 },
  refillRequest: last ? last.body : null,
  refillResponse: last ? { count: last.count, ids: last.ids } : null,
  overlapWithSwiped: overlap,
  remainingAfterFilter: remaining,
  emptyState: after.emptyText,
  sub: after.sub,
  deckCards: after.deckCards,
}
console.log(JSON.stringify(evidence, null, 2))
writeFileSync(outDir + '/refill-evidence.json', JSON.stringify(evidence, null, 2))

// —— 重置再看一轮：清空已划记录，重新装组 ——
const reset = await evaluate(`(() => {
  const b = [...document.querySelectorAll('.exhausted .act')].find((n) => n.textContent.includes('重置'))
  if (!b) return 'no-reset-button'
  b.click()
  return 'clicked'
})()`)
console.log('reset:', reset)
await sleep(2200)
await shoot('deck-after-reset')
console.log('cards after reset:', await evaluate(`document.querySelectorAll('.deck__top').length`))

await send('Target.closeTarget', { targetId })
ws.close()
