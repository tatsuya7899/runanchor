"""Replay + oracle verification.

Phase 1 — evidence replay: fork the recorded START image in a dedicated
verification session, rerun the recorded command disposable (-D — no session
history mutation, no checkpoint garbage), and compare against the original
receipt. Compared (per FR-5): exit_code, stdout/stderr fingerprints.
Fingerprints are of normalized streams (see receipt.fingerprint) so
legitimate non-determinism — elapsed times, timestamps — does not read as
fabrication. 'mismatch' means "the replay differed": evidence for a human,
not a proof of deceit.

Phase 2 — oracle check (optional): fork the recorded RESULT image and run a
hidden oracle command the agent never saw (e.g. a held-out test suite mounted
at /work/oracle). Evidence replay proves the reported evidence is reproducible;
the oracle proves the PRODUCED STATE satisfies the real contract — the layer a
stdout tail can never see (hardcoded answers, dropped boundaries, mutated
inputs). Oracle failure counts as mismatch: the claimed green does not hold.

Live-validated 2026-09-30 (#0): result_image_uuid CANNOT be a comparison
axis for equality — disposable runs return null and checkpoints are not
reproducible across sessions. But a result image CAN be forked and inspected,
which is what the oracle stage does.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .contree_driver import Driver, DriverError
from .receipt import Receipt, fingerprint


def _expand(spec: str) -> str:
    """receipt.files are home-scrubbed ("~/...") for publishable ledgers;
    expand back before handing the mount spec to the driver."""
    host, sep, inst = spec.partition(":")
    return f"{os.path.expanduser(host)}:{inst}" if sep else spec


@dataclass(frozen=True)
class VerifyResult:
    receipt_id: str
    verdict: str  # "match" | "mismatch" | "unverifiable"
    diffs: dict = field(default_factory=dict)
    replay_operation_uuid: str | None = None   # provider record of the replay itself
    replay_anchor_source: str | None = None
    oracle: dict | None = None                 # {"verdict","exit_code","command","operation_uuid",...}
    oracle_operation_uuid: str | None = None   # provider record of the oracle run

    @property
    def oracle_verdict(self) -> str | None:
        return (self.oracle or {}).get("verdict")


def _unverifiable(receipt, diffs) -> VerifyResult:
    return VerifyResult(receipt.receipt_id, "unverifiable", diffs)


def verify_receipt(receipt: Receipt, driver: Driver, *,
                   oracle_files: list[str] | None = None,
                   oracle_command: str | None = None) -> VerifyResult:
    # demo receipts replay against demo fixtures only, live receipts against
    # the real provider — crossing the two produces meaningless matches
    if bool(receipt.demo) != bool(getattr(driver, "is_demo", False)):
        return _unverifiable(receipt,
                             {"driver": {"expected": "same provenance as receipt",
                                         "actual": "demo/live mixed"}})
    if not receipt.image_uuid:
        return _unverifiable(receipt,
                             {"image_uuid": {"expected": "present", "actual": None}})

    try:
        driver.use(receipt.image_uuid)
        rerun = driver.run(
            receipt.command,
            cwd=receipt.cwd,
            files=[_expand(f) for f in receipt.files],
            shell_mode=receipt.shell_mode,
            disposable=True,  # -D: the replay never mutates session history;
                              # no checkpoint is needed since result images
                              # are not a comparable axis (#0 measured)
        )
        oracle = _run_oracle(receipt, driver, oracle_files, oracle_command)
    except DriverError as e:
        return _unverifiable(receipt,
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
        return _unverifiable(receipt,
                             {"driver": {"expected": "replayable",
                                         "actual": rerun.status}})

    diffs: dict = {}

    def check(name, expected, actual):
        if expected != actual:
            diffs[name] = {"expected": expected, "actual": actual}

    check("exit_code", receipt.exit_code, rerun.exit_code)
    check("stdout_sha256", receipt.stdout_sha256, fingerprint(rerun.stdout))
    check("stderr_sha256", receipt.stderr_sha256, fingerprint(rerun.stderr))

    oracle_record = None
    oracle_op_uuid = None
    if oracle is not None:
        oracle_op = oracle["op"]
        oracle_op_uuid = oracle_op.operation_uuid
        if oracle_op.status == "DRIVER_ERROR" or oracle_op.operation_uuid is None:
            # oracle could not run — the check itself failed, keep the run's
            # evidence verdict but mark the oracle axis honestly
            oracle_record = {"verdict": "error", "command": oracle["command"],
                             "operation_uuid": None,
                             "stdout_tail": oracle_op.stderr[-500:]}
        else:
            oracle_record = {"verdict": "pass" if oracle_op.exit_code == 0 else "fail",
                             "command": oracle["command"],
                             "operation_uuid": oracle_op.operation_uuid,
                             "exit_code": oracle_op.exit_code,
                             "stdout_tail": oracle_op.stdout[-500:]}
            if oracle_op.exit_code != 0:
                diffs["oracle"] = {"expected": "oracle exit 0",
                                   "actual": oracle_op.exit_code,
                                   "stdout_tail": oracle_op.stdout[-500:]}

    return VerifyResult(receipt.receipt_id, "match" if not diffs else "mismatch", diffs,
                        replay_operation_uuid=rerun.operation_uuid,
                        replay_anchor_source=rerun.anchor_source,
                        oracle=oracle_record,
                        oracle_operation_uuid=oracle_op_uuid)


def _run_oracle(receipt: Receipt, driver: Driver,
                oracle_files, oracle_command):
    """Run the hidden contract check against the RESULT image — the end state
    the agent actually produced. Returns {"op", "command"} or None when no
    oracle was configured or no result state exists to inspect."""
    if not oracle_command:
        return None
    target = receipt.result_image_uuid or receipt.image_uuid
    if not target:
        return None
    driver.use(target)
    op = driver.run(oracle_command, cwd=receipt.cwd,
                    files=[_expand(f) for f in oracle_files or []],
                    shell_mode=True, disposable=True)
    return {"op": op, "command": oracle_command}
