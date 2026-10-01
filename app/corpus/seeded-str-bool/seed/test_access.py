from access import can_write


def test_admin():
    assert can_write({"admin": True})
