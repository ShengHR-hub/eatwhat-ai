// 卡组手势实拍：左划 / 右划确认 / 点击雷达，逐帧存图（再拼 GIF 当"录屏"证据）
// 用法：node scripts/record.mjs [url] [outDir]
// 前置：Chrome 以 --headless=new --remote-debugging-port=9222 启动（同 shot.mjs）
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

const mouse = (type, x, y, extra = {}) =>
  send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1, ...extra }, sessionId)

/** 找到顶卡中心（按当前滚动位置换算成视口坐标） */
async function cardCenter() {
  return evaluate(`(() => {
    const el = document.querySelector('.deck__top')
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), top: Math.round(r.top) }
  })()`)
}

async function drag(from, dx, steps = 6, holdMs = 90) {
  await mouse('mousePressed', from.x, from.y)
  await sleep(60)
  for (let i = 1; i <= steps; i += 1) {
    await mouse('mouseMoved', from.x + (dx * i) / steps, from.y + i * 0.6, { buttons: 1 })
    await sleep(holdMs)
  }
}

// —— 到卡组位置 ——
await evaluate(`window.scrollTo(0, 520)`)
await sleep(700)
await shoot('deck-idle')

let box = await cardCenter()
if (!box) throw new Error('找不到 .deck__top')

// —— 1. 左划：拖到 -70px 截印章，再甩出 ——
await drag(box, -70, 5, 70)
await shoot('drag-left-stamp')
await mouse('mouseMoved', box.x - 140, box.y, { buttons: 1 })
await sleep(160)
await shoot('drag-left-over')
await mouse('mouseReleased', box.x - 140, box.y)
await sleep(900)
await shoot('after-left')

// —— 2. 右划：拖到 +80px 截印章，松手进确认态 ——
box = await cardCenter()
await drag(box, 80, 5, 70)
await shoot('drag-right-stamp')
await mouse('mouseReleased', box.x + 80, box.y)
await sleep(1200)
await shoot('confirm-state')

// —— 3. 确认"就吃这个" → 出牌 ——
const ok = await evaluate(`(() => {
  const b = [...document.querySelectorAll('.confirm__btn')].find((n) => n.textContent.includes('确认'))
  if (!b) return 'no-confirm-button'
  b.click()
  return 'clicked'
})()`)
console.log('confirm:', ok)
await sleep(900)
await shoot('after-confirm')

// —— 4. 点击卡面 → 雷达弹层（拖动 <10px 才算点击） ——
box = await cardCenter()
await mouse('mousePressed', box.x, box.y)
await sleep(80)
await mouse('mouseReleased', box.x, box.y)
await sleep(900)
await shoot('radar-sheet')

// —— 5. 关掉雷达，回到卡组 ——
await evaluate(`document.querySelector('.radar-panel__close')?.click()`)
await sleep(600)
await shoot('back-to-deck')

console.log('frames:', frame)
console.log('decisions:', JSON.stringify(await evaluate(`window.__eatwhatDecisions ? window.__eatwhatDecisions() : null`)))

await send('Target.closeTarget', { targetId })
ws.close()
