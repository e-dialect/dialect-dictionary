#!/usr/bin/env node
// Exercise the production Vue watchers and async requests without a browser.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(path.join(root, 'apps/web/package.json'))
const Vue = require('vue')
const read = file => readFile(path.join(root, 'apps/web/src', file), 'utf8')
const flush = async () => { await Promise.resolve(); await Vue.nextTick(); await Promise.resolve() }
const plain = value => JSON.parse(JSON.stringify(value))
const pageSource = await read('utils/resultPage.js')
const pageContext = vm.createContext({})
vm.runInContext(pageSource.replace('export function', 'function') + '\nglobalThis.resultPage = resultPage', pageContext)
const { resultPage } = pageContext

for (const value of [undefined, null, '', 'x', '-1', '0', '1.5', ['2'], 'Infinity', '9007199254740993']) {
  assert.equal(resultPage(value, 20, 8), 1, `invalid page ${value}`)
}
assert.equal(resultPage('2', 20, 8), 2)
assert.equal(resultPage('999', 20, 8), 3)
assert.equal(resultPage('2', 0, 8), 1)

function transport () {
  const requests = []
  const send = (method, url, data) => new Promise((resolve, reject) => requests.push({ method, url, data, resolve, reject }))
  return { requests, get: (url, data) => send('get', url, data), put: (url, data) => send('put', url, data) }
}

const axios = transport()
const listContext = vm.createContext({ axios, resultPage })
vm.runInContext((await read('components/pagedResults.js')).replace(/^import .*\n/gm, '').replace('export default function', 'function') + '\nglobalThis.factory = pagedResults', listContext)
const ids = Array.from({ length: 20 }, (_, index) => index + 1)
const list = new Vue({ ...listContext.factory('words'), propsData: { listData: ids, pageSize: 8, page: 2 } })
assert.equal(list.currentPage, 2)
assert.deepEqual(plain(axios.requests[0].data.words), ids.slice(8, 16), 'restored page fetches its own IDs')
const changes = []
list.$on('page-change', page => changes.push(page))
list.changePage(3)
assert.deepEqual(changes, [3])
assert.deepEqual(plain(axios.requests[1].data.words), ids.slice(16), 'click fetches next page immediately')
axios.requests[1].resolve({ data: { words: [{ id: 17 }] } })
await flush()
axios.requests[0].resolve({ data: { words: [{ id: 9 }] } })
await flush()
assert.equal(list.listSource[0].id, 17, 'late previous page cannot replace the visible page')

list.page = 1
await flush()
assert.equal(list.currentPage, 1, 'URL page change updates a mounted list')
axios.requests[2].reject(new Error('offline'))
await flush()
assert.equal(list.failed, true)
assert.equal(list.loading, false)
const retry = list.getCurrentPageData(list.currentPage)
axios.requests[3].resolve({ data: { words: [{ id: 1 }] } })
await retry
assert.equal(list.failed, false)
assert.equal(list.listSource[0].id, 1)

list.page = 99
await flush()
assert.equal(list.currentPage, 3, 'outdated page is clamped to last available page')
list.listData = [1]
await flush()
assert.equal(list.currentPage, 1, 'a smaller result set clamps a restored page')
list.$destroy()

const articles = new Vue({ ...listContext.factory('articles'), propsData: { listData: ids, pageSize: 8 } })
articles.changePage(2)
assert.equal(articles.currentPage, 2, 'existing callers without a page prop can still paginate')
articles.listData = [7, 8]
await flush()
assert.equal(articles.currentPage, 1, 'existing callers reset when their dataset changes')
articles.$destroy()

const searchAxios = transport()
const searchContext = vm.createContext({ axios: searchAxios, resultPage, PinyinList: {}, WordList: {}, ArticleList: {} })
const searchScript = (await read('views/SearchResult.vue')).match(/<script>([\s\S]*?)<\/script>/)[1]
vm.runInContext(searchScript.replace(/^import .*\n/gm, '').replace('export default', 'globalThis.component ='), searchContext)
const route = Vue.observable({ query: { key: '海', wordsPage: '2', articlesPage: '3' } })
const navigations = []
const search = new Vue({
  ...searchContext.component,
  beforeCreate () {
    this.$route = route
    this.$router = {
      replace: target => { navigations.push(target); route.query = target.query },
      push: target => navigations.push(target)
    }
    this.$featureEnabled = () => false
  },
  propsData: { keyWords: '海' }
})
searchAxios.requests[0].resolve({ data: { words: ids } })
searchAxios.requests[1].resolve({ data: { articles: ids } })
await flush()
assert.equal(search.wordsPage, 2)
assert.equal(search.articlesPage, 3)
search.changePage('words', 3)
assert.deepEqual(plain(route.query), { key: '海', wordsPage: '3', articlesPage: '3' }, 'word pagination preserves article pagination and keyword')
search.changePage('articles', 1)
assert.deepEqual(plain(route.query), { key: '海', wordsPage: '3' })
const navigationCount = navigations.length
search.changePage('words', 3)
assert.equal(navigations.length, navigationCount, 'selecting the same page avoids duplicate navigation')
search.search('  山  ')
assert.deepEqual(plain(navigations.at(-1)), { name: 'Search', query: { key: '山' } }, 'a new search drops both saved pages')

search.keyWords = '山'
await flush()
search.keyWords = '河'
await flush()
searchAxios.requests[4].resolve({ data: { words: [101] } })
searchAxios.requests[5].reject(new Error('unavailable'))
await flush()
searchAxios.requests[2].resolve({ data: { words: [99] } })
searchAxios.requests[3].resolve({ data: { articles: [99] } })
await flush()
assert.deepEqual(plain(search.words), [101], 'late search response cannot replace the new keyword')
assert.deepEqual(plain(search.articles), [])
assert.equal(search.failed.articles, true, 'late success cannot erase current failure')
const articleRetry = search.loadResults('articles', search.requestId)
searchAxios.requests[6].resolve({ data: { articles: [] } })
await articleRetry
assert.equal(search.failed.articles, false, 'successful empty results differ from request failure')
assert.equal(search.loading.articles, false)
search.$destroy()
console.log('PASS web search: restored and independent pages, invalid pages, legacy callers, retries and stale responses')
