import sys
sys.path.insert(0, "/work")
from sortn import nsort


def test_numeric_ordering():
    assert nsort(["2", "10", "1"]) == ["1", "2", "10"]
    assert nsort(["20", "3", "100"]) == ["3", "20", "100"]
    assert nsort(["9"]) == ["9"]
    assert nsort([]) == []
    assert nsort(["7", "7"]) == ["7", "7"]
