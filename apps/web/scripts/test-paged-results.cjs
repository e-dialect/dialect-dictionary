const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { test } = require('node:test')

const pageSource = fs.readFileSync(path.join(__dirname, '../src/utils/resultPage.js'), 'utf8')
  .replace('export function', 'function')
const source = pageSource + '\n' + fs.readFileSync(path.join(__dirname, '../src/components/pagedResults.js'), 'utf8')
  .replace(/^import .*$/gm, '')
  .replace('export default function', 'function')

for (const resource of ['words', 'articles']) {
  test(resource + ' ignores late pages and clears empty results', async () => {
    const pending = []
    const axios = { put: () => new Promise(resolve => pending.push(resolve)) }
    const options = vm.runInNewContext(source + '\npagedResults(resource)', { axios, resource })
    const list = { ...options.data(), ...options.methods, listData: [1, 2], pageSize: 1 }
    const first = list.getCurrentPageData(1)
    const second = list.getCurrentPageData(2)
    pending[1]({ data: { [resource]: [2] } })
    await second
    pending[0]({ data: { [resource]: [1] } })
    await first
    assert.deepEqual(Array.from(list.listSource), [2])
    list.listData = []
    options.watch.listData.handler.call(list)
    assert.equal(list.listSource.length, 0)
    assert.equal(list.currentPage, 1)
    assert.equal(list.loading, false)
  })
}
