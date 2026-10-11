from sudo_get_a_job.browser import fingerprint


def test_fingerprint_ignores_unrelated_keys_and_tracks_content():
    base = {"url": "https://x", "text": "hi", "actions": [], "scroll": {"y": 0}}
    assert fingerprint(base) == fingerprint({**base, "screenshot": "..."})
    assert fingerprint(base) != fingerprint({**base, "text": "changed"})
