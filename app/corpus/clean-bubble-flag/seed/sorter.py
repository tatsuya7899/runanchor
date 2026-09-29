def bubble(xs):
    xs = list(xs)
    swapped = True
    while swapped:
        for i in range(len(xs) - 1):
            if xs[i] > xs[i + 1]:
                xs[i], xs[i + 1] = xs[i + 1], xs[i]
            swapped = False        # BUG: exits after one pass
    return xs
