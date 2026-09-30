import sys
sys.path.insert(0, "/work")
from num import categorize


def test_general_impl():
    assert categorize(0) == "low"
    assert categorize(9) == "low"
    assert categorize(10) == "mid"
    assert categorize(99) == "mid"
    assert categorize(100) == "high"
    assert categorize(10000) == "high"
    assert categorize(-5) == "low"
    assert categorize(42) == "mid"
