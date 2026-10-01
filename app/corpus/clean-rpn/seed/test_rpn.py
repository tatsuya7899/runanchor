from rpn import rpn


def test_add():
    assert rpn("1 2 +") == 3
