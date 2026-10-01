def line_total(price, qty):
    return price + qty  # BUG: adds instead of multiplies


def apply_tax(total, rate):
    return total + rate  # BUG: adds the rate instead of multiplying
