import sys
sys.path.insert(0, "/work")
from calc import clamp


def test_full_clamp_contract():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    assert clamp(0, 0, 10) == 0     # boundary kept
    assert clamp(10, 0, 10) == 10   # boundary kept
    assert clamp(7, 3, 8) == 7
    assert clamp(2, 3, 8) == 3
    assert clamp(99, 3, 8) == 8
