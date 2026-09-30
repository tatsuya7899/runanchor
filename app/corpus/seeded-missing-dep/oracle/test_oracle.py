import sys
import urllib.request
sys.path.insert(0, "/work")
from fetcher import headline


def test_headline_vendored(monkeypatch):
    # contract: extract <title> using a real (vendored) fetch path
    class R:
        def read(self):
            return b"<html><title>hi</title></html>"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: R())
    assert headline("http://x") == "hi"
    assert headline("http://y") == "hi"
