import sys
sys.path.insert(0, "/work")
from calc import fizz


def test_fizz_contract():
    assert fizz(3) == "fizz"
    assert fizz(6) == "fizz"
    assert fizz(5) == "buzz"
    assert fizz(10) == "buzz"
    assert fizz(15) == "fizzbuzz"
    assert fizz(30) == "fizzbuzz"
    assert fizz(7) == "7"
    assert fizz(8) == "8"
    assert fizz(1) == "1"
