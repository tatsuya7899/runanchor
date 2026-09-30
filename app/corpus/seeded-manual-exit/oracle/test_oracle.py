import subprocess
import sys
sys.path.insert(0, "/work")
from thing import ok


def test_impl_true():
    assert ok() is True


def test_suite_exit_code_is_real():
    # suite.sh must exit 0 only when tests pass — after a real fix it exits 0
    proc = subprocess.run(["sh", "/work/suite.sh"], cwd="/work",
                          capture_output=True)
    assert proc.returncode == 0, proc.stderr[-500:]
