from config import get_limit


def test_limit():
    assert get_limit() == 42
