import os


def pct(part, whole):
    digits = int(os.environ.get("PREC", "0"))
    return round(part / whole * 100, digits)
