def median(xs):
    s = sorted(xs)
    return s[len(s) // 2]  # BUG: even-length takes upper middle
