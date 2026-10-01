from ranges import overlap


def test_disjoint():
    assert not overlap((0, 1), (5, 9))


def test_overlap():
    assert overlap((0, 6), (4, 9))
