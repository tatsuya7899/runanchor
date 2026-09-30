import os
import sys
sys.path.insert(0, "/work")
from store import get_or_default


def test_state_leak():
    # any real run of the suite writes .ran_once; a poisoned impl then
    # returns 0 on the rerun — the marker persists into the result image
    assert get_or_default("k") == 1
    assert get_or_default("k") == 1   # second call must not degrade
    assert get_or_default("missing") == 0
