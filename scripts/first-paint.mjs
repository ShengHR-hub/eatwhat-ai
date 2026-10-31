// 首屏出菜计时：登录态下进入首页，量「骨架屏出现」与「菜名出现」各在多少毫秒
// 用法：LOGIN_USER=xxx LOGIN_PASS=yyy node scripts/first-paint.mjs <url> [width] [height]
import { writeFileSync } from 'node:fs'

const [url = 'http://127.0.0.1:5173/m/home', w = '390', h = '844'] = process.argv.slice(2)
const width = Number(w)
const height = Number(h)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

let auth = null
if (process.env.LOGIN_USER) {
  const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: process.env.LOGIN_USER, password: process.env.LOGIN_PASS }),
  })
  auth = await res.json()
  if (!res.ok) throw new Error('登录失败：' + JSON.stringify(auth))
}

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
await send('Network.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 2, mobile: true }, sessionId)
if (process.env.THROTTLE === '1') {
  // 限速到「慢速 3G」：真实手机上首次进首页就是这个量级，用来确认骨架屏长什么样
  await send('Network.emulateNetworkConditions', {
    offline: false, latency: 600, downloadThroughput: 200 * 1024, uploadThroughput: 100 * 1024,
  }, sessionId)
}

const t0 = Date.now()
if (auth) {
  // 先落到同源空白页写好登录态，再进首页——等价于「刚登录完跳转」
  await send('Page.navigate', { url: url.replace(/\/m\/.*$/, '/') + 'favicon.ico' }, sessionId)
  await sleep(300)
  await send('Runtime.evaluate', {
    expression: `localStorage.setItem('eatwhat.token', ${JSON.stringify(auth.token)});
      localStorage.setItem('eatwhat.userId', ${JSON.stringify(String(auth.user?.id ?? auth.user_id))});
      localStorage.removeItem('eatwhat.v5.background');`,
    returnByValue: true,
  }, sessionId)
}
const tNav = Date.now()
await send('Page.navigate', { url }, sessionId)

const samples = []
let skeletonAt = null
let dishAt = null
let shot = false
for (let i = 0; i < 200; i += 1) {
  const r = await send('Runtime.evaluate', {
    expression: `(() => {
      const sk = document.querySelector('.home-skeleton')
      const title = document.querySelector('.dish__title')
      return { sk: Boolean(sk), dish: title ? title.textContent.trim() : '', loading: Boolean(document.querySelector('.notice')) }
    })()`,
    returnByValue: true,
  }, sessionId)
  const v = r.result?.value ?? {}
  const at = Date.now() - tNav
  if (v.sk && skeletonAt === null) skeletonAt = at
  if (v.dish && dishAt === null) {
    dishAt = at
    const { data } = await send('Page.captureScreenshot', { format: 'png' }, sessionId)
    writeFileSync('docs/review/final/first-paint-home.png', Buffer.from(data, 'base64'))
    shot = true
  }
  if (i % 10 === 0) samples.push({ at, ...v })
  if (v.sk && !globalThis.__skShot) {
    globalThis.__skShot = true
    const { data } = await send('Page.captureScreenshot', { format: 'png' }, sessionId)
    writeFileSync('docs/review/final/first-paint-skeleton.png', Buffer.from(data, 'base64'))
  }
  if (dishAt !== null && at > dishAt + 600) break
  await sleep(40)
}

console.log(JSON.stringify({
  url,
  skeletonAtMs: skeletonAt,
  dishAtMs: dishAt,
  skeletonShot: globalThis.__skShot ? 'docs/review/final/first-paint-skeleton.png' : null,
  screenshot: shot ? 'docs/review/final/first-paint-home.png' : null,
  samples,
}, null, 2))

await send('Target.closeTarget', { targetId })
ws.close()
