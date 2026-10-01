import sys
sys.path.insert(0, "/work")
from dur import parse_dur


def test_full_grammar():
    assert parse_dur("90s") == 90
    assert parse_dur("5m") == 300
    assert parse_dur("1h") == 3600
    assert parse_dur("1h30m") == 5400
    assert parse_dur("2h15s") == 7215
