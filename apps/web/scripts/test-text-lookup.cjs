const assert = require('assert')
const fs = require('fs')
const vm = require('vm')
const path = require('path')
const file = path.join(__dirname, '../src/views/Translation/ptxTranslation.vue')
const source = fs.readFileSync(file, 'utf8')
assert(!/IatRecorder|transcode\.worker|WebSocket|getUserMedia|xfyun/.test(source))
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace(/^import PinyinList.*$/m, 'const PinyinList = {}')
  .replace('export default', 'module.exports =')
const sandbox = { module: { exports: {} } }
vm.runInNewContext(script, sandbox)
const component = sandbox.module.exports
let calls = 0
let navigation
const instance = Object.assign(component.data(), {
  $site: { features: { pinyin: false } },
  $router: { push (value) { navigation = value } },
  $message: { warning () {}, info () {} },
  $axios: {
    async get (url, options) {
      calls++
      assert.strictEqual(url, 'pronunciation/combine')
      assert.strictEqual(options.params.words, '文字')
      return { data: { url: '/synthetic-audio' } }
    }
  }
})
for (const [key, method] of Object.entries(component.methods)) instance[key] = method.bind(instance)
;(async () => {
  instance.words = ' 文字 '
  instance.search()
  assert.strictEqual(navigation.name, 'Search')
  assert.strictEqual(navigation.query.key, '文字')
  await instance.lookupPronunciation()
  assert.strictEqual(calls, 0)
  assert.strictEqual(instance.audioUrl, '')
  instance.$site.features.pinyin = true
  await instance.lookupPronunciation()
  assert.strictEqual(calls, 1)
  assert.strictEqual(instance.audioUrl, '/synthetic-audio')
  assert.strictEqual(instance.loading, false)
  instance.loading = true
  await instance.lookupPronunciation()
  assert.strictEqual(calls, 1)
  console.log('PASS manual lookup: no recognition dependency; navigation and pinyin-disabled guard; explicit synthesis only')
})().catch(error => { console.error(error); process.exitCode = 1 })
