import os


def pick():
    return os.environ.get("FEATURE", "loose")
