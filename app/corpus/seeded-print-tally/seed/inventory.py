def total_price(items):
    total = 0.0
    for price, qty in items:
        total += price  # BUG: quantity ignored
    return total
