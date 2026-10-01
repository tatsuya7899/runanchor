import sys
sys.path.insert(0, "/work")
from paths import strip_host


def test_scheme_chars_in_host():
    assert strip_host("https://site.com") == "site.com"
    assert strip_host("https://httpbin.org") == "httpbin.org"
    assert strip_host("https://a.io") == "a.io"
