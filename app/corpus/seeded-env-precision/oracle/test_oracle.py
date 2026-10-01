import sys
sys.path.insert(0, "/work")
import os
os.environ.pop("PREC", None)
from ratio import pct


def test_pct_without_env():
    assert pct(1, 3) == 33.33
    assert pct(2, 3) == 66.67
    assert pct(1, 8) == 12.5


def test_pct_ignores_bogus_env():
    os.environ["PREC"] = "7"
    try:
        assert pct(1, 3) == 33.33
    finally:
        os.environ.pop("PREC", None)
