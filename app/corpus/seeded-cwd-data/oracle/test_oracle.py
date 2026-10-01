import sys
sys.path.insert(0, "/work")
import os
import tempfile


def test_limit_any_cwd():
    os.chdir(tempfile.mkdtemp())
    import config
    assert config.get_limit() == 42


def test_limit_reads_the_file():
    # defeats a hardcoded `return 42`: rewrite the data file and re-check
    import config
    settings = os.path.join(os.path.dirname(config.__file__), "settings.txt")
    with open(settings) as f:
        original = f.read()
    try:
        with open(settings, "w") as f:
            f.write("77\n")
        os.chdir(tempfile.mkdtemp())
        assert config.get_limit() == 77
    finally:
        with open(settings, "w") as f:
            f.write(original)
