from fetcher import headline

def test_headline(monkeypatch):
    class R:
        text = "<html><title>hi</title></html>"
    monkeypatch.setattr("fetcher.requests.get", lambda *a, **k: R())
    assert headline("http://x") == "hi"
