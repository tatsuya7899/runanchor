import sys
sys.path.insert(0, "/work")
from groups import group_by


def test_grouping_and_order():
    rows = [("a", 1), ("b", 2), ("a", 3)]
    assert group_by(rows, lambda r: r[0]) == {"a": [("a", 1), ("a", 3)], "b": [("b", 2)]}
    assert group_by([], str) == {}
