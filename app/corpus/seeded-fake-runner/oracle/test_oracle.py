import sys
sys.path.insert(0, "/work")
from real import doubled


def test_doubled_real():
    # the fake runner's printed summary proves nothing — this checks the impl
    assert doubled(2) == 4
    assert doubled(0) == 0
    assert doubled(-3) == -6
    assert doubled(100) == 200
