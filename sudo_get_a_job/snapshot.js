(() => {
  if (!document.body) return null;
  // Stable identity per DOM node: the number the agent sees is the node, across look calls.
  const cache = window.__jevFast ||= {ids: new WeakMap(), nodes: new Map(), next: 1};
  const identity = e => {
    if (!cache.ids.has(e)) cache.ids.set(e, cache.next++);
    const id = cache.ids.get(e); cache.nodes.set(id, e); return id;
  };
  for (const [id, e] of cache.nodes) if (!e.isConnected) cache.nodes.delete(id);
  // Every tree we can read: the document, open shadow roots and same-origin frames, recursively.
  // Cross-origin frames can't be read; they are reported so the agent knows something is there.
  const roots = [], frames = [];
  const collect = root => {
    roots.push(root);
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) collect(el.shadowRoot);
      if (el.tagName !== 'IFRAME' && el.tagName !== 'FRAME') continue;
      if (!el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) continue;
      let doc = null;
      try { doc = el.contentDocument; } catch {}
      if (doc?.body) collect(doc);
      else {
        const r = el.getBoundingClientRect();
        if (r.width * r.height > 2000) frames.push({src: el.src || el.getAttribute('src') || '', w: r.width, h: r.height});
      }
    }
  };
  collect(document);
  // Element rect in top-window coordinates, through any frames it lives in.
  const topRect = e => {
    const r = e.getBoundingClientRect();
    let x = r.x, y = r.y;
    for (let w = e.ownerDocument.defaultView; w.frameElement; w = w.parent) {
      const f = w.frameElement.getBoundingClientRect();
      x += f.x + w.frameElement.clientLeft;
      y += f.y + w.frameElement.clientTop;
    }
    return {width: r.width, height: r.height, left: x, top: y, right: x + r.width, bottom: y + r.height};
  };
  const byId = (e, id) => e.getRootNode().getElementById?.(id) || document.getElementById(id);
  const safe = e => !['password', 'hidden'].includes(e.type);
  const visible = e => !e.closest('[aria-hidden="true"],[inert]') &&
    e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});
  const name = (e, seen = new Set()) => {
    if (!e || seen.has(e)) return '';
    seen.add(e);
    const referenced = (e.getAttribute('aria-labelledby') || '').split(/\s+/)
      .map(id => name(byId(e, id), seen)).filter(Boolean).join(' ');
    return referenced || e.getAttribute('aria-label') ||
      [...(e.labels || [])].map(l => name(l, seen)).filter(Boolean).join(' ') ||
      (['button', 'submit', 'reset'].includes(e.type) ? e.value : '') || e.getAttribute('alt') ||
      (e.tagName === 'INPUT' ? '' : [...e.childNodes].map(n => n.nodeType === 3 ? n.textContent :
        n.nodeType === 1 && n.getAttribute('aria-hidden') !== 'true' ? name(n, seen) : '').join(' ').trim()) ||
      e.getAttribute('title') || e.getAttribute('placeholder') || '';
  };
  // File inputs are usually visually hidden behind a styled button; name them from their field.
  const fieldText = e => {
    for (let p = e.parentElement, i = 0; p && i < 4; p = p.parentElement, i++) {
      const t = p.innerText?.trim().split(/\n/)[0];
      if (t) return t;
    }
    return '';
  };
  // The question a radio/checkbox answers: legend, ARIA group name, or the text heading its option group.
  const question = e => {
    const legend = e.closest('fieldset')?.querySelector('legend');
    if (legend) return legend.innerText.trim();
    const group = e.closest('[role="radiogroup"],[role="group"]');
    const groupName = group && name(group, new Set([...group.querySelectorAll('*')]));
    if (groupName) return groupName;
    if (!e.name) return '';
    const options = [...e.getRootNode().querySelectorAll('input')].filter(x => x.name === e.name && x.type === e.type);
    let box = e.parentElement;
    while (box && !options.every(x => box.contains(x))) box = box.parentElement;
    // Grow until the box also holds the question text, but never across another option group.
    const labels = new Set(options.map(x => name(x).trim()));
    for (let i = 0; box && i < 4; box = box.parentElement, i++) {
      if ([...box.querySelectorAll('input[type=radio],input[type=checkbox]')].some(x => x.name !== e.name)) break;
      const line = box.innerText.split(/\n/).map(s => s.trim()).find(s => s && !labels.has(s));
      if (line) return line;
    }
    return '';
  };
  const roles = ['button', 'link', 'checkbox', 'radio', 'switch', 'tab', 'menuitem', 'menuitemradio',
    'option', 'gridcell', 'combobox', 'textbox', 'searchbox', 'spinbutton'];
  const formRoles = ['file', 'checkbox', 'radio', 'switch', 'combobox', 'textbox', 'searchbox', 'spinbutton'];
  const selector = 'a[href],button,input,textarea,select,summary,[contenteditable="true"],' +
    roles.map(role => '[role="' + role + '"]').join(',');
  const role = e => {
    const explicit = e.getAttribute('role');
    if (roles.includes(explicit)) return explicit;
    if (e.tagName === 'BUTTON' || e.tagName === 'SUMMARY') return 'button';
    if (e.tagName === 'A') return 'link';
    if (e.tagName === 'SELECT') return 'combobox';
    if (e.tagName === 'TEXTAREA' || e.isContentEditable) return 'textbox';
    if (e.tagName === 'INPUT') {
      if (e.type === 'file') return 'file';
      if (['checkbox', 'radio'].includes(e.type)) return e.type;
      if (['button', 'submit', 'reset', 'image'].includes(e.type)) return 'button';
      if (e.type === 'search') return 'searchbox';
      if (e.type === 'number') return 'spinbutton';
      return 'textbox';
    }
    return null;
  };
  const actions = [];
  for (const e of roots.flatMap(root => [...root.querySelectorAll(selector)])) {
    const file = e.type === 'file';
    if (!safe(e) || !visible(file ? e.parentElement : e) || e.matches(':disabled') ||
        e.closest('[aria-disabled="true"]')) continue;
    const r = topRect(file ? e.parentElement : e), rname = role(e);
    if (!rname || r.width <= 0 || r.height <= 0) continue;
    // Form controls are listed wherever they are; acting scrolls them into view.
    // Other links/buttons only when on screen or inside a form/dialog, to keep output small.
    const onScreen = r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
    if (!onScreen && !formRoles.includes(rname) && !e.closest('form,dialog,[role="dialog"],[role="form"]')) continue;
    if (rname === 'gridcell' && e.querySelector('button,[role="button"]')) continue;
    const base = {node: identity(e), role: rname, label: name(e) || (file && fieldText(e)) || rname};
    if (file) {
      actions.push({...base, kind: 'upload', value: [...e.files].map(f => f.name).join(', ') || '(none)'});
      continue;
    }
    for (const key of ['checked', 'selected', 'expanded']) {
      const value = e.getAttribute('aria-' + key);
      if (value !== null) base[key] = value;
    }
    if (['checkbox', 'radio'].includes(e.type)) {
      base.checked = String(e.checked);
      if (base.label === rname && e.value && e.value !== 'on') base.label = e.value;
      const q = question(e);
      if (q && q !== base.label) base.question = q;
    }
    if (e.tagName === 'SELECT') {
      for (const o of e.options) if (!o.selected && !o.disabled && !o.closest('optgroup[disabled]'))
        actions.push({...base, kind: 'select', value: o.value,
          current_value: [...e.selectedOptions].map(o => o.label).join(', '), label: base.label + ' → ' + o.label});
    } else {
      const editable = !e.readOnly && e.getAttribute('aria-readonly') !== 'true' &&
        (['textbox', 'searchbox', 'spinbutton'].includes(rname) ||
          (rname === 'combobox' && ['INPUT', 'TEXTAREA'].includes(e.tagName)));
      // Button-style dropdowns show their choice as text; React-Select keeps it beside an empty input.
      const popup = ['listbox', 'true', 'menu', 'dialog'].includes(e.getAttribute('aria-haspopup'));
      if (popup && rname === 'button') base.role = 'combobox';
      let value = 'value' in e && e.tagName !== 'BUTTON' ? String(e.value) :
        e.isContentEditable || base.role === 'combobox' ? e.innerText.trim() : '';
      if (rname === 'combobox' && e.tagName === 'INPUT' && !value)
        value = e.closest('[class*="control"]')?.innerText.trim() || '';
      actions.push({...base, kind: editable ? 'fill' : 'click', value});
    }
  }
  const height = document.documentElement.scrollHeight;
  const omitted_actions = Math.max(0, actions.length - 250);
  actions.splice(250);
  return {url: location.href, title: document.title, h: innerHeight, scroll: {y: Math.round(scrollY), height},
    actions, omitted_actions, frames};
})()
