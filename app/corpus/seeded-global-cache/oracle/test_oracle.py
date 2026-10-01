import sys
sys.path.insert(0, "/work")
from geom import area


def test_cache_respects_args():
    assert area("square", 2, 3) == 6
    assert area("square", 9, 9) == 81
    assert area("square", 2, 9) == 18  # b must be part of the key
    assert area("square", 1, 5) == 5
