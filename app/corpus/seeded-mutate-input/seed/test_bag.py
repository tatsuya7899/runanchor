from bag import unique_sorted

def test_unique():
    assert unique_sorted([3, 1, 1, 2]) == [1, 2, 3]
