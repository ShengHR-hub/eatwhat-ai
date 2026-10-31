/**
 * 把八维特征翻译成人话。
 *
 * 为什么不用 LLM：这些描述必须和 feature_vector 严格对应，模型容易加戏；
 * 规则拼装既能保证「说的一定是数据支持的」，也方便解释给评委听。
 *
 * 轴与 dashboardOptions.FEATURE_LABELS 同源：
 *   spicy_level 辣 / oily_level 油 / soup_level 汤 / temp_fit 温
 *   satiety_level 饱 / prep_speed 速 / social_fit 社 / comfort_level 抚
 */

const num = (value) => (typeof value === 'number' && Number.isFinite(value) ? value : null)

/** 口味：辣 + 油 + 汤，组合成一句 */
export function tasteLine(vector) {
  if (!vector) return ''
  const spicy = num(vector.spicy_level)
  const oily = num(vector.oily_level)
  const soup = num(vector.soup_level)

  const parts = []
  if (spicy !== null) {
    if (spicy >= 0.75) parts.push('辣得够劲')
    else if (spicy >= 0.45) parts.push('中辣偏上')
    else if (spicy >= 0.2) parts.push('微微带辣')
    else parts.push('不辣')
  }
  if (oily !== null) {
    if (oily >= 0.65) parts.push('油偏重')
    else if (oily <= 0.3) parts.push('清爽少油')
  }
  if (soup !== null && soup >= 0.7) parts.push('汤水足')
  if (soup !== null && soup <= 0.2 && oily !== null && oily >= 0.5) parts.push('干香')

  return parts.length ? parts.join('、') : ''
}

/** 场景：温度 + 天气 + 饱腹，说明「什么时候吃合适」 */
export function sceneLine(vector, weatherText = '') {
  if (!vector) return ''
  const temp = num(vector.temp_fit)
  const satiety = num(vector.satiety_level)
  const comfort = num(vector.comfort_level)
  const cold = /冷|寒|雨|雪|阴/.test(weatherText)
  const hot = /热|晒|高温|晴/.test(weatherText)

  const parts = []
  if (temp !== null) {
    if (temp >= 0.7) parts.push(cold ? '天冷吃正合适' : '要趁热吃')
    else if (temp <= 0.25) parts.push(hot ? '天热吃着舒服' : '凉了也不影响')
  }
  if (satiety !== null) {
    if (satiety >= 0.75) parts.push('吃完很顶饱')
    else if (satiety <= 0.3) parts.push('分量偏轻')
  }
  if (comfort !== null && comfort >= 0.75) parts.push('吃着踏实')

  return parts.length ? parts.join('，') : ''
}

/** 做法：主料 + 用时，外食与下厨措辞不同 */
export function makeLine(dish) {
  if (!dish) return ''
  const mains = Array.isArray(dish.ingredients_main) ? dish.ingredients_main.filter(Boolean).slice(0, 3) : []
  const minutes = num(dish.cook_minutes)
  const isCook = dish.mode_type === 'HOME_COOKING'

  const parts = []
  if (mains.length) parts.push(`主料是${mains.join('、')}`)
  if (minutes) {
    if (isCook) parts.push(`自己做大约 ${Math.round(minutes)} 分钟`)
    else parts.push(`现做大约 ${Math.round(minutes)} 分钟`)
  } else if (isCook) {
    parts.push('做起来不费事')
  }

  return parts.length ? parts.join('，') : ''
}

/** 社交：人多还是独食 */
export function socialLine(vector, modeType) {
  if (!vector || modeType === 'HOME_COOKING') return ''
  const social = num(vector.social_fit)
  const speed = num(vector.prep_speed)
  if (social !== null && social >= 0.75) return '适合几个人一起吃'
  if (speed !== null && speed >= 0.8) return '出餐快，赶时间也能吃'
  return ''
}

/**
 * 汇总成 2–3 句。空值维度直接跳过，不硬凑。
 * 返回数组而不是长字符串，前端可以分行排版。
 */
export function dishTalk(dish, options = {}) {
  if (!dish) return []
  const vector = dish.feature_vector || null
  const weatherText = options.weatherText || ''

  // 口味与场景分两行：拼成一句会有五六个短语，手机上读起来喘不过气
  const lines = [
    tasteLine(vector),
    sceneLine(vector, weatherText),
    makeLine(dish),
    socialLine(vector, dish.mode_type),
  ].filter(Boolean)

  return lines.slice(0, 3)
}
