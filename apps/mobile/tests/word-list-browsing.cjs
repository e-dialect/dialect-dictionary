const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadPage(name, dependencies) {
  const source = fs.readFileSync(path.join(__dirname, `../src/pages/lists/${name}.vue`), 'utf8');
  const script = source.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace(/^import .*\n/gm, '').replace('export default', 'globalThis.component =');
  const context = vm.createContext(dependencies);
  vm.runInContext(script, context);
  return context.component;
}

function instance(component) {
  return { ...component.data(), ...component.methods };
}

(async () => {
  let stopCount = 0;
  let resolveLists;
  let listRequest = () => new Promise(resolve => { resolveLists = resolve; });
  const lists = loadPage('index', {
    getWordLists: () => listRequest(), toSearchPage() {},
    uni: { stopPullDownRefresh() { stopCount += 1; } },
  });
  const page = instance(lists);
  assert.equal(page.lists.length, 0, 'No example entries before the first response');
  const pending = page.loadLists();
  assert.equal(page.status, 'loading');
  assert.equal(page.loading, true);
  await page.loadLists();
  assert.equal(stopCount, 1, 'Duplicate refresh is settled without a second request');
  resolveLists({ lists: [] });
  await pending;
  assert.equal(page.status, 'ready');
  assert.equal(page.lists.length, 0, 'An empty response stays distinct from a failure');
  assert.equal(page.loading, false);
  listRequest = async () => { throw new Error('offline'); };
  await page.loadLists();
  assert.equal(page.status, 'error');
  assert.equal(page.loading, false, 'A failed refresh can be retried');
  const fixture = { id: 'CD000001', name: '主题词单', words: [] };
  listRequest = async () => ({ lists: [fixture] });
  await page.loadLists();
  assert.equal(page.status, 'ready');
  assert.equal(page.lists[0].id, fixture.id);
  listRequest = () => new Promise(resolve => { resolveLists = resolve; });
  const stale = page.loadLists();
  lists.onUnload.call(page);
  resolveLists({ lists: [] });
  await stale;
  assert.equal(page.lists[0].id, fixture.id, 'An unloaded page ignores a delayed response');

  let detailRequest = async () => { throw { statusCode: 404 }; };
  let pages = [];
  const navigation = [];
  const detail = loadPage('details', {
    getWordListDetails: (...args) => detailRequest(...args), toWordPage() {},
    getCurrentPages: () => pages,
    uni: {
      navigateBack: args => navigation.push(['back', args]),
      redirectTo: args => navigation.push(['redirect', args]),
    },
  });
  const entry = instance(detail);
  await entry.loadDetails();
  assert.equal(entry.status, 'missing', 'An absent id never requests a fabricated list');
  entry.id = 'CD000001';
  await entry.loadDetails();
  assert.equal(entry.status, 'missing');
  detailRequest = async () => { throw { statusCode: 500 }; };
  await entry.loadDetails();
  assert.equal(entry.status, 'error', 'Server failures remain retryable');
  detailRequest = async () => fixture;
  await entry.loadDetails();
  assert.equal(entry.status, 'ready');
  assert.equal(entry.wordList.id, fixture.id);
  let resolveDetail;
  detailRequest = () => new Promise(resolve => { resolveDetail = resolve; });
  const oldDetail = entry.loadDetails();
  detail.onUnload.call(entry);
  resolveDetail({ id: 'old' });
  await oldDetail;
  assert.equal(entry.wordList.id, fixture.id);
  pages = [{ route: 'pages/lists/index' }, { route: 'pages/lists/details' }];
  entry.toLists();
  assert.equal(navigation[0][0], 'back', 'Returning from a list retains the previous list page');
  pages = [{ route: 'pages/lists/details' }];
  entry.toLists();
  assert.equal(navigation[1][0], 'redirect', 'A direct detail link has a usable list exit');
  assert.equal(navigation[1][1].url, '/pages/lists/index');
  assert.equal(detail.computed.formattedDate.call({ wordList: { createTime: 'invalid' } }), '');
  console.log('PASS word lists: no placeholders, loading/empty/error/retry, refresh settlement, stale responses, 404 and return navigation');
})().catch(error => { console.error(error); process.exitCode = 1; });
