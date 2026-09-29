"""Acceptance S5/S6: replay verification compares fork-and-rerun vs receipt."""

import hashlib

import pytest

from runanchor.contree_driver import DriverError
from runanchor.receipt import OperationRecord, issue_receipt
from runanchor.verifier import verify_receipt


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


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
    """Replays a canned op record; can fail on use() to simulate lost images."""

    def __init__(self, replay: OperationRecord | None = None, use_fails=False):
        self.replay = replay
        self.use_fails = use_fails
        self.used_images = []
        self.ran = []

    def use(self, image):
        if self.use_fails:
            raise DriverError("image not found")
        self.used_images.append(image)

    def run(self, command, cwd, files=None, shell_mode=False, disposable=False):
        self.ran.append(dict(command=command, cwd=cwd, disposable=disposable))
        return self.replay

    def events(self, operation_uuid):
        return []


def test_matching_replay_is_match():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(operation_uuid="op-replay"))
    result = verify_receipt(orig, driver)
    assert result.verdict == "match"
    assert driver.used_images == ["img-start"]
    assert driver.ran[0]["disposable"] is True  # -D: verify never mutates history


def test_different_exit_code_is_mismatch():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(exit_code=1, status="FAILURE", stdout=""))
    result = verify_receipt(orig, driver)
    assert result.verdict == "mismatch"
    assert "exit_code" in result.diffs


def test_different_stdout_fingerprint_is_mismatch():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(replay=op(stdout="fabricated output\n"))
    result = verify_receipt(orig, driver)
    assert result.verdict == "mismatch"
    assert "stdout_sha256" in result.diffs


def test_missing_image_is_unverifiable_not_mismatch():
    orig = issue_receipt(op(), task="t", run_seq=1)
    driver = FakeDriver(use_fails=True)
    result = verify_receipt(orig, driver)
    assert result.verdict == "unverifiable"


def test_no_start_image_is_unverifiable():
    orig = issue_receipt(op(image_uuid=None), task="t", run_seq=1)
    result = verify_receipt(orig, FakeDriver(replay=op()))
    assert result.verdict == "unverifiable"


def test_mismatch_fields_report_expected_vs_actual():
    orig = issue_receipt(op(stdout="real\n"), task="t", run_seq=1)
    driver = FakeDriver(replay=op(stdout="fake\n"))
    result = verify_receipt(orig, driver)
    diff = result.diffs["stdout_sha256"]
    assert diff["expected"] == sha("real\n")
    assert diff["actual"] == sha("fake\n")
