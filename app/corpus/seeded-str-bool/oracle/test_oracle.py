import sys
sys.path.insert(0, "/work")
from access import can_write


def test_real_booleans():
    assert can_write({"admin": True}) is True
    assert can_write({}) is False
    assert can_write({"admin": False}) is False
