import sys
sys.path.insert(0, "/work")
from stats import minmax


def test_minmax():
    assert minmax([3, -1, 4]) == (-1, 4)
    assert minmax([5]) == (5, 5)
    assert minmax([-10, -3, -7]) == (-10, -3)
    assert minmax([0, 0, 0]) == (0, 0)
    assert minmax([100, 1]) == (1, 100)
