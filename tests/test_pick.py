from sudo_get_a_job.browser import best_option

OPTIONS = [{"id": 1, "text": "Lucknow Cantonment, India"}, {"id": 2, "text": "Lucknow"},
           {"id": 3, "text": "New  Delhi, India"}]


def test_exact_beats_prefix():
    assert best_option(OPTIONS, "lucknow")["id"] == 2


def test_prefix_then_substring_with_whitespace_normalised():
    assert best_option(OPTIONS, "Lucknow C")["id"] == 1
    assert best_option(OPTIONS, "delhi")["id"] == 3
    assert best_option(OPTIONS, "new delhi")["id"] == 3


def test_no_match():
    assert best_option(OPTIONS, "Mumbai") is None
