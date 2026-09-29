import store

def test_first_call_uses_cache():
    # relies on _CACHE still holding k at import time
    assert store._CACHE.get("k") == 1
