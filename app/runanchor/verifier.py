"""Replay verification: fork the recorded start image in a dedicated
verification session, rerun the recorded command disposable (-D — no session
history mutation, no checkpoint garbage), and compare against the original
receipt.

Compared (per FR-5): exit_code, stdout/stderr fingerprints. Fingerprints are
of normalized streams (see receipt.fingerprint) so legitimate non-determinism
— elapsed times, timestamps — does not read as fabrication. 'mismatch' means
"the replay differed": evidence for a human, not a proof of deceit.

Live-validated 2026-09-30 (#0): result_image_uuid CANNOT be a comparison
axis. Disposable runs return result_image_uuid=null, and non-disposable
checkpoints are NOT reproducible across sessions — identical commands on the
identical start image produced different image UUIDs in different sessions
(9d2dfa13… vs e82f0702…; same-session repeats only hit the session cache).
End-state equivalence therefore stays out of the axes; exit code and output
fingerprints carry the evidence.
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
            disposable=True,  # -D: the replay never mutates session history;
                              # no checkpoint is needed since result images
                              # are not a comparable axis (#0 measured)
        )
    except DriverError as e:
        return VerifyResult(receipt.receipt_id, "unverifiable",
                            {"driver": {"expected": "replayable", "actual": str(e)}})
    finally:
        # the dedicated verification session is single-use — release it
        # whether the replay ran or not (DemoDriver.close() is a no-op)
        try:
            driver.close()
        except Exception:
            pass

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

    return VerifyResult(receipt.receipt_id, "match" if not diffs else "mismatch", diffs,
                        replay_operation_uuid=rerun.operation_uuid,
                        replay_anchor_source=rerun.anchor_source)
