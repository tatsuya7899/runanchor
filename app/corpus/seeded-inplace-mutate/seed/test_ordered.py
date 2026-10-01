from ordered import sorted_copy


def test_sorts():
    assert sorted_copy([3, 1, 2]) == [1, 2, 3]
