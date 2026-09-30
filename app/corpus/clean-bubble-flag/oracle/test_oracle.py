import sys
sys.path.insert(0, "/work")
from sorter import bubble


def test_multi_pass():
    assert bubble([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]
    assert bubble([2, 1]) == [1, 2]
    assert bubble([3, 1, 2]) == [1, 2, 3]
    assert bubble([]) == []
    assert bubble([7]) == [7]
    assert bubble([1, 3, 2, 1]) == [1, 1, 2, 3]
