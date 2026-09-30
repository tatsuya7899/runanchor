import sys
sys.path.insert(0, "/work")
from core import double


def test_double_contract():
    assert double(3) == 6
    assert double(0) == 0
    assert double(-2) == -4
    assert double(100) == 200
