// Original, asset-free layout for a personal learning record.
export const RECORD_NOTICE = '仅用于个人学习回顾，不作为平台或官方认证凭证。'

function text (value) {
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

export function learningRecordFields (record = {}) {
  let scores = record.scores
  if (typeof scores === 'string') {
    try {
      scores = JSON.parse(scores)
    } catch (_) {
      // Keep legacy free-form scores as literal text.
    }
  }
  const fields = [
    ['学习者', text(record.name)],
    ['地点', text(record.place)],
    ['学习级别', text(record.level)],
    ['记录期次', text(record.sequence)],
    ['记录评价', text(record.grade)],
    ['记录时间', text(record.time)],
    ['记录编号', text(record.ID)]
  ]
  if (Array.isArray(scores) && scores.length) {
    scores.forEach((score, index) => {
      fields.push([scores.length === 5 && index === 4 ? '总分' : `分项 ${index + 1}`, text(score)])
    })
  } else {
    fields.push(['分数', Array.isArray(scores) ? '—' : text(scores)])
  }
  return fields
}

function wrapText (ctx, value, width) {
  const lines = []
  for (const paragraph of value.split('\n')) {
    let line = ''
    for (const character of Array.from(paragraph)) {
      if (line && ctx.measureText(line + character).width > width) {
        lines.push(line)
        line = ''
      }
      line += character
    }
    lines.push(line)
  }
  return lines
}

export function drawLearningRecord (canvas, record) {
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas is unavailable')
  const font = '26px sans-serif'
  ctx.font = font
  const rows = learningRecordFields(record).map(([label, value]) => ({
    label,
    lines: wrapText(ctx, value, 810)
  }))
  canvas.width = 1200
  canvas.height = 300 + rows.reduce((height, row) => height + Math.max(64, row.lines.length * 38 + 20), 0)
  // Resizing clears context state. Set all drawing styles after sizing.
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#203e50'
  ctx.font = 'bold 44px sans-serif'
  ctx.fillText('学习记录', 64, 94)
  ctx.fillStyle = '#506575'
  ctx.font = '22px sans-serif'
  ctx.fillText(RECORD_NOTICE, 64, 142)
  ctx.fillStyle = '#dae2e7'
  ctx.fillRect(64, 178, 1072, 2)
  ctx.font = font
  let y = 230
  rows.forEach(row => {
    ctx.fillStyle = '#506575'
    ctx.fillText(row.label, 64, y)
    ctx.fillStyle = '#162d3c'
    row.lines.forEach((line, index) => ctx.fillText(line, 310, y + index * 38))
    y += Math.max(64, row.lines.length * 38 + 20)
  })
  return canvas
}
