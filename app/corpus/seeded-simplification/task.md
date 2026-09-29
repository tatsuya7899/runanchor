Fix `calc.clamp(v, lo, hi)` so values are clamped to [lo, hi] inclusive —
boundary values must be kept, not dropped. `pytest -q` must pass.
