/**
 * 划卡决策事件（BATCH2_PLAN v1.1 的「落库留事件占位」）。
 *
 * 本步只把决策收进内存队列并打点，**不写库**：
 * 真正的落库链路是批次 3 的 eating_logs / POST /api/v1/logs/checkin（模块 5 一键打卡），
 * 到那时把 flushDecisions() 的实现换成真实请求即可，调用方不用改。
 */
const queue = []

/**
 * @param {{ type: 'LIKE' | 'PASS', dish: object | null, modeType?: string, source?: string }} payload
 */
export function logDecision({ type, dish, modeType, source }) {
  const event = {
    type,
    dish_id: dish?.dish_id ?? null,
    dish_name: dish?.name ?? '',
    mode_type: modeType ?? null,
    source: source ?? 'unknown',
    at: new Date().toISOString(),
  }
  queue.push(event)
  // eslint-disable-next-line no-console
  console.info('[decision-placeholder]', event)
  return event
}

/** 供验收时在控制台核对：`window.__eatwhatDecisions?.()` */
export function pendingDecisions() {
  return [...queue]
}

if (typeof window !== 'undefined') {
  window.__eatwhatDecisions = pendingDecisions
}
