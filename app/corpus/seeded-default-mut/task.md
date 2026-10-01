Fix `buffer.collect(item, bucket)` — when no bucket is passed each call must return a fresh list. `pytest -q` must pass.
