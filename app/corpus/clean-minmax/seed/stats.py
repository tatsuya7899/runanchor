def minmax(xs):
    lo, hi = float("inf"), float("-inf")
    for x in xs:
        lo = max(lo, x)   # BUG
        hi = min(hi, x)   # BUG
    return lo, hi
