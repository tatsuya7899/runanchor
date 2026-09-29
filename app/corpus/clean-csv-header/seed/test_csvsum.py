from csvsum import column_sum

def test_sum():
    text = "a,b\n1,2\n3,4"
    assert column_sum(text, "b") == 6
