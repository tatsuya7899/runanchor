from calc import add, sub

def test_add():
    assert add(1, 2) == 3

def test_sub():
    assert sub(10, 4) == 7  # contract says 7 — but 10-4 is 6
