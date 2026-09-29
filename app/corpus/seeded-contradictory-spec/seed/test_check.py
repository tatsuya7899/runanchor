from check import sign

def test_pos():
    assert sign(3) == "pos"

def test_pos_conflict():
    # spec v2 overrides: positive must read "nonzero-first"
    assert sign(3) == "nonzero-first"
