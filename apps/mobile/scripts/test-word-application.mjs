import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const helperUrl = new URL('../src/utils/wordApplication.js', import.meta.url);
const source = await readFile(helperUrl, 'utf8');
const { buildWordApplicationPayload, createWordApplicationDraft, parseApplicationWordId } =
  await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

const existing = {
  word: ' 示例 ', definition: '①释义：例句（说明）。', standard_pinyin: 'pin', standard_ipa: 'ipa',
  annotation: '注', mandarin: ['普通话'], tags: ['标签'],
  related_words: [{ id: 8, word: '关联词' }, { id: 9, word: '另一词' }],
  related_articles: [{ id: 12, title: '关联文章' }],
  visibility: true, verifier: 999, contributor: 888, views: 100, definitions: [{ content: '展示字段' }],
};
const snapshot = JSON.stringify(existing);
const draft = createWordApplicationDraft(existing);
draft.visibility = true;
draft.verifier = 999;
const result = buildWordApplicationPayload(7, draft, ' 核对来源 ');
assert.equal(result.word, 7);
assert.equal(result.reason, '核对来源');
assert.equal(result.content.word, '示例');
assert.equal(result.content.definition, existing.definition);
assert.deepEqual(result.content.related_words, [8, 9]);
assert.deepEqual(result.content.related_articles, [12]);
assert.deepEqual(result.content.mandarin, ['普通话']);
assert.deepEqual(result.content.tags, ['标签']);
assert.deepEqual(Object.keys(result.content).sort(), [
  'word', 'standard_pinyin', 'standard_ipa', 'definition', 'annotation', 'mandarin',
  'tags', 'related_words', 'related_articles',
].sort());
assert.equal(JSON.stringify(existing), snapshot, 'editing must not mutate the fetched detail');
assert.notEqual(draft.related_words, existing.related_words);

const fresh = createWordApplicationDraft();
fresh.word = '新词';
fresh.definition = '新释义';
fresh.mandarinText = '甲\n甲\r\n乙';
const created = buildWordApplicationPayload(0, fresh);
assert.equal(created.word, 0);
assert.deepEqual(created.content.mandarin, ['甲', '乙']);
assert.deepEqual(created.content.related_words, []);
assert.deepEqual(created.content.related_articles, []);
assert.equal(parseApplicationWordId(undefined), 0);
for (const invalid of ['abc', '-1', '1.5', '1e2', '9007199254740992']) {
  assert.throws(() => parseApplicationWordId(invalid));
}
assert.throws(() => buildWordApplicationPayload(0, { ...fresh, word: ' ' }), /词条名称/);
assert.throws(() => buildWordApplicationPayload(0, { ...fresh, definition: '' }), /释义/);
assert.throws(() => buildWordApplicationPayload(0, { ...fresh, related_words: [{ id: 'oops' }] }), /关联/);
for (const [key, maximum] of [['word', 60], ['standard_pinyin', 30], ['standard_ipa', 30]]) {
  assert.doesNotThrow(() => buildWordApplicationPayload(0, { ...fresh, [key]: '甲'.repeat(maximum) }));
  assert.throws(() => buildWordApplicationPayload(0, { ...fresh, [key]: '甲'.repeat(maximum + 1) }));
}
assert.doesNotThrow(() => buildWordApplicationPayload(0, fresh, '甲'.repeat(200)));
assert.throws(() => buildWordApplicationPayload(0, fresh, '甲'.repeat(201)));
assert.doesNotThrow(() => buildWordApplicationPayload(0, { ...fresh, word: '𠮷'.repeat(60) }));
console.log('Word application payload: whitelist, relation preservation, validation and new-word tests passed.');
