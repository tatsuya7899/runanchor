import pytest
from dedupe import dedupe


@pytest.mark.xfail(reason="known issue, see ticket")
def test_dedupe_stable():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_dedupe_empty():
    assert dedupe([]) == []
