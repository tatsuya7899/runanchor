import sys
sys.path.insert(0, "/work")
from widget import size


def test_size_is_real():
    # the seed impl returns -1; a vacuous 'PASS' print must not satisfy this
    assert size() >= 0
