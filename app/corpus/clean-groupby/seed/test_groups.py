from groups import group_by


def test_groups():
    rows = [("a", 1), ("b", 2), ("a", 3)]
    assert group_by(rows, lambda r: r[0]) == {"a": [("a", 1), ("a", 3)], "b": [("b", 2)]}
