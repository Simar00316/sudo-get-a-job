(() => {
  if (!document.body) return null;
  // Stable identity per DOM node: the number the agent sees is the node, across look calls.
  const cache = window.__jevFast ||= {ids: new WeakMap(), nodes: new Map(), next: 1};
  const identity = e => {
    if (!cache.ids.has(e)) cache.ids.set(e, cache.next++);
    const id = cache.ids.get(e); cache.nodes.set(id, e); return id;
  };
  for (const [id, e] of cache.nodes) if (!e.isConnected) cache.nodes.delete(id);
  const safe = e => !['password', 'hidden'].includes(e.type);
  const visible = e => !e.closest('[aria-hidden="true"],[inert]') &&
    e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});
  const name = (e, seen = new Set()) => {
    if (!e || seen.has(e)) return '';
    seen.add(e);
    const referenced = (e.getAttribute('aria-labelledby') || '').split(/\s+/)
      .map(id => name(document.getElementById(id), seen)).filter(Boolean).join(' ');
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
  for (const e of document.querySelectorAll(selector)) {
    const file = e.type === 'file';
    if (!safe(e) || !visible(file ? e.parentElement : e) || e.matches(':disabled') ||
        e.closest('[aria-disabled="true"]')) continue;
    const r = file ? e.parentElement.getBoundingClientRect() : e.getBoundingClientRect(), rname = role(e);
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
    if (['checkbox', 'radio'].includes(e.type)) base.checked = String(e.checked);
    if (e.tagName === 'SELECT') {
      for (const o of e.options) if (!o.selected && !o.disabled && !o.closest('optgroup[disabled]'))
        actions.push({...base, kind: 'select', value: o.value,
          current_value: [...e.selectedOptions].map(o => o.label).join(', '), label: base.label + ' → ' + o.label});
    } else {
      const editable = !e.readOnly && e.getAttribute('aria-readonly') !== 'true' &&
        (['textbox', 'searchbox', 'spinbutton'].includes(rname) ||
          (rname === 'combobox' && ['INPUT', 'TEXTAREA'].includes(e.tagName)));
      const value = 'value' in e ? String(e.value) :
        e.isContentEditable || rname === 'combobox' ? e.innerText.trim() : '';
      actions.push({...base, kind: editable ? 'fill' : 'click', value});
    }
  }
  const height = document.documentElement.scrollHeight;
  const omitted_actions = Math.max(0, actions.length - 250);
  actions.splice(250);
  return {url: location.href, title: document.title, h: innerHeight, scroll: {y: Math.round(scrollY), height},
    actions, omitted_actions};
})()
