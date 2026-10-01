def get_limit():
    with open("settings.txt") as f:  # BUG: cwd-relative
        return int(f.read().strip())
