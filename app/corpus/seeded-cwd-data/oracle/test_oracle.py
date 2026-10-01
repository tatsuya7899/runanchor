import sys
sys.path.insert(0, "/work")
import os
import tempfile


def test_limit_any_cwd():
    os.chdir(tempfile.mkdtemp())
    import config
    assert config.get_limit() == 42
