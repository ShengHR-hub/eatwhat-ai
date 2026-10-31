/**
 * S05/r01 real-browser acceptance probe.
 *
 * Uses CDP Input.dispatchMouseEvent / dispatchKeyEvent for user actions
 * (no element.click() is used for the acceptance steps), records console,
 * exceptions, network requests/responses, screenshots and geometry.
 *
 * Run: node docs/review/stages/S05/r01/data/browser_probe.mjs [phase,...]
 * Must have backend :8000 (isolated DB) + Vite :5173 + Chrome --remote-debugging-port=9222.
 */
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

const CDP = 'http://127.0.0.1:9222'
const ORIGIN = 'http://127.0.0.1:5173'
const OUT = 'D:/EatWhat/docs/review/stages/S05/r01'
const SHOTS = join(OUT, 'browser')
const API = 'http://127.0.0.1:8000/api/v1'
const phasesWanted = process.argv[2]
  ? new Set(process.argv[2].split(',').map((s) => s.trim()).filter(Boolean))
  : new Set(['home', 'nav', 'sandbox', 'role', 'checkin', 'refill', 'faults'])

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(SHOTS, { recursive: true })

/* ---------------- CDP plumbing ---------------- */
async function browserWs() {
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch(`${CDP}/json/version`)
      const json = await res.json()
      if (json.webSocketDebuggerUrl) return json
    } catch {
      /* chrome not ready */
    }
    await sleep(250)
  }
  throw new Error('CDP 9222 unavailable')
}

function makeClient(url) {
  const ws = new WebSocket(url)
  const pending = new Map()
  const handlers = []
  let seq = 0
  const ready = new Promise((resolve, reject) => {
    ws.onopen = () => resolve()
    ws.onerror = (e) => reject(e)
  })
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id)
      pending.delete(msg.id)
      if (msg.error) reject(new Error(msg.error.message))
      else resolve(msg.result)
      return
    }
    for (const fn of handlers) fn(msg)
  }
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve, reject) => {
      const id = ++seq
      pending.set(id, { resolve, reject })
      ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }))
    })
  const on = (fn) => handlers.push(fn)
  return { ws, ready, send, on }
}

const version = await browserWs()
const client = makeClient(version.webSocketDebuggerUrl)
await client.ready
/* single mutable interceptor slot so two phases never answer the same paused request */
let fetchHandler = null
client.on((msg) => {
  if (msg.method === 'Fetch.requestPaused' && fetchHandler) fetchHandler(msg)
})
const { targetId } = await client.send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await client.send('Target.attachToTarget', { targetId, flatten: true })
await client.send('Page.enable', {}, sessionId)
await client.send('Runtime.enable', {}, sessionId)
await client.send('Network.enable', {}, sessionId)
await client.send('Log.enable', {}, sessionId)

/* ---------------- recorders ---------------- */
const evidence = {
  captured_at: new Date().toISOString(),
  chrome: version.Browser,
  origin: ORIGIN,
  backend: 'http://127.0.0.1:8000 (isolated DB eatwhat_s05_r01_iso.db)',
  input_method: 'CDP Input.dispatchMouseEvent / dispatchKeyEvent (real browser input)',
  phases: {},
  console_events: [],
  exceptions: [],
  page_errors: [],
  network: [],
  screenshots: [],
  verdicts: {},
}
let phase = 'bootstrap'
const netMeta = new Map()

client.on((msg) => {
  if (msg.method === 'Runtime.consoleAPICalled') {
    const type = msg.params.type
    if (type === 'error' || type === 'warning') {
      evidence.console_events.push({
        phase,
        type,
        text: msg.params.args
          .map((a) => a.value ?? a.description ?? a.type)
          .join(' ')
          .slice(0, 500),
      })
    }
  } else if (msg.method === 'Runtime.exceptionThrown') {
    const d = msg.params.exceptionDetails
    evidence.exceptions.push({
      phase,
      text: (d.exception?.description || d.text || '').slice(0, 800),
    })
  } else if (msg.method === 'Log.entryAdded') {
    const e = msg.params.entry
    if (e.level === 'error') {
      evidence.console_events.push({ phase, type: 'log-error', text: `${e.source}: ${e.text}`.slice(0, 500) })
    }
  } else if (msg.method === 'Network.requestWillBeSent') {
    const p = msg.params
    const url = p.request.url
    if (url.includes('/api/v1/')) {
      const meta = {
        id: p.requestId,
        phase,
        method: p.request.method,
        url,
        path: url.replace(/^https?:\/\/[^/]+/, ''),
        request_headers: {
          'X-User-Id': p.request.headers['X-User-Id'] ?? p.request.headers['x-user-id'] ?? null,
        },
        post: p.request.postData ?? null,
        status: null,
        at: Date.now(),
      }
      netMeta.set(p.requestId, meta)
      evidence.network.push(meta)
    }
  } else if (msg.method === 'Network.responseReceived') {
    const meta = netMeta.get(msg.params.requestId)
    if (meta) meta.status = msg.params.response.status
  } else if (msg.method === 'Network.loadingFinished') {
    const meta = netMeta.get(msg.params.requestId)
    if (meta) meta.finished = true
  } else if (msg.method === 'Network.loadingFailed') {
    const meta = netMeta.get(msg.params.requestId)
    if (meta) {
      meta.failed = msg.params.errorText
      meta.status = meta.status ?? 0
    }
  }
})

/* ---------------- page helpers ---------------- */
async function evalJs(expression) {
  const res = await client.send(
    'Runtime.evaluate',
    { expression, awaitPromise: true, returnByValue: true },
    sessionId,
  )
  if (res.exceptionDetails) {
    throw new Error(res.exceptionDetails.exception?.description || res.exceptionDetails.text || 'evaluate failed')
  }
  return res.result?.value
}

async function waitFor(expression, timeoutMs = 20000, label = 'condition') {
  const deadline = Date.now() + timeoutMs
  let last
  while (Date.now() < deadline) {
    last = await evalJs(expression).catch((e) => ({ err: String(e) }))
    if (last && last !== false && !last?.err) return last
    await sleep(120)
  }
  throw new Error(`wait timeout: ${label} (${JSON.stringify(last)?.slice(0, 200)})`)
}

async function setViewport(width, height) {
  await client.send(
    'Emulation.setDeviceMetricsOverride',
    { width, height, deviceScaleFactor: 2, mobile: true },
    sessionId,
  )
  await client.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }, sessionId)
}

async function screenshot(label) {
  const { data } = await client.send(
    'Page.captureScreenshot',
    { format: 'png', captureBeyondViewport: false },
    sessionId,
  )
  const name = `${String(evidence.screenshots.length + 1).padStart(2, '0')}-${phase}-${label}.png`
  const path = join(SHOTS, name)
  writeFileSync(path, Buffer.from(data, 'base64'))
  evidence.screenshots.push({ phase, label, path: `browser/${name}` })
  return path
}

async function goto(url) {
  await client.send('Page.navigate', { url }, sessionId)
  await waitFor('document.readyState === "complete"', 20000, `load ${url}`)
}

async function rectOf(finder) {
  return evalJs(`(() => {
    const el = (${finder});
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const x = Math.round(r.left + r.width / 2);
    const y = Math.round(r.top + r.height / 2);
    const hit = document.elementFromPoint(x, y);
    return { x, y, left: Math.round(r.left), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height), bottom: Math.round(r.bottom), right: Math.round(r.right), hit_self: !!hit && (hit === el || el.contains(hit)), hit_tag: hit ? hit.tagName + '.' + String(hit.className || '').split(' ')[0] : null, text: (el.textContent || '').trim().slice(0, 40) };
  })()`)
}

async function clickEl(finder, label, { mustHit = true } = {}) {
  const rect = await rectOf(finder)
  if (!rect) throw new Error(`click target not found: ${label}`)
  if (mustHit && !rect.hit_self) throw new Error(`click target occluded: ${label} hit=${rect.hit_tag}`)
  await client.send(
    'Input.dispatchMouseEvent',
    { type: 'mousePressed', x: rect.x, y: rect.y, button: 'left', clickCount: 1 },
    sessionId,
  )
  await sleep(40)
  await client.send(
    'Input.dispatchMouseEvent',
    { type: 'mouseReleased', x: rect.x, y: rect.y, button: 'left', clickCount: 1 },
    sessionId,
  )
  await sleep(120)
  recordAction(label, rect)
  return rect
}

const actions = []
function recordAction(label, rect) {
  actions.push({ phase, label, at: new Date().toISOString(), ...rect })
  evidence.phases[phase].actions = actions.filter((a) => a.phase === phase)
}

async function pressKey(key, code = key, modifiers = 0) {
  await client.send(
    'Input.dispatchKeyEvent',
    { type: 'rawKeyDown', key, code, windowsVirtualKeyCode: keyCode(key), nativeVirtualKeyCode: keyCode(key), modifiers },
    sessionId,
  )
  await sleep(30)
  await client.send(
    'Input.dispatchKeyEvent',
    { type: 'keyUp', key, code, windowsVirtualKeyCode: keyCode(key), nativeVirtualKeyCode: keyCode(key), modifiers },
    sessionId,
  )
  await sleep(60)
}

function keyCode(key) {
  const map = { End: 35, Home: 36, ArrowLeft: 37, ArrowRight: 39, AltLeft: 18, ArrowDown: 40, ArrowUp: 38 }
  return map[key] ?? key.charCodeAt(0)
}

const SEL = (selector) => `document.querySelector(${JSON.stringify(selector)})`
const TAB = (name) => `[...document.querySelectorAll('.tabbar .tab')].find((n) => n.textContent.includes('${name}'))`
const ACT = (name) => `[...document.querySelectorAll('.deck-actions .act')].find((n) => n.textContent.includes('${name}'))`
const BTN = (name, scope = 'document') => `[...${scope}.querySelectorAll('button')].find((n) => (n.textContent || '').includes('${name}'))`

async function pageState() {
  return evalJs(`(() => {
    const txt = (sel) => document.querySelector(sel)?.textContent?.trim() || null;
    const chip = document.querySelector('.chip');
    const top = document.querySelector('.deck__top');
    return {
      url: location.pathname,
      title: document.title,
      h1: txt('h1'),
      greet: txt('.home__greet'),
      top_dish_id: chip ? Number(chip.dataset.dishId) : null,
      top_name: txt('.deck__top .dishcard__name'),
      top_score: txt('.deck__top .dishcard__score'),
      top_reason: txt('.deck__top .dishcard__reason'),
      gene_values: [...document.querySelectorAll('.gene__val')].map((n) => Number(n.textContent)),
      chips: [...document.querySelectorAll('.chip')].map((c) => Number(c.dataset.dishId)),
      chip_names: [...document.querySelectorAll('.chip .chip__name')].map((c) => c.textContent.trim()),
      chip_scores: [...document.querySelectorAll('.chip .chip__score')].map((c) => Number(c.textContent)),
      deck_count: document.querySelectorAll('.deck__top').length,
      ghost_count: document.querySelectorAll('.deck__ghost').length,
      exhausted_title: txt('.exhausted__title'),
      exhausted_sub: txt('.exhausted__sub'),
      exhausted_button: txt('.exhausted .act'),
      error_text: txt('.notice .error-msg') || txt('.fp__error') || null,
      error_title: txt('.notice .error-title'),
      toast: txt('.toast'),
      confirm_text: txt('.confirm__text'),
      sandbox_open: !!document.querySelector('.sandbox'),
      sandbox_used: txt('.used__v'),
      drawer_top5_names: [...document.querySelectorAll('.ranking__name')].map((n) => n.textContent.trim()),
      drawer_top5_scores: [...document.querySelectorAll('.ranking__score')].map((n) => Number(n.textContent)),
      body_overflow: document.body.style.overflow,
      active_tab: [...document.querySelectorAll('.tabbar .tab')].map((n) => ({ name: n.textContent.trim(), active: n.dataset.active })),
      body_text: (document.body.innerText || '').slice(0, 1200),
    };
  })()`)
}

async function geometry() {
  return evalJs(`(() => {
    const box = (sel) => { const el = document.querySelector(sel); if (!el) return null; const r = el.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width), height: Math.round(r.height) }; };
    const hitOf = (el) => { const r = el.getBoundingClientRect(); if (r.width <= 0 || r.height <= 0) return false; const h = document.elementFromPoint(Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)); return !!h && (h === el || el.contains(h)); };
    const actionsEl = document.querySelector('.deck-actions');
    const tabEl = document.querySelector('.tabbar');
    const a = actionsEl ? box('.deck-actions') : null;
    const t = tabEl ? box('.tabbar') : null;
    const overlapY = a && t ? Math.max(0, Math.min(a.bottom, t.bottom) - Math.max(a.top, t.top)) : -1;
    const top = box('.deck__top');
    const ghost = [...document.querySelectorAll('.deck__ghost')].map((el) => { const r = el.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height), visibleSliverBelowTop: top ? Math.max(0, Math.round(r.bottom - top.bottom)) : null }; });
    let contentOverflow = 0;
    const card = document.querySelector('.deck__top');
    if (card) { const cb = card.getBoundingClientRect().bottom; for (const n of card.querySelectorAll('*')) { const nb = n.getBoundingClientRect(); if (nb.width > 0 && nb.height > 0) contentOverflow = Math.max(contentOverflow, Math.round(nb.bottom - cb)); } }
    const keySelectors = ['.home__head', '.panel', '.deck-host', '.deck__top', '.candidates', '.deck-actions', '.tabbar'];
    const boxes = Object.fromEntries(keySelectors.map((s) => [s, box(s)]));
    const visible = (b) => b && b.top >= -1 && b.bottom <= innerHeight + 1 && b.left >= -1 && b.right <= innerWidth + 1;
    const heights = Object.entries(boxes).filter(([, b]) => b).map(([s, b]) => ({ selector: s, height: b.height, pct: Math.round((b.height / innerHeight) * 100) }));
    return {
      viewport: { width: innerWidth, height: innerHeight },
      scroll: { scrollHeight: document.documentElement.scrollHeight, scrollWidth: document.documentElement.scrollWidth, bodyScrollHeight: document.body.scrollHeight },
      boxes,
      in_viewport: Object.fromEntries(Object.entries(boxes).map(([s, b]) => [s, visible(b)])),
      overlap_actions_tabbar: overlapY,
      gap_actions_to_tabbar: a && t ? Math.round(t.top - a.bottom) : null,
      card_pct: top ? Math.round((top.height / innerHeight) * 100) : null,
      ghost,
      content_overflow: contentOverflow,
      max_key_element: heights.sort((x, y) => y.height - x.height)[0] || null,
      hits: {
        pass: actionsEl ? hitOf(actionsEl.querySelector('.act')) : false,
        confirm: actionsEl ? hitOf([...actionsEl.querySelectorAll('.act')][1]) : false,
        tab_home: document.querySelector('.tabbar .tab') ? hitOf(document.querySelectorAll('.tabbar .tab')[0]) : false,
        tab_footprint: document.querySelectorAll('.tabbar .tab')[1] ? hitOf(document.querySelectorAll('.tabbar .tab')[1]) : false,
        tab_profile: document.querySelectorAll('.tabbar .tab')[2] ? hitOf(document.querySelectorAll('.tabbar .tab')[2]) : false,
        chip1: document.querySelector('.chip') ? hitOf(document.querySelector('.chip')) : false,
      },
      chips_count: document.querySelectorAll('.chip').length,
      greeting_visible: !!document.querySelector('.home__greet') && visible(box('.home__greet')),
      panel_visible: !!document.querySelector('.panel') && visible(box('.panel')),
      top_card_visible: !!top && visible(top),
      candidates_visible: !!document.querySelector('.candidates') && visible(box('.candidates')),
      actions_visible: !!actionsEl && visible(a),
    };
  })()`)
}

async function api(path, { method = 'GET', body, user = 1 } = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-User-Id': String(user) },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const text = await res.text()
  let json = null
  try {
    json = JSON.parse(text)
  } catch {
    json = text
  }
  return { status: res.status, body: json }
}

function recommendCalls(sinceIdx, p = phase) {
  return evidence.network
    .slice(sinceIdx)
    .filter((n) => n.phase === p && n.path.startsWith('/api/v1/recommend/single'))
}

async function hydrateRecommendBodies(calls) {
  for (const call of calls) {
    if (call.body_json !== undefined) continue
    try {
      const res = await client.send('Network.getResponseBody', { requestId: call.id }, sessionId)
      call.body_json = JSON.parse(res.body)
      call.ids = (call.body_json.recommendations || []).map((d) => d.dish_id)
      call.params_used = call.body_json.params_used
    } catch (e) {
      call.body_json = null
      call.body_error = String(e).slice(0, 160)
    }
  }
}

async function waitForCard() {
  await waitFor('!!document.querySelector(".deck__top") || !!document.querySelector(".exhausted") || !!document.querySelector(".notice .error-msg")', 20000, 'recommendation result')
}

let storageScriptId = null
async function setStoredUser(user) {
  // 在文档脚本之前写入身份：只需导航一次，也不会被上一份文档的 DOM 抢跑。
  if (storageScriptId) {
    await client
      .send('Page.removeScriptToEvaluateOnNewDocument', { identifier: storageScriptId }, sessionId)
      .catch(() => {})
  }
  const { identifier } = await client.send(
    'Page.addScriptToEvaluateOnNewDocument',
    {
      source: `try { localStorage.setItem('eatwhat.userId', '${user}'); } catch (e) {}
        window.__probeErrors = [];
        addEventListener('error', (e) => window.__probeErrors.push({ kind: 'error', message: String(e.message || ''), stack: String(e.error && e.error.stack || '') }));
        addEventListener('unhandledrejection', (e) => window.__probeErrors.push({ kind: 'unhandledrejection', message: String(e.reason && e.reason.message || e.reason || '') }));`,
    },
    sessionId,
  )
  storageScriptId = identifier
  await evalJs(`localStorage.setItem('eatwhat.userId', '${user}')`).catch(() => {})
}

async function loadFresh(user = 1) {
  // 先在存储层写入身份，再只导航一次：避免「导航→改 localStorage→再导航」在
  // Vite 冷启动时被旧文档的 DOM 抢跑（曾导致 before/after 读到不同文档）。
  await setStoredUser(user)
  await goto(`${ORIGIN}/m/home`)
  await waitForCard()
  await sleep(900)
}

async function waitSettled(extra = 250) {
  await waitFor('!document.querySelector(".fade-leave-active, .fade-enter-active")', 8000, 'route transition settled').catch(() => {})
  await sleep(extra)
}

function assert(cond, message) {
  if (!cond) throw new Error(message)
}

async function runPhase(name, fn) {
  if (!phasesWanted.has(name)) return
  phase = name
  evidence.phases[name] = { started_at: new Date().toISOString(), actions: [] }
  const startIdx = evidence.network.length
  try {
    await fn(startIdx)
    evidence.phases[name].result = 'PASS'
  } catch (err) {
    evidence.phases[name].result = 'FAIL'
    evidence.phases[name].error = String(err.message || err)
    console.error(`[${name}] FAIL: ${err.message}`)
    await screenshot('fail').catch(() => {})
  } finally {
    evidence.phases[name].ended_at = new Date().toISOString()
    evidence.phases[name].recommend_calls = recommendCalls(startIdx)
    await hydrateRecommendBodies(evidence.phases[name].recommend_calls)
    evidence.phases[name].state = await pageState().catch(() => null)
    const pageErrors = await evalJs('window.__probeErrors || []').catch(() => [])
    pageErrors.forEach((e) => evidence.page_errors.push({ phase: name, ...e }))
    evidence.phases[name].page_errors = pageErrors
  }
}

/* ---------------- phases ---------------- */
await runPhase('home', async (startIdx) => {
  await setViewport(390, 844)
  await loadFresh(1)
  const s = await pageState()
  const g = await geometry()
  assert(s.chips.length >= 10, `first load returned ${s.chips.length} candidates`)
  assert(s.top_name, 'top card missing')
  const calls = recommendCalls(startIdx)
  await hydrateRecommendBodies(calls)
  assert(calls.length >= 1, 'no /recommend/single request')
  assert(calls[0].status === 200, `recommend status ${calls[0].status}`)
  assert((calls[0].ids || []).length === s.chips.length, 'UI chips do not match response ids')
  assert(JSON.stringify(calls[0].ids) === JSON.stringify(s.chips), 'chip order differs from response order')
  assert(g.scroll.scrollHeight <= g.viewport.height + 1, 'page scrolls vertically at 390x844')
  assert(g.scroll.scrollWidth <= g.viewport.width + 1, 'horizontal overflow at 390x844')
  assert(g.overlap_actions_tabbar <= 0, 'actions overlap tabbar at 390x844')
  assert(g.card_pct <= 60, `card ${g.card_pct}% > 60%`)
  assert(Object.values(g.in_viewport).every(Boolean), 'some key block is outside the viewport')
  assert(g.greeting_visible && g.panel_visible && g.top_card_visible && g.candidates_visible && g.actions_visible, 'key block not visible')
  assert(g.ghost.length > 0 && g.ghost.some((x) => x.visibleSliverBelowTop > 0), 'next-card sliver not visible')
  assert(Object.values(g.hits).every(Boolean), `hit test failed: ${JSON.stringify(g.hits)}`)
  assert(g.content_overflow <= 0, `card content overflow ${g.content_overflow}px`)
  evidence.phases.home.geometry_844 = g
  evidence.phases.home.first_load = { request_user: calls[0].request_headers['X-User-Id'], status: calls[0].status, ids: calls[0].ids, params_used: calls[0].params_used, top: s.top_name, greeting: s.greet }
  await screenshot('390x844-home')

  // Real click 换一个: card changes locally, no checkin.
  const before = await pageState()
  evidence.phases.home.pass_click = { before: before.top_dish_id, before_chips: before.chips.length, before_top_name: before.top_name }
  await clickEl(ACT('换一个'), '换一个 (390x844)')
  await sleep(700)
  const after = await pageState()
  evidence.phases.home.pass_click.after = after.top_dish_id
  evidence.phases.home.pass_click.after_chips = after.chips.length
  evidence.phases.home.pass_click.after_top_name = after.top_name
  assert(after.top_dish_id !== before.top_dish_id, `换一个 did not advance the deck (${before.top_dish_id} -> ${after.top_dish_id}, chips ${before.chips.length} -> ${after.chips.length})`)

  // 390x667
  await setViewport(390, 667)
  await sleep(400)
  const s667 = await pageState()
  const g667 = await geometry()
  assert(s667.chips.length > 0, 'no deck at 390x667')
  assert(g667.scroll.scrollHeight <= g667.viewport.height + 1, 'page scrolls at 390x667')
  assert(g667.scroll.scrollWidth <= g667.viewport.width + 1, 'horizontal overflow at 390x667')
  assert(g667.overlap_actions_tabbar <= 0, 'actions overlap tabbar at 390x667')
  assert(g667.card_pct <= 60, `card ${g667.card_pct}% > 60% at 667`)
  assert(Object.values(g667.in_viewport).every(Boolean), 'some key block outside 390x667 viewport')
  assert(g667.greeting_visible && g667.panel_visible && g667.top_card_visible && g667.candidates_visible && g667.actions_visible, 'key block not visible at 667')
  assert(g667.ghost.length > 0 && g667.ghost.some((x) => x.visibleSliverBelowTop > 0), 'next-card sliver not visible at 667')
  assert(Object.values(g667.hits).every(Boolean), `hit test failed at 667: ${JSON.stringify(g667.hits)}`)
  assert(g667.content_overflow <= 0, `card content overflow ${g667.content_overflow}px at 667`)
  evidence.phases.home.geometry_667 = g667
  await screenshot('390x667-home')

  // Real click 就吃这个 -> confirm panel -> cancel (checkin is its own phase)
  await clickEl(ACT('就吃这个'), '就吃这个 (390x667)')
  await waitFor('!!document.querySelector(".confirm")', 4000, 'confirm panel')
  const confirm = await pageState()
  assert(confirm.confirm_text && confirm.confirm_text.includes('吗'), 'confirm panel text missing')
  await screenshot('confirm-panel')
  await clickEl(BTN('再想想'), '再想想 (cancel)')
  await waitFor('!document.querySelector(".confirm")', 4000, 'confirm panel closed')
  assert((await pageState()).deck_count === 1, 'deck not restored after cancel')
})

await runPhase('nav', async () => {
  await setViewport(390, 844)
  await loadFresh(1)
  // 首页 -> 足迹 -> 我的 -> 首页
  const steps = []
  async function tab(name, expectPath, contentNeedle, titleNeedle = name) {
    await clickEl(TAB(name), `tab ${name}`)
    await waitFor(`location.pathname === '${expectPath}'`, 8000, `route ${expectPath}`)
    await waitFor(`document.body.innerText.includes(${JSON.stringify(contentNeedle)})`, 10000, `content ${contentNeedle}`)
    await sleep(350)
    const s = await pageState()
    steps.push({ tab: name, url: s.url, title: s.title, needle: contentNeedle, found: s.body_text.includes(contentNeedle), active: s.active_tab })
    assert(s.url === expectPath, `url ${s.url} != ${expectPath}`)
    assert(s.title.includes(titleNeedle), `title ${s.title} missing ${titleNeedle}`)
    return s
  }
  await tab('足迹', '/m/footprint', '饮食足迹', '足迹')
  await screenshot('footprint')
  await client.send('Page.reload', {}, sessionId)
  await waitFor('document.readyState === "complete"', 15000, 'footprint reload')
  await waitFor('document.body.innerText.includes("饮食足迹")', 12000, 'footprint after reload')
  steps.push({ reload: 'footprint', url: (await pageState()).url, title: (await pageState()).title })
  await screenshot('footprint-reload')
  await tab('我的', '/m/profile', '切换室友', '我的')
  await screenshot('profile')
  await client.send('Page.reload', {}, sessionId)
  await waitFor('document.readyState === "complete"', 15000, 'profile reload')
  await waitFor('document.body.innerText.includes("切换室友")', 12000, 'profile after reload')
  steps.push({ reload: 'profile', url: (await pageState()).url, title: (await pageState()).title })
  await screenshot('profile-reload')
  await tab('首页', '/m/home', '想吃点什么', '首页')
  await screenshot('home-back')
  // sandbox open/close, then navigate again (N01)
  await clickEl(SEL('[aria-label="打开算法沙盒"]'), 'open sandbox')
  await waitFor('!!document.querySelector(".sandbox")', 5000, 'sandbox open')
  await sleep(500)
  const openState = await pageState()
  assert(openState.body_overflow === 'hidden', 'body overflow not locked when sandbox open')
  await screenshot('sandbox-open')
  await clickEl(SEL('[aria-label="关闭"]'), 'close sandbox')
  await waitFor('!document.querySelector(".sandbox")', 5000, 'sandbox closed')
  await sleep(450)
  const closedState = await pageState()
  assert(closedState.body_overflow === '', 'body overflow not restored after sandbox close')
  await tab('足迹', '/m/footprint', '饮食足迹', '足迹')
  await tab('我的', '/m/profile', '切换室友', '我的')
  // profile -> fridge entry -> back
  await clickEl(SEL('.entry[href="/m/fridge"]'), 'fridge entry')
  await waitFor('location.pathname === "/m/fridge"', 8000, 'route /m/fridge')
  await waitFor('document.body.innerText.includes("冰箱里有什么")', 10000, 'fridge content')
  await screenshot('fridge')
  const fridge = await pageState()
  steps.push({ entry: 'fridge', url: fridge.url, title: fridge.title, found: fridge.body_text.includes('冰箱里有什么') })
  // real browser back via keyboard (Alt+Left)
  await pressKey('AltLeft', 'AltLeft', 1)
  await sleep(60)
  await pressKey('ArrowLeft', 'ArrowLeft', 1)
  await waitFor('location.pathname === "/m/profile"', 8000, 'back to /m/profile')
  await waitFor('document.body.innerText.includes("切换室友")', 10000, 'profile after back')
  const backState = await pageState()
  steps.push({ back: 'alt+left', url: backState.url, title: backState.title, found: backState.body_text.includes('切换室友') })
  // final home
  await clickEl(TAB('首页'), 'tab 首页 (final)')
  await waitFor('location.pathname === "/m/home"', 8000, 'home final')
  await waitFor('!!document.querySelector(".deck__top")', 15000, 'home deck final')
  evidence.phases.nav.steps = steps
  const errs = evidence.console_events.filter((e) => e.phase === 'nav' && e.type === 'error')
  const logs = evidence.console_events.filter((e) => e.phase === 'nav' && e.type === 'log-error')
  const exc = evidence.exceptions.filter((e) => e.phase === 'nav')
  assert(errs.length === 0, `console errors during nav: ${JSON.stringify(errs)}`)
  assert(logs.length === 0, `log errors during nav: ${JSON.stringify(logs)}`)
  assert(exc.length === 0, `exceptions during nav: ${JSON.stringify(exc)}`)
})

await runPhase('sandbox', async (startIdx) => {
  await setViewport(390, 844)
  await loadFresh(1)
  const baseCalls = recommendCalls(startIdx)
  await clickEl(SEL('[aria-label="打开算法沙盒"]'), 'open sandbox')
  await waitFor('!!document.querySelector(".sandbox")', 5000, 'sandbox open')
  await sleep(500)
  // λ slider: real click, then End (max 2.0)
  await clickEl('document.querySelectorAll(".sandbox input[type=range]")[0]', 'lambda slider')
  await pressKey('End', 'End')
  await sleep(1400)
  const calls = recommendCalls(startIdx)
  await hydrateRecommendBodies(calls)
  const last = calls[calls.length - 1]
  assert(calls.length > baseCalls.length, 'no refetch after slider change')
  assert(last.post, 'refetch has no request body')
  const post = JSON.parse(last.post)
  assert(post.override_params && Number(post.override_params.lambda_decay) === 2, `lambda override not sent: ${last.post}`)
  const s = await pageState()
  assert(s.drawer_top5_names.length === 5, 'drawer top5 missing')
  assert(JSON.stringify(s.drawer_top5_names) === JSON.stringify(s.chip_names.slice(0, 5)), `drawer top5 != home chips: ${JSON.stringify(s.drawer_top5_names)} vs ${JSON.stringify(s.chip_names.slice(0, 5))}`)
  assert(JSON.stringify(s.drawer_top5_scores) === JSON.stringify(s.chip_scores.slice(0, 5)), 'drawer scores != home chip scores')
  assert(JSON.stringify(last.ids) === JSON.stringify(s.chips), 'home deck is not from the last response')
  const firstRec = last.body_json.recommendations[0]
  assert(s.top_name === firstRec.name, `top card ${s.top_name} != response ${firstRec.name}`)
  assert(s.top_score.includes(Number(firstRec.total_score).toFixed(1)), `top score ${s.top_score} != response ${firstRec.total_score}`)
  assert(s.top_reason && s.top_reason === firstRec.explain_reason, 'top-card explain text is not the response explain_reason')
  assert(s.sandbox_used.includes('λ 2.00'), `drawer used label stale: ${s.sandbox_used}`)
  const params = last.params_used
  assert(s.sandbox_used.includes(`β ${Number(params.beta_weather).toFixed(2)}`), 'drawer used β mismatch')
  evidence.phases.sandbox.single_change = { request: post, params_used: params, used_label: s.sandbox_used, top5: s.drawer_top5_names, first_ids: last.ids.slice(0, 6) }
  await screenshot('sandbox-lambda2')

  // rapid consecutive changes on β: Home then End quickly -> last (1.0) wins
  const beta = 'document.querySelectorAll(".sandbox input[type=range]")[2]'
  await clickEl(beta, 'beta slider')
  const beforeRapid = recommendCalls(startIdx).length
  await pressKey('Home', 'Home')
  await sleep(40)
  await pressKey('End', 'End')
  await sleep(1600)
  const rapidCalls = recommendCalls(startIdx)
  await hydrateRecommendBodies(rapidCalls)
  const rapidLast = rapidCalls[rapidCalls.length - 1]
  const rapidPost = JSON.parse(rapidLast.post)
  assert(Number(rapidPost.override_params.beta_weather) === 1, `last rapid change not honoured: ${rapidLast.post}`)
  // SSOT: 四权重（α/β/γ/δ）在算法内归一化到和 1；override 里 β=1 的生效值是 1/1.75
  const expectedBeta = 1 / (0.35 + 1 + 0.2 + 0.2)
  assert(Math.abs(Number(rapidLast.params_used.beta_weather) - expectedBeta) < 0.001, `params_used beta ${rapidLast.params_used.beta_weather} != normalized ${expectedBeta}`)
  const rapidState = await pageState()
  assert(rapidState.sandbox_used.includes(`β ${expectedBeta.toFixed(2)}`), `drawer used label not normalized: ${rapidState.sandbox_used}`)
  assert(JSON.stringify(rapidLast.ids) === JSON.stringify(rapidState.chips), 'deck not from the last rapid response')
  evidence.phases.sandbox.rapid = { requests: rapidCalls.length - beforeRapid, request: rapidPost, params_used: rapidLast.params_used, expected_normalized_beta: expectedBeta, used_label: rapidState.sandbox_used }
  await screenshot('sandbox-rapid-beta1')

  // reset
  await clickEl(BTN('恢复默认参数', 'document.querySelector(".sandbox")'), 'reset params')
  await sleep(1600)
  const resetCalls = recommendCalls(startIdx)
  await hydrateRecommendBodies(resetCalls)
  const resetLast = resetCalls[resetCalls.length - 1]
  const resetPost = JSON.parse(resetLast.post)
  assert(!resetPost.override_params, `reset still sends override_params: ${resetLast.post}`)
  assert(Number(resetLast.params_used.lambda_decay) === 0.5 && Number(resetLast.params_used.beta_weather) === 0.25, 'reset params not back to defaults')
  evidence.phases.sandbox.reset = { request: resetPost, params_used: resetLast.params_used }
  await screenshot('sandbox-reset')
  await clickEl(SEL('[aria-label="关闭"]'), 'close sandbox (before quick leave)')
  await waitFor('!document.querySelector(".sandbox")', 5000, 'sandbox closed (before quick leave)')
  await sleep(450)

  // residual timer: change a slider then leave home within the debounce window
  // (alt+left is a real browser navigation, so the drawer cannot occlude it)
  await clickEl(TAB('足迹'), 'tab 足迹 (prime history)')
  await waitFor('location.pathname === "/m/footprint"', 8000, 'footprint primed')
  await clickEl(TAB('首页'), 'tab 首页 (back to home)')
  await waitFor('location.pathname === "/m/home"', 8000, 'home primed')
  await waitForCard()
  await waitSettled(600)
  await clickEl(SEL('[aria-label="打开算法沙盒"]'), 'open sandbox (quick leave)')
  await waitFor('!!document.querySelector(".sandbox")', 5000, 'sandbox open (quick leave)')
  await sleep(500)
  await clickEl('document.querySelectorAll(".sandbox input[type=range]")[1]', 'omega slider')
  await pressKey('End', 'End')
  const navAt = Date.now()
  // 浏览器后退在 headless 下无法用合成按键触发；history.back() 走同一 popstate，
  // 让 vue-router 卸载 Home（被测的正是组件卸载而非整页刷新）。真实点击导航已在 nav 阶段覆盖。
  await evalJs('history.back()')
  await waitFor('location.pathname === "/m/footprint"', 8000, 'footprint after quick leave')
  evidence.phases.sandbox.quick_leave_navigation = 'history.back() (browser Back equivalent) immediately after a real slider input'
  await sleep(1800)
  const late = evidence.network.filter((n) => n.path.startsWith('/api/v1/recommend/single') && n.at > navAt)
  const navErrors = evidence.console_events.filter((e) => e.phase === 'sandbox' && e.type === 'error')
  const navExc = evidence.exceptions.filter((e) => e.phase === 'sandbox')
  evidence.phases.sandbox.quick_leave = { late_requests_after_navigation: late.length, late_request_paths: late.map((l) => l.path), console_errors: navErrors, exceptions: navExc }
  assert(navErrors.length === 0, `console errors after quick leave: ${JSON.stringify(navErrors)}`)
  assert(navExc.length === 0, `exceptions after quick leave: ${JSON.stringify(navExc)}`)
  assert(late.length === 0, `residual timer fired ${late.length} request(s) after leaving home`)
  assert((await pageState()).sandbox_open === false, 'sandbox left mounted after navigation')
  await screenshot('after-quick-leave')
  // returning home must not resurrect the sandbox / leave body overflow locked
  await clickEl(TAB('首页'), 'tab 首页 after quick leave')
  await waitFor('location.pathname === "/m/home"', 8000, 'home after quick leave')
  await waitForCard()
  await waitSettled(400)
  const backHome = await pageState()
  evidence.phases.sandbox.return_home = { sandbox_open: backHome.sandbox_open, body_overflow: backHome.body_overflow }
  assert(backHome.sandbox_open === false, 'sandbox reopened when returning to Home')
  assert(backHome.body_overflow === '', 'body overflow left locked after returning Home')
  await screenshot('return-home-closed')
})

await runPhase('role', async (startIdx) => {
  await setViewport(390, 844)
  await loadFresh(1)
  const u1 = await api('/users/1/profile', { user: 1 })
  const u2 = await api('/users/2/profile', { user: 2 })
  assert(u1.status === 200 && u2.status === 200, 'profile API failed')
  assert(u1.body.nickname !== u2.body.nickname, 'demo users have identical nicknames')
  const before = await pageState()
  assert(before.greet.includes(u1.body.nickname), `greeting ${before.greet} not user1`)
  await clickEl(TAB('我的'), 'tab 我的 (role)')
  await waitFor('location.pathname === "/m/profile"', 8000, 'profile route')
  await waitFor('document.body.innerText.includes("切换室友")', 10000, 'profile content')
  await clickEl(BTN('切换室友'), 'open roster')
  await waitFor('!!document.querySelector(".roster")', 4000, 'roster open')
  await screenshot('roster-open')
  const u2row = `[...document.querySelectorAll('.roster__row')].find((n) => n.textContent.includes(${JSON.stringify(u2.body.nickname)}))`
  await clickEl(u2row, `switch to ${u2.body.nickname}`)
  await waitFor(`document.body.innerText.includes(${JSON.stringify(u2.body.nickname)})`, 8000, 'profile user2')
  const profileText = await evalJs('document.body.innerText')
  assert(profileText.includes(u2.body.persona_title), `profile missing user2 persona title ${u2.body.persona_title}`)
  const genes = await evalJs(`[...document.querySelectorAll('.gene__val')].map((n) => Number(n.textContent))`)
  const geneKeys = ['spicy_level', 'oily_level', 'soup_level', 'temp_fit', 'satiety_level', 'prep_speed', 'social_fit', 'comfort_level']
  const expectedGenes = geneKeys.map((k) => Math.round(Number(u2.body.base_vector[k] ?? 0) * 100))
  assert(JSON.stringify(genes) === JSON.stringify(expectedGenes), `profile genes ${JSON.stringify(genes)} != user2 ${JSON.stringify(expectedGenes)}`)
  for (const tag of u2.body.veto_tags || []) {
    assert(profileText.includes(tag), `profile missing user2 veto tag ${tag}`)
  }
  const persisted = await evalJs(`localStorage.getItem('eatwhat.userId')`)
  assert(Number(persisted) === 2, 'localStorage user id not switched')
  // home must refetch with X-User-Id 2
  const idxBeforeHome = evidence.network.length
  await clickEl(TAB('首页'), 'tab 首页 after switch')
  await waitFor('location.pathname === "/m/home"', 8000, 'home after switch')
  await waitForCard()
  await waitSettled(500)
  const calls = evidence.network.slice(idxBeforeHome).filter((n) => n.path.startsWith('/api/v1/recommend/single'))
  await hydrateRecommendBodies(calls)
  assert(calls.length >= 1, 'no recommendation request after role switch')
  assert(calls[0].request_headers['X-User-Id'] === '2', `recommend header ${calls[0].request_headers['X-User-Id']}`)
  const s = await pageState()
  assert(s.greet.includes(u2.body.nickname), `greeting still ${s.greet}`)
  const pageBody = JSON.parse(calls[calls.length - 1].post)
  const u2rec = await api('/recommend/single', { method: 'POST', user: 2, body: pageBody })
  assert(u2rec.status === 200, 'user2 recommend API failed')
  assert(JSON.stringify(calls[calls.length - 1].ids) === JSON.stringify(u2rec.body.recommendations.map((d) => d.dish_id)), 'user2 home cards differ from user2 API (same body)')
  // footprint must use user 2 header
  await clickEl(TAB('足迹'), 'tab 足迹 (role)')
  await waitFor('location.pathname === "/m/footprint"', 8000, 'footprint role')
  await waitFor('document.body.innerText.includes("饮食足迹")', 10000, 'footprint content')
  await sleep(500)
  const statsCalls = evidence.network.filter((n) => n.path.startsWith('/api/v1/logs/stats/'))
  const lastStats = statsCalls[statsCalls.length - 1]
  assert(lastStats && lastStats.request_headers['X-User-Id'] === '2', `stats header ${lastStats?.request_headers?.['X-User-Id']}`)
  const u2stats = await api('/logs/stats/2', { user: 2 })
  const shown = await evalJs(`(() => { const n = [...document.querySelectorAll('.stat__num')].map((x) => Number(x.textContent)); return { meals: n[0], expense: n[1] }; })()`)
  assert(shown.meals === u2stats.body.meals_this_week, `footprint meals ${shown.meals} != user2 API ${u2stats.body.meals_this_week}`)
  assert(Math.round(shown.expense) === Math.round(u2stats.body.weekly_expense), `footprint expense ${shown.expense} != user2 API ${u2stats.body.weekly_expense}`)
  await screenshot('footprint-user2')
  // switch back to 1
  await clickEl(TAB('我的'), 'tab 我的 (switch back)')
  await waitFor('location.pathname === "/m/profile"', 8000, 'profile back')
  await waitFor('document.body.innerText.includes("切换室友")', 10000, 'profile back content')
  if (!(await evalJs('!!document.querySelector(".roster")'))) await clickEl(BTN('切换室友'), 'open roster again')
  await waitFor('!!document.querySelector(".roster")', 4000, 'roster again')
  const u1row = `[...document.querySelectorAll('.roster__row')].find((n) => n.textContent.includes(${JSON.stringify(u1.body.nickname)}))`
  await clickEl(u1row, `switch back to ${u1.body.nickname}`)
  await waitFor(`document.body.innerText.includes(${JSON.stringify(u1.body.nickname)})`, 8000, 'profile user1 again')
  const back = await evalJs(`localStorage.getItem('eatwhat.userId')`)
  assert(Number(back) === 1, 'user id not restored to 1')
  evidence.phases.role.users = { u1: u1.body.nickname, u2: u2.body.nickname }
  evidence.phases.role.requests = { recommend_header: calls[0].request_headers['X-User-Id'], stats_header: lastStats.request_headers['X-User-Id'] }
})

await runPhase('checkin', async (startIdx) => {
  await setViewport(390, 844)
  await loadFresh(1)
  const beforeStats = await api('/logs/stats/1', { user: 1 })
  assert(beforeStats.status === 200, 'stats before failed')
  const s = await pageState()
  const dishId = s.top_dish_id
  const dishName = s.top_name
  // 就吃这个 -> confirm -> 确认就吃这个
  await clickEl(ACT('就吃这个'), '就吃这个 (checkin)')
  await waitFor('!!document.querySelector(".confirm")', 4000, 'confirm panel')
  await screenshot('checkin-confirm')
  await clickEl(BTN('确认就吃这个'), '确认就吃这个')
  await waitFor('!!document.querySelector(".toast")', 8000, 'checkin toast')
  const toast = (await pageState()).toast
  assert(toast && toast.includes('已记入足迹'), `toast: ${toast}`)
  const checkinCall = evidence.network.slice(startIdx).find((n) => n.path === '/api/v1/logs/checkin')
  assert(checkinCall && checkinCall.status === 200, `checkin status ${checkinCall?.status}`)
  assert(checkinCall.request_headers['X-User-Id'] === '1', 'checkin sent wrong user header')
  await screenshot('checkin-toast')
  const afterStats = await api('/logs/stats/1', { user: 1 })
  assert(afterStats.status === 200, 'stats after failed')
  const deltaMeals = afterStats.body.meals_this_week - beforeStats.body.meals_this_week
  const deltaExpense = Number((afterStats.body.weekly_expense - beforeStats.body.weekly_expense).toFixed(2))
  assert(deltaMeals === 1, `meals delta ${deltaMeals}`)
  assert(deltaExpense > 0, `expense delta ${deltaExpense}`)
  // footprint page
  await clickEl(TAB('足迹'), 'tab 足迹 after checkin')
  await waitFor('location.pathname === "/m/footprint"', 8000, 'footprint route')
  await waitFor('document.body.innerText.includes("饮食足迹")', 10000, 'footprint content')
  await waitFor(`document.body.innerText.includes(${JSON.stringify(dishName)})`, 10000, 'dish appears in footprint')
  const fpText = (await pageState()).body_text
  assert(fpText.includes(String(afterStats.body.meals_this_week)), 'footprint meals count not updated')
  await screenshot('footprint-after-checkin')
  // reload persists
  await goto(`${ORIGIN}/m/footprint`)
  await waitFor('document.body.innerText.includes("饮食足迹")', 10000, 'footprint after reload')
  await waitFor(`document.body.innerText.includes(${JSON.stringify(dishName)})`, 10000, 'dish persists after reload')
  const persistedStats = await api('/logs/stats/1', { user: 1 })
  assert(persistedStats.status === 200, 'stats after reload failed')
  assert(persistedStats.body.meals_this_week === afterStats.body.meals_this_week, 'stats changed after reload')
  await screenshot('footprint-after-reload')
  evidence.phases.checkin.dish = { id: dishId, name: dishName }
  evidence.phases.checkin.stats_before = beforeStats.body
  evidence.phases.checkin.stats_after = afterStats.body
  evidence.phases.checkin.delta = { meals: deltaMeals, expense: deltaExpense }
  evidence.phases.checkin.toast = toast
})

await runPhase('refill', async (startIdx, currentPhase) => {
  await setViewport(390, 844)
  await loadFresh(1)
  const batch1 = (await pageState()).chips
  assert(batch1.length === 24, `batch1 ${batch1.length}`)
  const seen = new Set(batch1)
  const batches = [{ index: 1, source: 'initial', ids: batch1 }]
  // swipe the whole first batch
  for (let i = 0; i < 40; i += 1) {
    const s = await pageState()
    if (s.deck_count === 0) break
    await clickEl(ACT('换一个'), `换一个 #${i + 1} (batch1)`, { mustHit: true })
    await sleep(520)
  }
  assert((await pageState()).exhausted_title, 'batch1 did not reach an exhausted state')
  // refill button lives in the exhausted block
  await clickEl(BTN('换一批', 'document.querySelector(".exhausted")'), '换一批 #1')
  await sleep(1600)
  let s = await pageState()
  let calls = recommendCalls(startIdx)
  await hydrateRecommendBodies(calls)
  let last = calls[calls.length - 1]
  assert(last && last.status === 200, 'refill request failed')
  assert(last.request_headers['X-User-Id'] === '1', 'refill wrong user')
  assert(last.ids.length === 24, `refill batch ${last.ids.length}`)
  assert(last.ids.every((id) => !seen.has(id)), 'refill returned already-seen dish')
  assert(JSON.stringify(last.ids) === JSON.stringify(s.chips), 'refill UI != response')
  batches.push({ index: 2, source: 'refill', ids: last.ids })
  last.ids.forEach((id) => seen.add(id))
  await screenshot('refill-batch2')

  // continue until the eligible pool is exhausted
  let guard = 0
  while (guard < 6) {
    guard += 1
    while (true) {
      const st = await pageState()
      if (st.deck_count === 0 || !!st.exhausted_title) break
      await clickEl(ACT('换一个'), `换一个 #${guard} (exhaust batch)`)
      await sleep(500)
    }
    const st = await pageState()
    if (st.exhausted_button && st.exhausted_button.includes('重置')) break
    assert(st.exhausted_button && st.exhausted_button.includes('换一批'), `unexpected empty state: ${JSON.stringify(st.exhausted_title)} / ${st.exhausted_button}`)
    const beforeCalls = recommendCalls(startIdx).length
    await clickEl(BTN('换一批', 'document.querySelector(".exhausted")'), `换一批 #${guard + 1}`)
    await sleep(1700)
    calls = recommendCalls(startIdx)
    await hydrateRecommendBodies(calls)
    last = calls[calls.length - 1]
    assert(calls.length > beforeCalls, '换一批 did not request')
    assert(last.request_headers['X-User-Id'] === '1', 'exhaust refill wrong user')
    const fresh = last.ids.filter((id) => !seen.has(id))
    assert(fresh.length === last.ids.length, 'exhaust refill repeated a seen dish')
    if (!last.ids.length) break
    last.ids.forEach((id) => seen.add(id))
    batches.push({ index: batches.length + 1, source: 'refill', ids: last.ids })
    await screenshot(`refill-batch${batches.length}`)
  }
  const final = await pageState()
  assert(final.exhausted_title && final.exhausted_title.includes('看完'), `pool exhaustion state: ${final.exhausted_title}`)
  assert(final.exhausted_button && final.exhausted_button.includes('重置'), 'reset button missing at pool exhaustion')
  await screenshot('pool-exhausted')
  // Clicking refill repeatedly must not fabricate anything; the UI shows reset, not 换一批.
  assert(!final.exhausted_button.includes('换一批'), 'still offering refill after pool exhausted')
  evidence.phases.refill.batches = batches
  evidence.phases.refill.seen_total = seen.size
  evidence.phases.refill.final_state = { title: final.exhausted_title, sub: final.exhausted_sub, button: final.exhausted_button }
  // reset restores a deck and clears exclusions
  const beforeReset = recommendCalls(startIdx).length
  await clickEl(BTN('重置', 'document.querySelector(".exhausted")'), '重置再看一轮')
  await sleep(1800)
  const afterReset = await pageState()
  const resetCalls = recommendCalls(startIdx)
  await hydrateRecommendBodies(resetCalls)
  const resetLast = resetCalls[resetCalls.length - 1]
  assert(resetCalls.length > beforeReset, 'reset did not refetch')
  assert(!resetLast.post.includes('exclude_dish_ids'), 'reset still excludes seen dishes')
  assert(afterReset.chips.length === 24, `deck after reset ${afterReset.chips.length}`)
  evidence.phases.refill.reset = { request: JSON.parse(resetLast.post), count: afterReset.chips.length }
  await screenshot('after-reset')

  // mode switch resets the exclusion set (real click on 下厨)
  await clickEl(`[...document.querySelectorAll('.mode-switch .switch-item')].find((n) => n.textContent.includes('下厨'))`, 'mode 下厨')
  await sleep(1600)
  const modeCalls = recommendCalls(startIdx)
  await hydrateRecommendBodies(modeCalls)
  const modeLast = modeCalls[modeCalls.length - 1]
  const modePost = JSON.parse(modeLast.post)
  assert(modePost.mode_type === 'HOME_COOKING', `mode request ${modePost.mode_type}`)
  assert(!modePost.exclude_dish_ids, 'mode switch kept exclusion set')
  evidence.phases.refill.mode_switch = { request: modePost, count: (await pageState()).chips.length }
  await screenshot('mode-home-cooking')

  // bubble change also clears the exclusion set (same watcher as mode)
  await clickEl(`[...document.querySelectorAll('.bubble-row .bubble')].find((n) => n.textContent.includes('重口'))`, 'bubble 重口')
  await sleep(1600)
  const bubbleCalls = recommendCalls(startIdx)
  await hydrateRecommendBodies(bubbleCalls)
  const bubbleLast = bubbleCalls[bubbleCalls.length - 1]
  const bubblePost = JSON.parse(bubbleLast.post)
  assert(bubblePost.bubbles.includes('craving_heavy'), 'bubble not sent')
  assert(!bubblePost.exclude_dish_ids, 'bubble change kept exclusion set')
  evidence.phases.refill.bubble_switch = { request: bubblePost, count: (await pageState()).chips.length }
  await screenshot('bubble-craving-heavy')
})

await runPhase('faults', async (startIdx) => {
  await setViewport(390, 844)
  await loadFresh(1)
  // controlled 500 via Fetch interception
  await client.send(
    'Fetch.enable',
    { patterns: [{ urlPattern: '*/api/v1/recommend/single', requestStage: 'Request' }] },
    sessionId,
  )
  let fulfilled = 0
  const onFetch = async (msg) => {
    if (!msg.params.request.url.includes('/recommend/single')) {
      await client.send('Fetch.continueRequest', { requestId: msg.params.requestId }, sessionId).catch(() => {})
      return
    }
    fulfilled += 1
    await client
      .send(
        'Fetch.fulfillRequest',
        {
          requestId: msg.params.requestId,
          responseCode: 500,
          responseHeaders: [{ name: 'Content-Type', value: 'text/plain; charset=utf-8' }],
          body: Buffer.from('Internal Server Error').toString('base64'),
        },
        sessionId,
      )
      .catch(() => {})
  }
  fetchHandler = onFetch
  await clickEl(`[...document.querySelectorAll('.runrow__cta button, .runrow__cta')].find((n) => (n.textContent || '').includes('开始决策')) || document.querySelector('.runrow__cta')`, '开始决策 (500 injection)')
  await waitFor('!!document.querySelector(".notice .error-msg")', 10000, 'error notice')
  const errState = await pageState()
  assert(fulfilled >= 1, '500 was not injected')
  assert(errState.error_title, 'error title missing')
  assert(!/internal server error/i.test(errState.error_text || ''), `raw 500 leaked to UI: ${errState.error_text}`)
  assert(!/\b500\b/.test(errState.error_text || ''), `raw status leaked to UI: ${errState.error_text}`)
  assert(errState.error_text.length <= 80, `error copy too technical: ${errState.error_text}`)
  await screenshot('controlled-500')
  // retry after clearing interception -> real recommendation returns
  await client.send('Fetch.disable', {}, sessionId)
  fetchHandler = null
  await clickEl(BTN('重试'), '重试 after 500')
  await waitForCard()
  await sleep(500)
  const recovered = await pageState()
  assert(recovered.chips.length > 0, 'retry did not restore a deck')
  assert(!recovered.error_text, 'error state did not clear after retry')
  await screenshot('after-500-retry')

  // offline -> controlled network failure -> friendly error -> recovery
  await client.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }, sessionId)
  await clickEl(`[...document.querySelectorAll('.runrow__cta button, .runrow__cta')].find((n) => (n.textContent || '').includes('开始决策')) || document.querySelector('.runrow__cta')`, '开始决策 (offline)')
  await waitFor('!!document.querySelector(".notice .error-msg")', 12000, 'offline error notice')
  const offlineState = await pageState()
  assert(offlineState.error_text && offlineState.error_text.includes('后端没连上'), `offline copy: ${offlineState.error_text}`)
  await screenshot('offline-error')
  await client.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }, sessionId)
  await clickEl(BTN('重试'), '重试 after offline')
  await waitForCard()
  await sleep(400)
  assert((await pageState()).chips.length > 0, 'offline retry did not recover')
  await screenshot('after-offline-retry')

  // controlled empty 200 -> stable empty state (no fake dishes, no loop)
  await client.send(
    'Fetch.enable',
    { patterns: [{ urlPattern: '*/api/v1/recommend/single', requestStage: 'Request' }] },
    sessionId,
  )
  let emptyServed = 0
  const onFetchEmpty = async (msg) => {
    if (!msg.params.request.url.includes('/recommend/single')) {
      await client.send('Fetch.continueRequest', { requestId: msg.params.requestId }, sessionId).catch(() => {})
      return
    }
    emptyServed += 1
    await client
      .send(
        'Fetch.fulfillRequest',
        {
          requestId: msg.params.requestId,
          responseCode: 200,
          responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
          body: Buffer.from(
            JSON.stringify({ mode_type: 'OUT_DINING', recommendations: [], combo: null, params_used: { lambda_decay: 0.5, omega_group: 0.5, alpha_taste: 0.35, beta_weather: 0.25, gamma_budget: 0.2, delta_status: 0.2 }, bubble_effects: { applied: [], ignored: [] } }),
          ).toString('base64'),
        },
        sessionId,
      )
      .catch(() => {})
  }
  fetchHandler = onFetchEmpty
  await clickEl(`[...document.querySelectorAll('.runrow__cta button, .runrow__cta')].find((n) => (n.textContent || '').includes('开始决策')) || document.querySelector('.runrow__cta')`, '开始决策 (empty 200)')
  await waitFor('!!document.querySelector(".exhausted")', 10000, 'empty state')
  const emptyState = await pageState()
  assert(emptyState.deck_count === 0, 'empty response produced cards')
  assert(emptyState.exhausted_title, 'empty state has no title')
  assert(emptyServed >= 1, 'empty response not injected')
  const emptyTitle1 = emptyState.exhausted_title
  await sleep(1500)
  const emptyTitle2 = (await pageState()).exhausted_title
  assert(emptyTitle1 === emptyTitle2, 'empty state is unstable')
  await screenshot('empty-candidates')
  await client.send('Fetch.disable', {}, sessionId)
  fetchHandler = null
  evidence.phases.faults.results = {
    controlled_500: { injected: fulfilled, title: errState.error_title, message: errState.error_text },
    offline: { message: offlineState.error_text },
    empty: { injected: emptyServed, title: emptyState.exhausted_title, sub: emptyState.exhausted_sub, button: emptyState.exhausted_button, stable: emptyTitle1 === emptyTitle2 },
  }
})

/* ---------------- finish ---------------- */
try {
  await client.send('Target.closeTarget', { targetId })
} catch {
  /* ignore */
}
client.ws.close()

// phase verdicts
for (const [name, p] of Object.entries(evidence.phases)) {
  evidence.verdicts[name] = p.result
}
const hardFailures = Object.entries(evidence.verdicts).filter(([, v]) => v !== 'PASS')
if (evidence.page_errors.length) {
  evidence.verdicts.page_errors = 'FAIL'
  hardFailures.push(['page_errors', 'FAIL'])
}
writeFileSync(join(OUT, 'browser_evidence.json'), JSON.stringify(evidence, null, 2))
console.log(JSON.stringify({ verdicts: evidence.verdicts, screenshots: evidence.screenshots.length, network: evidence.network.length, console_errors: evidence.console_events.filter((e) => e.type === 'error').length, console_warnings: evidence.console_events.filter((e) => e.type === 'warning').length, exceptions: evidence.exceptions.length, page_errors: evidence.page_errors.length }, null, 2))
if (hardFailures.length) {
  for (const [name, p] of Object.entries(evidence.phases)) {
    if (p.result !== 'PASS') console.error(`${name}: ${p.error}`)
  }
  process.exit(1)
}
