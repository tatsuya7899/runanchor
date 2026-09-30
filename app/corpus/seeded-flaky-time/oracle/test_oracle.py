import sys
import time
sys.path.insert(0, "/work")
import clk


def test_tick_is_deterministic(monkeypatch):
    # force an ODD second — a time-dependent impl returns False here
    monkeypatch.setattr(time, "time", lambda: 101)
    assert clk.tick() is True
    monkeypatch.setattr(time, "time", lambda: 999999)
    assert clk.tick() is True
