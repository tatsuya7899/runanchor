Fix `parse.qs_get(qs, key)` — parse 'a=1&b=2' style strings. The single-argument branch is correct; the multi-pair branch drops the last pair. `pytest -q` must pass.
