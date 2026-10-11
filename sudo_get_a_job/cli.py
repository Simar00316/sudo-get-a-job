"""sgaj: compact browser eyes and hands for coding agents. Run `sgaj --help`."""

import argparse
import sys

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
        lines.append(line)
    for f in snap.get("frames", []):
        lines.append(f"frame (cross-origin, not readable here): {clip(f['src'], 120)} -> sgaj goto it to fill")
    if snap["omitted_actions"]:
        lines.append(f"… {snap['omitted_actions']} more elements not shown")
    if y + snap["h"] < height - 2:
        lines.append("more below: scroll down")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="sgaj", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open", help="open URL in a new tab and remember it").add_argument("url")
    sub.add_parser("goto", help="navigate the current tab").add_argument("url")
    sub.add_parser("look", help="list interactive elements")
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
    sub.add_parser("press", help="press a key: Enter, Tab, Escape, ArrowDown, ...").add_argument("key")
    sub.add_parser("scroll", help="scroll the page").add_argument("direction", choices=["up", "down"])
    sub.add_parser("back", help="browser back")
    sub.add_parser("close", help="close the tab")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    tab = Tab.new(args.url) if args.cmd == "open" else Tab.current()
    try:
        if args.cmd in {"open", "goto", "look", "back", "scroll"}:
            {"goto": lambda: tab.goto(args.url), "back": tab.back,
             "scroll": lambda: tab.scroll(args.direction)}.get(args.cmd, lambda: None)()
            print(render(tab.snapshot()))
        elif args.cmd == "read":
            print(tab.read(args.max))
        elif args.cmd == "click":
            tab.click(args.n)
            print("ok")
        elif args.cmd == "fill":
            tab.fill(args.n, args.text)
            print("ok")
        elif args.cmd == "select":
            print(f"ok: {tab.select(args.n, args.option)}")
        elif args.cmd == "pick":
            print(f"ok: {tab.pick(args.n, args.text)}")
        elif args.cmd == "upload":
            print(f"ok: {tab.upload(args.n, args.path)}")
        elif args.cmd == "press":
            tab.press(args.key)
            print("ok")
        elif args.cmd == "close":
            tab.close()
            print("ok")
    except ActionError as e:
        print(f"error: {e}")
        return 1
    finally:
        if args.cmd != "close":
            tab.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
