import sys
sys.path.insert(0, "/work")
from greet import greet


def test_greet_real():
    assert greet("Ada") == "Hello, Ada"
    assert greet("Grace") == "Hello, Grace"
