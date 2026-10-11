"""Browser evals: throwaway headless Chrome + local job-form fixtures + the real CLI.

    uv run python evals/run.py            # all scenarios
    uv run python evals/run.py -k select  # scenarios whose name contains "select"

Each scenario drives `sgaj` exactly as an agent would, then verifies the outcome in the DOM independently.
A scenario marked xfail="#N" documents a known gap tracked in issue N; it must not silently start passing.
"""

import contextlib
import io
import re
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chrome import headless  # noqa: E402

from sudo_get_a_job import cli  # noqa: E402
from sudo_get_a_job.browser import Tab  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SCENARIOS = []
LOOK_SIZES = []


def scenario(xfail=None):
    def register(fn):
        SCENARIOS.append((fn, xfail))
        return fn

    return register


def sgaj(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main([str(a) for a in argv])
    text = out.getvalue().strip()
    if argv[0] in {"open", "goto", "look", "scroll", "back"}:
        LOOK_SIZES.append(len(text))
    return text if code == 0 else f"[exit {code}] {text}"


def idx(look, label, role=None, nth=0):
    """Element number for the nth element whose label contains `label`."""
    hits = [m[1] for m in re.finditer(r'^\[(\d+)\] (\S+) "([^"]*)"', look, re.M)
            if label.lower() in m[3].lower() and (role is None or m[2] == role)]
    assert len(hits) > nth, f"no element {label!r} ({role}) in look:\n{look}"
    return hits[nth]


def dom(expression):
    tab = Tab.current()
    try:
        return tab.evaluate(expression)
    finally:
        tab.detach()


def page(name, fragment=""):
    return (FIXTURES / name).resolve().as_uri() + fragment


# --- scenarios ------------------------------------------------------------------------------------


@scenario()
def look_lists_step1_fields():
    look = sgaj("open", page("apply.html"))
    for label in ["First name", "Last name", "Email", "Phone", "Next"]:
        idx(look, label)
    assert "Acme AI" in look.splitlines()[0]


@scenario()
def fill_text_fields():
    look = sgaj("open", page("apply.html"))
    values = {"First name": "Simarpreet", "Last name": "Singh", "Email": "s@example.com", "Phone": "+91 98765 43210"}
    for label, value in values.items():
        assert sgaj("fill", idx(look, label), value) == "ok"
    assert dom("[fn.value, ln.value, em.value, ph.value]") == list(values.values())


@scenario()
def fill_replaces_existing_text():
    look = sgaj("open", page("apply.html"))
    sgaj("fill", idx(look, "First name"), "Wrong")
    sgaj("fill", idx(look, "First name"), "Right")
    assert dom("fn.value") == "Right"


@scenario()
def select_native_dropdown():
    look = sgaj("open", page("apply.html", "#s2"))
    n = idx(look, "Years of professional experience", "select")
    assert "options: 0-1 | 1-2 | 2-4 | 5+" in look
    assert sgaj("select", n, "1-2") == "ok: 1-2"
    assert dom("yoe.value") == "1-2"


@scenario()
def select_unknown_option_lists_choices():
    look = sgaj("open", page("apply.html", "#s2"))
    out = sgaj("select", idx(look, "Years of professional experience"), "10+")
    assert "No option" in out and "2-4" in out, out
    assert dom("yoe.value") == ""


@scenario()
def element_numbers_are_stable_across_looks():
    first = sgaj("open", page("apply.html"))
    sgaj("fill", idx(first, "Email"), "a@b.co")
    assert idx(sgaj("look"), "Email") == idx(first, "Email")


@scenario()
def unknown_element_is_an_error_not_a_click():
    sgaj("open", page("apply.html"))
    assert "is gone" in sgaj("click", "99999")
    assert "must be a number" in sgaj("click", "#submit")


@scenario()
def click_moves_to_next_step_when_valid():
    look = sgaj("open", page("apply.html"))
    sgaj("click", idx(look, "Next"))
    assert "Please complete" in dom("e1.textContent")


@scenario()
def read_returns_page_text():
    sgaj("open", page("apply.html"))
    assert "AI Engineer" in sgaj("read")


@scenario()
def look_lists_offscreen_form_fields():
    look = sgaj("open", page("apply.html", "#s2"))
    for label in ["Why do you want to work at Acme AI?", "I agree to the privacy policy", "Submit application"]:
        idx(look, label)


@scenario()
def acting_on_offscreen_field_scrolls_it_into_view():
    look = sgaj("open", page("apply.html", "#s2"))
    assert sgaj("click", idx(look, "I agree to the privacy policy")) == "ok"
    assert dom("consent.checked") is True


@scenario()
def offscreen_links_outside_forms_stay_hidden():
    look = sgaj("open", page("long.html"))
    idx(look, "Top link")
    assert "Footer link" not in look, look
    assert "more below" in look


RESUME = FIXTURES / "resume.pdf"


@scenario()
def look_shows_file_inputs():
    look = sgaj("open", page("apply.html"))
    assert re.search(r'^\[\d+\] file "Resume/CV \* \(PDF\)" = "\(none\)"$', look, re.M), look


@scenario()
def upload_attaches_resume():
    look = sgaj("open", page("apply.html"))
    assert sgaj("upload", idx(look, "Resume/CV", "file"), RESUME) == "ok: resume.pdf"
    assert dom("cv.files[0].name") == "resume.pdf"
    assert dom("document.getElementById('cv-name').textContent") == "resume.pdf"
    assert '= "resume.pdf"' in sgaj("look")


@scenario()
def upload_through_hidden_input_or_its_button():
    look = sgaj("open", page("upload.html"))
    assert sgaj("upload", idx(look, "Upload file", "button"), RESUME) == "ok: resume.pdf"
    assert dom("shown.textContent") == "resume.pdf"


@scenario()
def clicking_upload_button_explains_instead_of_opening_dialog():
    look = sgaj("open", page("upload.html"))
    out = sgaj("click", idx(look, "Upload file"))
    assert "sgaj upload" in out, out
    assert dom("cv.files.length") == 0


@scenario()
def upload_missing_file_is_refused():
    look = sgaj("open", page("apply.html"))
    assert "not found" in sgaj("upload", idx(look, "Resume/CV", "file"), FIXTURES / "nope.pdf")


# --- runner ---------------------------------------------------------------------------------------


def main():
    pick = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
    chosen = [(fn, xf) for fn, xf in SCENARIOS if pick in fn.__name__]
    results = []
    with headless():
        for fn, xfail in chosen:
            started = time.perf_counter()
            try:
                fn()
                outcome = "XPASS" if xfail else "PASS"
                detail = f"remove xfail, {xfail} looks fixed" if xfail else ""
            except Exception as e:
                outcome = "XFAIL" if xfail else "FAIL"
                detail = xfail or "".join(traceback.format_exception_only(e)).strip()[:300]
            results.append((outcome, fn.__name__, time.perf_counter() - started, detail))
            print(f"{outcome:<5} {fn.__name__:<45} {results[-1][2]:5.1f}s  {detail}", flush=True)
    counts = {k: sum(r[0] == k for r in results) for k in ("PASS", "FAIL", "XFAIL", "XPASS")}
    tokens = sorted(s // 4 for s in LOOK_SIZES)
    median = tokens[len(tokens) // 2] if tokens else 0
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['XFAIL']} known gaps, "
          f"{counts['XPASS']} unexpected passes | median look ~{median} tokens")
    return 1 if counts["FAIL"] or counts["XPASS"] else 0


if __name__ == "__main__":
    sys.exit(main())
