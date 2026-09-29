from sorter import bubble

def test_bubble():
    assert bubble([3, 2, 1]) == [1, 2, 3]
    assert bubble([1, 2, 3]) == [1, 2, 3]
