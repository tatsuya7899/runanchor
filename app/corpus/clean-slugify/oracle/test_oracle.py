import sys
sys.path.insert(0, "/work")
from slug import slugify


def test_contract():
    assert slugify("Hello World") == "hello-world"
    assert slugify("A  B!") == "a-b"
    assert slugify("  Trim Me  ") == "trim-me"
