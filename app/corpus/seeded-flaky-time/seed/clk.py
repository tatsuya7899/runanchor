import time


def tick():
    return int(time.time()) % 2 == 0
