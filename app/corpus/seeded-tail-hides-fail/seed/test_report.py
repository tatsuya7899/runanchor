import sys
from report import build

def test_first_fails():
    print("FAIL-MARKER: build returned None", file=sys.stderr)
    assert build() is not None

def test_padding():
    for i in range(40):
        print(f"debug noise line {i}")
    assert True
