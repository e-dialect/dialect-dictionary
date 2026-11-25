import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

const root = new URL('../../', import.meta.url)
const read = path => readFile(new URL(path, root), 'utf8')
const importSource = async path => import(`data:text/javascript;base64,${Buffer.from(await read(path)).toString('base64')}`)
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const tick = () => new Promise(resolve => setImmediate(resolve))

class FakeAudio {
  static instances = []
  constructor(src) {
    this.src = src
    this.events = {}
    this.pauses = 0
    this.destroyed = 0
    this.pending = deferred()
    FakeAudio.instances.push(this)
  }
  addEventListener(event, callback) { this.events[event] = callback }
  onPlay(callback) { this.events.playing = callback }
  onEnded(callback) { this.events.ended = callback }
  onError(callback) { this.events.error = callback }
  onStop(callback) { this.events.stop = callback }
  play() { return this.pending.promise }
  pause() { this.pauses += 1 }
  stop() { this.pauses += 1; this.events.stop?.() }
  destroy() { this.destroyed += 1 }
  removeAttribute() { this.src = '' }
  load() {}
  emit(event) { this.events[event]?.() }
}
globalThis.Audio = FakeAudio
const toasts = []
globalThis.uni = { createInnerAudioContext: () => new FakeAudio(), showToast: options => toasts.push(options.title) }
const web = await importSource('apps/web/src/utils/audio.js')
const mobile = await importSource('apps/mobile/src/utils/audio.js')

for (const [platform, api] of [['web', web], ['mobile', mobile]]) {
  const play = (src, options) => platform === 'web' ? api.playAudio(src, options) : api.playAudio(src, true, options)
  test(`${platform}: repeat during loading stops and releases the player`, () => {
    api.stopAudio()
    const states = []
    const owner = {}
    const options = { owner, onState: state => states.push(state.status) }
    play('a.wav', options)
    const player = FakeAudio.instances.at(-1)
    play('a.wav', options)
    assert.equal(player.pauses, 1)
    assert.deepEqual(states, ['loading', 'idle'])
    if (platform === 'mobile') assert.equal(player.destroyed, 1)
  })
  test(`${platform}: replacement, stale events, and owner cleanup preserve the current player`, async () => {
    const first = {}, second = {}
    const states = []
    play('a.wav', { owner: first })
    const old = FakeAudio.instances.at(-1)
    play('b.wav', { owner: second, onState: state => states.push(state.status) })
    const current = FakeAudio.instances.at(-1)
    old.emit('ended'); old.emit('error')
    if (platform === 'web') old.pending.reject(new Error('old request aborted'))
    await tick()
    api.stopAudio(first)
    assert.equal(current.pauses, 0)
    current.emit('playing')
    current.emit('ended')
    assert.deepEqual(states, ['loading', 'playing', 'idle'])
    assert.equal(current.pauses, 1)
    api.stopAudio(second)
    assert.equal(current.pauses, 1)
  })
  test(`${platform}: playback error is visible and retry creates a working player`, async () => {
    const states = []
    let errors = 0
    const owner = {}
    const options = { owner, onState: state => states.push(state.status), onError: () => { errors++ } }
    play('missing.wav', options)
    const failed = FakeAudio.instances.at(-1)
    if (platform === 'web') failed.pending.reject(new Error('network error'))
    else failed.emit('error')
    await tick()
    assert.deepEqual(states, ['loading', 'error'])
    if (platform === 'web') assert.equal(errors, 1)
    else assert.match(toasts.at(-1), /失败.*重试/)
    play('missing.wav', options)
    const retried = FakeAudio.instances.at(-1)
    assert.notEqual(retried, failed)
    retried.emit('playing')
    assert.equal(states.at(-1), 'playing')
    api.stopAudio(owner)
  })
}

async function component(path, imports, props = {}) {
  const source = (await read(path)).match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace(/^import .*$/gm, '').replace('export default', 'globalThis.options =')
  const context = { ...imports, uni: globalThis.uni }
  vm.runInNewContext(source, context)
  const options = context.options
  const instance = { ...options.data(), ...props, $message: { info() {}, error() {} } }
  for (const [key, method] of Object.entries(options.methods)) instance[key] = method.bind(instance)
  for (const [key, getter] of Object.entries(options.computed)) Object.defineProperty(instance, key, { get: getter.bind(instance) })
  return { instance, options }
}
const mobileImports = () => ({
  featureEnabled: () => true, ...mobile,
  getPronunciations: async () => [],
  combinePronunciationByIpa: async () => '',
  combinePronunciationByPinyin: async () => '',
})
const mobilePath = 'apps/mobile/src/components/WordPronunciationButton.vue'
const mobileProps = { source: '', wordId: 1, pinyin: 'a', ipa: 'a' }

test('mobile: cancelling synthesis keeps its button available and can reopen the confirmation', async () => {
  const modals = []
  globalThis.uni.showModal = options => modals.push(options)
  const { instance } = await component(mobilePath, mobileImports(), mobileProps)
  await instance.loadPronunciation()
  await instance.play()
  await modals[0].success({ confirm: false }); modals[0].complete()
  assert.equal(instance.buttonText, '尝试合成')
  assert.equal(instance.isDisabled, false)
  await instance.play()
  assert.equal(modals.length, 2)
})

test('mobile: changed word ignores old recording lookup and unmount stops only its own player', async () => {
  const old = deferred()
  const { instance, options } = await component(mobilePath, { ...mobileImports(), getPronunciations: () => old.promise }, mobileProps)
  const loading = instance.loadPronunciation()
  instance.wordId = 2; instance.source = 'current.wav'
  await instance.loadPronunciation()
  old.resolve([{ pronunciation: { source: 'old.wav' } }]); await loading
  assert.equal(instance.recordingSource, 'current.wav')
  assert.equal(instance.firstPronunciation, null)
  await instance.play()
  const player = FakeAudio.instances.at(-1)
  assert.equal(instance.isDisabled, false, 'loading playback remains stoppable')
  options.beforeUnmount.call(instance)
  assert.equal(player.destroyed, 1)
})

test('mobile: synthesis cannot start playback after word change, page hiding, or unmount', async () => {
  for (const transition of ['word', 'hide', 'unmount']) {
    const pending = deferred()
    const { instance, options } = await component(mobilePath, { ...mobileImports(), combinePronunciationByIpa: () => pending.promise }, mobileProps)
    const count = FakeAudio.instances.length
    const loading = instance.playUrl()
    if (transition === 'word') { instance.source = 'new.wav'; await instance.loadPronunciation() }
    if (transition === 'hide') mobile.stopAudio()
    if (transition === 'unmount') options.beforeUnmount.call(instance)
    pending.resolve('stale.wav'); await loading
    assert.equal(FakeAudio.instances.length, count, transition)
  }
})

test('web: changed word ignores stale fallback; failed lookup can be retried', async () => {
  const first = deferred()
  let calls = 0
  const { instance, options } = await component('apps/web/src/components/Tools/PlayWordSoundButton.vue', {
    ...web, featureEnabled: () => false,
    axios: { get: () => { calls++; return first.promise } },
  }, { wordId: 1, url: '', ipa: '', pinyin: '' })
  const loading = instance.loadPronunciations()
  await tick()
  instance.wordId = 2; instance.url = 'current.wav'
  await instance.loadPronunciations()
  first.resolve({ data: { pronunciation: [{ pronunciation: { source: 'old.wav' } }] } })
  await loading
  assert.equal(instance.ipaSource, 'current.wav')
  assert.equal(instance.fallback_url, '')
  instance.playSound('current.wav', 'IPA')
  const player = FakeAudio.instances.at(-1)
  assert.equal(instance.buttonText('current.wav', '试听'), '加载中 · 停止')
  options.beforeDestroy.call(instance)
  assert.equal(player.pauses, 1)
  assert.equal(calls, 1)

  let attempts = 0
  const retry = await component('apps/web/src/components/Tools/PlayWordSoundButton.vue', {
    ...web, featureEnabled: () => false,
    axios: { get: async () => { attempts++; if (attempts === 1) throw new Error('offline'); return { data: { pronunciation: [{ pronunciation: { source: 'ok.wav' } }] } } } },
  }, { wordId: 1, url: 'null', ipa: '', pinyin: '' })
  await retry.instance.loadPronunciations()
  assert.equal(retry.instance.buttonText('', '试听'), '重试查找录音')
  await retry.instance.loadPronunciations()
  assert.equal(retry.instance.ipaSource, 'ok.wav')
})

test('mobile: the latest synthesis request wins regardless of response order', async () => {
  for (const firstResponse of ['a', 'b']) {
    const a = deferred(), b = deferred()
    const aComponent = await component(mobilePath, { ...mobileImports(), combinePronunciationByIpa: () => a.promise }, mobileProps)
    const bComponent = await component(mobilePath, { ...mobileImports(), combinePronunciationByIpa: () => b.promise }, { ...mobileProps, wordId: 2 })
    const count = FakeAudio.instances.length
    const aPending = aComponent.instance.playUrl()
    const bPending = bComponent.instance.playUrl()
    if (firstResponse === 'a') {
      a.resolve('a.wav'); await aPending
      b.resolve('b.wav'); await bPending
    } else {
      b.resolve('b.wav'); await bPending
      a.resolve('a.wav'); await aPending
    }
    assert.equal(FakeAudio.instances.length, count + 1)
    assert.equal(FakeAudio.instances.at(-1).src, 'b.wav')
    mobile.stopAudio()
  }
})

test('mobile: pending synthesis can be cancelled without silencing another preview', async () => {
  const pending = deferred()
  const { instance } = await component(mobilePath, { ...mobileImports(), combinePronunciationByIpa: () => pending.promise }, mobileProps)
  const loading = instance.playUrl()
  assert.equal(instance.isDisabled, false)
  assert.equal(instance.buttonText, '合成中 · 取消')
  mobile.playAudio('another.wav')
  const other = FakeAudio.instances.at(-1)
  const count = FakeAudio.instances.length
  await instance.play()
  assert.equal(instance.synthesizing, false)
  pending.resolve('cancelled.wav'); await loading
  assert.equal(FakeAudio.instances.length, count)
  assert.equal(other.pauses, 0)
  mobile.stopAudio()
})

test('mobile: registered page hide and unload hooks release helper-only previews', async () => {
  const mixins = []
  const app = { config: { globalProperties: {} }, mixin: value => mixins.push(value) }
  const source = (await read('apps/mobile/src/main.js'))
    .replace(/^import .*$/gm, '').replace('export function createApp', 'function createApp')
  vm.runInNewContext(`${source}\ncreateApp()`, {
    createSSRApp: () => app, siteConfig: {}, featureEnabled() {},
    installFeatureGuards() {}, stopAudio: mobile.stopAudio, Mixin: {}, share: {}, App: {},
  })
  for (const event of ['onHide', 'onUnload']) {
    mobile.playAudio(`${event}.wav`)
    const player = FakeAudio.instances.at(-1)
    const hook = mixins.find(mixin => typeof mixin[event] === 'function')
    assert.ok(hook, `${event} is registered`)
    hook[event]()
    assert.equal(player.destroyed, 1)
  }
})
