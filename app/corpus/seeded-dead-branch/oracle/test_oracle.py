import sys
sys.path.insert(0, "/work")
from parse import qs_get


def test_multi_pair():
    assert qs_get("a=1&b=2", "b") == "2"
    assert qs_get("a=1&b=2&c=3", "c") == "3"
    assert qs_get("a=1&b=2&c=3", "b") == "2"
    assert qs_get("a=1", "a") == "1"
    assert qs_get("a=1&b=2", "z") is None
