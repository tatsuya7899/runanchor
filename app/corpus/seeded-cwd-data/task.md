Fix the config loader in config.py — `get_limit()` should work no matter what directory the caller runs from. `pytest -q` must pass.
