/**
 * F05 现场恢复探针：建房 → 开团 → 刷新页面 → 必须回到 SWIPING 且候选还在。
 *
 * 前置：headless Chrome 带 --remote-debugging-port=9222，dev server 跑在 5173。
 * 用法：node scripts/room-recover.mjs
 */
const CDP = 'http://127.0.0.1:9222'
const ORIGIN = 'http://127.0.0.1:5173'
const OUT = 'D:/EatWhat/docs/review/room'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function browserWs() {
  const version = await (await fetch(`${CDP}/json/version`)).json()
  return version.webSocketDebuggerUrl
}

function makeClient(url) {
  const ws = new WebSocket(url)
  const pending = new Map()
  let seq = 0
  const ready = new Promise((resolve, reject) => {
    ws.onopen = () => resolve()
    ws.onerror = (e) => reject(e)
  })
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (!msg.id || !pending.has(msg.id)) return
    const { resolve, reject } = pending.get(msg.id)
    pending.delete(msg.id)
    if (msg.error) reject(new Error(msg.error.message))
    else resolve(msg.result)
  }
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve, reject) => {
      const id = ++seq
      pending.set(id, { resolve, reject })
      ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }))
    })
  return { ws, ready, send }
}

async function evaluate(client, sessionId, expression) {
  const res = await client.send(
    'Runtime.evaluate',
    { expression, awaitPromise: true, returnByValue: true },
    sessionId,
  )
  if (res.exceptionDetails) throw new Error(res.exceptionDetails.exception?.description || 'evaluate failed')
  return res.result?.value
}

async function waitFor(client, sessionId, expression, timeoutMs = 15000, label = 'condition') {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const value = await evaluate(client, sessionId, expression).catch(() => false)
    if (value) return value
    await sleep(200)
  }
  throw new Error(`等超时：${label}`)
}

const main = async () => {
  const client = makeClient(await browserWs())
  await client.ready

  const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await client.send('Target.attachToTarget', { targetId, flatten: true })
  await client.send(
    'Emulation.setDeviceMetricsOverride',
    { width: 393, height: 852, deviceScaleFactor: 2, mobile: true },
    sessionId,
  )
  await client.send('Page.enable', {}, sessionId)
  await client.send('Runtime.enable', {}, sessionId)

  await client.send('Page.navigate', { url: `${ORIGIN}/m/home` }, sessionId)
  await waitFor(client, sessionId, 'document.readyState === "complete"', 15000, 'home load')
  await evaluate(client, sessionId, 'localStorage.setItem("eatwhat.userId", "1"); location.replace("/m/room"); true')
  await sleep(1200)
  await waitFor(client, sessionId, '!!document.querySelector(".btn-ink")', 12000, 'landing')

  await evaluate(
    client,
    sessionId,
    `[...document.querySelectorAll('.btn-ink')].find((n) => n.textContent.includes('创建房间'))?.click(); true`,
  )
  await waitFor(client, sessionId, '!!document.querySelector(".lobby__digits")', 15000, 'lobby')
  const code = await evaluate(client, sessionId, 'document.querySelector(".lobby__digits").textContent.trim()')
  const url = await evaluate(client, sessionId, 'location.href')
  console.log('room code:', code, '| url has code:', url.includes(code))
  if (!url.includes(code)) throw new Error('房间码没有写进地址栏，刷新就回不来')

  await evaluate(
    client,
    sessionId,
    `[...document.querySelectorAll('.btn-ink')].find((n) => n.textContent.includes('开始划卡'))?.click(); true`,
  )
  await waitFor(client, sessionId, '!!document.querySelector(".card__name")', 15000, 'swiping')
  const before = await evaluate(client, sessionId, 'document.querySelector(".card__name").textContent.trim()')
  console.log('swiping, first card:', before)

  // 刷新页面：必须凭地址栏里的 code 回到同一局，且候选还在
  await client.send('Page.reload', {}, sessionId)
  await waitFor(client, sessionId, 'document.readyState === "complete"', 15000, 'reload')
  const stage = await waitFor(
    client,
    sessionId,
    'document.querySelector(".card__name") || document.querySelector(".reveal__name") ? "back" : false',
    20000,
    'restored stage',
  )
  const after = await evaluate(
    client,
    sessionId,
    `JSON.stringify({
      stage: ${JSON.stringify(stage)},
      card: document.querySelector('.card__name')?.textContent?.trim() || '',
      seconds: document.querySelector('.timer__num')?.textContent?.trim() || '',
      progress: document.querySelector('.progress__val')?.textContent?.trim() || '',
      title: document.querySelector('.room__sub')?.textContent?.trim() || ''
    })`,
  )
  console.log('after reload:', after)

  const { data } = await client.send('Page.captureScreenshot', { format: 'png', fromSurface: true }, sessionId)
  const fs = await import('node:fs/promises')
  await fs.writeFile(`${OUT}/room-recovered.png`, Buffer.from(data, 'base64'))
  console.log('saved', `${OUT}/room-recovered.png`)
  client.ws.close()
}

main().catch((err) => {
  console.error('FAILED:', err.message)
  process.exit(1)
})
