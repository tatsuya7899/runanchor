def strip_host(url):
    return url.lstrip("https://")  # BUG: char-set strip
