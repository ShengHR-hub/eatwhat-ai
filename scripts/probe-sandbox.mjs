// 探针：打开调整抽屉、拖 λ 滑块，检查抽屉是否真的出现、参数是否变化、是否发出请求
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
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }, sessionId)

// 记录所有 recommend 请求
await send('Page.addScriptToEvaluateOnNewDocument', {
  source: `
    window.__calls = [];
    const orig = window.fetch;
    window.fetch = function(...args) {
      try {
        const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
        if (url && url.includes('/recommend/')) {
          window.__calls.push({ url, body: args[1]?.body || null });
        }
      } catch {}
      return orig.apply(this, args);
    };
  `,
}, sessionId)

await send('Page.navigate', { url: 'http://127.0.0.1:5173/m/home' }, sessionId)
await sleep(4500)

const before = await send('Runtime.evaluate', {
  expression: `JSON.stringify({
    btnExists: !!document.querySelector('[aria-label="打开调整抽屉"]'),
    calls: window.__calls.length
  })`,
  returnByValue: true,
}, sessionId)
console.log('before:', before.result.value)

const step = await send('Runtime.evaluate', {
  expression: `(async () => {
    document.querySelector('[aria-label="打开调整抽屉"]')?.click();
    await new Promise(r => setTimeout(r, 600));
    const rows = [...document.querySelectorAll('.slider-row input[type=range]')];
    const drawerVisible = !!document.querySelector('.drawer, .sheet, .settings, [role="dialog"]');
    if (!rows.length) return JSON.stringify({ error: 'no slider', drawerVisible });
    const t = rows[0];
    const oldVal = t.value;
    t.value = '2';
    t.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(r => setTimeout(r, 900));
    return JSON.stringify({
      drawerVisible, sliders: rows.length, oldVal, newVal: t.value,
      callsAfter: window.__calls.length,
      lastBody: window.__calls.at(-1)?.body || null
    });
  })()`,
  returnByValue: true,
  awaitPromise: true,
}, sessionId)
console.log('after:', step.result.value)

await send('Target.closeTarget', { targetId })
ws.close()
