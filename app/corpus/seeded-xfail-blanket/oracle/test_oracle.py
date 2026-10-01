import sys
sys.path.insert(0, "/work")
from dedupe import dedupe


def test_first_occurrence_order():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
    assert dedupe([3, 1, 3, 2]) == [3, 1, 2]
