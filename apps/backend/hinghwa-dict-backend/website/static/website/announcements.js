'use strict';
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.announcement-editor').forEach(editor => {
    const hidden = editor.querySelector('input[type=hidden]');
    const initial = JSON.parse(editor.querySelector('script[type="application/json"]').textContent);
    let selected = initial.slice();
    const list = editor.querySelector('.announcement-selected');
    const message = editor.querySelector('.announcement-message');
    const results = editor.querySelector('.announcement-results');
    const query = editor.querySelector('.announcement-query');
    let generation = 0;
    const element = (tag, text, className) => {
      const node = document.createElement(tag); node.textContent = text;
      if (className) node.className = className;
      return node;
    };
    const button = (label, action) => {
      const node = element('button', label); node.type = 'button';
      node.addEventListener('click', action); return node;
    };
    const detail = item => {
      const block = element('div', '', 'announcement-detail');
      block.append(element('strong', item.title));
      block.append(element('span', item.public === true ? '已公开' : item.public === false ? '未公开（不会在网站显示）' : '不可查看', 'announcement-badge'));
      block.append(element('span', item.date ? '发布：' + item.date : '日期不可查看', 'announcement-date'));
      if (item.preview) {
        const preview = element('details', ''); preview.append(element('summary', '文字预览'));
        preview.append(element('p', item.preview)); block.append(preview);
      }
      return block;
    };
    const render = () => {
      list.replaceChildren();
      selected.forEach((item, index) => {
        const row = element('li', ''); row.append(detail(item));
        const controls = element('div', '', 'announcement-controls');
        const up = button('上移', () => { [selected[index - 1], selected[index]] = [selected[index], selected[index - 1]]; render(); });
        const down = button('下移', () => { [selected[index + 1], selected[index]] = [selected[index], selected[index + 1]]; render(); });
        up.disabled = index === 0; down.disabled = index === selected.length - 1;
        controls.append(up, down, button('移除', () => { selected.splice(index, 1); render(); }));
        row.append(controls); list.append(row);
      });
      // Preserve malformed original storage until explicitly corrected server-side.
      if (!editor.querySelector('.errornote')) hidden.value = JSON.stringify(selected.map(item => item.id));
      if (!selected.length) list.append(element('li', '暂未选择公告。'));
    };
    const search = async () => {
      const current = ++generation;
      message.textContent = '正在查找…';
      try {
        const url = new URL(editor.dataset.searchUrl, window.location.origin); url.searchParams.set('q', query.value);
        const response = await fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('search failed');
        const data = await response.json();
        if (current !== generation) return;
        results.replaceChildren();
        data.articles.forEach(item => {
          const row = element('div', '', 'announcement-result'); row.append(detail(item));
          row.append(button('加入公告', () => {
            if (selected.some(existing => existing.id === item.id)) { message.textContent = '这篇文章已经在已选公告中，没有重复加入。'; return; }
            selected.push(item); render(); message.textContent = '已加入待保存列表；请点击页面底部保存。';
          })); results.append(row);
        });
        message.textContent = data.articles.length ? (data.has_more ? '只显示前20篇，请缩小标题范围。' : '找到' + data.articles.length + '篇；点击加入后还需保存。') : '没有找到文章，请换个标题关键词。';
      } catch (error) {
        if (current === generation) message.textContent = '搜索未成功，可能登录已过期或暂无权限。已选列表没有改变，请重试或重新登录。';
      }
    };
    editor.querySelector('.announcement-search').addEventListener('click', search);
    query.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); search(); } });
    editor.querySelector('.announcement-reset').addEventListener('click', () => { selected = initial.slice(); render(); message.textContent = '已恢复打开页面时的选择，尚未保存。'; });
    render();
  });
});
