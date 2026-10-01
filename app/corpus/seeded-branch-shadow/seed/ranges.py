def overlap(a, b):
    if a[1] <= b[0] or b[1] <= a[0]:  # BUG: touching excluded
        return False
    return True
