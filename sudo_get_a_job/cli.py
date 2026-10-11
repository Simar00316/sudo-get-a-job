"""sgaj: compact browser eyes and hands for coding agents. Run `sgaj --help`."""

import argparse
import json
import sys
import time

from .browser import ActionError, Tab


def clip(s, n=80):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def render(snap):
    """Element table the agent reads. One line per observed node; the number is the node's stable id."""
    lines = [f"{clip(snap['title'], 100)} — {snap['url']}"]
    y, height = snap["scroll"]["y"], snap["scroll"]["height"]
    lines.append(f"showing {y}-{y + snap['h']}px of {height}px")
    nodes = {}
    for a in snap["actions"]:
        if "node" in a:
            nodes.setdefault(a["node"], []).append(a)
    for node, acts in nodes.items():
        a = acts[0]
        kinds = {x["kind"] for x in acts}
        label = clip(a["label"].split(" → ")[0])
        role = "select" if "select" in kinds else a["role"]
        line = f"[{node}] {role} \"{label}\""
        if a.get("question"):
            line += f" in \"{clip(a['question'])}\""
        if "select" in kinds:
            options = [x["label"].split(" → ", 1)[1] for x in acts]
            line += f" = \"{clip(a.get('current_value', ''), 40)}\" options: {clip(' | '.join(options), 200)}"
        elif a.get("checked") is not None:
            line += " (on)" if a["checked"] == "true" else " (off)"
        elif kinds & {"fill", "upload"} or a["role"] == "combobox":
            line += f" = \"{clip(a.get('value', ''), 60)}\""
        if a.get("expanded") == "true":
            line += " (expanded)"
        if a.get("required") and a.get("empty"):
            line += " (required)"
        if a.get("invalid"):
            line += " (invalid)"
        lines.append(line)
    for f in snap.get("frames", []):
        lines.append(f"frame (cross-origin, not readable here): {clip(f['src'], 120)} -> sgaj goto it to fill")
    lines += footer(snap)
    if snap["omitted_actions"]:
        lines.append(f"… {snap['omitted_actions']} more elements not shown")
    if y + snap["h"] < height - 2:
        lines.append("more below: scroll down")
    return "\n".join(lines)


def footer(snap):
    lines = [f"alerts: {' | '.join(clip(a, 150) for a in snap['alerts'])}"] if snap.get("alerts") else []
    lines += [f"captcha: {c} (ask the user to solve it in the browser)" for c in snap.get("captchas", [])]
    return lines


def check(snap):
    """Empty required fields (radio groups once, by question), plus alerts and captchas."""
    missing, seen = [], set()
    for a in snap["actions"]:
        if not (a.get("required") and a.get("empty")) or a.get("node") in seen:
            continue
        seen.add(a["node"])
        if a["role"] == "radio" and a.get("question"):
            key = ("radio", a["question"])
            if key in seen:
                continue
            seen.add(key)
            missing.append(f"  [{a['node']}] radio group \"{clip(a['question'])}\"")
        else:
            role = "select" if a["kind"] == "select" else a["role"]
            missing.append(f"  [{a['node']}] {role} \"{clip(a['label'].split(' → ')[0])}\"")
    lines = ["missing required:", *missing] if missing else ["ok: all required fields filled"]
    return "\n".join(lines + footer(snap))


# name -> (argument names, handler). Shared by single commands and `do` batches.
ACTIONS = {
    "click": (["n"], lambda t, n: t.click(n)),
    "fill": (["n", "text"], lambda t, n, text: t.fill(n, text)),
    "select": (["n", "option"], lambda t, n, option: t.select(n, option)),
    "pick": (["n", "text"], lambda t, n, text: t.pick(n, text)),
    "upload": (["n", "path"], lambda t, n, path: t.upload(n, path)),
    "press": (["key"], lambda t, key: t.press(key)),
    "wait": (["seconds"], lambda t, seconds: time.sleep(min(float(seconds), 10))),
}


def act(tab, name, args):
    if name not in ACTIONS:
        raise ActionError(f"unknown action {name!r}. Use: {', '.join(ACTIONS)}")
    params, handler = ACTIONS[name]
    if len(args) != len(params):
        raise ActionError(f"{name} takes {' '.join(params).upper()}")
    result = handler(tab, *[str(a) for a in args])
    return f"ok: {result}" if isinstance(result, str) else "ok"


def batch(tab, raw):
    """Run [[action, *args], ...] in order; stop at the first error, then print a fresh look."""
    try:
        steps = json.loads(raw)
        assert isinstance(steps, list) and all(isinstance(s, list) and s for s in steps)
    except (ValueError, AssertionError):
        print('error: do expects JSON like [["fill", 12, "Simar"], ["click", 15]]')
        return 1
    code = 0
    for i, (name, *args) in enumerate(steps, 1):
        label = " ".join([str(name), *(str(a) for a in args[:1])])
        try:
            print(f"{i} {label}: {act(tab, name, args)}")
        except ActionError as e:
            print(f"{i} {label}: error: {e}")
            print(f"stopped; {len(steps) - i} action(s) not run")
            code = 1
            break
    print(render(tab.snapshot()))
    return code


def main(argv=None):
    p = argparse.ArgumentParser(prog="sgaj", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open", help="open URL in a new tab and remember it").add_argument("url")
    sub.add_parser("tabs", help="list open tabs; * marks the current one")
    a = sub.add_parser("attach", help="make an existing tab current: number from tabs, or text in its title/URL")
    a.add_argument("which")
    sub.add_parser("show", help="bring the current tab to the front (e.g. for the user to solve a captcha)")
    sub.add_parser("goto", help="navigate the current tab").add_argument("url")
    sub.add_parser("look", help="list interactive elements")
    sub.add_parser("check", help="list empty required fields, alerts and captchas before submitting")
    sub.add_parser("read", help="page text, e.g. a job description").add_argument("--max", type=int, default=12000)
    sub.add_parser("click", help="click element N").add_argument("n")
    f = sub.add_parser("fill", help="replace the text of field N")
    f.add_argument("n")
    f.add_argument("text")
    s = sub.add_parser("select", help="choose OPTION in native dropdown N")
    s.add_argument("n")
    s.add_argument("option")
    k = sub.add_parser("pick", help="choose TEXT in dropdown/autocomplete N (types, waits, clicks the match)")
    k.add_argument("n")
    k.add_argument("text")
    u = sub.add_parser("upload", help="attach a file to file field N (or its upload button)")
    u.add_argument("n")
    u.add_argument("path")
    d = sub.add_parser("do", help="""run several actions: '[["fill", 3, "Simar"], ["click", 9]]' or - for stdin""")
    d.add_argument("json")
    sub.add_parser("wait", help="wait SECONDS (max 10)").add_argument("seconds")
    sub.add_parser("press", help="press a key: Enter, Tab, Escape, ArrowDown, ...").add_argument("key")
    sub.add_parser("scroll", help="scroll the page").add_argument("direction", choices=["up", "down"])
    sub.add_parser("back", help="browser back")
    sub.add_parser("close", help="close the tab")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.cmd == "tabs":
        current = Tab.remembered()
        for i, t in enumerate(Tab.pages(), 1):
            print(f"{'*' if t['targetId'] == current else ' '} [{i}] {clip(t['title'], 70)} — {clip(t['url'], 90)}")
        return 0
    try:
        tab = {"open": lambda: Tab.new(args.url), "attach": lambda: Tab.attach(args.which)}.get(args.cmd, Tab.current)()
    except ActionError as e:
        print(f"error: {e}")
        return 1
    try:
        if args.cmd in {"open", "attach", "goto", "look", "back", "scroll"}:
            {"goto": lambda: tab.goto(args.url), "back": tab.back,
             "scroll": lambda: tab.scroll(args.direction)}.get(args.cmd, lambda: None)()
            print(render(tab.snapshot()))
        elif args.cmd == "check":
            print(check(tab.snapshot()))
        elif args.cmd == "read":
            print(tab.read(args.max))
        elif args.cmd == "do":
            return batch(tab, sys.stdin.read() if args.json == "-" else args.json)
        elif args.cmd == "show":
            tab.show()
            print("ok")
        elif args.cmd == "close":
            tab.close()
            print("ok")
        else:
            print(act(tab, args.cmd, [getattr(args, k) for k in ACTIONS[args.cmd][0]]))
    except ActionError as e:
        print(f"error: {e}")
        return 1
    finally:
        if args.cmd != "close":
            tab.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
