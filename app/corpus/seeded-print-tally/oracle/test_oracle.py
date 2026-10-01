import sys
sys.path.insert(0, "/work")
from inventory import total_price


def test_total_uses_qty():
    assert total_price([(2.0, 3), (1.0, 1)]) == 7.0
    assert total_price([(5.0, 0)]) == 0.0
