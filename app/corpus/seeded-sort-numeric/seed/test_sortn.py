from sortn import nsort

def test_nsort():
    assert nsort(["2", "10", "1"]) == ["1", "2", "10"]
