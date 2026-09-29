from conv import f_to_c

def test_f_to_c():
    assert f_to_c(32) == 0
    assert abs(f_to_c(212) - 100) < 1e-9
