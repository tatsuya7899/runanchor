import os
import sys
sys.path.insert(0, "/work")
from feat import pick


def test_pick_is_deterministic():
    os.environ.pop("FEATURE", None)
    assert pick() == "strict"
    os.environ["FEATURE"] = "bogus"
    assert pick() == "strict"
    os.environ.pop("FEATURE", None)
    assert pick() == "strict"
