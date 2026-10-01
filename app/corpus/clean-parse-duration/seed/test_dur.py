from dur import parse_dur


def test_minutes():
    assert parse_dur("5m") == 300
