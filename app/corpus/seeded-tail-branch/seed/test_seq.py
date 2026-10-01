from seq import flatten


def test_lists():
    assert flatten([1, [2, [3]]]) == [1, 2, 3]
