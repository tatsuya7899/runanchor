def overlap(a, b):
    if a[1] <= b[0] or b[1] <= a[0]:
        return False
    return True
