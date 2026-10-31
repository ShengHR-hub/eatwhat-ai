// 量首页各区块高度，定位溢出量（用于矮屏降级断点）
const [w, h] = [Number(process.argv[2] || 390), Number(process.argv[3] || 667)]
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
await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 2, mobile: true }, sessionId)
await send('Page.navigate', { url: 'http://127.0.0.1:5173/m/home' }, sessionId)
await sleep(6000)

const expr = `(() => {
  const content = document.querySelector('.v5-home .content');
  const phone = document.querySelector('.v5-home .phone');
  const tabbar = document.querySelector('.tabbar');
  if (!content) return JSON.stringify({ error: 'no .content' });
  const kids = [...content.children].map(el => ({
    cls: (el.className || el.tagName).toString().split(' ')[0],
    h: Math.round(el.getBoundingClientRect().height)
  }));
  const cr = content.getBoundingClientRect();
  const sum = kids.reduce((a, k) => a + k.h, 0);
  return JSON.stringify({
    viewport: [innerWidth, innerHeight],
    phone: phone ? Math.round(phone.getBoundingClientRect().height) : null,
    contentH: Math.round(cr.height),
    contentScrollH: content.scrollHeight,
    sumChildren: sum,
    overflow: sum - Math.round(cr.height),
    kids,
    tabbarTop: tabbar ? Math.round(tabbar.getBoundingClientRect().top) : null,
    actionsBottom: (() => { const a = document.querySelector('.v5-home .actions'); return a ? Math.round(a.getBoundingClientRect().bottom) : null })()
  }, null, 1);
})()`
const out = await send('Runtime.evaluate', { expression: expr, returnByValue: true }, sessionId)
console.log(out.result.value)
await send('Target.closeTarget', { targetId })
ws.close()
