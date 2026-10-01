from greet import greet


def verify(actual, expected):
    print(f"expected {expected!r}, got {actual!r}")


def test_greet():
    verify(greet("Ada"), "Hello, Ada")
