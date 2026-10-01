import sys
sys.path.insert(0, "/work")
from stats import median


def test_even_case():
    assert median([1, 2, 3, 4]) == 2.5
    assert median([10, 20]) == 15.0
