"""Agent eval: a real coding agent, given only the skill, completes the fixture application.

    uv run python evals/agent_eval.py [--model MODEL]

Runs Claude Code headless (`claude -p`) with the skill installed in a temp project, a fictional
persona's profile and a throwaway headless Chrome. Local fixture only; nothing real is submitted.
Uses your Claude Code subscription, so it is not part of CI.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome import headless  # noqa: E402

from sudo_get_a_job import tracker  # noqa: E402
from sudo_get_a_job.browser import Tab  # noqa: E402
from sudo_get_a_job.install import install_skill  # noqa: E402

HERE = Path(__file__).parent
EXPECTED = {
    "fn": "Asha", "ln": "Verma", "em": "asha.verma@example.com", "ph": "+91 98765 43210",
    "loc": "Lucknow, Uttar Pradesh, India", "cv": "resume.pdf", "li": "https://linkedin.com/in/asha-verma-example",
    "gh": "https://github.com/asha-verma-example", "yoe": "1-2", "auth": "yes", "spon": "no", "np": "30 days",
    "ctc": "18", "gender": "Decline to self-identify", "vet": False, "pronouns": "she/her", "consent": True,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not shutil.which("claude"):
        raise SystemExit("Claude Code CLI not found")
    root = Path(tempfile.mkdtemp(prefix="sgaj-agent-eval-"))
    workspace, project = root / "job-hunt", root / "project"
    (workspace / "resume").mkdir(parents=True)
    shutil.copy(HERE / "fixtures" / "resume.pdf", workspace / "resume" / "resume.pdf")
    profile = (HERE / "agent" / "profile.md").read_text(encoding="utf-8")
    (workspace / "profile.md").write_text(profile.replace("<workspace>", workspace.as_posix()), encoding="utf-8")
    install_skill([project / ".claude" / "skills" / "sudo-get-a-job"])
    url = (HERE / "fixtures" / "apply.html").resolve().as_uri()

    with headless():
        env = {**os.environ, "SGAJ_WORKSPACE": str(workspace),
               "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]}  # sgaj from this venv
        cmd = ["claude", "-p", f"Use the sudo-get-a-job skill to apply to this job: {url}",
               "--output-format", "json", "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,Skill",
               "--max-turns", "80"] + (["--model", args.model] if args.model else [])
        started = time.perf_counter()
        run = subprocess.run(cmd, cwd=project, env=env, capture_output=True, text=True, encoding="utf-8")
        seconds = time.perf_counter() - started
        try:
            report = json.loads(run.stdout)
        except ValueError:
            raise SystemExit(f"claude failed:\n{run.stdout[-2000:]}\n{run.stderr[-2000:]}")
        tab = Tab.current()
        result = tab.evaluate("window.__result") or {}
        tab.detach()

    os.environ["SGAJ_WORKSPACE"] = str(workspace)
    rows = tracker.rows()
    checks = {k: result.get(k) == v for k, v in EXPECTED.items()}
    checks["why (non-empty)"] = bool(result.get("why"))
    checks["tracked once"] = len(rows) == 1 and rows[0]["Status"] == "applied" and "Acme" in rows[0]["Company"]
    for name, ok in checks.items():
        got = result.get(name, rows[0] if name == "tracked once" and rows else None)
        print(f"{'PASS' if ok else 'FAIL'}  {name:<18} {'' if ok else repr(got)}")
    usage = report.get("usage", {})
    tokens = sum(usage.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
                                           "output_tokens"))
    print(f"\n{sum(checks.values())}/{len(checks)} checks | {report.get('num_turns')} turns | {seconds:.0f}s | "
          f"${report.get('total_cost_usd', 0):.2f}")
    print(f"tokens: {tokens:,} = cache read {usage.get('cache_read_input_tokens', 0):,} + cache write "
          f"{usage.get('cache_creation_input_tokens', 0):,} + input {usage.get('input_tokens', 0):,} + output "
          f"{usage.get('output_tokens', 0):,}")
    print("agent's final message:", (report.get("result") or "")[:600])
    shutil.rmtree(root, ignore_errors=True)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
