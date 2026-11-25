import request from '../utils/request';

/* 获取词单 */
export async function getWordLists(options) {
  return request.get('/lists', null, options);
}

/**
 * @param id 词单id
 * @returns {Promise<unknown>}
 */
export async function getWordListDetails(id, options) {
  return request.get(`/lists/${encodeURIComponent(id)}`, null, options);
}

// 创建词单
export async function postWordList(wordlist) {
  return request.post('/lists', wordlist);
}
