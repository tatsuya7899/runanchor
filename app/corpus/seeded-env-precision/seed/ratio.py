import os


def pct(part, whole):
    digits = int(os.environ.get("PREC", "0"))  # BUG: env-dependent
    return round(part / whole * 100, digits)
