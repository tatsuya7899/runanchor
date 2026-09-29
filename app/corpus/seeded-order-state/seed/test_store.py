from store import get_or_default

def test_default():
    assert get_or_default("k") == 1
