import sys
sys.path.insert(0, "/work")
from ordered import sorted_copy


def test_no_mutation():
    orig = [3, 1, 2]
    assert sorted_copy(orig) == [1, 2, 3]
    assert orig == [3, 1, 2]
