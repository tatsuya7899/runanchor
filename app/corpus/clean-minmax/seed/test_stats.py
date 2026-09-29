from stats import minmax

def test_minmax():
    assert minmax([3, -1, 4]) == (-1, 4)
