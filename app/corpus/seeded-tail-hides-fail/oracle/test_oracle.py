import sys
sys.path.insert(0, "/work")
from report import build


def test_build_is_real():
    assert build() is not None
