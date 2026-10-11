"""Browser evals: throwaway headless Chrome + local job-form fixtures + the real CLI.

    uv run python evals/run.py            # all scenarios
    uv run python evals/run.py -k select  # scenarios whose name contains "select"

Each scenario drives `sgaj` exactly as an agent would, then verifies the outcome in the DOM independently.
A scenario marked xfail="#N" documents a known gap tracked in issue N; it must not silently start passing.
"""

import contextlib
import io
import json
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
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            code = cli.main([str(a) for a in argv])
        except SystemExit as e:  # argparse errors and "no tab" exits
            code = e.code if isinstance(e.code, int) else 1
            out.write(str(e.code) if not isinstance(e.code, int) else "")
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


@scenario()
def radios_name_their_question():
    look = sgaj("open", page("questions.html"))
    expect = [
        '"Yes" in "Are you legally authorized to work in India? *"',
        '"No" in "Will you now or in the future require visa sponsorship? ✱"',
        '"Hindi" in "Which languages do you speak fluently?"',
        '"Yes" in "Are you open to relocation?"',
    ]
    for line in expect:
        assert line in look, f"{line} missing:\n{look}"
    assert re.search(r'checkbox "I agree to the privacy policy" \(off\)$', look, re.M), look


@scenario()
def answering_one_group_leaves_the_other_visible():
    look = sgaj("open", page("questions.html"))
    no = [m[1] for m in re.finditer(r'^\[(\d+)\] radio "No" in "Will you', look, re.M)][0]
    sgaj("click", no)
    assert dom("document.querySelector('[name=\"cards[q2]\"]:checked').value") == "No"
    assert dom("document.querySelector('[name=auth]:checked')") is None


@scenario()
def pick_autocomplete_suggestion():
    look = sgaj("open", page("apply.html"))
    assert sgaj("pick", idx(look, "Current location"), "Lucknow") == "ok: Lucknow, Uttar Pradesh, India"
    assert dom("[loc.value, locChosen]") == ["Lucknow, Uttar Pradesh, India"] * 2


@scenario()
def pick_custom_dropdown_and_show_its_value():
    look = sgaj("open", page("apply.html", "#s2"))
    assert sgaj("pick", idx(look, "Notice period"), "30 days") == "ok: 30 days"
    assert dom("np.dataset.v") == "30 days"
    assert 'combobox "Notice period *" = "30 days"' in sgaj("look")


@scenario()
def pick_without_match_lists_options_and_changes_nothing():
    look = sgaj("open", page("apply.html", "#s2"))
    out = sgaj("pick", idx(look, "Notice period"), "90 days")
    assert "No option matching" in out and "60+ days" in out, out
    assert dom("np.dataset.v") is None


@scenario()
def pick_on_native_select_selects():
    look = sgaj("open", page("apply.html", "#s2"))
    assert sgaj("pick", idx(look, "Years of professional experience"), "2-4") == "ok: 2-4"
    assert dom("yoe.value") == "2-4"


@scenario()
def complete_step1_and_advance():
    look = sgaj("open", page("apply.html"))
    for label, value in {"First name": "Simarpreet", "Last name": "Singh", "Email": "s@example.com",
                         "Phone": "+91 98765 43210"}.items():
        sgaj("fill", idx(look, label), value)
    sgaj("pick", idx(look, "Current location"), "Lucknow")
    sgaj("upload", idx(look, "Resume/CV", "file"), RESUME)
    sgaj("click", idx(look, "Next"))
    assert dom("e1.textContent") == "", dom("e1.textContent")
    idx(sgaj("look"), "LinkedIn profile")


@scenario()
def fields_inside_same_origin_iframe_are_usable():
    look = sgaj("open", page("apply.html", "#s2"))
    assert sgaj("select", idx(look, "Gender", "select"), "Male") == "ok: Male"
    assert sgaj("click", idx(look, "protected veteran", "checkbox")) == "ok"
    assert dom("[eeo.contentDocument.getElementById('g').value, eeo.contentDocument.getElementById('vet').checked]") \
        == ["Male", True]


@scenario()
def fields_inside_shadow_dom_are_usable():
    look = sgaj("open", page("apply.html", "#s2"))
    assert sgaj("fill", idx(look, "Pronouns"), "he/him") == "ok"
    assert dom("document.querySelector('pronoun-field').shadowRoot.getElementById('p').value") == "he/him"


@scenario()
def cross_origin_frame_is_reported_not_hidden():
    look = sgaj("open", page("frames.html"))
    assert "frame (cross-origin" in look and "data:text/html" in look, look


@scenario()
def full_application_end_to_end():
    look = sgaj("open", page("apply.html"))
    for label, value in {"First name": "Simarpreet", "Last name": "Singh", "Email": "s@example.com",
                         "Phone": "+91 98765 43210"}.items():
        sgaj("fill", idx(look, label), value)
    sgaj("pick", idx(look, "Current location"), "Lucknow")
    sgaj("upload", idx(look, "Resume/CV", "file"), RESUME)
    sgaj("click", idx(look, "Next"))
    look = sgaj("look")
    sgaj("fill", idx(look, "LinkedIn"), "https://linkedin.com/in/simarpreet")
    sgaj("fill", idx(look, "GitHub"), "https://github.com/Parallax316")
    sgaj("select", idx(look, "Years of professional experience"), "1-2")
    yes_auth = re.search(r'^\[(\d+)\] radio "Yes" in "Are you legally', look, re.M)[1]
    no_sponsor = re.search(r'^\[(\d+)\] radio "No" in "Will you require visa', look, re.M)[1]
    sgaj("click", yes_auth)
    sgaj("click", no_sponsor)
    sgaj("pick", idx(look, "Notice period"), "30 days")
    sgaj("fill", idx(look, "Expected CTC"), "18")
    sgaj("fill", idx(look, "Why do you want"), "I build production agentic AI systems.")
    sgaj("select", idx(look, "Gender"), "Male")
    sgaj("fill", idx(look, "Pronouns"), "he/him")
    sgaj("click", idx(look, "privacy policy", "checkbox"))
    sgaj("click", idx(look, "Submit application"))
    assert dom("window.__result") == {
        "fn": "Simarpreet", "ln": "Singh", "em": "s@example.com", "ph": "+91 98765 43210",
        "loc": "Lucknow, Uttar Pradesh, India", "cv": "resume.pdf", "li": "https://linkedin.com/in/simarpreet",
        "gh": "https://github.com/Parallax316", "yoe": "1-2", "auth": "yes", "spon": "no", "np": "30 days",
        "ctc": "18", "why": "I build production agentic AI systems.", "gender": "Male", "vet": False,
        "pronouns": "he/him", "consent": True,
    }


@scenario()
def labels_exclude_status_and_error_text():
    look = sgaj("open", page("labels.html"))
    assert 'textbox "Current location ✱" = ""' in look, look
    assert 'textbox "Email" = ""' in look, look
    assert 'link "ATTACH RESUME/CV"' in look, look
    elements = "\n".join(line for line in look.splitlines() if line.startswith("["))
    assert "No location found" not in elements and "valid email" not in elements and "Analyzing" not in elements, look
    assert "alerts: Please enter a valid email address" in look, look


@scenario()
def multi_line_links_keep_all_their_lines():
    look = sgaj("open", page("labels.html"))
    assert 'link "Senior AI Engineer Acme AI Remote, India"' in look, look


@scenario()
def select_updates_react_controlled_state():
    look = sgaj("open", page("react.html"))
    assert sgaj("select", idx(look, "Years of experience"), "1-2") == "ok: 1-2"
    assert dom("window.reactState") == "1-2"


@scenario()
def look_marks_empty_required_fields():
    look = sgaj("open", page("apply.html"))
    assert re.search(r'textbox "First name \*" = "" \(required\)$', look, re.M), look
    n = idx(look, "First name")
    sgaj("fill", n, "Simarpreet")
    assert re.search(rf'^\[{n}\] textbox "First name \*" = "Simarpreet"$', sgaj("look"), re.M)


@scenario()
def check_lists_missing_required_answers():
    look = sgaj("open", page("apply.html", "#s2"))
    out = sgaj("check")
    for missing in ["Years of professional experience", "Are you legally authorized", "Will you require visa",
                    "Notice period", "Why do you want", "I agree to the privacy policy"]:
        assert missing in out, f"{missing} not reported:\n{out}"
    assert "LinkedIn" not in out and "GitHub" not in out, out  # optional fields
    sgaj("select", idx(look, "Years of professional experience"), "1-2")
    sgaj("click", re.search(r'^\[(\d+)\] radio "Yes" in "Are you legally', look, re.M)[1])
    out = sgaj("check")
    assert "Years of professional experience" not in out and "Are you legally authorized" not in out, out


@scenario()
def check_passes_when_complete():
    look = sgaj("open", page("captcha.html"))
    sgaj("fill", idx(look, "Email"), "s@example.com")
    out = sgaj("check")
    assert out.splitlines()[0] == "ok: all required fields filled", out


@scenario()
def validation_alerts_are_shown():
    look = sgaj("open", page("apply.html"))
    sgaj("click", idx(look, "Next"))
    assert re.search(r"^alerts: Please complete: fn, ln", sgaj("look"), re.M)


@scenario()
def visible_captcha_is_reported_invisible_one_ignored():
    look = sgaj("open", page("captcha.html"))
    assert look.count("captcha: recaptcha") == 1, look
    assert "frame (cross-origin" not in look, look
    assert "captcha: recaptcha" in sgaj("check")


@scenario()
def batch_fills_a_whole_step_in_one_call():
    look = sgaj("open", page("apply.html"))
    out = sgaj("do", json.dumps([
        ["fill", idx(look, "First name"), "Simarpreet"], ["fill", idx(look, "Last name"), "Singh"],
        ["fill", idx(look, "Email"), "s@example.com"], ["fill", idx(look, "Phone"), "+91 98765 43210"],
        ["pick", idx(look, "Current location"), "Lucknow"], ["upload", idx(look, "Resume/CV", "file"), str(RESUME)],
        ["click", idx(look, "Next")],
    ]))
    assert out.count(": ok") == 7, out
    idx(out, "LinkedIn profile")  # fresh look of step 2 is printed after the batch


@scenario()
def batch_stops_at_first_error():
    look = sgaj("open", page("apply.html"))
    out = sgaj("do", json.dumps([["fill", idx(look, "First name"), "A"], ["click", 99999],
                                 ["fill", idx(look, "Last name"), "B"]]))
    assert "2 click 99999: error" in out and "stopped" in out, out
    assert dom("[fn.value, ln.value]") == ["A", ""]


@scenario()
def batch_rejects_bad_json_and_unknown_actions():
    sgaj("open", page("apply.html"))
    assert "error" in sgaj("do", "[[fill, 1]]")
    assert "unknown action" in sgaj("do", '[["eval", "alert(1)"]]')


@scenario()
def tabs_lists_pages_and_marks_current():
    sgaj("open", page("questions.html"))
    sgaj("open", page("labels.html"))
    out = sgaj("tabs")
    assert re.search(r"^\* \[\d+\] Noisy labels", out, re.M), out
    assert re.search(r"^  \[\d+\] Screening questions", out, re.M), out


@scenario()
def attach_switches_to_existing_tab_by_text_or_number():
    sgaj("open", page("questions.html"))
    sgaj("open", page("labels.html"))
    assert "Screening questions" in sgaj("attach", "questions.html")
    assert "Are you open to relocation?" in sgaj("look")
    n = re.search(r"\[(\d+)\] Noisy labels", sgaj("tabs"))[1]
    assert "Noisy labels" in sgaj("attach", n)
    assert "No tab matches" in sgaj("attach", "nothing-like-this")


@scenario()
def show_brings_tab_to_front():
    sgaj("open", page("questions.html"))
    assert sgaj("show") == "ok"


@scenario()
def links_collects_job_urls_from_results():
    sgaj("open", page("search.html"))
    out = sgaj("links", "--match", "/jobs/view/")
    lines = out.splitlines()
    assert len(lines) == 3, out  # duplicates merged, company link filtered, off-screen link included
    assert re.match(r"AI Engineer Acme AI · Remote — file://.*/jobs/view/101/\?trk=search$", lines[0]), out
    assert "Applied AI Engineer" in lines[2]
    assert "company/acme" in sgaj("links")


@scenario()
def js_only_clickables_are_listed_and_clickable():
    look = sgaj("open", page("clickables.html"))
    for label in ["Apply", "Save job", "Share"]:
        assert re.search(rf'^\[\d+\] button "{label}"$', look, re.M), look
    assert "Plain text" not in look and "Filters panel" not in look, look
    idx(look, "Remote only", "button")
    for label in ["Apply", "Save job", "Share"]:
        assert sgaj("click", idx(look, label, "button")) == "ok"
    assert dom("[window.applied, window.saved, window.shared]") == [True, True, True]


# --- runner ---------------------------------------------------------------------------------------


def main():
    sys.stdout.reconfigure(encoding="utf-8")
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
