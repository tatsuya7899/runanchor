import urllib.request

from fetcher import headline


def test_headline(monkeypatch):
    class R:
        def read(self):
            return b"<html><title>hi</title></html>"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: R())
    assert headline("http://x") == "hi"
