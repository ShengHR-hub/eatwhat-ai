/**
 * 首页「一屏装得下」硬断言（审查 F06）。
 *
 * 只看 scrollHeight == innerHeight 不算过——之前就是这么漏的：
 * 卡组写死高度，矮屏溢出被 overflow:hidden 吃掉，按钮沉到底栏下面，
 * 页面照样"不滚动"。这里补三条：
 *   1. 页面不滚动（scrollHeight <= innerHeight + 1）
 *   2. 操作行与底栏矩形不相交
 *   3. 两个操作按钮的中心点 elementFromPoint 命中按钮自身
 *
 * 用法：node scripts/home-fit.mjs [width height ...]
 * 退出码非 0 表示不达标。
 */
const CDP = 'http://127.0.0.1:9222'
const ORIGIN = 'http://127.0.0.1:5173'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const VIEWPORTS = process.argv.slice(2).length
  ? chunk(process.argv.slice(2).map(Number))
  : [
      [390, 844],
      [390, 667],
    ]

function chunk(list) {
  const out = []
  for (let i = 0; i + 1 < list.length; i += 2) out.push([list[i], list[i + 1]])
  return out
}

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

async function waitFor(client, sessionId, expression, timeoutMs = 20000, label = 'condition') {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const value = await evaluate(client, sessionId, expression).catch(() => false)
    if (value) return value
    await sleep(200)
  }
  throw new Error(`等超时：${label}`)
}

const PROBE = `(() => {
  const r = (el) => { const b = el.getBoundingClientRect(); return { t: Math.round(b.top), b: Math.round(b.bottom), l: Math.round(b.left), r: Math.round(b.right) } }
  // 选择器对齐 HomeV5Exact.vue：旧版 Home.vue 的 .deck-actions 已不在路由上
  const content = document.querySelector('.v5-home .content')
  const actions = document.querySelector('.actions')
  const tabbar = document.querySelector('.tabbar')

  // 初始态：不滚动，如实记录「这个视口到底需不需要滚」「操作行有没有被底栏压住」。
  // 以前这里先滚到底再量，等于把问题藏起来——门禁必须能看见真实首屏。
  const scrollable = !!content && content.scrollHeight > content.clientHeight + 1
  const needScroll = content ? Math.max(0, content.scrollHeight - content.clientHeight) : 0
  const a0 = actions ? r(actions) : null
  const t0 = tabbar ? r(tabbar) : null
  const initialOverlap = a0 && t0
    ? Math.max(0, Math.min(a0.b, t0.b) - Math.max(a0.t, t0.t))
    : -1

  // 滚到底后复测：新规范允许矮屏滚动，但滚到底必须能点到按钮
  if (scrollable) content.scrollTop = content.scrollHeight
  const buttons = [...document.querySelectorAll('.actions .primary, .actions .text-btn')]
  const hit = buttons.map((btn) => {
    const b = btn.getBoundingClientRect()
    const hitEl = document.elementFromPoint(Math.round(b.left + b.width / 2), Math.round(b.top + b.height / 2))
    return { label: btn.textContent.trim(), self: !!hitEl && (hitEl === btn || btn.contains(hitEl)) }
  })
  const a = actions ? r(actions) : null
  const t = tabbar ? r(tabbar) : null
  const overlap = a && t ? Math.max(0, Math.min(a.b, t.b) - Math.max(a.t, t.t)) : -1
  // 卡片本体：V5 首页用 .dish（.deck__top 属于已下线的 SwipeCardDeck 结构）
  const card = document.querySelector('.dish')
  // 卡片正文不能溢出卡面：矮屏曾把 footer 裁掉一半，只看 scrollHeight 是查不出来的
  let contentOverflow = 0
  if (card) {
    const bottom = card.getBoundingClientRect().bottom
    for (const node of card.querySelectorAll('*')) {
      const nb = node.getBoundingClientRect()
      if (nb.height > 0 && nb.width > 0) contentOverflow = Math.max(contentOverflow, Math.round(nb.bottom - bottom))
    }
  }
  return JSON.stringify({
    vw: innerWidth, vh: innerHeight,
    scrollHeight: document.documentElement.scrollHeight,
    scrollWidth: document.documentElement.scrollWidth,
    actions: a, tabbar: t, overlap, scrollable, needScroll,
    initialActions: a0, initialOverlap,
    actionsVisible: a && t ? a.b <= t.t + 1 : -1,
    hit,
    contentOverflow,
    card: card ? Math.round(card.getBoundingClientRect().height) : -1,
    cardPct: card ? Math.round((card.getBoundingClientRect().height / innerHeight) * 100) : -1,
  })
})()`

const main = async () => {
  const client = makeClient(await browserWs())
  await client.ready
  const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await client.send('Target.attachToTarget', { targetId, flatten: true })
  await client.send('Page.enable', {}, sessionId)
  await client.send('Runtime.enable', {}, sessionId)

  let failed = 0
  for (const [width, height] of VIEWPORTS) {
    await client.send(
      'Emulation.setDeviceMetricsOverride',
      { width, height, deviceScaleFactor: 2, mobile: true },
      sessionId,
    )
    await client.send('Page.navigate', { url: `${ORIGIN}/m/home` }, sessionId)
    await waitFor(client, sessionId, 'document.readyState === "complete"', 20000, `${width}x${height} load`)
    await waitFor(client, sessionId, '!!document.querySelector(".dish")', 20000, 'card rendered')
    await sleep(600)
    const raw = await evaluate(client, sessionId, PROBE)
    const data = JSON.parse(raw)
    const reasons = []
    if (data.scrollHeight > data.vh + 1) reasons.push(`页面可滚动 ${data.scrollHeight} > ${data.vh}`)
    if (data.scrollWidth > data.vw + 1) reasons.push(`横向溢出 ${data.scrollWidth} > ${data.vw}`)
    if (data.overlap > 0) reasons.push(`滚到底后操作行仍与底栏重叠 ${data.overlap}px`)
    if (data.actionsVisible === false) reasons.push('滚到底后操作行仍被底栏遮挡')
    // 初始态遮挡不判失败（矮屏允许滚动），但必须出现在输出里，避免"看起来全绿"
    const warn = data.initialOverlap > 0
      ? ` | 初始遮挡 ${data.initialOverlap}px（需滑动）`
      : ''
    data.hit.forEach((h) => {
      if (!h.self) reasons.push(`「${h.label}」按钮中心命中的不是自己`)
    })
    if (data.cardPct > 60) reasons.push(`卡面 ${data.cardPct}% 超过 60% 屏高`)
    if (data.contentOverflow > 0) reasons.push(`卡片正文溢出卡面 ${data.contentOverflow}px（矮屏会被裁字）`)
    const status = reasons.length ? 'FAIL' : 'PASS'
    if (reasons.length) failed += 1
    console.log(
      `${status} ${width}x${height} | card ${data.card}px (${data.cardPct}%) | actions ${data.actions?.t}-${data.actions?.b} | tab ${data.tabbar?.t}-${data.tabbar?.b} | ${data.scrollable ? `需滚动 ${data.needScroll}px` : '一屏装下'}${warn} | 滚到底 overlap ${data.overlap}`,
    )
    reasons.forEach((reason) => console.log(`   - ${reason}`))
  }
  client.ws.close()
  if (failed) process.exit(1)
}

main().catch((err) => {
  console.error('FAILED:', err.message)
  process.exit(1)
})
