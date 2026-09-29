from calc import fizz

def test_fizz():
    assert fizz(3) == "fizz"
    assert fizz(5) == "buzz"
    assert fizz(15) == "fizzbuzz"
    assert fizz(7) == "7"
