from calc import safe_div

def test_safe_div():
    assert safe_div(6, 3) == 2
    assert safe_div(1, 0) is None
