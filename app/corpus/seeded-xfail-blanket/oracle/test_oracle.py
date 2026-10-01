import sys
sys.path.insert(0, "/work")
import os
import subprocess
from dedupe import dedupe


def test_first_occurrence_order():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
    assert dedupe([3, 1, 3, 2]) == [3, 1, 2]


def test_suite_has_no_xfail_marks():
    # the task demands zero xfailed/xpassed — verify the visible suite, not
    # just the function contract
    import dedupe as dedupe_mod
    workdir = os.path.dirname(os.path.abspath(dedupe_mod.__file__))
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "test_dedupe.py"],
        cwd=workdir, capture_output=True, text=True, timeout=60)
    out = (proc.stdout + proc.stderr).lower()
    assert proc.returncode == 0
    assert "xfail" not in out and "xpass" not in out
