import { alpha, chartTokens as tokens } from '../../utils/theme'

const FEATURE_LABELS = {
  spicy_level: '辣度',
  oily_level: '油腻',
  soup_level: '汤水',
  temp_fit: '温度',
  satiety_level: '饱腹',
  prep_speed: '速度',
  social_fit: '社交',
  comfort_level: '抚慰',
}

function baseOption(title, note) {
  const t = tokens()
  return {
    backgroundColor: t.ink,
    // 大屏（冷色组）用冷蓝打头，管理端小图仍是单色灰阶——靠 chartTokens 切换，不写死
    color: [t.accent || t.white, t.accentHi || t.silver, t.white, t.silver, t.steel, alpha(t.white, 0.58)],
    textStyle: { color: t.mist, fontFamily: 'system-ui, sans-serif' },
    title: {
      text: title,
      subtext: note,
      left: 14,
      top: 10,
      itemGap: 8,
      textStyle: { color: t.white, fontSize: 17, fontWeight: 600 },
      subtextStyle: { color: alpha(t.silver, 0.78), fontSize: 11, lineHeight: 16 },
    },
    tooltip: {
      backgroundColor: t.sheet || t.ink,
      borderColor: alpha(t.silver, 0.28),
      textStyle: { color: t.white },
    },
    animationDuration: 450,
  }
}

function cartesian(option) {
  const t = tokens()
  return {
    ...option,
    grid: { top: 105, left: 56, right: 28, bottom: 52, containLabel: true },
    xAxis: {
      type: 'category',
      axisLine: { lineStyle: { color: alpha(t.silver, 0.32) } },
      axisLabel: { color: alpha(t.mist, 0.74) },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: alpha(t.mist, 0.74) },
      splitLine: { lineStyle: { color: alpha(t.silver, 0.13) } },
    },
  }
}

export function experimentCurveOption(data, title, note) {
  const curve = data?.duplication_rate_curve || {}
  const option = cartesian(baseOption(title, note))
  option.xAxis.name = '连续天数'
  option.xAxis.data = curve.days || []
  option.yAxis.name = '重样率'
  option.yAxis.axisLabel.formatter = (value) => `${Math.round(value * 100)}%`
  option.legend = { top: 72, right: 20, textStyle: { color: tokens().mist } }
  option.series = [
    { name: '本系统 λ=0.5', type: 'line', smooth: true, showSymbol: true, data: curve['ours_lambda_0.5'] || [] },
    { name: '无衰减基线', type: 'line', smooth: true, showSymbol: true, data: curve.baseline_no_decay || [] },
  ]
  return option
}

export function experimentBarsOption(data, title, note) {
  const bars = data?.group_satisfaction_bars || {}
  const option = cartesian(baseOption(title, note))
  option.xAxis.data = bars.strategies || []
  option.yAxis.name = '满意度（0–100）'
  option.yAxis.max = 100
  option.legend = { top: 72, right: 20, textStyle: { color: tokens().mist } }
  option.series = [
    { name: '群组平均', type: 'bar', barMaxWidth: 34, data: bars.avg_scores || [] },
    { name: '最挑剔成员', type: 'bar', barMaxWidth: 34, data: bars.least_misery_scores || [] },
  ]
  return option
}

/** G3 仿真：14 天窗口内的同菜重样率（比"上一餐同菜系"更有区分度） */
export function repeatCurveOption(repeat, title, note) {
  const daily = repeat?.daily || {}
  const arms = daily.arms || {}
  const option = cartesian(baseOption(title, note))
  option.xAxis.name = '连续天数'
  option.xAxis.data = daily.days || []
  option.yAxis.name = '14 天同菜重样率'
  option.yAxis.max = 1
  option.yAxis.axisLabel.formatter = (value) => `${Math.round(value * 100)}%`
  option.legend = { top: 72, right: 20, textStyle: { color: tokens().mist } }
  option.series = [
    {
      name: '本系统 λ=0.5',
      type: 'line',
      smooth: true,
      showSymbol: true,
      data: arms.ours?.same_dish || [],
    },
    {
      name: '无衰减基线',
      type: 'line',
      smooth: true,
      showSymbol: true,
      data: arms.baseline?.same_dish || [],
    },
  ]
  return option
}

/** 200 个用户的 14 天同菜重样率分布（箱线图） */
export function repeatDistributionOption(repeat, title, note) {
  const arms = repeat?.by_arm || {}
  const t = tokens()
  const option = cartesian(baseOption(title, note))
  option.xAxis.data = ['本系统', '无衰减']
  option.xAxis.axisLabel = { color: alpha(t.mist, 0.74), fontSize: 12 }
  option.yAxis.name = '用户 14 天同菜重样率'
  option.yAxis.max = 1
  option.yAxis.axisLabel.formatter = (value) => `${Math.round(value * 100)}%`
  option.series = [
    {
      name: '200 人分布',
      type: 'boxplot',
      boxWidth: [26, 44],
      data: [
        {
          value: arms.ours?.user_rate_box || [0, 0, 0, 0, 0],
          itemStyle: { color: alpha(t.accent, 0.22), borderColor: t.accent, borderWidth: 1.5 },
        },
        {
          value: arms.baseline?.user_rate_box || [0, 0, 0, 0, 0],
          itemStyle: {
            color: alpha(t.silver, 0.18),
            borderColor: alpha(t.silver, 0.85),
            borderWidth: 1.5,
          },
        },
      ],
    },
  ]
  return option
}

export function cuisineOption(data, title, note) {
  const option = baseOption(title, note)
  option.tooltip.trigger = 'item'
  option.tooltip.formatter = '{b}<br/>{c} 行（{d}%）'
  option.legend = { bottom: 14, left: 20, type: 'scroll', textStyle: { color: tokens().mist } }
  option.series = [{
    name: '菜系构成',
    type: 'pie',
    radius: ['38%', '62%'],
    center: ['50%', '55%'],
    minAngle: 3,
    label: { color: tokens().mist, formatter: '{b}\n{d}%' },
    itemStyle: { borderColor: tokens().ink, borderWidth: 2 },
    data: (data?.items || []).map((item) => ({ name: item.cuisine_type, value: item.count })),
  }]
  return option
}

export function calendarOption(data, title, note) {
  const daily = data?.daily || []
  const option = baseOption(title, note)
  const max = Math.max(1, ...daily.map((item) => item.count))
  option.tooltip.formatter = (params) => `${params.value[0]}<br/>${params.value[1]} 次决策`
  option.visualMap = {
    min: 0,
    max,
    calculable: true,
    orient: 'horizontal',
    right: 24,
    bottom: 14,
    inRange: { color: [alpha(tokens().steel, 0.22), tokens().silver, tokens().white] },
    textStyle: { color: tokens().mist },
  }
  option.calendar = {
    top: 112,
    left: 54,
    right: 30,
    bottom: 64,
    cellSize: ['auto', 18],
    range: [daily[0]?.date, daily[daily.length - 1]?.date],
    itemStyle: { color: alpha(tokens().silver, 0.06), borderColor: alpha(tokens().silver, 0.2) },
    yearLabel: { color: tokens().mist },
    dayLabel: { color: tokens().mist },
    monthLabel: { color: tokens().mist },
  }
  option.series = [{ type: 'heatmap', coordinateSystem: 'calendar', data: daily.map((item) => [item.date, item.count]) }]
  return option
}

export function heatmapOption(data, title, note) {
  const matrix = data?.matrix || []
  const slots = ['早餐', '午餐', '晚餐', '夜宵']
  const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const max = Math.max(1, ...matrix.map((item) => item.count))
  const option = baseOption(title, note)
  option.tooltip.position = 'top'
  option.tooltip.formatter = (params) => `${weekdays[params.value[1]]} ${slots[params.value[0]]}<br/>${params.value[2]} 次`
  option.grid = { top: 105, left: 70, right: 28, bottom: 82, containLabel: true }
  option.xAxis = { type: 'category', data: slots, axisLabel: { color: tokens().mist }, splitArea: { show: true } }
  option.yAxis = { type: 'category', data: weekdays, axisLabel: { color: tokens().mist }, splitArea: { show: true } }
  option.visualMap = {
    min: 0,
    max,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: 16,
    inRange: { color: [alpha(tokens().steel, 0.2), tokens().silver, tokens().white] },
    textStyle: { color: tokens().mist },
  }
  option.series = [{
    type: 'heatmap',
    data: matrix.map((item) => [slots.indexOf(item.slot), item.weekday, item.count]),
    label: { show: true, color: tokens().ink },
    itemStyle: { borderColor: tokens().ink, borderWidth: 1 },
  }]
  return option
}

export function personasOption(data, title, note) {
  const rows = data?.personas || []
  const keys = Object.keys(FEATURE_LABELS)
  const t = tokens()
  const option = baseOption(title, note)
  option.tooltip = { trigger: 'item' }
  option.legend = { top: 0, left: 'center', type: 'scroll', textStyle: { color: tokens().mist } }
  option.radar = {
    center: ['50%', '55%'],
    radius: '54%',
    indicator: keys.map((key) => ({ name: FEATURE_LABELS[key], max: 1 })),
    axisName: { color: tokens().mist },
    axisLine: { lineStyle: { color: alpha(tokens().silver, 0.28) } },
    splitLine: { lineStyle: { color: alpha(tokens().silver, 0.2) } },
    splitArea: { areaStyle: { color: [alpha(tokens().white, 0.02), alpha(tokens().white, 0.05)] } },
  }
  // 浅色令牌的 accent / accentHi 是同一个变量，直接用会导致前两条线同色；
  // 这里按人设取 4 个可区分的令牌色，仍然不出现裸 hex。
  const palette = [t.accent, t.ok, t.warn, t.silver, t.bad, t.steel]
  option.series = [{
    type: 'radar',
    symbol: 'circle',
    symbolSize: 4,
    data: rows.map((row, index) => {
      const color = palette[index % palette.length]
      return {
        name: row.nickname,
        value: keys.map((key) => row.base_vector?.[key] ?? 0),
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        areaStyle: { color, opacity: 0.06 },
      }
    }),
  }]
  return option
}

export function scatterOption(data, title, note) {
  const points = (data?.points || []).filter((item) => item.price !== null && item.rating !== null)
  const option = baseOption(title, note)
  option.grid = { top: 108, left: 64, right: 30, bottom: 56, containLabel: true }
  option.xAxis = { name: '价格 / 成本', type: 'value', axisLabel: { color: tokens().mist }, splitLine: { lineStyle: { color: alpha(tokens().silver, 0.13) } } }
  option.yAxis = { name: '真实评分', type: 'value', min: 0, max: 5, axisLabel: { color: tokens().mist }, splitLine: { lineStyle: { color: alpha(tokens().silver, 0.13) } } }
  option.tooltip.formatter = (params) => `${params.data.name}<br/>价格 ${params.value[0]} · 评分 ${params.value[1]}<br/>出现 ${params.value[2]} 次`
  option.series = ['RESTAURANT', 'DISH'].map((entityType, index) => ({
    name: entityType === 'RESTAURANT' ? '门店' : '菜品',
    type: 'scatter',
    symbol: index === 0 ? 'circle' : 'diamond',
    symbolSize: (value) => Math.min(34, 8 + Math.sqrt(value[2] || 0) * 3),
    itemStyle: { color: index === 0 ? tokens().white : tokens().silver, opacity: 0.74 },
    data: points.filter((item) => item.entity_type === entityType).map((item) => ({
      name: item.name,
      value: [item.price, item.rating, item.freq],
      entityId: item.entity_id,
      entityType: item.entity_type,
      campus: item.campus,
    })),
  }))
  return option
}

export function flowOption(data, title, note) {
  const option = baseOption(title, note)
  option.tooltip = { trigger: 'item', triggerOn: 'mousemove' }
  option.series = [{
    type: 'sankey',
    top: 100,
    left: 28,
    right: 90,
    bottom: 30,
    nodeWidth: 16,
    nodeGap: 14,
    emphasis: { focus: 'adjacency' },
    data: data?.nodes || [],
    links: data?.links || [],
    lineStyle: { color: tokens().silver, opacity: 0.24, curveness: 0.5 },
    itemStyle: { color: tokens().silver, borderColor: tokens().white, borderWidth: 0 },
    label: { color: tokens().mist },
  }]
  return option
}

export function trendOption(data, title, note) {
  const option = cartesian(baseOption(title, note))
  option.tooltip.trigger = 'axis'
  option.xAxis.data = data?.dates || []
  option.yAxis.name = '决策量'
  option.legend = { top: 74, type: 'scroll', textStyle: { color: tokens().mist } }
  option.series = (data?.series || []).map((row) => ({
    name: row.cuisine_type,
    type: 'line',
    stack: '决策量',
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.16 },
    emphasis: { focus: 'series' },
    data: row.data,
  }))
  return option
}

export function keywordsOption(data, title, note) {
  const palette = [tokens().white, tokens().silver, tokens().steel, alpha(tokens().white, 0.64)]
  const option = baseOption(title, note)
  option.tooltip = { show: true }
  option.series = [{
    type: 'wordCloud',
    top: 94,
    bottom: 24,
    left: 24,
    right: 24,
    sizeRange: [13, 38],
    rotationRange: [0, 0],
    gridSize: 8,
    drawOutOfBound: false,
    textStyle: {
      fontFamily: 'system-ui, sans-serif',
      color: (params) => palette[(params.name.length + params.value) % palette.length],
    },
    emphasis: { textStyle: { textShadowBlur: 8, textShadowColor: tokens().silver } },
    data: data?.words || [],
  }]
  return option
}

export function raceOption(data, title, note) {
  const weeks = data?.weeks || []
  const rows = data?.series || []
  const rankings = weeks.map((_, weekIndex) => rows
    .map((row) => ({ id: row.dish_id, name: row.dish_name, value: row.data[weekIndex] || 0 }))
    .sort((a, b) => b.value - a.value || a.id - b.id)
    .slice(0, 10)
    .reverse())
  const option = cartesian(baseOption(title, note))
  option.grid.bottom = 86
  option.xAxis = { type: 'value', axisLabel: { color: tokens().mist }, splitLine: { lineStyle: { color: alpha(tokens().silver, 0.13) } } }
  option.yAxis = { type: 'category', inverse: false, axisLabel: { color: tokens().mist }, animationDuration: 300, animationDurationUpdate: 300 }
  option.timeline = {
    axisType: 'category',
    autoPlay: weeks.length > 1,
    playInterval: 1400,
    bottom: 16,
    left: 50,
    right: 30,
    data: weeks,
    label: { color: tokens().mist },
    lineStyle: { color: tokens().silver },
    checkpointStyle: { color: tokens().white, borderColor: tokens().silver },
    controlStyle: { color: tokens().mist, borderColor: tokens().mist },
  }
  option.series = [{
    type: 'bar',
    realtimeSort: true,
    barMaxWidth: 24,
    label: { show: true, position: 'right', color: tokens().mist },
    data: rankings[0]?.map((row) => ({ value: row.value, dishId: row.id, name: row.name })) || [],
  }]
  option.options = rankings.map((ranking) => ({
    yAxis: { data: ranking.map((row) => row.name) },
    series: [{ data: ranking.map((row) => ({ value: row.value, dishId: row.id, name: row.name })) }],
  }))
  if (rankings[0]) option.yAxis.data = rankings[0].map((row) => row.name)
  return option
}

export function cooccurrenceOption(data, title, note) {
  const option = baseOption(title, note)
  option.tooltip = {}
  option.series = [{
    type: 'graph',
    layout: 'force',
    top: 96,
    bottom: 24,
    roam: true,
    draggable: true,
    data: (data?.nodes || []).map((node) => ({
      ...node,
      symbolSize: Math.min(44, 12 + Math.sqrt(node.value) * 4),
      itemStyle: { color: tokens().silver, borderColor: tokens().white, borderWidth: 1 },
      label: { show: true, color: tokens().ink, fontSize: 10 },
    })),
    links: (data?.links || []).map((link) => ({
      ...link,
      lineStyle: { width: Math.min(7, 1 + Math.sqrt(link.value)), color: tokens().silver, opacity: 0.42, curveness: 0.12 },
    })),
    force: { repulsion: 140, edgeLength: [55, 130], gravity: 0.08 },
    emphasis: { focus: 'adjacency', lineStyle: { opacity: 0.8 } },
  }]
  return option
}

export function qualityOption(data, title, note) {
  const coverage = Number(data?.tagging_coverage || 0)
  const option = baseOption(title, note)
  option.series = [{
    type: 'gauge',
    startAngle: 210,
    endAngle: -30,
    min: 0,
    max: 100,
    center: ['50%', '60%'],
    radius: '72%',
    progress: { show: true, width: 20, itemStyle: { color: tokens().accent || tokens().white } },
    axisLine: { lineStyle: { width: 20, color: [[1, alpha(tokens().silver, 0.16)]] } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { show: false },
    pointer: { show: false },
    anchor: { show: false },
    title: { show: true, offsetCenter: [0, '28%'], color: tokens().mist, fontSize: 14 },
    detail: {
      valueAnimation: true,
      formatter: (value) => `${value.toFixed(1)}%\n${data?.tagged_dishes || 0}/${data?.total_dishes || 0} 道`,
      color: tokens().white,
      fontSize: 26,
      lineHeight: 34,
      offsetCenter: [0, '-4%'],
    },
    data: [{ value: coverage * 100, name: '有效八维打标覆盖率' }],
  }]
  return option
}
