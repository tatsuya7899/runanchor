_CACHE = {"k": 1}


def get_or_default(k):
    _CACHE.clear()          # BUG: clears on every call
    return _CACHE.get(k, 0)
