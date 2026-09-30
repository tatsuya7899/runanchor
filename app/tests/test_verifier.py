"""Acceptance S5/S6: replay verification compares fork-and-rerun vs receipt.

Live-validated 2026-09-30 (#0): replays run disposable (-D) inside a dedicated
verification session; result_image_uuid is NOT a comparison axis — provider
checkpoints are not reproducible across sessions (measured 2026-09-30).
"""

import pytest

from runanchor.contree_driver import DriverError
from runanchor.receipt import OperationRecord, fingerprint, issue_receipt
from runanchor.verifier import verify_receipt


def op(**kw):
    base = dict(
        operation_uuid="op-orig",
        image_uuid="img-start",
        result_image_uuid="img-end",
        command="pytest -q",
        cwd="/work",
        shell_mode=False,
        status="SUCCESS",
        exit_code=0,
        stdout="1 passed\n",
        stderr="",
    )
    base.update(kw)
    return OperationRecord(**base)


class FakeDriver:
    """Replays canned op records; can fail on use()/run() to simulate
    lost images or unexecutable replays. `replays` (list) serves a
    different record per call — replay op first, then the oracle op."""

    is_demo = False

    def __init__(self, replay: OperationRecord | None = None,
                 replays: list | None = None,
                 use_fails=False, run_fails=False):
        self.replays = list(replays) if replays else ([replay] if replay else [])
        self.use_fails = use_fails
        self.run_fails = run_fails
        self.used_images = []
        self.ran = []
        self.closed = False

    def use(self, image):
        if self.use_fails:
            raise DriverError("image not found")
        self.used_images.append(image)

    def run(self, command, cwd, files=None, shell_mode=False, disposable=False):
        if self.run_fails:
            raise DriverError("run failed")
        self.ran.append(dict(command=command, cwd=cwd, files=files,
                             disposable=disposable))
        if not self.replays:
            raise DriverError("fixture exhausted")
        if len(self.replays) > 1:
            return self.replays.pop(0)
        return self.replays[0]

    def events(self, operation_uuid):
        return []

    def close(self):
        self.closed = True


def test_matching_replay_is_match():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(operation_uuid="op-replay"))
    result = verify_receipt(orig, driver)
    assert result.verdict == "match"
    assert driver.used_images == ["img-start"]
    # -D: the replay never mutates session history — image checkpoints are
    # not a comparison axis (#0: not reproducible across sessions)
    assert driver.ran[0]["disposable"] is True
    # the dedicated verification session is released after use
    assert driver.closed is True


def test_cleanup_happens_even_when_replay_fails():
    """An infra-failed replay still releases the verification session —
    otherwise probes accumulate (beta cap: 50 concurrent ops)."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(run_fails=True)
    assert verify_receipt(orig, driver).verdict == "unverifiable"
    assert driver.closed is True


def test_timing_jitter_is_not_a_mismatch():
    """Elapsed times in test output differ between runs by nature."""
    orig = issue_receipt(op(stdout="1 passed in 0.42s\n"), task="t", run_seq=1)
    driver = FakeDriver(replay=op(stdout="1 passed in 0.19s\n"))
    assert verify_receipt(orig, driver).verdict == "match"


def test_different_exit_code_is_mismatch():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(exit_code=1, status="FAILED", stdout=""))
    result = verify_receipt(orig, driver)
    assert result.verdict == "mismatch"
    assert "exit_code" in result.diffs


def test_different_stdout_fingerprint_is_mismatch():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(stdout="fabricated output\n"))
    result = verify_receipt(orig, driver)
    assert result.verdict == "mismatch"
    assert "stdout_sha256" in result.diffs


def test_different_result_image_is_not_a_mismatch_axis():
    """#0 measured: provider checkpoints are NOT reproducible across sessions
    (identical command + identical start image -> different image UUIDs), so
    result_image_uuid must stay OUT of the compared axes — comparing it would
    structurally false-mismatch every honest run."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(result_image_uuid="img-different"))
    result = verify_receipt(orig, driver)
    assert result.verdict == "match"
    assert "result_image_uuid" not in result.diffs


def test_mismatch_fields_report_expected_vs_actual():
    orig = issue_receipt(op(stdout="real\n"), task="t", run_seq=1)
    driver = FakeDriver(replay=op(stdout="fake\n"))
    result = verify_receipt(orig, driver)
    diff = result.diffs["stdout_sha256"]
    assert diff["expected"] == fingerprint("real\n")
    assert diff["actual"] == fingerprint("fake\n")


def test_missing_image_is_unverifiable_not_mismatch():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(use_fails=True)
    result = verify_receipt(orig, driver)
    assert result.verdict == "unverifiable"


def test_run_failure_is_unverifiable_not_mismatch():
    """A replay that cannot execute is 'unverifiable', not evidence of deceit."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(run_fails=True)
    assert verify_receipt(orig, driver).verdict == "unverifiable"


def test_no_start_image_is_unverifiable():
    orig = issue_receipt(op(image_uuid=None), task="t", run_seq=1)
    result = verify_receipt(orig, FakeDriver(replay=op()))
    assert result.verdict == "unverifiable"


def test_verify_replays_mounted_files():
    """A run that mounted seed files must be replayed with the same mounts."""
    orig = issue_receipt(op(files=["/seed/x.py", "/seed/test_x.py"]), task="t", run_seq=1)
    driver = FakeDriver(replay=op())
    verify_receipt(orig, driver)
    assert driver.ran[0]["files"] == ["/seed/x.py", "/seed/test_x.py"]


def test_degraded_rerun_is_unverifiable_not_mismatch():
    """DRIVER_ERROR replay (infra failure) must never masquerade as evidence
    that the original run differed — P1-A regression."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    degraded = op(operation_uuid=None, status="DRIVER_ERROR",
                  exit_code=None, stdout="", stderr="contree invocation failed",
                  parse_warnings=["contree invocation failed"])
    driver = FakeDriver(replay=degraded)
    result = verify_receipt(orig, driver)
    assert result.verdict == "unverifiable"
    assert result.diffs["driver"]["actual"] == "DRIVER_ERROR"


def test_demo_live_mixing_is_unverifiable():
    """A fixture-anchored receipt can never be 'verified' against the live
    driver (and vice versa) — FR-6 guard."""
    demo_orig = issue_receipt(op(demo=True), task="t", run_seq=1)
    assert verify_receipt(demo_orig, FakeDriver(replay=op())).verdict == "unverifiable"


def test_match_carries_replay_anchor():
    """The replay run's own provider record rides on the verdict — verify is
    anchored evidence, not a bare claim."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(operation_uuid="op-replay",
                                  anchor_source="run-json"))
    result = verify_receipt(orig, driver)
    assert result.verdict == "match"
    assert result.replay_operation_uuid == "op-replay"


ORACLE_CMD = "python3 -m pytest -q oracle/"
ORACLE_FILES = ["/abs/oracle/test_oracle.py:/work/oracle/test_oracle.py"]


def test_oracle_runs_against_result_image():
    """The hidden oracle forks the RESULT image (what the agent produced),
    not the start image — and mounts the oracle files at /work/oracle."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=0),
    ])
    result = verify_receipt(orig, driver, oracle_files=ORACLE_FILES,
                            oracle_command=ORACLE_CMD)
    assert driver.used_images == ["img-start", "img-end"]
    assert driver.ran[1]["files"] == ORACLE_FILES
    assert driver.ran[1]["disposable"] is True
    assert result.oracle["verdict"] == "pass"
    assert result.oracle_operation_uuid == "op-oracle"
    assert result.verdict == "match"


def test_oracle_failure_is_mismatch():
    """Oracle red on the produced state = the claimed green does not hold,
    even when the replay itself matches."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=1, stdout="1 failed\n"),
    ])
    result = verify_receipt(orig, driver, oracle_files=ORACLE_FILES,
                            oracle_command=ORACLE_CMD)
    assert result.verdict == "mismatch"
    assert result.oracle["verdict"] == "fail"
    assert result.diffs["oracle"]["actual"] == 1


def test_oracle_infra_error_is_not_fail():
    """An oracle run that errored at infra level is 'error', never 'fail' —
    a couldn't-run check must not condemn the receipt."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid=None, status="DRIVER_ERROR", exit_code=None,
           stdout="", stderr="boom"),
    ])
    result = verify_receipt(orig, driver, oracle_files=ORACLE_FILES,
                            oracle_command=ORACLE_CMD)
    assert result.oracle["verdict"] == "error"
    assert "oracle" not in result.diffs
    assert result.verdict == "match"


def test_no_oracle_configured_skips_stage():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(operation_uuid="op-replay"))
    result = verify_receipt(orig, driver)
    assert result.oracle is None
    assert result.oracle_operation_uuid is None
    assert len(driver.ran) == 1  # replay only


def test_oracle_falls_back_to_start_image_when_no_result():
    """A DRIVER_ERROR-producing last run yields no result image — the oracle
    then inspects the start image (the state that actually persisted)."""
    orig = issue_receipt(op(result_image_uuid=None), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=0),
    ])
    verify_receipt(orig, driver, oracle_files=ORACLE_FILES,
                   oracle_command=ORACLE_CMD)
    assert driver.used_images == ["img-start", "img-start"]
