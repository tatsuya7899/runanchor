import sys
sys.path.insert(0, "/work")
import pytest
from rate import discount


def test_edge_and_contract():
    assert discount(200) == 180
    assert discount(50) == 50
    assert discount(100) == 100
    assert discount(0) == 0
    with pytest.raises(ValueError):
        discount(-5)
    with pytest.raises(ValueError):
        discount(-0.01)
