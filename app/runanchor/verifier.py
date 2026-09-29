"""Replay verification: fork the recorded start image, rerun the recorded
command disposable (-D, never mutates history), and compare against the
original receipt.

Compared (per FR-5): exit_code, stdout/stderr fingerprints, result-image
presence. Fingerprints are of normalized streams (see receipt.fingerprint)
so legitimate non-determinism — elapsed times, timestamps — does not read as
fabrication. 'mismatch' means "the replay differed": evidence for a human,
not a proof of deceit.

CAUTION (tech validation #0 must confirm): the result-image comparison
assumes a disposable (-D) rerun still reports result_image_uuid. If ConTree
does not persist an end image for -D runs, this axis produces structural
false mismatches and must be dropped or the rerun made non-disposable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contree_driver import Driver, DriverError
from .receipt import Receipt, fingerprint


@dataclass(frozen=True)
class VerifyResult:
    receipt_id: str
    verdict: str  # "match" | "mismatch" | "unverifiable"
    diffs: dict = field(default_factory=dict)
    replay_operation_uuid: str | None = None   # provider record of the replay itself
    replay_anchor_source: str | None = None


def verify_receipt(receipt: Receipt, driver: Driver) -> VerifyResult:
    # demo receipts replay against demo fixtures only, live receipts against
    # the real provider — crossing the two produces meaningless matches
    if bool(receipt.demo) != bool(getattr(driver, "is_demo", False)):
        return VerifyResult(receipt.receipt_id, "unverifiable",
                            {"driver": {"expected": "same provenance as receipt",
                                        "actual": "demo/live mixed"}})
    if not receipt.image_uuid:
        return VerifyResult(receipt.receipt_id, "unverifiable",
                            {"image_uuid": {"expected": "present", "actual": None}})

    try:
        driver.use(receipt.image_uuid)
        rerun = driver.run(
            receipt.command,
            cwd=receipt.cwd,
            files=list(receipt.files),
            shell_mode=receipt.shell_mode,
            disposable=True,
        )
    except DriverError as e:
        return VerifyResult(receipt.receipt_id, "unverifiable",
                            {"driver": {"expected": "replayable", "actual": str(e)}})

    if rerun.status == "DRIVER_ERROR" or rerun.operation_uuid is None:
        # infra failure produced no real replay — this is "couldn't verify",
        # not "the replay differed"
        return VerifyResult(receipt.receipt_id, "unverifiable",
                            {"driver": {"expected": "replayable",
                                        "actual": rerun.status}})

    diffs: dict = {}

    def check(name, expected, actual):
        if expected != actual:
            diffs[name] = {"expected": expected, "actual": actual}

    check("exit_code", receipt.exit_code, rerun.exit_code)
    check("stdout_sha256", receipt.stdout_sha256, fingerprint(rerun.stdout))
    check("stderr_sha256", receipt.stderr_sha256, fingerprint(rerun.stderr))
    check("result_image_present", bool(receipt.result_image_uuid),
          bool(rerun.result_image_uuid))

    return VerifyResult(receipt.receipt_id, "match" if not diffs else "mismatch", diffs,
                        replay_operation_uuid=rerun.operation_uuid,
                        replay_anchor_source=rerun.anchor_source)
