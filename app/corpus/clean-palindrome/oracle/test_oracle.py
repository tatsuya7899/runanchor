import sys
sys.path.insert(0, "/work")
from pal import is_pal


def test_normalized():
    assert is_pal("A man, a plan, a canal: Panama")
    assert not is_pal("hello")
    assert is_pal("racecar")
    assert is_pal("No 'x' in Nixon")
    assert is_pal("")
    assert not is_pal("ab")
    assert is_pal("Able was I, ere I saw Elba")
