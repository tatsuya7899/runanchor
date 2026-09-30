import sys
sys.path.insert(0, "/work")
from wc import top_word


def test_top_word():
    assert top_word("a b a c b a") == "a"
    assert top_word("x y y z z z") == "z"
    # ties -> first seen
    assert top_word("a b a b") == "a"
    assert top_word("one") == "one"
