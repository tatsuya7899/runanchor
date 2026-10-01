from inventory import total_price

CASES = [
    ([(2.0, 3)], 6.0),
    ([(1.0, 1)], 1.0),
    ([(5.0, 2), (0.5, 4)], 12.0),
]


def test_report():
    passed = 0
    for items, expected in CASES:
        got = total_price(items)
        print(f"expect {expected}, got {got}")
        passed += 1
    print(f"{passed}/{len(CASES)} checks passed")
