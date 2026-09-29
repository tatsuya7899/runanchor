"""Replay verification: fork the recorded start image, rerun the recorded
command disposable (-D, never mutates history), and compare against the
original receipt.

Compared: exit_code, stdout/stderr SHA-256 fingerprints, presence of a
result image (per FR-5). If the recorded start image is gone or absent the
receipt is 'unverifiable' — distinct from 'mismatch'.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .contree_driver import Driver, DriverError
from .receipt import Receipt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class VerifyResult:
    receipt_id: str
    verdict: str  # "match" | "mismatch" | "unverifiable"
    diffs: dict = field(default_factory=dict)


def verify_receipt(receipt: Receipt, driver: Driver) -> VerifyResult:
    if not receipt.image_uuid:
        return VerifyResult(receipt.receipt_id, "unverifiable", {"image_uuid": {"expected": "present", "actual": None}})

    try:
        driver.use(receipt.image_uuid)
    except DriverError:
        return VerifyResult(receipt.receipt_id, "unverifiable", {"image_uuid": {"expected": receipt.image_uuid, "actual": "not found"}})

    rerun = driver.run(
        receipt.command,
        cwd=receipt.cwd,
        shell_mode=receipt.shell_mode,
        disposable=True,
    )

    diffs: dict = {}

    def check(name, expected, actual):
        if expected != actual:
            diffs[name] = {"expected": expected, "actual": actual}

    check("exit_code", receipt.exit_code, rerun.exit_code)
    check("stdout_sha256", receipt.stdout_sha256, _sha256(rerun.stdout))
    check("stderr_sha256", receipt.stderr_sha256, _sha256(rerun.stderr))
    check("result_image_present", bool(receipt.result_image_uuid), bool(rerun.result_image_uuid))

    return VerifyResult(receipt.receipt_id, "match" if not diffs else "mismatch", diffs)
