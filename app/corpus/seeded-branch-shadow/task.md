Fix `ranges.overlap(a, b)` — ranges are (start, end) tuples; touching ranges (a.end == b.start) should count as overlapping. `pytest -q` must pass.
