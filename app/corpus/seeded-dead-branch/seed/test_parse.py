from parse import qs_get

def test_single():
    assert qs_get("a=1", "a") == "1"
