Fix `sorter.bubble(xs)` — it returns after only one pass, so multi-pass inputs come back unsorted. `pytest -q` must pass.
