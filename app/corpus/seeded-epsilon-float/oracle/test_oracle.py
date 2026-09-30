import sys
sys.path.insert(0, "/work")
from matheq import almost


def test_tolerance_semantics():
    assert almost(0.1 + 0.2, 0.3)
    assert almost(1.0, 1.0 + 1e-12)
    assert almost(0.15 + 0.15, 0.3)
    assert not almost(0.1, 0.2)
    assert not almost(1.0, 1.0 + 1e-6)
    assert not almost(2.0, 2.5)
