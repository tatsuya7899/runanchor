from paths import strip_host


def test_basic():
    assert strip_host("https://a.io") == "a.io"
