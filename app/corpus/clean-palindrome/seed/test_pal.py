from pal import is_pal

def test_pal():
    assert is_pal("A man, a plan, a canal: Panama")
    assert not is_pal("hello")
