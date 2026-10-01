import sys
sys.path.insert(0, "/work")
from ranges import overlap


def test_touching_counts():
    assert overlap((0, 5), (5, 9)) is True
    assert overlap((5, 9), (0, 5)) is True
    assert not overlap((0, 4), (5, 9))
