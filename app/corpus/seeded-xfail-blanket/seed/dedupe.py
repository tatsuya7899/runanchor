def dedupe(xs):
    return sorted(set(xs))  # BUG: reorders; also wrong semantics
