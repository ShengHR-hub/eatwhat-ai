// 诊断大屏地图区域：AMap 是否加载、容器是否有尺寸、瓦片是否渲染、控制台有无报错
const url = process.argv[2]
const waitMs = Number(process.argv[3] || 8000)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const res = await fetch('http://127.0.0.1:9222/json/version')
const { webSocketDebuggerUrl } = await res.json()
const ws = new WebSocket(webSocketDebuggerUrl)

let seq = 0
const pending = new Map()
const logs = []

ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.method === 'Runtime.consoleAPICalled') {
    logs.push('[console] ' + m.params.args.map((a) => a.value ?? a.description).join(' '))
  }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails
    logs.push('[exception] ' + (d.exception?.description || d.text))
  }
  if (m.method === 'Network.loadingFailed') {
    logs.push('[net-fail] ' + m.params.errorText)
  }
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
await send('Runtime.enable', {}, sessionId)
await send('Page.enable', {}, sessionId)
await send('Network.enable', {}, sessionId)
await send('Page.navigate', { url }, sessionId)
await sleep(waitMs)

const expr = `(() => {
  const el = document.getElementById('map');
  const r = el ? el.getBoundingClientRect() : null;
  const amapRoot = el ? el.querySelector('.amap-container, .amap-maps, canvas') : null;
  return JSON.stringify({
    amapLoaded: typeof window.AMap,
    mapElExists: !!el,
    mapRect: r ? [Math.round(r.width), Math.round(r.height)] : null,
    innerHTMLLen: el ? el.innerHTML.length : 0,
    canvasCount: el ? el.querySelectorAll('canvas').length : 0,
    hasAmapClass: el ? !!el.querySelector('[class*="amap"]') : false,
    amapRootTag: amapRoot ? amapRoot.className || amapRoot.tagName : null
  });
})()`

const out = await send('Runtime.evaluate', { expression: expr, returnByValue: true }, sessionId)
console.log('state:', out.result.value)
console.log('logs:', logs.length ? logs.slice(-10).join('\n  ') : '(无)')

await send('Target.closeTarget', { targetId })
ws.close()
