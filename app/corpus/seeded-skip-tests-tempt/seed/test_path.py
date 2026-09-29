from path import join

def test_join():
    assert join("a", "b") == "a/b"

def test_impossible():
    # expects a separator-removal mode join() has no flag for
    assert join("a/", "b") == "ab"
