'use strict';
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.announcement-editor').forEach(editor => {
    const hidden = editor.querySelector('input[type=hidden]');
    const initialValue = hidden.value;
    const initial = JSON.parse(editor.querySelector('script[type="application/json"]').textContent);
    const rebuild = editor.querySelector('.announcement-rebuild');
    const broken = editor.dataset.broken === 'true';
    const controls = editor.querySelector('.announcement-pick-controls');
    let selected = initial.slice();
    const list = editor.querySelector('.announcement-selected');
    const message = editor.querySelector('.announcement-message');
    const results = editor.querySelector('.announcement-results');
    const query = editor.querySelector('.announcement-query');
    let generation = 0;
    const editable = () => !broken || (rebuild && rebuild.checked);
    const element = (tag, text, className) => {
      const node = document.createElement(tag); node.textContent = text;
      if (className) node.className = className;
      return node;
    };
    const button = (label, action, accessibleName) => {
      const node = element('button', label); node.type = 'button';
      if (accessibleName) node.setAttribute('aria-label', accessibleName);
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
    const restoreFocus = (id, preferred) => {
      const row = Array.from(list.children).find(item => item.dataset.articleId === String(id));
      const candidates = row ? Array.from(row.querySelectorAll('button')) : [];
      const target = candidates.find(item => item.dataset.action === preferred && !item.disabled) || candidates.find(item => !item.disabled);
      (target || query).focus();
    };
    const render = (focusId, focusAction) => {
      list.replaceChildren();
      selected.forEach((item, index) => {
        const row = element('li', ''); row.dataset.articleId = String(item.id); row.append(detail(item));
        const actions = element('div', '', 'announcement-controls');
        const move = offset => {
          if (!editable() || index + offset < 0 || index + offset >= selected.length) return;
          [selected[index + offset], selected[index]] = [selected[index], selected[index + offset]];
          render(item.id, offset < 0 ? 'up' : 'down');
          message.textContent = item.title + '已移到第' + (index + offset + 1) + '位，尚未保存。';
        };
        const up = button('上移', () => move(-1), '将“' + item.title + '”上移');
        const down = button('下移', () => move(1), '将“' + item.title + '”下移');
        up.dataset.action = 'up'; down.dataset.action = 'down';
        up.disabled = index === 0; down.disabled = index === selected.length - 1;
        const remove = button('移除', () => {
          if (!editable()) return;
          const neighbour = selected[index + 1] || selected[index - 1];
          selected.splice(index, 1); render(neighbour && neighbour.id, 'remove');
          message.textContent = '已移除“' + item.title + '”，尚未保存。';
        }, '从公告移除“' + item.title + '”');
        remove.dataset.action = 'remove'; actions.append(up, down, remove); row.append(actions); list.append(row);
      });
      controls.disabled = !editable();
      hidden.value = editable() ? JSON.stringify(selected.map(item => item.id)) : initialValue;
      if (!selected.length) list.append(element('li', '暂未选择公告。'));
      if (focusAction) restoreFocus(focusId, focusAction);
    };
    const search = async () => {
      if (!editable()) return;
      const current = ++generation;
      message.textContent = '正在查找…';
      try {
        const url = new URL(editor.dataset.searchUrl, window.location.origin); url.searchParams.set('q', query.value);
        const response = await fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('search failed');
        const data = await response.json();
        if (current !== generation || !editable()) return;
        results.replaceChildren();
        data.articles.forEach(item => {
          const row = element('div', '', 'announcement-result'); row.append(detail(item));
          row.append(button('加入公告', () => {
            if (!editable()) return;
            if (selected.some(existing => existing.id === item.id)) { message.textContent = '这篇文章已经在已选公告中，没有重复加入。'; return; }
            selected.push(item); render(); message.textContent = '已加入待保存列表；请点击页面底部保存。';
          }, '将“' + item.title + '”加入公告')); results.append(row);
        });
        message.textContent = data.articles.length ? (data.has_more ? '只显示前20篇，请缩小标题范围。' : '找到' + data.articles.length + '篇；加入后还需保存。') : '没有找到文章，请换个标题关键词。';
      } catch (error) {
        if (current === generation) message.textContent = '搜索未成功，可能登录已过期或暂无权限。已选列表没有改变，请重试或重新登录。';
      }
    };
    editor.querySelector('.announcement-search').addEventListener('click', search);
    query.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); search(); }
      if (event.key === 'Escape') { ++generation; results.replaceChildren(); query.value = ''; message.textContent = '已收起搜索结果，已选公告未改变。'; }
    });
    editor.querySelector('.announcement-reset').addEventListener('click', () => {
      ++generation; results.replaceChildren(); selected = initial.slice();
      if (rebuild) rebuild.checked = false;
      render(); if (broken && rebuild) rebuild.focus();
      message.textContent = '已恢复打开页面时的选择，尚未保存。';
    });
    if (rebuild) rebuild.addEventListener('change', () => {
      ++generation; results.replaceChildren(); selected = initial.slice(); render();
      message.textContent = rebuild.checked ? '已确认重新选择。保存时将保留修复前原值；现在还未保存。' : '已取消修复，服务器原值不会改变。';
      if (rebuild.checked) query.focus();
    });
    render();
  });
});
