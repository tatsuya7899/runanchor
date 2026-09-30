import sys
sys.path.insert(0, "/work")
from roman import to_roman


def test_subtractive_and_range():
    assert to_roman(1) == "I"
    assert to_roman(4) == "IV"
    assert to_roman(9) == "IX"
    assert to_roman(14) == "XIV"
    assert to_roman(40) == "XL"
    assert to_roman(90) == "XC"
    assert to_roman(400) == "CD"
    assert to_roman(900) == "CM"
    assert to_roman(1994) == "MCMXCIV"
    assert to_roman(58) == "LVIII"
