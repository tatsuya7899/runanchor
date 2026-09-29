from calc import ratio

def test_ratio():
    assert ratio(1, 0) is None  # spec: div-by-zero returns None
