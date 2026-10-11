"""Throwaway headless Chrome for evals. Never touches the user's browser or profile."""

import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager, suppress
from pathlib import Path

CANDIDATES = [
    os.environ.get("CHROME_PATH"),
    shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("chrome"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


@contextmanager
def headless():
    chrome = next((c for c in CANDIDATES if c and Path(c).exists()), None)
    if not chrome:
        raise SystemExit("Chrome not found. Set CHROME_PATH.")
    profile = Path(tempfile.mkdtemp(prefix="sgaj-eval-"))
    proc = subprocess.Popen(
        [chrome, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={profile}", "--no-first-run",
         "--no-default-browser-check", "--window-size=1280,800", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    port_file = profile / "DevToolsActivePort"
    deadline = time.monotonic() + 20
    while not port_file.exists() or len(port_file.read_text().split()) < 2:
        if time.monotonic() > deadline:
            proc.kill()
            raise SystemExit("Headless Chrome did not start")
        time.sleep(0.1)
    port, path = port_file.read_text().split()[:2]
    os.environ["SGAJ_CDP_WS"] = f"ws://127.0.0.1:{port}{path}"
    os.environ["SGAJ_HOME"] = str(profile)
    try:
        yield
    finally:
        from browser_harness.admin import restart_daemon

        with suppress(OSError):  # Windows can hold the port file briefly; the daemon is gone either way
            restart_daemon(f"sgaj_{port}")
        proc.kill()
        proc.wait()
        shutil.rmtree(profile, ignore_errors=True)
