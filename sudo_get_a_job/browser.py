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

KEYS = {"Enter": 13, "Tab": 9, "Escape": 27, "Backspace": 8, "ArrowDown": 40, "ArrowUp": 38, "Space": 32}


class Tab:
    def __init__(self, target):
        self.target = target
        self.session = cdp("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
        # Keep timers/animations running even when the user is looking at another tab.
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)

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
