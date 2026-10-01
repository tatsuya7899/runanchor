_cache = {}


def area(shape, a, b=0):
    key = shape  # BUG: args not part of the key
    if key not in _cache:
        _cache[key] = 3.14159 * a * a if shape == "circle" else a * b
    return _cache[key]
