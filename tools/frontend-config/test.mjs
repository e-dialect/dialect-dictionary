#!/usr/bin/env node
// Pure Node checks of actual runtime modules. No build or browser. Generator checks
// write only to a disposable temporary project and never modify this repository.
import assert from 'node:assert/strict'
import { readFile, mkdtemp, mkdir, copyFile, rm } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import os from 'node:os'
import path from 'node:path'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const read = file => readFile(path.join(root, file.replace(/^web\//, 'apps/web/').replace(/^uni-app\//, 'apps/mobile/').replace(/^frontends-config\//, 'tools/frontend-config/')), 'utf8')
const json = async file => JSON.parse(await read(file))
const brands = await Promise.all(['coast', 'mountain'].map(name => json(`config/examples/${name}.json`)))
const defaultSettings = await json('apps/web/src/config/generated.json')
const safeDefaults = await json('tools/frontend-config/defaults.json')
const featureNames = ['pinyin', 'kinship', 'geography', 'quiz', 'music', 'dailyExpressions', 'translation']
const blockedWeb = ['Pinyin', 'Dictionary', 'Conditions', 'Characters', 'Relative', 'Music', 'DailyExpressions', 'PuxianExam', 'QuizCreate', 'QuizDetails', 'QuizResearch', 'Certificate', 'Translation', 'ptxTranslation', 'xtpTranslation']
const blockedMobile = ['/pages/tools/pinyin', '/pages/tools/dictionary', '/pages/tools/condition', '/pages/words/characters/details?id=1', '/pages/tools/relative', '/pages/tools/daily-expression/index', '/pages/quizzes/index', '/pages/quizzes/tests/answer', '/pages/music']
const featureModules = Object.fromEntries(await Promise.all(['web', 'uni-app'].map(async frontend => [frontend, await read(`${frontend}/src/config/features.js`)])))

// These modules use only JSON and local function imports; inject those dependencies
// into isolated VM contexts after removing ESM declarations. Production source runs.
function executable(source) {
  return source.replace(/^import .*\n/gm, '').replace(/^export default siteConfig\s*;?$/gm, '').replace(/^export /gm, '')
}
async function load(frontend, config, miniProgram = false) {
  let source = await read(`${frontend}/src/config/site.js`)
  if (miniProgram) source = source.replace(/\/\/ #ifdef H5[\s\S]*?\/\/ #endif/g, '')
  const context = vm.createContext({ defaults: safeDefaults, generated: defaultSettings, ...(miniProgram ? {} : { window: { __DICTIONARY_CONFIG__: config } }) })
  vm.runInContext(`${executable(source)}\nglobalThis.settings = siteConfig; globalThis.enabled = featureEnabled;`, context)
  vm.runInContext(`${executable(featureModules[frontend])}\nglobalThis.allowed = ${frontend === 'web' ? 'routeEnabled' : 'pageEnabled'};`, context)
  return context
}

for (const brand of brands) {
  for (const frontend of ['web', 'uni-app']) {
    const app = await load(frontend, brand)
    for (const key of ['name', 'shortName', 'logo', 'apiBase', 'webUrl', 'mobileUrl']) assert.equal(app.settings[key], brand[key], `${frontend}: ${key}`)
    assert.equal(app.settings.dialect.code, brand.dialect.code)
    assert.equal(app.settings.dialect.name, brand.dialect.name)
    assert.equal(app.settings.contentSource.notice, brand.contentSource.notice)
    for (const feature of featureNames) assert.equal(app.enabled(feature), false, `${frontend}: ${feature} disabled`)
    for (const route of frontend === 'web' ? blockedWeb : blockedMobile) assert.equal(app.allowed(route), false, `${frontend}: blocked ${route}`)
    for (const route of frontend === 'web' ? ['Home', 'Search', 'WordDetails', 'WordCreate', 'WordEdit'] : ['/pages/index', '/pages/search', '/pages/words/details?id=1', '/pages/words/edit?id=0']) assert.equal(app.allowed(route), true, `${frontend}: core route ${route}`)
    const enabled = await load(frontend, { ...brand, features: { ...brand.features, pinyin: true, kinship: true } })
    assert.equal(enabled.allowed(frontend === 'web' ? 'Pinyin' : '/pages/tools/pinyin'), true)
    assert.equal(enabled.allowed(frontend === 'web' ? 'Relative' : '/pages/tools/relative'), true)
    const invalidBoolean = await load(frontend, { ...brand, features: { ...brand.features, pinyin: 'true' } })
    assert.equal(invalidBoolean.enabled('pinyin'), false, 'Only explicit boolean true enables a feature')
    console.log(`PASS ${frontend}: ${brand.name} (${brand.dialect.code}), runtime branding and feature guards`)
  }
}
const miniProgram = await load('uni-app', null, true)
assert.equal(miniProgram.settings.name, defaultSettings.name, 'Mini-program uses generated build settings without window')
console.log('PASS mini-program: generated fallback without browser globals')

// Execute the actual mobile sample-playback handlers with a recording fake.
const pinyinPage = await read('apps/mobile/src/pages/tools/pinyin.vue')
const pinyinScript = pinyinPage.match(/<script>([\s\S]*?)<\/script>/)[1]
for (const [enabled, base, expectedPlays] of [[false, 'https://audio.example.test', 0], [true, '', 0], [true, 'https://audio.example.test', 3]]) {
  let plays = 0
  let loads = 0
  const audio = { play() { plays += 1 }, set src(value) { assert.match(value, /^https:\/\/audio\.example\.test\//); loads += 1 } }
  const context = vm.createContext({
    siteConfig: { phonologyAudioBase: base },
    featureEnabled: () => enabled,
    MarkdownViewer: {},
    getApp: () => ({}),
  })
  const source = pinyinScript.replace(/^import .*\n/gm, '').replace('export default', 'globalThis.component =')
  vm.runInContext(source, context)
  const page = { innerAudioContext: audio, shengmu: [{ pinyin: 'a' }], yunmu: [[{ pinyin: 'a' }]], tone: [{ type: '1' }], TabCur: 0 }
  for (const method of ['playShengmu', 'playYunmu', 'playTone']) context.component.methods[method].call(page, { currentTarget: { dataset: { id: 0 } } })
  assert.equal(loads, expectedPlays, 'No audio source is assigned unless enabled and configured')
  assert.equal(plays, expectedPlays, 'No sample playback occurs unless enabled and configured')
}
console.log('PASS phonology audio: disabled or missing source performs no load/play')

// A runtime config must not inherit enabled features or optional endpoints from a
// different brand compiled into the same artifact.
const hinghwa = await json('config/examples/hinghwa.json')
for (const frontend of ['web', 'uni-app']) {
  let source = await read(`${frontend}/src/config/site.js`)
  const context = vm.createContext({ defaults: safeDefaults, generated: hinghwa, window: { __DICTIONARY_CONFIG__: { name: 'Minimal runtime brand' } } })
  vm.runInContext(`${executable(source)}\nglobalThis.settings = siteConfig; globalThis.enabled = featureEnabled;`, context)
  for (const feature of Object.keys(safeDefaults.features)) assert.equal(context.enabled(feature), false, `${frontend}: missing ${feature} must fail closed`)
  assert.equal(context.settings.phonologyAudioBase, '')
  assert.equal(context.settings.feedback, null)
  assert.equal(context.settings.webUrl, '')
  assert.equal(context.settings.name, 'Minimal runtime brand')
  assert.deepEqual(await json(`${frontend}/src/config/defaults.json`), safeDefaults)
}
console.log('PASS runtime isolation: missing flags and optional endpoints never inherit compiled brand settings')

// Exercise the real generator sequentially in an isolated temporary project.
const temporary = await mkdtemp(path.join(os.tmpdir(), 'dictionary-config-test-'))
try {
  for (const dir of ['tools/frontend-config', 'apps/web/src/config', 'apps/mobile/src/config']) await mkdir(path.join(temporary, dir), { recursive: true })
  for (const file of ['tools/frontend-config/generate.mjs', 'tools/frontend-config/defaults.json', 'apps/mobile/src/manifest.json', 'apps/mobile/src/pages.json']) await copyFile(path.join(root, file), path.join(temporary, file.replace(/^web\//, 'apps/web/').replace(/^uni-app\//, 'apps/mobile/').replace(/^frontends-config\//, 'tools/frontend-config/')))
  const run = name => execFileSync(process.execPath, [path.join(temporary, 'tools/frontend-config/generate.mjs'), path.join(root, `config/examples/${name}.json`)], { env: { ...process.env, WECHAT_APP_ID: 'wxown-test-appid' }, stdio: 'pipe' })
  const readGenerated = file => readFile(path.join(temporary, file.replace(/^web\//, 'apps/web/').replace(/^uni-app\//, 'apps/mobile/').replace(/^frontends-config\//, 'tools/frontend-config/')), 'utf8').then(JSON.parse)
  run('hinghwa')
  const first = await readGenerated('apps/web/src/config/generated.json')
  assert.equal(first.features.pinyin, true)
  assert.equal(first.phonologyAudioBase, hinghwa.phonologyAudioBase)
  assert.equal(first.feedback.productId, hinghwa.feedback.productId)
  const hinghwaManifest = await readGenerated('apps/mobile/src/manifest.json')
  assert.deepEqual(hinghwaManifest['mp-weixin'].embeddedAppIdList, [hinghwa.feedback.miniProgramAppId])
  assert.equal(hinghwaManifest['mp-weixin'].appid, 'wxown-test-appid')
  run('coast')
  for (const frontend of ['web', 'uni-app']) {
    const next = await readGenerated(`${frontend}/src/config/generated.json`)
    assert.equal(next.name, brands[0].name)
    assert.equal(next.phonologyAudioBase, '')
    assert.equal(next.feedback, null)
    for (const feature of Object.keys(safeDefaults.features)) assert.equal(next.features[feature], false)
  }
  const coastManifest = await readGenerated('apps/mobile/src/manifest.json')
  assert.deepEqual(coastManifest['mp-weixin'].embeddedAppIdList, [])
  assert.equal(coastManifest['mp-weixin'].appid, 'wxown-test-appid')
} finally { await rm(temporary, { recursive: true, force: true }) }
console.log('PASS generator isolation: hinghwa -> coast clears optional endpoints, enabled flags, and embedded feedback app IDs')

const feedbackSource = executable(await read('apps/mobile/src/routers/index.js'))
for (const enabled of [false, true]) {
  const calls = []
  const context = vm.createContext({ siteConfig: hinghwa, featureEnabled: () => enabled, window: { location: { assign: url => calls.push(['web', url]) } }, uni: { getSystemInfoSync: () => ({ uniPlatform: 'web' }), showModal: () => calls.push(['unavailable']) } })
  vm.runInContext(`${feedbackSource}\ntoTuxiaochaoPage();`, context)
  assert.equal(calls[0][0], enabled ? 'web' : 'unavailable')
  if (enabled) assert.equal(calls[0][1], hinghwa.feedback.webUrl)
}
const miniFeedbackCalls = []
const miniFeedback = vm.createContext({ siteConfig: hinghwa, featureEnabled: () => true, uni: { getSystemInfoSync: () => ({ uniPlatform: 'mp-weixin' }), openEmbeddedMiniProgram: options => miniFeedbackCalls.push(options), showModal() { throw new Error('Configured feedback should be available') } } })
vm.runInContext(`${feedbackSource}\ntoTuxiaochaoPage();`, miniFeedback)
assert.equal(miniFeedbackCalls[0].appId, hinghwa.feedback.miniProgramAppId)
assert.equal(miniFeedbackCalls[0].extraData.id, hinghwa.feedback.productId)
console.log('PASS feedback: configured channels require legacyLinks and preserve own mini-program identity')
