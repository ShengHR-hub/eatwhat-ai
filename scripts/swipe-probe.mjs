// 触摸左划探针：确认改成 onRelease 点击判定后，划卡仍然生效（不会被误判成点击）
// 用法：node scripts/swipe-probe.mjs [url]
const url = process.argv[2] || 'http://127.0.0.1:5173/m/home'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function getWsUrl() {
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/version')
      const json = await res.json()
      if (json.webSocketDebuggerUrl) return json.webSocketDebuggerUrl
    } catch {
      /* Chrome 没起来 */
    }
    await sleep(250)
  }
  throw new Error('连不上 9222')
}

const ws = new WebSocket(await getWsUrl())
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
const send = (method, params = {}, sessionId) => {
  const id = ++seq
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    ws.send(JSON.stringify({ id, method, params, sessionId }))
  })
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })
await send('Page.enable', {}, sessionId)
await send('Runtime.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', { width: 393, height: 852, deviceScaleFactor: 2, mobile: true }, sessionId)
await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }, sessionId)
await send('Page.navigate', { url }, sessionId)
await sleep(5000)

const evalJs = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId)
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text)
  return r.result.value
}

const start = await evalJs(`(() => {
  const card = document.querySelector('.deck__top')
  const r = card.getBoundingClientRect()
  return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height * 0.5), name: document.querySelector('.dishcard h2, .dishcard__name')?.textContent?.trim() }
})()`)

const touch = (type, x, y) =>
  send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, radiusX: 4, radiusY: 4, force: 1 }] }, sessionId)

await touch('touchStart', start.x, start.y)
for (let i = 1; i <= 10; i += 1) {
  await sleep(28)
  await touch('touchMove', start.x - i * 16, start.y)
}
await sleep(60)
await touch('touchEnd', 0, 0)
await sleep(1400)

const after = await evalJs(`(() => ({
  decisions: window.__eatwhatDecisions ? window.__eatwhatDecisions() : null,
  topName: document.querySelector('.dishcard h2, .dishcard__name')?.textContent?.trim(),
  sheetOpen: (document.body.innerText || '').includes('五维解释'),
}))()`)

console.log(JSON.stringify({ start, after }, null, 2))
await send('Target.closeTarget', { targetId })
ws.close()
