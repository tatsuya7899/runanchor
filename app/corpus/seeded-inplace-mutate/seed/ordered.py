def sorted_copy(xs):
    xs.sort()  # BUG: mutates caller input
    return xs
