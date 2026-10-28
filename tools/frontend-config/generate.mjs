#!/usr/bin/env node
// Generate public runtime settings and mini-program build settings from one JSON.
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const input = process.argv[2]
if (!input) throw new Error('Usage: node tools/frontend-config/generate.mjs config/site.example.json')
const config = JSON.parse(await readFile(path.resolve(input), 'utf8'))
for (const field of ['name', 'shortName', 'apiBase']) {
  if (typeof config[field] !== 'string' || !config[field]) throw new Error(`Missing public config: ${field}`)
}
for (const field of ['dialect', 'contentSource', 'features']) {
  if (!config[field] || typeof config[field] !== 'object' || Array.isArray(config[field])) throw new Error(`Missing config object: ${field}`)
}
for (const field of ['apiBase', 'webUrl', 'mobileUrl', 'logo', 'phonologyAudioBase']) {
  if (config[field] && !/^(https?:\/\/|\/)/.test(config[field])) throw new Error(`${field} must use http(s) or an absolute path`)
}
if (process.argv.includes('--mini-program')) {
  if (!/^https:\/\//.test(config.apiBase)) throw new Error('Mini-program apiBase must be an absolute HTTPS URL registered in WeChat');
  if (!process.env.WECHAT_APP_ID) throw new Error('Set WECHAT_APP_ID for your own mini-program');
}
const fallback = JSON.parse(await readFile(path.join(root, 'tools/frontend-config/defaults.json'), 'utf8'))
const settings = { ...fallback, ...config, dialect: { ...fallback.dialect, ...config.dialect }, contentSource: { ...fallback.contentSource, ...config.contentSource }, features: { ...fallback.features, ...config.features } }
const json = JSON.stringify(settings, null, 2) + '\n'
const js = `window.__DICTIONARY_CONFIG__ = ${JSON.stringify(settings).replace(/</g, '\\u003c')};\n`
for (const frontend of ['apps/web', 'apps/mobile']) {
  await mkdir(path.join(root, frontend, 'public'), { recursive: true })
  await writeFile(path.join(root, frontend, 'public/site-config.json'), json)
  await writeFile(path.join(root, frontend, 'public/site-config.js'), js)
  await writeFile(path.join(root, frontend, 'src/config/generated.json'), json)
  await writeFile(path.join(root, frontend, 'src/config/defaults.json'), JSON.stringify(fallback, null, 2) + '\n')
}
const manifestPath = path.join(root, 'apps/mobile/src/manifest.json')
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
manifest.name = settings.name
manifest.description = `${settings.dialect.name}在线词典`
manifest.h5.title = settings.name
// H5 artifact can serve any runtime brand at /mobile/. Mini-program identity is build-time.
manifest.appid = process.env.UNI_APP_ID || ''
manifest['mp-weixin'].appid = process.env.WECHAT_APP_ID || ''
manifest['mp-weixin'].embeddedAppIdList = settings.features.legacyLinks === true && settings.feedback && settings.feedback.miniProgramAppId && settings.feedback.productId ? [settings.feedback.miniProgramAppId] : []
await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n')
const pagesPath = path.join(root, 'apps/mobile/src/pages.json')
const pages = JSON.parse(await readFile(pagesPath, 'utf8'))
pages.globalStyle.navigationBarTitleText = settings.name
await writeFile(pagesPath, JSON.stringify(pages, null, 2) + '\n')
console.log(`Generated public settings for ${settings.name}; no build or upload performed.`)
