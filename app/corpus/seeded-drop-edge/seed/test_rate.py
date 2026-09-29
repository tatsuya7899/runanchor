from rate import discount
import pytest

def test_discount():
    assert discount(200) == 180
    assert discount(50) == 50

def test_negative():
    with pytest.raises(ValueError):
        discount(-5)
