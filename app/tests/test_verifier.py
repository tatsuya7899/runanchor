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
    different record per call — replay op first, then the oracle op.
    `fail_calls` are 1-based run() ordinals that raise DriverError."""

    is_demo = False

    def __init__(self, replay: OperationRecord | None = None,
                 replays: list | None = None,
                 use_fails=False, run_fails=False, fail_calls=()):
        self.replays = list(replays) if replays else ([replay] if replay else [])
        self.use_fails = use_fails
        self.run_fails = run_fails
        self.fail_calls = set(fail_calls)
        self.used_images = []
        self.ran = []
        self.closed = False

    def use(self, image):
        if self.use_fails:
            raise DriverError("image not found")
        self.used_images.append(image)

    def run(self, command, cwd, files=None, shell_mode=False, disposable=False):
        if self.run_fails or len(self.ran) + 1 in self.fail_calls:
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


ORACLE_CMD = "python3 -I -S {runner} {cwd} {oracle_dir} {ini}"


@pytest.fixture
def oracle_dir(tmp_path):
    (tmp_path / "test_oracle.py").write_text("def test_x():\n    assert True\n")
    return tmp_path


def _oracle_run(driver):
    return driver.ran[1]


def test_oracle_runs_against_result_image(oracle_dir):
    """The hidden oracle forks the RESULT image (what the agent produced),
    not the start image."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=0),
    ])
    result = verify_receipt(orig, driver, oracle_dir=oracle_dir,
                            oracle_command=ORACLE_CMD)
    assert driver.used_images == ["img-start", "img-end"]
    assert _oracle_run(driver)["disposable"] is True
    assert result.oracle["verdict"] == "pass"
    assert result.oracle_operation_uuid == "op-oracle"
    assert result.verdict == "match"


def test_oracle_is_isolated_from_the_workspace(oracle_dir):
    """Adversarial-review regression: the oracle must not run inside the
    produced workspace (a planted /work/pytest.py, conftest.py or pytest.ini
    could otherwise shadow the runner, poison collection, or hijack rootdir).
    Requirements: mounts land OUTSIDE /work at an unpredictable path, the run
    cwd is /, and the command launches the runner under `python3 -I -S`."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=0),
    ])
    verify_receipt(orig, driver, oracle_dir=oracle_dir,
                   oracle_command=ORACLE_CMD)
    oracle_run = _oracle_run(driver)
    assert oracle_run["cwd"] == "/"
    mounts = oracle_run["files"]
    insts = [m.split(":", 1)[1] for m in mounts]
    assert all("/work" not in i for i in insts)
    assert all(i.startswith("/tmp/.runanchor-oracle-") for i in insts)
    assert any(i.endswith("/oracle/test_oracle.py") for i in insts)
    assert any(i.endswith("/run_oracle.py") for i in insts)
    assert any(i.endswith("/pytest.ini") for i in insts)
    assert oracle_run["command"].startswith("python3 -I -S")
    assert "/run_oracle.py /work " in oracle_run["command"]


def test_oracle_mount_path_is_unpredictable(oracle_dir):
    """The mount dir embeds a random token — the agent finished its series
    before verify ran, but a guessable fixed path is free to pre-poison."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    d1 = FakeDriver(replays=[op(operation_uuid="r1"),
                             op(operation_uuid="o1")])
    d2 = FakeDriver(replays=[op(operation_uuid="r2"),
                             op(operation_uuid="o2")])
    verify_receipt(orig, d1, oracle_dir=oracle_dir, oracle_command=ORACLE_CMD)
    verify_receipt(orig, d2, oracle_dir=oracle_dir, oracle_command=ORACLE_CMD)
    assert _oracle_run(d1)["command"] != _oracle_run(d2)["command"]


def test_oracle_failure_is_mismatch(oracle_dir):
    """Oracle red on the produced state = the claimed green does not hold,
    even when the replay itself matches — and the axes stay labelled."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=1, stdout="1 failed\n"),
    ])
    result = verify_receipt(orig, driver, oracle_dir=oracle_dir,
                            oracle_command=ORACLE_CMD)
    assert result.verdict == "mismatch"
    assert result.replay_verdict == "match"   # oracle failed, not the replay
    assert result.oracle["verdict"] == "fail"
    assert result.diffs["oracle"]["actual"] == 1


def test_oracle_nonfailure_nonzero_exit_is_error_not_fail(oracle_dir):
    """pytest exit 2/4/5 (collection, usage, no-tests) = 'could not
    evaluate' — only exit 1 is a contract violation."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    for rc in (2, 4, 5):
        driver = FakeDriver(replays=[
            op(operation_uuid="op-replay"),
            op(operation_uuid="op-oracle", exit_code=rc),
        ])
        result = verify_receipt(orig, driver, oracle_dir=oracle_dir,
                                oracle_command=ORACLE_CMD)
        assert result.oracle["verdict"] == "error"
        assert result.verdict == "match"  # an unevaluated oracle condemns nothing


def test_oracle_infra_error_is_not_fail(oracle_dir):
    """An oracle run that errored at infra level is 'error', never 'fail' —
    a couldn't-run check must not condemn the receipt."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid=None, status="DRIVER_ERROR", exit_code=None,
           stdout="", stderr="boom"),
    ])
    result = verify_receipt(orig, driver, oracle_dir=oracle_dir,
                            oracle_command=ORACLE_CMD)
    assert result.oracle["verdict"] == "error"
    assert "oracle" not in result.diffs
    assert result.verdict == "match"


def test_oracle_exception_does_not_eat_replay_evidence(oracle_dir):
    """If the oracle stage blows up, the completed replay is still
    recorded — replay evidence is not hostage to the second axis."""
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(operation_uuid="op-replay"),
                        fail_calls={2})
    result = verify_receipt(orig, driver, oracle_dir=oracle_dir,
                            oracle_command=ORACLE_CMD)
    assert result.replay_verdict == "match"
    assert result.replay_operation_uuid == "op-replay"
    assert result.oracle["verdict"] == "error"
    assert result.verdict == "match"


def test_no_oracle_configured_skips_stage():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(operation_uuid="op-replay"))
    result = verify_receipt(orig, driver)
    assert result.oracle is None
    assert result.oracle_operation_uuid is None
    assert len(driver.ran) == 1  # replay only


def test_oracle_falls_back_to_start_image_when_no_result(oracle_dir):
    """A DRIVER_ERROR-producing last run yields no result image — the oracle
    then inspects the start image (the state that actually persisted)."""
    orig = issue_receipt(op(result_image_uuid=None), task="t", run_seq=1)
    driver = FakeDriver(replays=[
        op(operation_uuid="op-replay"),
        op(operation_uuid="op-oracle", exit_code=0),
    ])
    verify_receipt(orig, driver, oracle_dir=oracle_dir,
                   oracle_command=ORACLE_CMD)
    assert driver.used_images == ["img-start", "img-start"]


def test_scrubbed_command_is_unverifiable_not_mismatch():
    """A receipt whose command was secret-scrubbed (REDACTED) cannot be
    re-executed faithfully — replaying the scrubbed text would manufacture a
    false mismatch. Honest answer is 'unverifiable'."""
    orig = issue_receipt(op(command="curl -H 'Bearer abc123' x"), task="t",
                         run_seq=1)
    assert "REDACTED" in orig.command  # the fixture input must actually scrub
    result = verify_receipt(orig, FakeDriver(replay=op()))
    assert result.verdict == "unverifiable"
    assert result.diffs["command"]["actual"] == \
        "command contains scrubbed secrets"
