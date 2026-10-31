/**
 * 「换一批」必须给新候选（审查 F13）。
 *
 * 流程：把一批划完 → 点「换一批」→ 断言
 *   1. 请求里带了 24 个 exclude_dish_ids
 *   2. 新一批的 dish_id 与已划过的没有任何交集
 *   3. 卡组确实有新卡，而不是直接弹「本轮推荐已看完」
 *
 * 用法：node scripts/refill-fresh.mjs
 */
const CDP = 'http://127.0.0.1:9222'
const ORIGIN = 'http://127.0.0.1:5173'
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

async function waitFor(client, sessionId, expression, timeoutMs = 25000, label = 'condition') {
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
  await client.send('Page.enable', {}, sessionId)
  await client.send('Runtime.enable', {}, sessionId)
  await client.send(
    'Emulation.setDeviceMetricsOverride',
    { width: 393, height: 852, deviceScaleFactor: 2, mobile: true },
    sessionId,
  )
  await client.send(
    'Page.addScriptToEvaluateOnNewDocument',
    {
      source: `
        window.__calls = [];
        const origFetch = window.fetch;
        window.fetch = async (...args) => {
          const url = String(args[0]);
          const res = await origFetch(...args);
          if (url.includes('/recommend/single')) {
            const body = args[1] && args[1].body ? JSON.parse(args[1].body) : null;
            const clone = res.clone();
            const json = await clone.json().catch(() => null);
            window.__calls.push({ body, ids: (json?.recommendations || []).map((d) => d.dish_id) });
          }
          return res;
        };
      `,
    },
    sessionId,
  )

  await client.send('Page.navigate', { url: `${ORIGIN}/m/home` }, sessionId)
  await waitFor(client, sessionId, '!!document.querySelector(".dish")', 20000, 'card rendered')
  await sleep(600)

  // 一批划完
  let swiped = 0
  for (let i = 0; i < 60; i += 1) {
    const gone = await evaluate(client, sessionId, '!document.querySelector(".dish")')
    if (gone) break
    await evaluate(
      client,
      sessionId,
      `(() => { const b = [...document.querySelectorAll('.text-btn')].find((x) => x.textContent.includes('换一个')); if (b) b.click(); return true })()`,
    )
    swiped += 1
    await sleep(620)
  }

  const beforeRefill = await evaluate(client, sessionId, 'window.__calls.length')
  // 点「换一批」
  const clicked = await evaluate(
    client,
    sessionId,
    `(() => {
      const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('换一批'));
      if (!btn) return false;
      btn.click();
      return true;
    })()`,
  )
  if (!clicked) throw new Error('没找到「换一批」按钮，划卡可能没走完')
  await sleep(2200)

  const state = JSON.parse(
    await evaluate(
      client,
      sessionId,
      `JSON.stringify({
        calls: window.__calls.length,
        lastBody: window.__calls.at(-1)?.body || null,
        lastIds: window.__calls.at(-1)?.ids || [],
        firstIds: window.__calls[0]?.ids || [],
        card: document.querySelector('.dish__title')?.textContent?.trim() || null,
        exhausted: !!document.querySelector('.exhausted'),
      })`,
    ),
  )

  const excluded = state.lastBody?.exclude_dish_ids || []
  const overlap = state.lastIds.filter((id) => state.firstIds.includes(id))
  const reasons = []
  if (state.calls <= beforeRefill) reasons.push('点「换一批」没有再发请求')
  if (excluded.length !== state.firstIds.length)
    reasons.push(`exclude_dish_ids 数量 ${excluded.length}，应为 ${state.firstIds.length}`)
  if (overlap.length) reasons.push(`新一批仍有旧菜：${overlap.join(',')}`)
  if (!state.lastIds.length) reasons.push('新一批是空的')
  if (state.exhausted) reasons.push('换一批之后直接进了空态')

  console.log(`swiped ${swiped} 张，第一批 ${state.firstIds.length} 道`)
  console.log(`refill 请求 exclude ${excluded.length} 个 | 返回 ${state.lastIds.length} 道`)
  console.log(`新首卡：${state.card}`)
  reasons.forEach((r) => console.log(`   - ${r}`))
  console.log(`${reasons.length ? 'FAIL' : 'PASS'} 「换一批」给的是新候选`)

  client.ws.close()
  if (reasons.length) process.exit(1)
}

main().catch((err) => {
  console.error('FAILED:', err.message)
  process.exit(1)
})
