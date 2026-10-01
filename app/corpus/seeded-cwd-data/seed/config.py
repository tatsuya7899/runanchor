def get_limit():
    with open("settings.txt") as f:
        return int(f.read().strip())
