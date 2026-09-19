/* DB Studio preview: no database writes, no third-party runtime, no data persistence. */
(function (root) {
  'use strict';
  const MAX_BYTES = 2 * 1024 * 1024;
  const MAX_ROWS = 5000;
  const MAX_FIELDS = 200;
  const MODES = ['table', 'cards', 'json', 'schema'];
  const FORMATS = ['auto', 'text', 'number', 'badge', 'json'];
  const own = (o, key) => Object.prototype.hasOwnProperty.call(o, key);
  const isObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const number = (v, low, high, fallback) => Number.isFinite(Number(v)) ? Math.max(low, Math.min(high, Number(v))) : fallback;
  function parse(text) {
    if (new TextEncoder().encode(text).length > MAX_BYTES) throw new Error('JSON 超过 2 MiB 限制。');
    const value = JSON.parse(text);
    const pending = [[value, 0]];
    while (pending.length) {
      const [v, depth] = pending.pop();
      if (depth > 32) throw new Error('JSON 嵌套超过 32 层。');
      if (v && typeof v === 'object') Object.values(v).forEach(child => pending.push([child, depth + 1]));
    }
    return value;
  }
  function normalize(value) {
    let data = value;
    if (isObject(data)) {
      if (data.available === false) throw new Error('数据源明确返回不可用；未使用示例数据替代。');
      const wrapper = ['tasks', 'rows', 'items', 'records', 'data'].find(key => Array.isArray(data[key]));
      if (wrapper) data = data[wrapper];
      else if (isObject(data.profile)) data = [data.profile];
      else data = [data];
    }
    if (!Array.isArray(data)) throw new Error('需要 JSON 数组或对象。');
    if (data.length > MAX_ROWS) throw new Error('首版最多载入 5000 条，请先导出较小数据集。');
    const rows = data.map(row => isObject(row) ? row : { value: row });
    const fields = [...new Set(rows.flatMap(row => Object.keys(row)))];
    if (fields.length > MAX_FIELDS) throw new Error('顶层字段超过 200 个，请先选择字段。');
    return { rows, fields };
  }
  function defaults(fields) {
    return { version: 1, view: 'table', density: 50, detail: 2,
      columns: fields.map(field => ({ field, label: field, visible: true, width: 180, format: 'auto' })) };
  }
  function validate(raw, fields) {
    if (!isObject(raw) || raw.version !== 1 || !Array.isArray(raw.columns)) throw new Error('不是 version=1 的 DB Studio 样式文件。');
    if (raw.columns.length > MAX_FIELDS) throw new Error('样式字段过多。');
    const allowed = new Set(fields), used = new Set(), columns = [];
    raw.columns.forEach(col => {
      if (!isObject(col) || !allowed.has(col.field) || used.has(col.field)) return;
      used.add(col.field);
      columns.push({ field: col.field, label: typeof col.label === 'string' ? col.label.slice(0, 80) : col.field,
        visible: col.visible !== false, width: number(col.width, 90, 480, 180),
        format: FORMATS.includes(col.format) ? col.format : 'auto' });
    });
    defaults(fields.filter(field => !used.has(field))).columns.forEach(col => columns.push(col));
    return { version: 1, view: MODES.includes(raw.view) ? raw.view : 'table',
      density: number(raw.density, 0, 100, 50), detail: Math.round(number(raw.detail, 1, 3, 2)), columns };
  }
  const visible = config => config.columns.filter(c => c.visible).slice(0, config.detail === 1 ? 3 : config.detail === 2 ? 8 : MAX_FIELDS);
  const text = value => value === null ? 'null' : value === undefined ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  const type = value => value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value;
  function project(row, columns) {
    return Object.fromEntries(columns.filter(c => own(row, c.field)).map(c => [c.field, row[c.field]]));
  }
  const model = { parse, normalize, defaults, validate, visible, text, type, project, MAX_BYTES };
  if (typeof module === 'object' && module.exports) module.exports = model;
  if (!root.document) return;
  root.DBStudioModel = model;
  const $ = id => document.getElementById(id);
  const el = (tag, value, className) => {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = value;
    if (className) node.className = className;
    return node;
  };
  let rows = [], fields = [], config = defaults([]), page = 0, sourceKey = 'local';
  let generation = 0, abort = null, activeSession = null;
  let presets = [];
  function session() {
    try { return { token: localStorage.getItem('warehouse_auth_token') || '', tenant: localStorage.getItem('warehouse_current_tenant') || '' }; }
    catch (_) { return { token: '', tenant: '' }; }
  }
  const sameSession = (a, b) => a && b && a.token === b.token && a.tenant === b.tenant;
  const message = (value, error = false) => { $('message').textContent = value; $('message').classList.toggle('error', error); };
  function cancel() { generation += 1; if (abort) abort.abort(); abort = null; $('load').disabled = false; }
  function clearInspector() {
    $('record-content').replaceChildren();
    if ($('record-dialog').open) $('record-dialog').close();
  }
  function clearData(note) {
    clearInspector();
    cancel(); activeSession = null; rows = []; fields = []; config = defaults([]); presets = []; page = 0;
    $('source-title').textContent = '尚未载入数据'; $('identity').textContent = '请重新载入数据';
    $('search').value = ''; renderPresets(); sync(); message(note);
  }
  function guard() {
    if (activeSession && !sameSession(activeSession, session())) { clearData('登录身份或公司已变化，已清除旧数据。请重新载入。'); return false; }
    return true;
  }
  function accept(value, key, title) {
    const next = normalize(value);
    clearInspector();
    rows = next.rows; fields = next.fields; sourceKey = key;
    config = defaults(fields); page = 0; presets = [];
    $('source-title').textContent = title; $('search').value = '';
    renderPresets(); sync();
  }
  function sync() {
    $('view').value = config.view; $('detail').value = String(config.detail); $('density').value = String(config.density);
    $('density-value').value = String(config.density); $('field-count').textContent = fields.length;
    renderFields(); render();
  }
  function renderFields() {
    const container = $('fields'); container.replaceChildren();
    config.columns.forEach((col, index) => {
      const item = el('div', undefined, 'field');
      const line = el('div', undefined, 'field-line');
      const toggle = el('input'); toggle.type = 'checkbox'; toggle.checked = col.visible; toggle.setAttribute('aria-label', `显示 ${col.field}`);
      toggle.onchange = () => { col.visible = toggle.checked; render(); };
      const label = el('input'); label.type = 'text'; label.value = col.label; label.maxLength = 80; label.setAttribute('aria-label', `${col.field} 的显示名称`);
      label.onchange = () => { col.label = label.value; render(); };
      line.append(toggle, label); item.append(line, el('code', col.field));
      const opts = el('div', undefined, 'field-options'); const format = el('select'); format.setAttribute('aria-label', `${col.field} 的格式`);
      FORMATS.forEach((value, i) => { const option = el('option', ['自动', '文本', '数字', '标签', 'JSON'][i]); option.value = value; format.append(option); });
      format.value = col.format; format.onchange = () => { col.format = format.value; render(); };
      const width = el('input'); width.type = 'number'; width.min = 90; width.max = 480; width.value = col.width; width.setAttribute('aria-label', `${col.field} 的列宽`);
      width.onchange = () => { col.width = number(width.value, 90, 480, 180); width.value = col.width; render(); };
      opts.append(format, width);
      [-1, 1].forEach(direction => {
        const button = el('button', direction < 0 ? '↑' : '↓'); button.type = 'button';
        button.setAttribute('aria-label', `${direction < 0 ? '上移' : '下移'} ${col.field}`);
        const dest = index + direction; button.disabled = dest < 0 || dest >= config.columns.length;
        button.onclick = () => { [config.columns[index], config.columns[dest]] = [config.columns[dest], config.columns[index]]; renderFields(); render(); };
        opts.append(button);
      });
      item.append(opts); container.append(item);
    });
  }
  function cell(value, col) {
    const node = el('span', undefined, 'cell-value');
    if (value === null || value === undefined) { node.textContent = text(value); node.classList.add('null'); return node; }
    if (col.format === 'number' && typeof value === 'number' && Number.isFinite(value)) node.textContent = new Intl.NumberFormat(undefined, { maximumSignificantDigits: 15 }).format(value);
    else if (col.format === 'json') node.textContent = JSON.stringify(value, null, 2);
    else node.textContent = text(value);
    if (col.format === 'badge') node.classList.add('badge');
    return node;
  }
  function tree(value, key, depth = 0) {
    if (value !== null && typeof value === 'object' && depth < 8) {
      const node = el('details');
      const entries = Object.entries(value);
      node.append(el('summary', `${key} ${Array.isArray(value) ? '[' : '{'} ${entries.length} ${Array.isArray(value) ? ']' : '}'}`));
      let cursor = 0;
      const more = el('button', '展开后续 100 项'); more.type = 'button';
      const appendBatch = () => {
        more.remove();
        const end = Math.min(cursor + 100, entries.length);
        for (; cursor < end; cursor++) {
          const [name, child] = entries[cursor]; node.append(tree(child, name, depth + 1));
        }
        if (cursor < entries.length) node.append(more);
      };
      more.onclick = event => { event.preventDefault(); appendBatch(); };
      node.addEventListener('toggle', () => { if (node.open && !cursor) appendBatch(); });
      node.open = depth < Math.min(config.detail, 2);
      return node;
    }
    return el('div', `${key}: ${text(value)}`, 'leaf');
  }
  function inspect(row) {
    if (!guard()) return;
    $('record-content').replaceChildren(tree(row, 'record'));
    $('record-dialog').showModal();
  }
  function recordButton(row, index) {
    const button = el('button', `#${index + 1} ↗`, 'record-button'); button.type = 'button';
    button.setAttribute('aria-label', `查看第 ${index + 1} 条记录详情`); button.onclick = () => inspect(row); return button;
  }
  function render() {
    if (!guard()) return;
    document.documentElement.style.setProperty('--cell-pad', `${14 - config.density / 10}px`);
    document.documentElement.style.setProperty('--card-gap', `${24 - config.density * .16}px`);
    $('density-value').value = String(config.density);
    const cols = visible(config), query = $('search').value.trim().toLocaleLowerCase();
    const filtered = rows.map((row, index) => ({ row, index })).filter(({ row }) => !query || Object.values(row).some(v => text(v).toLocaleLowerCase().includes(query)));
    const size = Number($('page-size').value), count = Math.ceil(filtered.length / size);
    page = Math.min(Math.max(0, page), Math.max(0, count - 1));
    const slice = filtered.slice(page * size, (page + 1) * size);
    $('stats').textContent = `已载入 ${rows.length} 条 · ${fields.length} 字段 · 展示 ${cols.length} 字段`;
    $('page-info').textContent = `${count ? page + 1 : 0} / ${count} · 匹配 ${filtered.length} 条`;
    $('previous').disabled = page <= 0; $('next').disabled = !count || page >= count - 1;
    const canvas = $('canvas'); canvas.replaceChildren();
    if (!rows.length) { canvas.append(el('div', '没有记录。空结果不等于完整数据库没有数据。', 'empty')); return; }
    if (config.view === 'schema') {
      const table = el('table', undefined, 'schema'); const head = el('thead'); const tr = el('tr');
      ['原字段', '显示名称', '已载入样本类型', '存在 / 非 null'].forEach(v => tr.append(el('th', v))); head.append(tr); table.append(head);
      const body = el('tbody');
      config.columns.forEach(col => {
        const row = el('tr'); const present = rows.filter(r => own(r, col.field));
        [col.field, col.label, [...new Set(present.map(r => type(r[col.field])))].join(' / '), `${present.length} / ${present.filter(r => r[col.field] !== null).length}`].forEach(v => row.append(el('td', v)));
        body.append(row);
      }); table.append(body); canvas.append(table); return;
    }
    if (!slice.length) { canvas.append(el('div', '已载入数据中没有匹配记录。', 'empty')); return; }
    if (config.view === 'table') {
      const table = el('table'); const group = el('colgroup');
      [90, ...cols.map(c => c.width)].forEach(width => { const col = el('col'); col.style.width = `${width}px`; group.append(col); }); table.append(group);
      const head = el('thead'), tr = el('tr'); tr.append(el('th', '记录详情'));
      cols.forEach(col => { const th = el('th', col.label); if (col.label !== col.field) th.append(el('small', col.field)); tr.append(th); }); head.append(tr); table.append(head);
      const body = el('tbody'); slice.forEach(({ row, index }) => { const tr = el('tr'), link = el('td'); link.append(recordButton(row, index)); tr.append(link); cols.forEach(col => { const td = el('td'); td.append(cell(row[col.field], col)); tr.append(td); }); body.append(tr); }); table.append(body); canvas.append(table);
    } else if (config.view === 'cards') {
      const cards = el('div', undefined, 'cards'); slice.forEach(({ row, index }) => { const card = el('article', undefined, 'record-card'); card.append(recordButton(row, index)); const dl = el('dl'); cols.forEach(col => { const dd = el('dd'); dd.append(cell(row[col.field], col)); dl.append(el('dt', col.label), dd); }); card.append(dl); cards.append(card); }); canvas.append(cards);
    } else {
      const wrap = el('div', undefined, 'tree'); slice.forEach(({ row, index }) => { const box = el('div'); box.append(recordButton(row, index), tree(project(row, cols), `record ${index + 1}`)); wrap.append(box); }); canvas.append(wrap);
    }
  }
  function renderPresets() {
    const select = $('presets'); select.replaceChildren(el('option', '选择已保存设计')); select.firstChild.value = '';
    presets.forEach((preset, i) => { const opt = el('option', preset.name); opt.value = String(i); select.append(opt); });
  }
  async function boundedJSON(response) {
    if (response.status === 401) throw new Error('登录已失效，请返回系统登录后重新载入。');
    if (response.status === 403) throw new Error('当前身份没有读取该数据的权限。');
    if (!response.ok) throw new Error(`数据读取失败（HTTP ${response.status}）。`);
    if (!(response.headers.get('content-type') || '').includes('json')) throw new Error('没有收到 JSON；请通过 2.1 后端打开本页，而不是静态开发服务器。');
    if (Number(response.headers.get('content-length')) > MAX_BYTES) throw new Error('响应超过 2 MiB，请使用较小数据集。');
    const reader = response.body.getReader(); let total = 0, parts = []; const decoder = new TextDecoder();
    try { while (true) { const { done, value } = await reader.read(); if (done) break; total += value.byteLength; if (total > MAX_BYTES) throw new Error('响应超过 2 MiB，请使用较小数据集。'); parts.push(decoder.decode(value, { stream: true })); } parts.push(decoder.decode()); }
    finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
    return parse(parts.join(''));
  }
  async function loadRemote() {
    const key = $('source').value;
    if (key === 'local') { $('data-file').click(); return; }
    clearData('正在读取授权范围内的数据…');
    const captured = session();
    if (!captured.token || !captured.tenant) { message('请先在同源 Warehouse 2.1 系统登录并选择公司。', true); return; }
    const current = generation; abort = new AbortController(); const signal = abort.signal;
    $('load').disabled = true;
    const headers = { Authorization: `Bearer ${captured.token}`, 'X-Tenant-Slug': captured.tenant, Accept: 'application/json' };
    const request = path => fetch(path, { method: 'GET', headers, signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error' }).then(boundedJSON);
    try {
      const auth = await request('/api/auth/me');
      const payload = await request(key === 'tasks' ? '/api/tasks?scope=mine' : '/api/account/profile');
      if (generation !== current || !sameSession(captured, session())) return;
      accept(payload, key, key === 'tasks' ? '我的任务 · 授权 API 投影' : '我的资料 · 授权 API 投影');
      activeSession = captured;
      const user = auth.user || auth;
      $('identity').textContent = `${user.display_name || user.username || '已验证身份'} · ${captured.tenant}`;
      message('数据只读。显示的是本次 API 返回记录，不是物理数据库完整字段或全库总量。');
    } catch (error) { if (generation === current && error.name !== 'AbortError') message(error.message, true); }
    finally { if (generation === current) { $('load').disabled = false; abort = null; } }
  }
  function loadLocal(value, label) {
    normalize(value); // Validate first; a rejected local import must keep remote-session protection.
    cancel(); activeSession = null; $('source').value = 'local'; accept(value, `local:${label}`, label);
    $('identity').textContent = '本地 JSON · 未上传'; message('数据仅存在当前页面内存；刷新页面会清除记录。');
  }
  async function readFile(input, callback, maxBytes = MAX_BYTES) {
    const file = input.files[0]; if (!file) return;
    const current = generation;
    try { if (file.size > maxBytes) throw new Error('文件过大。'); const value = parse(await file.text()); if (current === generation) callback(value, file.name); }
    catch (error) { message(error.message, true); } finally { input.value = ''; }
  }
  $('load').onclick = loadRemote;
  $('source').onchange = () => clearData('数据来源已切换，请载入。');
  $('paste').onclick = () => { $('paste-error').textContent = ''; $('paste-dialog').showModal(); };
  $('apply-json').onclick = () => { try { loadLocal(parse($('json-input').value), '粘贴的 JSON'); $('json-input').value = ''; $('paste-dialog').close(); } catch (error) { $('paste-error').textContent = error.message; } };
  $('data-file').onchange = () => readFile($('data-file'), loadLocal);
  $('view').onchange = () => { config.view = $('view').value; render(); };
  $('detail').onchange = () => { config.detail = Number($('detail').value); render(); };
  $('density').oninput = () => { config.density = Number($('density').value); render(); };
  $('search').oninput = () => { page = 0; render(); };
  $('page-size').onchange = () => { page = 0; render(); };
  $('previous').onclick = () => { page--; render(); };
  $('next').onclick = () => { page++; render(); };
  $('reset').onclick = () => { config = defaults(fields); sync(); };
  $('save').onclick = () => {
    if (!guard()) return;
    const name = $('preset-name').value.trim(); if (!name) { message('请先填写视图名称。', true); return; }
    if (presets.length >= 30) { message('当前页面最多保存 30 个命名视图。', true); return; }
    presets.push({ name, config: validate(config, fields) }); renderPresets(); message(`已在当前页面保存「${name}」。需要保留到下次，请下载样式 JSON。`);
  };
  $('presets').onchange = () => { if ($('presets').value === '' || !guard()) return; config = validate(presets[Number($('presets').value)].config, fields); sync(); };
  $('export').onclick = () => {
    if (!guard()) return;
    const blob = new Blob([JSON.stringify(validate(config, fields), null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob), a = el('a'); a.href = url; a.download = 'db-studio-view.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    message('已下载样式；文件不含记录、数据来源地址或登录凭证。');
  };
  $('style-file').onchange = () => readFile($('style-file'), value => { if (!guard()) return; config = validate(value, fields); sync(); message('已应用兼容字段样式；不存在的字段已忽略，新字段保留默认设置。'); }, 128 * 1024);
  document.querySelectorAll('[data-close]').forEach(button => { button.onclick = () => $(button.dataset.close).close(); });
  window.addEventListener('storage', guard); window.addEventListener('focus', guard);
  const guardTimer = window.setInterval(guard, 1000);
  window.addEventListener('pagehide', () => { cancel(); activeSession = null; rows = []; fields = []; presets = []; $('canvas').replaceChildren(); $('record-content').replaceChildren(); $('json-input').value = ''; window.clearInterval(guardTimer); });
  window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
  sync();
})(typeof window === 'object' ? window : globalThis);
