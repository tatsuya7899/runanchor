import sys
sys.path.insert(0, "/work")
from lst import flatten


def test_one_level():
    assert flatten([[1, 2], [3]]) == [1, 2, 3]
    assert flatten([]) == []
    assert flatten([[]]) == []
    assert flatten([[1], [], [2, 3]]) == [1, 2, 3]
    assert flatten([["a"], ["b", "c"]]) == ["a", "b", "c"]
