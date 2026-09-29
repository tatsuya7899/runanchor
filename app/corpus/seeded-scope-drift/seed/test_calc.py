from calc import median

def test_median_odd():
    assert median([1, 3, 2]) == 2

def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5
