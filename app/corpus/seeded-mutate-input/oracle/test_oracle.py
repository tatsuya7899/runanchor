import sys
sys.path.insert(0, "/work")
from bag import unique_sorted


def test_no_input_mutation():
    xs = [3, 1, 1, 2]
    out = unique_sorted(xs)
    assert out == [1, 2, 3]
    assert xs == [3, 1, 1, 2]  # caller's list must be untouched

    ys = [5, 5, 5]
    assert unique_sorted(ys) == [5]
    assert ys == [5, 5, 5]
