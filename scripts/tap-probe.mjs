// 触摸点击探针：验证「点卡片是否真的能打开雷达弹层」
// 用法：node scripts/tap-probe.mjs [url]
// 做的事：CDP 开触摸模拟 → 真派发 touchStart/touchEnd → 读弹层状态 → 再派发一次鼠标 click 做对照
import { writeFileSync } from 'node:fs'

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
  throw new Error('连不上 9222，先启动 Chrome --headless=new --remote-debugging-port=9222')
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

const point = await evalJs(`(() => {
  const card = document.querySelector('.deck__top')
  if (!card) return null
  const r = card.getBoundingClientRect()
  return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height * 0.45) }
})()`)
if (!point) throw new Error('找不到 .deck__top，页面可能还在加载')

const state = () => evalJs(`(() => {
  const sheet = document.querySelector('.radar-sheet, .sheet, [data-radar]')
  return {
    hasSheet: !!sheet,
    sheetVisible: sheet ? getComputedStyle(sheet).display !== 'none' && sheet.getBoundingClientRect().height > 0 : false,
    bodyText: (document.body.innerText || '').includes('五维解释'),
  }
})()`)

const before = await state()

// 1) 真触摸 tap
await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: point.x, y: point.y, radiusX: 3, radiusY: 3, force: 1 }] }, sessionId)
await sleep(60)
await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }, sessionId)
await sleep(900)
const afterTouch = await state()
const shot1 = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, sessionId)
writeFileSync('D:/EatWhat/docs/review/deck-gesture/tap-touch.png', Buffer.from(shot1.data, 'base64'))

// 2) 对照：鼠标 click（同一坐标）
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 }, sessionId)
await sleep(60)
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 }, sessionId)
await sleep(900)
const afterMouse = await state()

console.log(JSON.stringify({ point, before, afterTouch, afterMouse }, null, 2))
await send('Target.closeTarget', { targetId })
ws.close()
