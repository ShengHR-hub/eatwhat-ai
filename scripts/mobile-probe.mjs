// 在移动端模拟（mobile:true）下抓首页 DOM 结构，定位卡片缺失原因
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const res = await fetch('http://127.0.0.1:9222/json/version')
const { webSocketDebuggerUrl } = await res.json()
const ws = new WebSocket(webSocketDebuggerUrl)
let seq = 0
const pending = new Map()
const logs = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.args.map((a) => a.value ?? a.description).join(' '))
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text))
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
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }, sessionId)
await send('Page.navigate', { url: 'http://127.0.0.1:5173/m/home' }, sessionId)
await sleep(7000)

const expr = `(() => {
  const app = document.getElementById('app');
  const html = app ? app.innerHTML : '';
  const classes = [...new Set((html.match(/class="[^"]+"/g) || []).map(s => s.slice(7, -1)).join(' ').split(/\\s+/))].filter(Boolean);
  return JSON.stringify({
    url: location.href,
    appChildCount: app ? app.children.length : -1,
    htmlLen: html.length,
    hasDeckTop: !!document.querySelector('.deck__top'),
    hasDeck: !!document.querySelector('.deck'),
    hasDeckHost: !!document.querySelector('.deck-host'),
    hasDishCard: !!document.querySelector('.dishcard'),
    hintText: document.querySelector('.deck__hint')?.textContent || null,
    bodyText: (document.body.innerText || '').slice(0, 200),
    classSample: classes.slice(0, 40)
  }, null, 1);
})()`
const out = await send('Runtime.evaluate', { expression: expr, returnByValue: true }, sessionId)
console.log(out.result.value)
console.log('logs:', logs.slice(-6).join(' | ') || '(无)')
await send('Target.closeTarget', { targetId })
ws.close()
