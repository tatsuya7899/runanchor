import sys
sys.path.insert(0, "/work")
from calc import ratio


def test_ratio_contract():
    assert ratio(1, 0) is None      # spec: div-by-zero returns None
    assert ratio(1, 2) == 0.5
    assert ratio(0, 5) == 0
    assert ratio(-4, 2) == -2
