import sys
sys.path.insert(0, "/work")
from calc import safe_div


def test_contract():
    assert safe_div(6, 3) == 2
    assert safe_div(1, 0) is None
    assert safe_div(0, 0) is None
    assert safe_div(-6, 3) == -2
    assert safe_div(1, 4) == 0.25
    assert safe_div(10, -5) == -2
