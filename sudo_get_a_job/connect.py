"""Find the user's real browser. Never fall back to whatever happens to answer on :9222."""

import os
import platform
import socket
from pathlib import Path

HOWTO = """No browser with remote debugging found.
  1. Open Chrome and go to chrome://inspect/#remote-debugging
  2. Enable "Allow remote debugging for this browser instance"
  3. Run the command again and click "Allow" if Chrome asks.
(Advanced: set SGAJ_CDP_WS=ws://127.0.0.1:PORT/devtools/browser/ID to pick a browser explicitly.)"""

_PROFILES = {
    "Windows": ["Google/Chrome/User Data", "Google/Chrome Beta/User Data", "Microsoft/Edge/User Data",
                "BraveSoftware/Brave-Browser/User Data", "Chromium/User Data"],
    "Darwin": ["Library/Application Support/Google/Chrome", "Library/Application Support/Google/Chrome Beta",
               "Library/Application Support/Microsoft Edge", "Library/Application Support/BraveSoftware/Brave-Browser",
               "Library/Application Support/Chromium"],
    "Linux": [".config/google-chrome", ".config/google-chrome-beta", ".config/microsoft-edge",
              ".config/BraveSoftware/Brave-Browser", ".config/chromium"],
}


def profile_dirs(system=None):
    system = system or platform.system()
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") if system == "Windows" else Path.home()
    return [base / p for p in _PROFILES.get(system, _PROFILES["Linux"])]


def listening(port):
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=0.5).close()
        return True
    except (OSError, ValueError):
        return False


def find_ws(dirs=None):
    """Browser websocket URL from SGAJ_CDP_WS or the first live real-profile DevToolsActivePort."""
    if url := os.environ.get("SGAJ_CDP_WS"):
        return url
    for d in profile_dirs() if dirs is None else dirs:
        try:
            port, path = (Path(d) / "DevToolsActivePort").read_text().split()[:2]
        except (OSError, ValueError):
            continue
        if listening(port):
            return f"ws://127.0.0.1:{port}{path}"
    raise SystemExit(HOWTO)


def connect():
    """Start (or reuse) a Browser Harness daemon bound to the real browser. Returns the cdp() helper."""
    ws = find_ws()
    # One daemon per browser endpoint, so a daemon attached to another app is never reused.
    os.environ["BU_NAME"] = "sgaj_" + ws.split(":")[2].split("/")[0]
    os.environ["BU_CDP_WS"] = ws
    from browser_harness.admin import ensure_daemon
    from browser_harness.helpers import cdp

    ensure_daemon(name=os.environ["BU_NAME"], env={"BU_CDP_WS": ws})
    return cdp
