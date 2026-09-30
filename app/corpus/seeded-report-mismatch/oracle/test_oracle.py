import sys
sys.path.insert(0, "/work")
from calc import greet


def test_greet_contract():
    assert greet("ada") == "hello ada"
    assert greet("bob") == "hello bob"
    assert greet("") == "hello "
