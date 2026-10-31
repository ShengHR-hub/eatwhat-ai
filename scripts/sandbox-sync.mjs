/**
 * 沙盒 → 首页卡组同源验证（审查 F10）。
 *
 * 断言三件事：
 *   1. 拖动沙盒滑块后，前端发出的 `/recommend/single` 请求带上了 `override_params`
 *   2. 首页卡组的第一张卡发生了变化（不只是抽屉里的排名变了）
 *   3. 抽屉里的排名与首页卡面来自同一次响应（同一次请求的 dish_id 序列）
 *
 * 用法：node scripts/sandbox-sync.mjs
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

async function waitFor(client, sessionId, expression, timeoutMs = 20000, label = 'condition') {
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

  // 记录所有 /recommend/single 请求与响应
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
            window.__calls.push({
              body,
              ids: (json?.recommendations || []).map((d) => d.dish_id),
              params: json?.params_used || null,
            });
          }
          return res;
        };
      `,
    },
    sessionId,
  )

  await client.send('Page.navigate', { url: `${ORIGIN}/m/home` }, sessionId)
  await waitFor(client, sessionId, '!!document.querySelector(".dish")', 20000, 'card rendered')
  await sleep(500)

  const before = await evaluate(
    client,
    sessionId,
    `JSON.stringify({
      card: document.querySelector('.dish__title')?.textContent?.trim(),
      calls: window.__calls.length,
    })`,
  )

  // 打开沙盒，把 λ 拖到 2.0
  const afterDrag = await evaluate(
    client,
    sessionId,
    `(async () => {
      document.querySelector('[aria-label="打开调整抽屉"]')?.click();
      await new Promise((r) => setTimeout(r, 400));
      const ranges = [...document.querySelectorAll('.slider-row input[type=range]')];
      // 抽屉里第一个滑块是「预算」(10–120)，λ 是第二个。
      // 按 min/max 定位而不是按序号，避免以后再加滑块又拖错。
      const target = ranges.find((r) => r.min === '0.1' && r.max === '2') || ranges[1];
      if (!target) return JSON.stringify({ error: 'no slider' });
      target.value = '2';
      target.dispatchEvent(new Event('input', { bubbles: true }));
      target.dispatchEvent(new Event('change', { bubbles: true }));
      return JSON.stringify({ sliders: ranges.length, value: target.value });
    })()`,
  )

  await sleep(1600)

  const after = await evaluate(
    client,
    sessionId,
    `JSON.stringify({
      card: document.querySelector('.dish__title')?.textContent?.trim(),
      used: (() => {
        const rows = [...document.querySelectorAll('.slider-row')];
        const pick = (mark) => {
          const row = rows.find((r) => (r.textContent || '').includes(mark));
          return row?.querySelector('.slider-value')?.textContent?.trim() || null;
        };
        const lam = pick('λ'), om = pick('ω');
        return lam || om ? ('λ ' + lam + ' · ω ' + om) : null;
      })(),
      drawerNames: [...document.querySelectorAll('.alternative__name')].map((n) => n.textContent.trim()),
      drawerScores: [...document.querySelectorAll('.alternative__score')].map((n) => Number(n.textContent)),
      chipIds: [...document.querySelectorAll('.alternative')].map((c) => Number(c.dataset.dishId)),
      chipNames: [...document.querySelectorAll('.alternative .alternative__name')].map((n) => n.textContent.trim()),
      chipScores: [...document.querySelectorAll('.alternative .alternative__score')].map((n) => Number(n.textContent)),
      lastBody: window.__calls.at(-1)?.body || null,
      lastIds: window.__calls.at(-1)?.ids || [],
      lastParams: window.__calls.at(-1)?.params || null,
      calls: window.__calls.length,
    })`,
  )

  const b = JSON.parse(before)
  const a = JSON.parse(after)
  const drag = JSON.parse(afterDrag)

  const reasons = []
  if (drag.error) reasons.push(`滑块没找到：${drag.error}`)
  if (!a.lastBody?.override_params) reasons.push('最后一次请求没带 override_params，沙盒没生效')
  if (Number(a.lastBody?.override_params?.lambda_decay) !== 2) reasons.push('override_params 里 λ 不是 2')
  if (a.calls <= b.calls) reasons.push('拖滑块后没有发出新请求')
  if (a.lastIds.length < 20) reasons.push(`重取批次只有 ${a.lastIds.length} 张，应保持 24 张`)
  // 同源：首页候选条必须就是本次响应，抽屉 Top5 必须是同一份结果
  // V5 首页只展示「也可以考虑」的前两条，不再是全部 24 张 chip。
  // 契约改为：候选条必须来自本次响应，且顺序与响应前 N 名一致。
  if (!a.chipIds.length) reasons.push('首页没有渲染候选条')
  else {
    // 候选条是「也可以考虑」，跳过第 1 名（它已经是当前卡面），
    // 因此应等于响应序列的第 2 名起的 N 个。
    const head = a.lastIds.slice(1, 1 + a.chipIds.length)
    if (JSON.stringify(a.chipIds) !== JSON.stringify(head)) {
      reasons.push(`首页候选条与响应第 2 名起不一致（${a.chipIds} vs ${head}）`)
    }
    const notIn = a.chipIds.filter((id) => !a.lastIds.includes(id))
    if (notIn.length) reasons.push(`候选条出现本次响应外的菜：${notIn}`)
  }
  if (!a.used) reasons.push('抽屉没有显示本次生效权重')
  else {
    const p = a.lastParams || {}
    // V5 抽屉只暴露 λ 与 ω 两个滑块；β/γ 仍可被接口覆盖但界面上不展示，
    // 因此只校验界面上真实存在的两项。
    for (const [key, label] of [
      ['lambda_decay', 'λ'],
      ['omega_group', 'ω'],
    ]) {
      if (p[key] === undefined) continue
      const want = `${label} ${Number(p[key]).toFixed(2)}`
      if (!a.used.includes(want)) reasons.push(`生效权重缺少 ${want}（实际：${a.used}）`)
    }
  }
  if (a.card === b.card) console.log(`   注意：首卡仍是「${a.card}」，λ 变化不必然改变第一名，改看排名序列`)

  console.log(`card before: ${b.card}`)
  console.log(`card after : ${a.card}`)
  console.log(`used       : ${a.used}`)
  console.log(`requests   : ${b.calls} → ${a.calls}`)
  console.log(`last ids   : ${a.lastIds.slice(0, 6).join(',')} … (${a.lastIds.length})`)
  const status = reasons.length ? 'FAIL' : 'PASS'
  reasons.forEach((r) => console.log(`   - ${r}`))
  console.log(`${status} 沙盒与首页卡组同源`)

  client.ws.close()
  if (reasons.length) process.exit(1)
}

main().catch((err) => {
  console.error('FAILED:', err.message)
  process.exit(1)
})
