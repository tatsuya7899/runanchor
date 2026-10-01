from buffer import collect


def test_single():
    assert collect(1) == [1]
