def to_roman(n):
    vals = [(10, "X"), (5, "V"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out
