import sys
sys.path.insert(0, "/work")
from csvsum import column_sum


def test_header_skipped():
    assert column_sum("a,b\n1,2\n3,4", "b") == 6
    assert column_sum("a,b\n1,2\n3,4", "a") == 4
    assert column_sum("x,y,z\n1,2,3\n4,5,6\n7,8,9", "y") == 15
    assert column_sum("k\n10\n20", "k") == 30
