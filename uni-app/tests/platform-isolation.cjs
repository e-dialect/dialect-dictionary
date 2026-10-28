/* Run from uni-app: node tests/platform-isolation.cjs. No full build/network. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { initPreContext, preJs } = require('@dcloudio/uni-cli-shared/dist/preprocess');
const { parse } = require('@vue/compiler-sfc');
const babel = require('@babel/parser');
const root = path.resolve(__dirname, '..');
const files = ['App.vue', 'main.js', 'config/site.js', 'routers/mob2pc.js', 'routers/pc2mob.js', 'routers/index.js', 'components/WordListShowing.vue', 'pages/words/pronunciations/upload.vue', 'services/login.js', 'services/user.js', 'services/shareMessages.js', 'services/capabilities.js', 'pages/words/edit.vue'];
function code(file, platform) {
  initPreContext(platform);
  const raw = fs.readFileSync(path.join(root, 'src', file), 'utf8');
  return preJs(file.endsWith('.vue') ? parse(raw).descriptor.script.content : raw, file);
}
function identifiers(node, found = new Set()) {
  if (!node || typeof node !== 'object') return found;
  if (node.type === 'Identifier') found.add(node.name);
  for (const [key, value] of Object.entries(node)) {
    if (['loc', 'start', 'end', 'comments', 'tokens'].includes(key)) continue;
    if (Array.isArray(value)) value.forEach(item => identifiers(item, found));
    else if (value && typeof value === 'object') identifiers(value, found);
  }
  return found;
}
function runnable(source) {
  return source.replace(/^import .*\n/gm, '').replace(/export default/, 'globalThis.component =').replace(/^export /gm, '');
}
(async () => {
  for (const platform of ['h5', 'mp-weixin']) {
    for (const file of files) {
      const source = code(file, platform);
      const ast = babel.parse(source, { sourceType: 'module' });
      if (platform === 'mp-weixin') {
        const names = identifiers(ast);
        for (const name of ['window', 'document', 'navigator', 'MediaRecorder', 'Blob', 'URLSearchParams']) assert(!names.has(name), `${file} leaks ${name} into MP-WEIXIN`);
      }
    }
    const source = code('services/login.js', platform);
    const calls = [];
    const context = vm.createContext({ uni: { login: () => calls.push('native-login'), showToast: () => calls.push('disabled') }, featureEnabled: () => true, toLoginPage: () => calls.push('account-login') });
    vm.runInContext(runnable(source), context);
    await context.mpLogin();
    assert.deepEqual(calls, platform === 'h5' ? ['account-login'] : ['native-login']);
    if (platform === 'mp-weixin') {
      calls.length = 0;
      context.featureEnabled = () => false;
      await context.mpLogin();
      assert.deepEqual(calls, ['disabled']);
    }
    console.log(`PASS ${platform}: ${files.length} preprocessed scripts parse; login stays on its platform`);
  }
  const app = vm.createContext({ getLoginStatus: async () => {}, uni: { getSystemInfo: ({ success }) => success({ platform: 'ios', statusBarHeight: 20 }), getMenuButtonBoundingClientRect: () => ({ top: 24, bottom: 56 }) } });
  vm.runInContext(runnable(code('App.vue', 'mp-weixin')), app);
  const instance = { globalData: app.component.globalData };
  await app.component.onLaunch.call(instance);
  assert.equal(instance.globalData.CustomBar, 60);
  const sharing = vm.createContext({ siteConfig: { name: 'Test', logo: '' } });
  vm.runInContext(runnable(code('services/shareMessages.js', 'mp-weixin')), sharing);
  assert.equal(Object.keys(sharing.defaultMessage()).length, 0);
  assert.equal('success' in sharing.component.onShareTimeline(), false);
  assert(!fs.readFileSync(path.join(root, 'src/main.js'), 'utf8').includes('Polyfill.init'));
  console.log('PASS MP startup without browser globals; native APIs are not replaced; share delivery is not claimed');
})().catch(error => { console.error(error); process.exitCode = 1; });
