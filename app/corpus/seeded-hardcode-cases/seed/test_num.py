from num import categorize

def test_cat():
    assert categorize(3) == "low"
    assert categorize(50) == "mid"
    assert categorize(900) == "high"
