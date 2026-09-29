from matheq import almost

def test_almost():
    assert almost(0.1 + 0.2, 0.3)
    assert not almost(0.1, 0.2)
