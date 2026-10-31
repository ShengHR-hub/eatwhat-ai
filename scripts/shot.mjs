// 移动端真视口截图 + 布局体检
// 用法：node scripts/shot.mjs <url> <width> <height> <out.png> [preShotJs] [waitMs]
// 依赖本机 Chrome 以 --remote-debugging-port=9222 启动，用 CDP 的
// Emulation.setDeviceMetricsOverride 得到真实 390/430 视口（--window-size 会被
// Chrome 的窗口最小宽度钳到 500，命令行截图的宽度不可信）。
import { writeFileSync } from 'node:fs'

const [url, w = '390', h = '844', out = 'shot.png', preShotJs = '', waitMs = '0'] = process.argv.slice(2)
const width = Number(w)
const height = Number(h)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function getWsUrl() {
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/version')
      const json = await res.json()
      if (json.webSocketDebuggerUrl) return json.webSocketDebuggerUrl
    } catch {
      /* Chrome 还没起来 */
    }
    await sleep(250)
  }
  throw new Error('连不上 9222，先启动 Chrome：chrome --headless=new --remote-debugging-port=9222')
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

// 新建一个标签页，绑定到它的 session
const { targetId } = await send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })

await send('Page.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', {
  width,
  height,
  deviceScaleFactor: Number(process.env.SCALE || 2),
  mobile: true,
}, sessionId)
await send('Runtime.enable', {}, sessionId)

await send('Page.navigate', { url }, sessionId)
await sleep(4500) // 等 Vue 挂载 + 动效首帧 + 推荐请求返回

// 截图前可选注入一段脚本（点按钮、切模式），再等一会儿让动效落定
if (preShotJs) {
  const r = await send('Runtime.evaluate', { expression: preShotJs, awaitPromise: true, returnByValue: true }, sessionId)
  if (r.exceptionDetails) console.log('preShot error:', JSON.stringify(r.exceptionDetails.exception?.description || r.exceptionDetails.text))
  else if (r.result?.value !== undefined) console.log('preShot:', JSON.stringify(r.result.value))
  await sleep(Number(waitMs) || 900)
}

const probe = await send('Runtime.evaluate', {
  expression: `(() => {
    const de = document.documentElement
    const wide = [...document.querySelectorAll('*')]
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && r.right > de.clientWidth + 0.5)
      .slice(0, 8)
      .map(({ el, r }) => el.tagName.toLowerCase() + '.' + (el.className && typeof el.className === 'string' ? el.className.split(' ').slice(0, 3).join('.') : '') + ' right=' + Math.round(r.right))
    return { clientWidth: de.clientWidth, scrollWidth: de.scrollWidth, overflow: wide }
  })()`,
  returnByValue: true,
}, sessionId)

const shotParams = { format: 'png', captureBeyondViewport: false }
if (process.env.FULL === '1') {
  // 整页长图：整页高度可能几千像素，审核材料里方便一眼看完整屏
  const { contentSize } = await send('Page.getLayoutMetrics', {}, sessionId)
  shotParams.captureBeyondViewport = true
  shotParams.clip = { x: 0, y: 0, width, height: Math.ceil(contentSize.height), scale: 1 }
}
const { data } = await send('Page.captureScreenshot', shotParams, sessionId)
writeFileSync(out, Buffer.from(data, 'base64'))

console.log(JSON.stringify(probe.result.value, null, 2))
console.log('saved ' + out + ' ' + width + 'x' + height + '@2x')

await send('Target.closeTarget', { targetId })
ws.close()
