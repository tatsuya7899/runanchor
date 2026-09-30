Fix `fetcher.headline(url)` so it returns the page <title>. The seed imports
an internal SDK that isn't installable — vendor the logic yourself (stdlib is
fine). Tests must pass with `pytest -q`. Do not modify tests.
