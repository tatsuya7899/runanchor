Fix `calc.safe_div(a, b)` so it returns None when b == 0 and a/b otherwise.
The first attempt may look right but fails on the division-by-zero edge.
`pytest -q` must pass.
