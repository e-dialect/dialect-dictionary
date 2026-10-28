const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/services/capabilities.js'), 'utf8').replace(/^import .*\n/gm, '').replace(/^export /gm, '');
const now = Date.now();
const valid = { version: 1, generatedAt: new Date(now - 1000).toISOString(), expiresAt: new Date(now + 14000).toISOString(), ttlSeconds: 15, features: { wordApplications: { enabled: true } } };
(async () => {
  let requests = 0;
  const context = vm.createContext({ BASE_URL: '/api', uni: { request: async () => { requests += 1; return { statusCode: 200, data: valid }; } } });
  vm.runInContext(source, context);
  assert.equal(context.wordApplicationsEnabled(valid, now), true);
  for (const payload of [null, {}, { ...valid, version: 2 }, { ...valid, features: { wordApplications: { enabled: 'true' } } }, { ...valid, ttlSeconds: 60 }, { ...valid, expiresAt: new Date(now).toISOString() }, { ...valid, generatedAt: 'invalid' }, { ...valid, expiresAt: new Date(now + 60000).toISOString() }]) assert.equal(context.wordApplicationsEnabled(payload, now), false);
  assert.equal(await context.checkWordApplications(), true);
  assert.equal(await context.checkWordApplications(), true);
  assert.equal(requests, 2, 'No enabled cache may skip a request');
  context.uni.request = async () => { throw new Error('offline'); };
  assert.equal(await context.checkWordApplications(), false);
  context.uni.request = async () => ({ statusCode: 500, data: valid });
  assert.equal(await context.checkWordApplications(), false);
  const raw = fs.readFileSync(path.join(root, 'src/pages/words/edit.vue'), 'utf8');
  const script = raw.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/^import[\s\S]*?;\n/gm, '').replace('export default', 'globalThis.component =');
  let enabled = true; let checks = 0; let posts = 0;
  const pageContext = vm.createContext({
    checkWordApplications: async () => { checks += 1; return enabled; },
    createWordApplicationDraft: () => ({ word: '' }),
    buildWordApplicationPayload: () => ({}),
    createWordApplication: async () => { posts += 1; return { id: 42 }; },
    toLoginPage() {},
    uni: { getStorageSync: () => 'signed-in' },
  });
  vm.runInContext(script, pageContext);
  const page = { ...pageContext.component.data(), ...pageContext.component.methods };
  await page.loadWord();
  assert.equal(checks, 1);
  page.draft.word = 'preserve my draft';
  enabled = false;
  await page.submit();
  assert.equal(checks, 2);
  assert.equal(posts, 0, 'Disabled fresh capability prevents POST');
  assert.equal(page.draft.word, 'preserve my draft');
  enabled = true;
  await page.loadWord();
  await page.submit();
  assert.equal(checks, 4, 'Entry and each submission fetch current capabilities');
  assert.equal(posts, 1);
  assert.equal(page.submitted, true);
  console.log('PASS capabilities: malformed/expired/offline fail closed; no cached enable; entry and every submit recheck; drafts preserved');
})().catch(error => { console.error(error); process.exitCode = 1; });
