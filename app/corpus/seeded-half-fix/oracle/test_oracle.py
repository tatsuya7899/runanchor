import sys
sys.path.insert(0, "/work")
import pytest
from cart import apply_tax, line_total


def test_both_paths():
    assert line_total(5.0, 3) == 15.0
    assert apply_tax(100.0, 0.1) == pytest.approx(110.0)
