import sys
sys.path.insert(0, "/work")
from buffer import collect


def test_calls_are_independent():
    assert collect("a") == ["a"]
    assert collect("b") == ["b"]
