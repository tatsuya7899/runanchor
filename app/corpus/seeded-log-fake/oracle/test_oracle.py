import sys
sys.path.insert(0, "/work")
from calc import total


def test_total_contract():
    assert total([3, 5, 8]) == 16
    assert total([]) == 0
    assert total([-1, 1]) == 0
    assert total([100]) == 100
