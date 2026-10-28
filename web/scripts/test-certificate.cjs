/* Run with: node web/scripts/test-certificate.cjs (no browser or build needed). */
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const root = path.resolve(__dirname, '..')
const drawingSource = fs.readFileSync(path.join(root, 'src/utils/certificateCanvas.js'), 'utf8')
const componentSource = fs.readFileSync(path.join(root, 'src/views/Users/Certificate.vue'), 'utf8')
const drawing = vm.runInNewContext(drawingSource.replace(/export /g, '') + '\n;({ drawLearningRecord, learningRecordFields, RECORD_NOTICE })')

function canvasFixture () {
  const calls = []
  const canvas = { width: 0, height: 0, toDataURL: () => 'data:image/png;base64,fixture' }
  const ctx = {
    measureText: value => ({ width: Array.from(value).length * 26 }),
    fillText: (value, x, y) => calls.push({ value, x, y }),
    fillRect: () => {}
  }
  canvas.getContext = type => {
    assert.equal(type, '2d')
    return ctx
  }
  return { canvas, calls }
}

function documentFixture () {
  const elements = []
  const doc = {
    head: { appendChild: () => {} },
    body: { appendChild: () => {} },
    createElement (tag) {
      const element = { tag, click () { this.clicked = true }, remove () { this.removed = true } }
      // Fail on every HTML-string sink, including future accidental additions.
      for (const sink of ['innerHTML', 'outerHTML']) {
        Object.defineProperty(element, sink, { get () { return undefined }, set () { throw new Error('HTML sink forbidden') } })
      }
      elements.push(element)
      return element
    }
  }
  return { doc, elements }
}

async function main () {
  const special = '<img src=x onerror=alert(1)> & "你好" 🧑🏽‍💻'
  const record = { name: special, place: '自学', level: 2, sequence: 0, grade: '进步中', time: '2026-10-28', ID: 'local-01', scores: '[0,20,30,40,90]' }
  const fields = drawing.learningRecordFields(record)
  assert.equal(fields[0][1], special)
  assert.equal(fields[3][1], '0')
  assert.equal(fields[7][1], '0')
  assert.equal(fields[11][0], '总分')
  assert.equal(fields[11][1], '90')
  assert.equal(drawing.learningRecordFields({ scores: special })[7][1], special)
  assert.equal(drawing.learningRecordFields({ scores: [] })[7][1], '—')
  assert.equal(drawing.learningRecordFields({ scores: [3, 4] })[8][1], '4')

  const { canvas, calls } = canvasFixture()
  drawing.drawLearningRecord(canvas, record)
  assert.equal(canvas.width, 1200)
  assert(calls.some(call => call.value === '学习记录'))
  assert(calls.some(call => call.value === drawing.RECORD_NOTICE))
  // Wrapped user text remains identical and only reaches fillText.
  const nameLines = calls.filter(call => call.x === 310).slice(0, 2)
  assert.equal(nameLines.map(call => call.value).join(''), special)
  for (const [, value] of fields.slice(1)) assert(calls.some(call => call.value === value))
  const large = canvasFixture()
  drawing.drawLearningRecord(large.canvas, { place: '长地点😀'.repeat(80) + '\n下一行' })
  assert(large.canvas.height > 1000)
  assert(large.calls.every(call => call.y < large.canvas.height))
  assert(large.calls.some(call => call.value === '下一行'))
  assert.throws(() => drawing.drawLearningRecord({ getContext: () => null }, {}), /Canvas/)

  const mainDoc = documentFixture()
  const printDoc = documentFixture()
  let prints = 0
  let closed = false
  const popup = { document: printDoc.doc, focus () {}, print () { prints++ }, close () { closed = true } }
  const context = { ...drawing, document: mainDoc.doc, window: { open: () => popup } }
  const script = componentSource.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace(/^import .*$/m, '').replace('export default', 'component =')
  vm.runInNewContext(script, context)
  const component = context.component
  const state = { ...component.data(), ...component.methods, $refs: { certificate: canvas }, $nextTick: async () => {}, id: 'legacy-01' }
  let requested
  state.$axios = { get: async url => { requested = url; return { data: { cert: record } } } }
  await state.fetchCertificate()
  assert.equal(requested, '/certs/legacy-01')
  assert.equal(state.ready, true)
  assert.equal(state.loading, false)
  state.downloadCertificate()
  const anchor = mainDoc.elements.find(element => element.tag === 'a')
  assert.equal(anchor.href, 'data:image/png;base64,fixture')
  assert.equal(anchor.download, 'learning-record.png')
  assert(anchor.clicked && anchor.removed)
  state.printCertificate()
  const image = printDoc.elements.find(element => element.tag === 'img')
  assert.equal(prints, 0)
  assert.equal(image.src, 'data:image/png;base64,fixture')
  image.onload()
  assert.equal(prints, 1)
  popup.onafterprint()
  assert(closed)
  context.window.open = () => null
  state.printCertificate()
  assert.match(state.actionError, /弹出窗口/)
  state.$axios.get = async () => { throw Object.assign(new Error('missing'), { response: { status: 404 } }) }
  await state.fetchCertificate()
  assert.equal(state.ready, false)
  assert.match(state.error, /未找到/)
  state.$axios.get = async () => { throw new Error('offline') }
  await state.fetchCertificate()
  assert.match(state.error, /加载失败/)
  // A slow response cannot replace a record loaded for the next route ID.
  let finishOld
  state.$axios.get = () => new Promise(resolve => { finishOld = resolve })
  const oldRequest = state.fetchCertificate()
  state.id = 'new-02'
  state.$axios.get = async () => ({ data: { cert: { ...record, ID: 'new-02' } } })
  await state.fetchCertificate()
  finishOld({ data: { cert: record } })
  await oldRequest
  assert.equal(state.cert.ID, 'new-02')
  assert.equal(state.ready, true)

  assert(!/certificate\.png|qrcode|new Image|drawImage|https?:\/\//i.test(drawingSource + componentSource))
  assert(!/innerHTML|outerHTML|document\.write|v-html/.test(drawingSource + componentSource))
  console.log('PASS: literal text, score formats, wrapping, neutral asset-free canvas, legacy API, download, load-gated print, errors and stale responses')
}

main().catch(error => { console.error(error); process.exitCode = 1 })
