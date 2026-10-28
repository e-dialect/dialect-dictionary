/**
 * Keep editable dictionary fields separate from server-owned audit/publication data.
 */
export function createWordApplicationDraft(source = {}) {
  return {
    word: source.word || '',
    standard_pinyin: source.standard_pinyin || '',
    standard_ipa: source.standard_ipa || '',
    definition: source.definition || '',
    annotation: source.annotation || '',
    mandarinText: Array.isArray(source.mandarin) ? source.mandarin.join('\n') : '',
    tagsText: Array.isArray(source.tags) ? source.tags.join('\n') : '',
    related_words: Array.isArray(source.related_words) ? source.related_words.slice() : [],
    related_articles: Array.isArray(source.related_articles) ? source.related_articles.slice() : [],
  };
}

function text(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function lines(value) {
  return [...new Set(text(value).split(/\r?\n/).map((item) => item.trim()).filter(Boolean))];
}

function relatedIds(values) {
  if (!Array.isArray(values)) return [];
  return [...new Set(values.map((item) => {
    const id = Number(item && typeof item === 'object' ? item.id : item);
    if (!Number.isSafeInteger(id) || id <= 0) throw new Error('关联内容编号无效，请重新加载词条');
    return id;
  }))];
}

export function parseApplicationWordId(value) {
  if (value === undefined || value === null || value === '') return 0;
  if (!/^\d+$/.test(String(value))) throw new Error('词条编号无效');
  const id = Number(value);
  if (!Number.isSafeInteger(id) || id < 0) throw new Error('词条编号无效');
  return id;
}

export function buildWordApplicationPayload(wordId, draft, reason = '') {
  const word = parseApplicationWordId(wordId);
  const content = {
    word: text(draft.word),
    standard_pinyin: text(draft.standard_pinyin),
    standard_ipa: text(draft.standard_ipa),
    definition: text(draft.definition),
    annotation: text(draft.annotation),
    mandarin: lines(draft.mandarinText),
    tags: lines(draft.tagsText),
    related_words: relatedIds(draft.related_words),
    related_articles: relatedIds(draft.related_articles),
  };
  if (!content.word) throw new Error('请填写词条名称');
  if (!content.definition) throw new Error('请填写词条释义');
  if (Array.from(content.word).length > 60) throw new Error('词条名称不能超过60字');
  if (Array.from(content.standard_pinyin).length > 30) throw new Error('拼音不能超过30字，请在申请说明中补充');
  if (Array.from(content.standard_ipa).length > 30) throw new Error('国际音标不能超过30字，请在申请说明中补充');
  if (Array.from(text(reason)).length > 200) throw new Error('申请说明不能超过200字');
  return { word, content, reason: text(reason) };
}
