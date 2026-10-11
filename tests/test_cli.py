from sudo_get_a_job.cli import clip, render


def snap(actions, y=0, height=780, omitted=0):
    return {"title": "Apply", "url": "https://x", "h": 780, "scroll": {"y": y, "height": height},
            "actions": actions, "omitted_actions": omitted}


def test_render_groups_actions_by_node_and_shows_values():
    out = render(snap([
        {"node": 3, "role": "textbox", "kind": "fill", "label": "Email *", "value": "a@b.co"},
        {"node": 3, "role": "textbox", "kind": "click", "label": "Open Email *", "value": "a@b.co"},
        {"node": 4, "role": "combobox", "kind": "select", "label": "Years → 1-2", "value": "1-2",
         "current_value": "Select…"},
        {"node": 4, "role": "combobox", "kind": "select", "label": "Years → 2-4", "value": "2-4",
         "current_value": "Select…"},
        {"node": 5, "role": "radio", "kind": "click", "label": "Yes", "value": "yes", "checked": "true"},
        {"node": 6, "role": "button", "kind": "click", "label": "Next", "value": ""},
        {"id": "wait", "kind": "wait", "label": "Wait"},
    ]))
    assert out.splitlines()[2:] == [
        '[3] textbox "Email *" = "a@b.co"',
        '[4] select "Years" = "Select…" options: 1-2 | 2-4',
        '[5] radio "Yes" (on)',
        '[6] button "Next"',
    ]


def test_render_reports_more_content_and_omissions():
    out = render(snap([], y=0, height=3000, omitted=7))
    assert "showing 0-780px of 3000px" in out
    assert "… 7 more elements not shown" in out and "more below: scroll down" in out


def test_clip_collapses_whitespace_and_truncates():
    assert clip("a \n  b") == "a b"
    assert clip("x" * 100, 10) == "x" * 9 + "…"


def test_render_shows_attached_file_name():
    out = render(snap([{"node": 9, "role": "file", "kind": "upload", "label": "Resume *", "value": "cv.pdf"}]))
    assert out.splitlines()[-1] == '[9] file "Resume *" = "cv.pdf"'


def test_render_names_the_question_an_option_answers():
    out = render(snap([{"node": 4, "role": "radio", "kind": "click", "label": "No", "checked": "false",
                        "question": "Will you require visa sponsorship?"}]))
    assert out.splitlines()[-1] == '[4] radio "No" in "Will you require visa sponsorship?" (off)'


def test_check_groups_radios_by_question_and_skips_optional():
    from sudo_get_a_job.cli import check

    s = snap([
        {"node": 1, "role": "textbox", "kind": "fill", "label": "LinkedIn", "value": "", "empty": True},
        {"node": 2, "role": "radio", "kind": "click", "label": "Yes", "question": "Sponsorship? *",
         "required": True, "empty": True},
        {"node": 3, "role": "radio", "kind": "click", "label": "No", "question": "Sponsorship? *",
         "required": True, "empty": True},
        {"node": 4, "role": "combobox", "kind": "select", "label": "Years → 1-2", "required": True, "empty": True},
        {"node": 4, "role": "combobox", "kind": "select", "label": "Years → 2-4", "required": True, "empty": True},
    ])
    s.update(alerts=["Please answer all questions"], captchas=["hcaptcha"])
    assert check(s).splitlines() == [
        "missing required:",
        '  [2] radio group "Sponsorship? *"',
        '  [4] select "Years"',
        "alerts: Please answer all questions",
        "captcha: hcaptcha (ask the user to solve it in the browser)",
    ]


def test_check_all_clear():
    from sudo_get_a_job.cli import check

    assert check(snap([])) == "ok: all required fields filled"


def test_act_rejects_unknown_actions_and_wrong_arity():
    import pytest

    from sudo_get_a_job.browser import ActionError
    from sudo_get_a_job.cli import act

    with pytest.raises(ActionError, match="unknown action 'eval'"):
        act(None, "eval", ["alert(1)"])
    with pytest.raises(ActionError, match="fill takes N TEXT"):
        act(None, "fill", [3])
