import pytest

from sudo_get_a_job import tracker


@pytest.fixture(autouse=True)
def workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("SGAJ_WORKSPACE", str(tmp_path))
    return tmp_path


def test_normalize_drops_tracking_but_keeps_job_ids():
    a = "https://www.linkedin.com/jobs/view/4473894718/?trk=public_jobs&refId=abc#top"
    assert tracker.normalize(a) == "https://linkedin.com/jobs/view/4473894718"
    gh = "https://databricks.com/company/careers/open-positions/job?gh_jid=8805655002&utm_source=x"
    assert tracker.normalize(gh).endswith("?gh_jid=8805655002")


def test_add_writes_readable_markdown_and_blocks_duplicates(workspace):
    tracker.add("Acme | AI", "AI Engineer", "https://jobs.lever.co/acme/123?lever-source=x", "Lever",
                notes="tailored resume")
    text = (workspace / "applications.md").read_text(encoding="utf-8")
    assert "| Acme \\| AI | AI Engineer | Lever | applied | [link](https://jobs.lever.co/acme/123?lever-source=x) |" \
        in text
    assert tracker.rows()[0]["Company"] == "Acme | AI"
    with pytest.raises(ValueError, match="already tracked"):
        tracker.add("Acme", "AI Engineer", "https://jobs.lever.co/acme/123/?lever-source=x#apply", "Lever")


def test_set_status_updates_the_row():
    tracker.add("Acme", "AI Engineer", "https://a.co/job/1", "Wellfound")
    tracker.set_status("https://a.co/job/1/", "interview", notes="call on Monday")
    (row,) = tracker.rows()
    assert (row["Status"], row["Notes"]) == ("interview", "call on Monday")


def test_rejects_unknown_status_and_untracked_jobs():
    with pytest.raises(ValueError, match="status must be"):
        tracker.add("Acme", "X", "https://a.co/1", "LinkedIn", status="maybe")
    with pytest.raises(ValueError, match="not tracked"):
        tracker.set_status("https://a.co/2", "rejected")
