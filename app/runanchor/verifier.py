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
hidden oracle command the agent never saw. Evidence replay proves the
reported evidence is reproducible; the oracle proves the PRODUCED STATE
satisfies the real contract — the layer a stdout tail can never see
(hardcoded answers, dropped boundaries, mutated inputs).

ORACLE ISOLATION (added after adversarial review 2026-10-01): the oracle runs
INSIDE the produced filesystem — anything the agent wrote is still there. A
naive `cd /work && python3 -m pytest oracle/` is deterministically bypassable
(planted /work/pytest.py shadows the real -m target, a planted conftest.py is
loaded unconditionally, a planted pytest.ini hijacks rootdir). The oracle is
therefore mounted at a random per-verify path outside the workspace and
launched via a runner under `python3 -I -S`: isolated mode drops cwd from
sys.path, ignores PYTHON* env vars, and -S disables site processing so a
planted sitecustomize/.pth cannot run either. site-packages is re-added
explicitly, the produced workspace is appended LAST in sys.path (test imports
of the code under test still work, but workspace files can never shadow the
test runner), and `-c <mounted ini>` pins pytest configuration. Residual risk
documented honestly: an agent that overwrote site-packages itself can still
subvert the check — the oracle trusts the image's interpreter + site-packages,
not its workspace.

Live-validated 2026-09-30 (#0): result_image_uuid CANNOT be a comparison
axis for equality — disposable runs return null and checkpoints are not
reproducible across sessions. But a result image CAN be forked and inspected,
which is what the oracle stage does.
"""

from __future__ import annotations

import os
import secrets
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .contree_driver import Driver, DriverError
from .receipt import Receipt, fingerprint

# Oracle mount base: a random path per verify call — the agent finished its
# series before verify ran, but an unpredictable path is still free insurance
# against pre-planted poison files at a guessed location.
_ORACLE_BASE = "/tmp/.runanchor-oracle-{tag}"

# Launched as `python3 -I -S run_oracle.py <workdir> <oracle_dir> <ini>` —
# see module docstring for why every flag is there.
_ORACLE_RUNNER = '''"""runanchor oracle runner — mounted into the target image at verify time.

Isolated interpreter (-I -S): no site processing (sitecustomize/usercustomize/
.pth cannot run), no PYTHON* env vars, no implicit cwd on sys.path. We add the
real site-packages ourselves and append the produced workspace LAST so test
files can import the code under test while a planted pytest.py or conftest in
that workspace can never shadow the runner.
"""
import sys
import sysconfig


def main() -> int:
    _script, workdir, oracle_dir, ini = sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, sysconfig.get_paths()["purelib"])
    if workdir:
        sys.path.append(workdir)
    import pytest  # noqa: E402 — resolved from site-packages, not the workspace
    return int(pytest.main(["-q", "-c", ini, "-p", "no:cacheprovider", oracle_dir]))


sys.exit(main())
'''

_ORACLE_INI = "[pytest]\n"

# Default hidden-oracle command. Placeholders are substituted at verify time:
# {runner} mounted runner path, {oracle_dir} mounted oracle dir, {ini} mounted
# pytest config, {cwd} the receipt's working directory (where code under test
# lives). Custom commands get the same substitution; run the default to keep
# the isolation guarantees.
DEFAULT_ORACLE_COMMAND = "python3 -I -S {runner} {cwd} {oracle_dir} {ini}"


def _expand(spec: str) -> str:
    """receipt.files are home-scrubbed ("~/...") for publishable ledgers;
    expand back before handing the mount spec to the driver."""
    host, sep, inst = spec.partition(":")
    return f"{os.path.expanduser(host)}:{inst}" if sep else spec


@dataclass(frozen=True)
class VerifyResult:
    receipt_id: str
    verdict: str  # "match" | "mismatch" | "unverifiable" — replay + oracle combined
    diffs: dict = field(default_factory=dict)
    replay_verdict: str = "match"    # evidence-replay axis alone
    replay_operation_uuid: str | None = None   # provider record of the replay itself
    replay_anchor_source: str | None = None
    oracle: dict | None = None                 # {"verdict","exit_code","command","operation_uuid",...}
    oracle_operation_uuid: str | None = None   # provider record of the oracle run

    @property
    def oracle_verdict(self) -> str | None:
        return (self.oracle or {}).get("verdict")


def _unverifiable(receipt, diffs) -> VerifyResult:
    return VerifyResult(receipt.receipt_id, "unverifiable", diffs,
                        replay_verdict="unverifiable")


def verify_receipt(receipt: Receipt, driver: Driver, *,
                   oracle_dir=None,
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
    if "REDACTED" in receipt.command:
        # the ledger stores a secret-scrubbed command — we cannot re-run the
        # original, and replaying the scrubbed text would produce a false
        # mismatch. Honest answer: cannot verify.
        return _unverifiable(
            receipt, {"command": {"expected": "replayable",
                                  "actual": "command contains scrubbed secrets"}})

    rerun = None
    oracle = None
    oracle_exc = None
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
        try:
            oracle = _run_oracle(receipt, driver, oracle_dir, oracle_command)
        except Exception as e:  # noqa: BLE001 — an oracle failure must not
            oracle_exc = e      # eat the replay evidence already gathered
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

    if (rerun.status == "DRIVER_ERROR" or rerun.operation_uuid is None
            or rerun.exit_code is None):
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
    replay_verdict = "mismatch" if diffs else "match"

    oracle_record = None
    oracle_op_uuid = None
    oracle_failed = False
    if oracle_exc is not None:
        oracle_record = {"verdict": "error", "command": oracle_command,
                         "operation_uuid": None,
                         "stdout_tail": str(oracle_exc)[-500:]}
    elif oracle is not None:
        oracle_op = oracle["op"]
        oracle_op_uuid = oracle_op.operation_uuid
        oracle_record = _classify_oracle(oracle_op, oracle["command"])
        oracle_failed = oracle_record["verdict"] == "fail"
        if oracle_failed:
            diffs["oracle"] = {"expected": "oracle exit 0",
                               "actual": oracle_op.exit_code,
                               "stdout_tail": oracle_op.stdout[-500:]}

    # combined verdict: oracle "error" is an inability to evaluate, not a
    # defect signal — it does not downgrade an otherwise-matching replay
    verdict = "mismatch" if (replay_verdict == "mismatch" or oracle_failed) \
        else "match"
    return VerifyResult(receipt.receipt_id, verdict, diffs,
                        replay_verdict=replay_verdict,
                        replay_operation_uuid=rerun.operation_uuid,
                        replay_anchor_source=rerun.anchor_source,
                        oracle=oracle_record,
                        oracle_operation_uuid=oracle_op_uuid)


def _classify_oracle(op, command: str) -> dict:
    """pytest exit codes: 0 = tests passed, 1 = test failures, everything
    else = the check itself did not run (collection/usage/internal error,
    missing pytest, wrong cwd). Only exit 1 means the produced state violated
    the hidden contract; the rest are 'error' — could not evaluate."""
    base = {"command": command, "operation_uuid": op.operation_uuid}
    if (op.status == "DRIVER_ERROR" or op.operation_uuid is None
            or op.exit_code is None):
        return {**base, "verdict": "error",
                "stdout_tail": (op.stderr or "")[-500:]}
    verdict = "pass" if op.exit_code == 0 else \
        "fail" if op.exit_code == 1 else "error"
    return {**base, "verdict": verdict,
            "exit_code": op.exit_code,
            "stdout_tail": (op.stdout or "")[-500:]}


def _run_oracle(receipt: Receipt, driver: Driver,
                oracle_dir, oracle_command):
    """Run the hidden contract check against the RESULT image — the end state
    the agent actually produced. Returns {"op", "command"} or None when no
    oracle was configured or no result state exists to inspect.

    Isolation (see module docstring): mounts land at a random path outside the
    workspace and the default command runs a runner under `python3 -I -S` with
    cwd=/ — the produced tree can be *inspected* but can no longer influence
    the test runner itself.
    """
    if not oracle_command:
        return None
    target = receipt.result_image_uuid or receipt.image_uuid
    if not target:
        return None
    driver.use(target)

    base = _ORACLE_BASE.format(tag=secrets.token_hex(4))
    runner_inst = f"{base}/run_oracle.py"
    ini_inst = f"{base}/pytest.ini"
    oracle_inst = f"{base}/oracle"
    command = oracle_command.format(
        runner=runner_inst, oracle_dir=oracle_inst, ini=ini_inst,
        cwd=receipt.cwd)

    files, tmps = _oracle_mounts(
        oracle_dir, oracle_inst,
        {runner_inst: _ORACLE_RUNNER, ini_inst: _ORACLE_INI})
    try:
        op = driver.run(command, cwd="/",
                        files=files, shell_mode=True, disposable=True)
    finally:
        for t in tmps:
            try:
                os.unlink(t)
            except OSError:
                pass
    return {"op": op, "command": command}


def _oracle_mounts(oracle_dir, oracle_inst: str,
                   generated: dict[str, str]) -> tuple[list[str], list[str]]:
    """Build host:instance mount specs — the oracle suite plus the generated
    runner/ini (written to temp host files for the mount only)."""
    files = []
    tmps = []
    if oracle_dir is not None:
        odir = Path(oracle_dir)
        for p in sorted(odir.rglob("*")):
            if p.is_file():
                files.append(
                    f"{p.resolve()}:{oracle_inst}/{p.relative_to(odir)}")
    for inst, content in generated.items():
        fd, tmp = tempfile.mkstemp(prefix="runanchor-ora-")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        tmps.append(tmp)
        files.append(f"{tmp}:{inst}")
    return files, tmps
