/**
 * 多人房间端到端演示（CDP 双标签页）。
 *
 * 前置：headless Chrome 已带 --remote-debugging-port=9222 启动，dev server 跑在 5173。
 * 用法：node scripts/room-demo.mjs
 *
 * 做的事：A 页建房 → 读房间码 → B 页加入 → A 页开团 → 两边各投 10 张
 * → 等 CONSENSUS_REVEAL → 各截一张图到 docs/review/room/。
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
    if (msg.error) reject(new Error(`${msg.error.message} (${JSON.stringify(msg.error.data || '')})`))
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

async function attach(client, targetId) {
  const { sessionId } = await client.send('Target.attachToTarget', { targetId, flatten: true })
  return sessionId
}

async function evaluate(client, sessionId, expression) {
  const res = await client.send(
    'Runtime.evaluate',
    { expression, awaitPromise: true, returnByValue: true },
    sessionId,
  )
  if (res.exceptionDetails) {
    throw new Error(res.exceptionDetails.exception?.description || 'evaluate failed')
  }
  return res.result?.value
}

async function waitFor(client, sessionId, expression, timeoutMs = 12000, label = 'condition') {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const value = await evaluate(client, sessionId, expression).catch(() => false)
    if (value) return value
    await sleep(200)
  }
  throw new Error(`等超时：${label}`)
}

async function openTab(client, url) {
  const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' })
  const sessionId = await attach(client, targetId)
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: 393,
    height: 852,
    deviceScaleFactor: 2,
    mobile: true,
  }, sessionId)
  await client.send('Page.enable', {}, sessionId)
  await client.send('Runtime.enable', {}, sessionId)
  await client.send('Page.navigate', { url }, sessionId)
  await waitFor(client, sessionId, 'document.readyState === "complete"', 15000, 'page load')
  return { targetId, sessionId }
}

async function shot(client, sessionId, file) {
  const { data } = await client.send('Page.captureScreenshot', { format: 'png', fromSurface: true }, sessionId)
  const fs = await import('node:fs/promises')
  await fs.writeFile(file, Buffer.from(data, 'base64'))
  console.log('saved', file)
}

const clickByText = (selector, text) => `
(() => {
  const el = [...document.querySelectorAll(${JSON.stringify(selector)})]
    .find((n) => n.textContent.replace(/\\s+/g, '').includes(${JSON.stringify(text)}));
  if (!el) return false;
  el.click();
  return true;
})()`

const main = async () => {
  const client = makeClient(await browserWs())
  await client.ready

  // 两个标签页共享 localStorage，必须显式指定各自身份，否则都是同一个 user
  const a = await openTab(client, `${ORIGIN}/m/home`)
  await evaluate(client, a.sessionId, 'localStorage.setItem("eatwhat.userId", "1"); location.replace("/m/profile"); true')
  await sleep(900)
  await waitFor(client, a.sessionId, 'document.querySelectorAll(".entry").length >= 2', 15000, 'profile entries')
  const clicked = await evaluate(client, a.sessionId, clickByText('.entry', '多人干饭房间'))
  if (!clicked) throw new Error('Profile 上没找到房间入口')
  await waitFor(client, a.sessionId, 'location.pathname === "/m/room"', 8000, 'navigate to room')
  await waitFor(client, a.sessionId, '!!document.querySelector(".btn-ink")', 8000, 'room landing')

  await evaluate(client, a.sessionId, clickByText('.btn-ink', '创建房间'))
  const code = await waitFor(
    client,
    a.sessionId,
    'document.querySelector(".lobby__digits")?.textContent?.trim() || ""',
    12000,
    'room code',
  )
  console.log('room code:', code)

  // B 页要换个身份，否则两个标签页都是 localStorage 里的同一个 user（join 幂等，永远只有 1 人）
  const b = await openTab(client, `${ORIGIN}/m/home`)
  await evaluate(client, b.sessionId, 'localStorage.setItem("eatwhat.userId", "2"); location.replace("/m/room"); true')
  await sleep(900)
  await waitFor(client, b.sessionId, '!!document.querySelector(".field")', 12000, 'join form')
  await evaluate(
    client,
    b.sessionId,
    `(() => {
      const input = document.querySelector('.field');
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(input, ${JSON.stringify(code)});
      input.dispatchEvent(new Event('input', { bubbles: true }));
      return input.value;
    })()`,
  )
  const joinClicked = await evaluate(client, b.sessionId, clickByText('.btn-ghost-ink', '加入'))
  console.log('join clicked:', joinClicked, '| code typed:', code)
  try {
    await waitFor(
      client,
      b.sessionId,
      'document.querySelectorAll(".member").length >= 2',
      12000,
      'two members',
    )
  } catch (err) {
    const dump = await evaluate(
      client,
      b.sessionId,
      'JSON.stringify({ path: location.pathname, members: document.querySelectorAll(".member").length, hint: document.querySelector(".hint--warn")?.textContent?.trim() || "", text: document.body.innerText.slice(0, 220) })',
    )
    throw new Error(`${err.message} | B state: ${dump}`)
  }
  console.log('joined, members = 2')
  await shot(client, b.sessionId, `${OUT}/room-lobby-b.png`)

  await evaluate(client, a.sessionId, clickByText('.btn-ink', '开始划卡'))
  await waitFor(client, a.sessionId, '!!document.querySelector(".card__name")', 15000, 'swiping started')
  await waitFor(client, b.sessionId, '!!document.querySelector(".card__name")', 15000, 'peer swiping')
  await sleep(400)
  await shot(client, a.sessionId, `${OUT}/room-swiping.png`)

  const voteAll = async (sessionId) => {
    for (let i = 0; i < 12; i += 1) {
      const done = await evaluate(
        client,
        sessionId,
        'document.querySelector(".reveal__name") ? "revealed" : (document.querySelector(".vote") ? "vote" : "wait")',
      )
      if (done === 'revealed') return true
      if (done === 'vote') {
        await evaluate(client, sessionId, 'document.querySelector(".vote").click(); true')
      }
      await sleep(260)
    }
    return false
  }

  const [ra, rb] = await Promise.all([voteAll(a.sessionId), voteAll(b.sessionId)])
  console.log('both voted to reveal:', ra, rb)

  await sleep(1600)
  const winner = await evaluate(
    client,
    a.sessionId,
    'document.querySelector(".reveal__name")?.textContent?.trim() || "none"',
  )
  const stage = await evaluate(client, a.sessionId, 'document.querySelector(".room__sub")?.textContent?.trim()')
  const art = await evaluate(client, a.sessionId, 'JSON.stringify({ art: !!document.querySelector(".reveal__art"), svg: document.querySelector(".reveal__art svg")?.childElementCount ?? -1, rect: (() => { const el = document.querySelector(".reveal__art"); return el ? Math.round(el.getBoundingClientRect().height) : -1 })(), rowKeys: Object.keys(JSON.parse(JSON.stringify(window.__lastReveal || {}))) })')
  console.log('art:', art)
  const html = await evaluate(client, a.sessionId, 'document.querySelector(".reveal__art")?.innerHTML?.slice(0, 420) || "none"')
  const missing = await evaluate(client, a.sessionId, 'JSON.stringify({ missing: document.querySelector(".reveal__art")?.getAttribute("data-missing") ?? "none", cls: document.querySelector(".reveal__art")?.firstElementChild?.className ?? "none" })')
  console.log('missing:', missing)
  console.log('winner:', winner, '| sub:', stage)
  // 截图前把目标页切到前台，否则后台页可能拿到未重绘的帧
  await client.send('Target.activateTarget', { targetId: a.targetId })
  await sleep(500)
  await shot(client, a.sessionId, `${OUT}/room-revealed-a.png`)
  await client.send('Target.activateTarget', { targetId: b.targetId })
  await sleep(500)
  await shot(client, b.sessionId, `${OUT}/room-revealed-b.png`)

  client.ws.close()
}

main().catch((err) => {
  console.error('FAILED:', err.message)
  process.exit(1)
})
