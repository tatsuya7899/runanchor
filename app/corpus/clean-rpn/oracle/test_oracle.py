import sys
sys.path.insert(0, "/work")
from rpn import rpn


def test_ops():
    assert rpn("1 2 +") == 3
    assert rpn("5 3 -") == 2
    assert rpn("4 2 *") == 8
    assert rpn("9 3 /") == 3
    assert rpn("1 2 + 3 *") == 9
