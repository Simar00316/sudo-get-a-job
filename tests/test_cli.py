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
