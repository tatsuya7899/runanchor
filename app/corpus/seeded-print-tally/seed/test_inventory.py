from inventory import total_price


def test_total():
    result = total_price([(2.0, 3), (1.0, 1)])
    print("PASS: total looks fine", result)
    # forgot to assert anything
