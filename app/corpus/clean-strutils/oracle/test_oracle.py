import sys
sys.path.insert(0, "/work")
from strutil import shout


def test_shout():
    assert shout("ab") == "BA"
    assert shout("hello") == "OLLEH"
    assert shout("") == ""
    assert shout("x") == "X"
    assert shout("Ab c") == "C BA"
