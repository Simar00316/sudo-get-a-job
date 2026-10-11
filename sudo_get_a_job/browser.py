"""One persistent tab, observed through snapshot.js and driven by observed element ids."""

import json
import os
import sys
import time
from pathlib import Path

from .connect import connect

SNAPSHOT = Path(__file__).with_name("snapshot.js").read_text(encoding="utf-8")
_cdp = None


def cdp(method, **params):
    global _cdp
    _cdp = _cdp or connect()
    return _cdp(method, **params)


def state_file():
    return Path(os.environ.get("SGAJ_HOME") or Path.home() / ".sudo-get-a-job") / "tab.json"


class ActionError(RuntimeError):
    """The requested action could not run. Nothing was changed."""


# Resolve an observed node, refuse anything the user couldn't interact with, return its click point.
RESOLVE = """(node => {
  const e = window.__jevFast?.nodes.get(node);
  if (!e?.isConnected) return {error: `Element [${node}] is gone. Run look again.`};
  if (e.matches(':disabled') || e.closest('[aria-disabled="true"],[inert]'))
    return {error: `Element [${node}] is disabled.`};
  if (!e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}))
    return {error: `Element [${node}] is hidden.`};
  let r = e.getBoundingClientRect();
  if (r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth) {
    e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
    r = e.getBoundingClientRect();
  }
  const x = r.x + r.width / 2, y = r.y + r.height / 2;
  if (!r.width || !r.height || x < 0 || y < 0 || x >= innerWidth || y >= innerHeight)
    return {error: `Element [${node}] could not be scrolled into view.`};
  const hit = document.elementFromPoint(x, y);
  if (!e.contains(hit) && !hit?.contains(e)) return {error: `Element [${node}] is covered by another element.`};
  return {x, y, tag: e.tagName, readOnly: !!e.readOnly};
})"""

SELECT = """((node, want) => {
  const e = window.__jevFast.nodes.get(node), norm = s => s.trim().toLowerCase();
  if (e.tagName !== 'SELECT') return {error: `Element [${node}] is not a dropdown. Click it instead.`};
  const usable = [...e.options].filter(o => !o.disabled && !o.closest('optgroup[disabled]'));
  const o = usable.find(o => norm(o.label) === norm(want) || norm(o.value) === norm(want));
  if (!o) return {error: `No option "${want}". Options: ${usable.map(o => o.label).join(' | ')}`};
  e.value = o.value;
  e.dispatchEvent(new Event('input', {bubbles: true}));
  e.dispatchEvent(new Event('change', {bubbles: true}));
  return {selected: o.label};
})"""

# The file input that belongs to an observed node: the node itself, or the single one in its field.
FILE_INPUT = """(node => {
  const e = window.__jevFast?.nodes.get(node);
  if (!e?.isConnected) return null;
  if (e.type === 'file') return e;
  for (let p = e.parentElement, i = 0; p && i < 5; p = p.parentElement, i++) {
    const found = p.querySelectorAll('input[type=file]');
    if (found.length) return found.length === 1 ? found[0] : null;
  }
  return null;
})"""

# Clicking these opens the OS file dialog, which no automation can drive.
FILE_TRIGGER = """(node => {
  const e = window.__jevFast?.nodes.get(node), f = (""" + FILE_INPUT + """)(node);
  if (!f) return null;
  const trigger = e === f || e.control === f ||
    /upload|attach|browse|choose file|select file|drop/i.test(e.innerText || e.value || '');
  return trigger ? (window.__jevFast.ids.get(f) ?? node) : null;
})"""

# Visible options for an opened dropdown/autocomplete, registered so they can be clicked by id.
OPTIONS = """(node => {
  const c = window.__jevFast, e = c.nodes.get(node);
  const ids = (e?.getAttribute('aria-controls') || e?.getAttribute('aria-owns') || '').split(/\\s+/).filter(Boolean);
  const roots = ids.map(id => document.getElementById(id)).filter(Boolean);
  const found = (roots.length ? roots : [document]).flatMap(r => [...r.querySelectorAll('[role=option]')]);
  return found.filter(o => o.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) &&
      o.getAttribute('aria-disabled') !== 'true' && o.getBoundingClientRect().height > 0)
    .map(o => {
      if (!c.ids.has(o)) c.ids.set(o, c.next++);
      c.nodes.set(c.ids.get(o), o);
      return {id: c.ids.get(o), text: o.innerText.trim()};
    });
})"""


def best_option(options, want):
    """Exact, then prefix, then substring match (case-insensitive). Ties keep the site's order."""
    want = " ".join(want.split()).casefold()
    for test in (lambda t: t == want, lambda t: t.startswith(want), lambda t: want in t):
        for o in options:
            if test(" ".join(o["text"].split()).casefold()):
                return o
    return None


KEYS = {"Enter": 13, "Tab": 9, "Escape": 27, "Backspace": 8, "ArrowDown": 40, "ArrowUp": 38, "Space": 32}


class Tab:
    def __init__(self, target):
        self.target = target
        self.session = cdp("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
        # Keep timers/animations running even when the user is looking at another tab.
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)
        # Backstop: never let a click open the native file dialog.
        self.call("Page.setInterceptFileChooserDialog", enabled=True)

    @classmethod
    def new(cls, url):
        target = cdp("Target.createTarget", url="about:blank")["targetId"]
        state_file().parent.mkdir(parents=True, exist_ok=True)
        state_file().write_text(json.dumps({"target": target}))
        tab = cls(target)
        tab.goto(url)
        return tab

    @classmethod
    def current(cls):
        try:
            target = json.loads(state_file().read_text())["target"]
        except (OSError, ValueError, KeyError):
            target = None
        if not any(t["targetId"] == target for t in cdp("Target.getTargets")["targetInfos"]):
            raise SystemExit("No open tab. Run: sgaj open URL")
        return cls(target)

    def call(self, method, **params):
        return cdp(method, session_id=self.session, **params)

    def evaluate(self, expression, await_promise=False):
        r = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=await_promise)
        if r.get("exceptionDetails"):
            raise ActionError("Page changed while reading it. Run look again.")
        return r.get("result", {}).get("value")

    def wait_ready(self, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self.evaluate("document.readyState") == "complete":
                    return
            except ActionError:
                pass
            time.sleep(0.1)

    def goto(self, url):
        self.call("Page.navigate", url=url)
        time.sleep(0.2)
        self.wait_ready()

    def snapshot(self):
        for _ in range(20):
            self.wait_ready()
            try:
                if state := self.evaluate(SNAPSHOT):
                    return state
            except ActionError:
                pass
            time.sleep(0.15)
        raise ActionError("Page did not settle. Try again.")

    def read(self, limit=12000):
        return self.evaluate(
            "(() => { const m = [...document.querySelectorAll('main,[role=main],article')]"
            ".find(e => e.innerText.length > 500); return (m || document.body).innerText; })()"
        )[:limit]

    def _resolve(self, node):
        if not str(node).isdigit():
            raise ActionError(f"Element must be a number from look, got {node!r}.")
        target = self.evaluate(f"{RESOLVE}({int(node)})")
        if target is None:
            raise ActionError("Run look first; this page has not been observed.")
        if "error" in target:
            raise ActionError(target["error"])
        return target

    def _mouse_click(self, x, y):
        for event in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=event, x=x, y=y, button="left", clickCount=1)

    def click(self, node):
        if str(node).isdigit() and (f := self.evaluate(f"{FILE_TRIGGER}({int(node)})")):
            raise ActionError(f"[{node}] opens a file picker. Use: sgaj upload {f} PATH")
        t = self._resolve(node)
        self._mouse_click(t["x"], t["y"])

    def fill(self, node, text):
        t = self._resolve(node)
        if t["readOnly"]:
            raise ActionError(f"Element [{node}] is read-only. Click it instead.")
        self._mouse_click(t["x"], t["y"])
        mod = 4 if sys.platform == "darwin" else 2
        self.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA", modifiers=mod, commands=["selectAll"])
        self.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA", modifiers=mod)
        self.call("Input.insertText", text=text)

    def select(self, node, option):
        self._resolve(node)
        r = self.evaluate(f"{SELECT}({int(node)}, {json.dumps(option)})")
        if "error" in r:
            raise ActionError(r["error"])
        return r["selected"]

    def pick(self, node, text, timeout=3.0):
        """Choose `text` in a native select, custom dropdown or autocomplete. Returns the chosen option."""
        t = self._resolve(node)
        if t["tag"] == "SELECT":
            return self.select(node, text)
        editable = t["tag"] in {"INPUT", "TEXTAREA"} and not t["readOnly"]
        self.fill(node, text) if editable else self.click(node)
        deadline = time.monotonic() + timeout
        options = []
        while time.monotonic() < deadline:
            time.sleep(0.1)
            options = self.evaluate(f"{OPTIONS}({int(node)})") or []
            if match := best_option(options, text):
                self.click(match["id"])
                return match["text"]
        if not editable:
            self.press("Escape")  # close the list we opened; nothing was chosen
        listed = " | ".join(o["text"] for o in options[:15])
        hint = f"Options: {listed}" if listed else "No options appeared."
        raise ActionError(f"No option matching {text!r}. {hint}")

    def upload(self, node, path):
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise ActionError(f"File not found: {path}")
        if not str(node).isdigit():
            raise ActionError(f"Element must be a number from look, got {node!r}.")
        r = self.call("Runtime.evaluate", expression=f"{FILE_INPUT}({int(node)})")
        object_id = r.get("result", {}).get("objectId")
        if not object_id:
            raise ActionError(f"Element [{node}] is not a file field or its upload button.")
        self.call("DOM.setFileInputFiles", files=[str(path)], objectId=object_id)
        names = self.call("Runtime.callFunctionOn", objectId=object_id, returnByValue=True,
                          functionDeclaration="function() { return [...this.files].map(f => f.name).join(', '); }")
        return names["result"]["value"]

    def press(self, key):
        if key not in KEYS:
            raise ActionError(f"Unsupported key {key!r}. Use one of: {', '.join(KEYS)}")
        params = dict(key=key, code=key, windowsVirtualKeyCode=KEYS[key])
        text = {"Enter": "\r", "Space": " "}.get(key)
        self.call("Input.dispatchKeyEvent", type="keyDown", **params, **({"text": text} if text else {}))
        self.call("Input.dispatchKeyEvent", type="keyUp", **params)

    def scroll(self, direction):
        self.evaluate(f"scrollBy(0, {1 if direction == 'down' else -1} * innerHeight * 0.8)")

    def back(self):
        self.evaluate("history.back()")
        time.sleep(0.3)
        self.wait_ready()

    def close(self):
        cdp("Target.closeTarget", targetId=self.target)
        state_file().unlink(missing_ok=True)

    def detach(self):
        try:
            cdp("Target.detachFromTarget", sessionId=self.session)
        except Exception:
            pass
