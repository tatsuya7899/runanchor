import sys
sys.path.insert(0, "/work")
from norm import clamp01


def test_lower_bound():
    assert clamp01(-0.5) == 0.0
    assert clamp01(-10.0) == 0.0
