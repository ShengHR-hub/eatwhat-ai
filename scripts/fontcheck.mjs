// 查页面实际渲染用了哪个字体（CSS.getPlatformFontsForNode 是唯一可靠的办法，
// getComputedStyle 只返回 CSS 里写的字体栈，不告诉你最终落到哪个字体）
import { writeFileSync } from 'node:fs'

const url = process.argv[2]
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const res = await fetch('http://127.0.0.1:9222/json/version')
const { webSocketDebuggerUrl } = await res.json()
const ws = new WebSocket(webSocketDebuggerUrl)
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
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
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
await send('DOM.enable', {}, sessionId)
await send('CSS.enable', {}, sessionId)
await send('Page.navigate', { url }, sessionId)
await sleep(1500)

const { root } = await send('DOM.getDocument', { depth: -1 }, sessionId)

const targets = [
  ['页面标题 h1', '.page-head h1'],
  ['正文 td', 'tbody td'],
  ['KPI 数字', '.kpi__value'],
  ['侧栏导航', '.nav__item'],
  ['表头 th', 'thead th'],
]

for (const [label, selector] of targets) {
  const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector }, sessionId)
  if (!nodeId) {
    console.log(`${label}: 未找到`)
    continue
  }
  const { fonts } = await send('CSS.getPlatformFontsForNode', { nodeId }, sessionId)
  const list = fonts.map((f) => `${f.familyName}(${f.glyphCount})`).join(', ')
  console.log(`${label}: ${list || '无'}`)
}

const probe = await send('Runtime.evaluate', {
  expression: `(() => {
    const h1 = document.querySelector('.page-head h1')
    const cs = getComputedStyle(h1)
    return { family: cs.fontFamily, size: cs.fontSize, weight: cs.fontWeight, spacing: cs.letterSpacing }
  })()`,
  returnByValue: true,
}, sessionId)
console.log('h1 computed:', JSON.stringify(probe.result.value))

await send('Target.closeTarget', { targetId })
ws.close()
writeFileSync('/tmp/fontcheck.done', 'ok')
