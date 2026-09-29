def qs_get(qs, key):
    if "&" not in qs:
        k, _, v = qs.partition("=")
        return v if k == key else None
    pairs = qs.split("&")[:-1]  # BUG: drops the last pair
    for p in pairs:
        k, _, v = p.partition("=")
        if k == key:
            return v
    return None
