from norm import clamp01


def test_in_range():
    assert clamp01(0.5) == 0.5


def test_above():
    assert clamp01(2.0) == 1.0
