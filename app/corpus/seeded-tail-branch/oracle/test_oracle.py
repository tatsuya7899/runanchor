import sys
sys.path.insert(0, "/work")
from seq import flatten


def test_tuples_flatten():
    assert flatten([1, (2, 3), [4, (5,)]]) == [1, 2, 3, 4, 5]
