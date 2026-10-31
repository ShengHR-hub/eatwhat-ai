// 逐层测量地图容器的尺寸，找出是哪一层高度塌陷
const url = process.argv[2]
const waitMs = Number(process.argv[3] || 6000)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const res = await fetch('http://127.0.0.1:9222/json/version')
const { webSocketDebuggerUrl } = await res.json()
const ws = new WebSocket(webSocketDebuggerUrl)
let seq = 0
const pending = new Map()

ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id)
    pending.delete(m.id)
    m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result)
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
await send('Runtime.enable', {}, sessionId)
await send('Page.navigate', { url }, sessionId)
await sleep(waitMs)

const expr = `(() => {
  const map = document.getElementById('map');
  const rows = [];
  let el = map;
  let depth = 0;
  while (el && depth < 6) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    rows.push({
      tag: el.tagName + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(' ').join('.') : ''),
      rect: [Math.round(r.width), Math.round(r.height)],
      display: cs.display,
      flex: cs.flex,
      height: cs.height,
      minHeight: cs.minHeight,
      position: cs.position
    });
    el = el.parentElement;
    depth++;
  }
  return JSON.stringify(rows, null, 1);
})()`

const out = await send('Runtime.evaluate', { expression: expr, returnByValue: true }, sessionId)
console.log(out.result.value)
await send('Target.closeTarget', { targetId })
ws.close()
