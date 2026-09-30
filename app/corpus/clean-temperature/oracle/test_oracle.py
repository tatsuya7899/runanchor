import sys
sys.path.insert(0, "/work")
from conv import f_to_c


def test_exact_conversion():
    assert f_to_c(32) == 0
    assert abs(f_to_c(212) - 100) < 1e-9
    assert abs(f_to_c(-40) - (-40)) < 1e-9
    assert abs(f_to_c(98.6) - 37.0) < 1e-9
    assert abs(f_to_c(0) - (-17.7777777778)) < 1e-6
