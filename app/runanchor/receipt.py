"""Receipt domain model: one verifiable record per agent run.

A receipt is issued from an OperationRecord (what the driver observed for a
single sandbox run). Streams are fingerprinted + trimmed, never stored whole;
command and tails pass through secret scrubbing before persistence (the
ledger may be published with the measurement package — FR-11).
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone

from .sanitize import scrub_path, scrub_text

TAIL_LINES = 20

# Volatile tokens (elapsed times, ISO timestamps, tmp paths) are normalized
# out before fingerprinting — otherwise deterministic replays would read as
# mismatches. The fingerprint proves "same output modulo jitter", not
# "identical bytes"; the raw tail is kept for human reading.
VOLATILE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ms|s)\b"
    r"|\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*"
    r"|/tmp/\S+"
)


def normalize_stream(text: str) -> str:
    return VOLATILE.sub("<VOLATILE>", text)


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_stream(text).encode()).hexdigest()

# Seed is accepted by the Token Factory inference API but produces different
# outputs for identical requests (measured 2026-09-29). It is metadata, never
# the basis of replay.
SEED_NOTE = "seed accepted by the API but not deterministic; metadata only"


@dataclass(frozen=True)
class OperationRecord:
    """Provider-observed record of one sandbox run, as returned by a driver."""

    operation_uuid: str | None
    image_uuid: str | None
    result_image_uuid: str | None
    command: str
    cwd: str
    shell_mode: bool
    status: str
    exit_code: int | None
    stdout: str
    stderr: str
    diff_sha256: str | None = None
    files: list[str] = field(default_factory=list)  # host paths mounted via --file
    demo: bool = False                              # driver-supplied provenance
    anchor_source: str | None = None                # "run-json" | "head" | "demo"
    parse_warnings: list[str] = field(default_factory=list)
    duration_s: float | None = None
    consumed_cpu_s: float | None = None
    consumed_memory: int | None = None
    consumed_memory_unit: str | None = None


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    task: str
    run_seq: int
    operation_uuid: str | None
    image_uuid: str | None
    result_image_uuid: str | None
    command: str
    cwd: str
    shell_mode: bool
    status: str
    exit_code: int | None
    stdout_sha256: str
    stderr_sha256: str
    stdout_tail: str
    stderr_tail: str
    diff_sha256: str | None
    files: list[str]
    anchor_source: str | None
    duration_s: float | None
    consumed_cpu_s: float | None
    consumed_memory: int | None
    consumed_memory_unit: str | None
    model: str | None
    seed: int | None
    seed_note: str | None
    issued_at: str
    state: str = "pending"
    decision: dict | None = None
    demo: bool = False
    unresolved: bool = False  # True when the agent loop gave up without green
    warnings: list[str] = field(default_factory=list)  # degraded/partial evidence notes
    verification: dict | None = None  # latest verify evidence (verdict, diffs, replay op)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Receipt":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _tail(text: str, lines: int = TAIL_LINES) -> str:
    return "\n".join(text.rstrip("\n").splitlines()[-lines:])


def issue_receipt(
    op: OperationRecord,
    *,
    task: str,
    run_seq: int,
    model: str | None = None,
    seed: int | None = None,
    seed_note: str | None = None,
    demo: bool = False,
    issued_at: str | None = None,
) -> Receipt:
    if seed is not None and seed_note is None:
        seed_note = SEED_NOTE
    return Receipt(
        receipt_id=uuid.uuid4().hex,
        task=task,
        run_seq=run_seq,
        operation_uuid=op.operation_uuid,
        image_uuid=op.image_uuid,
        result_image_uuid=op.result_image_uuid,
        command=scrub_text(op.command),
        cwd=op.cwd,
        shell_mode=op.shell_mode,
        status=op.status,
        exit_code=op.exit_code,
        stdout_sha256=fingerprint(op.stdout),
        stderr_sha256=fingerprint(op.stderr),
        stdout_tail=scrub_text(_tail(op.stdout)),
        stderr_tail=scrub_text(_tail(op.stderr)),
        diff_sha256=op.diff_sha256,
        # mount specs keep host_path:instance_path (replay needs the host
        # side); the home dir is scrubbed so a published ledger carries no
        # local identity
        files=[scrub_path(f) for f in op.files],
        anchor_source=op.anchor_source,
        duration_s=op.duration_s,
        consumed_cpu_s=op.consumed_cpu_s,
        consumed_memory=op.consumed_memory,
        consumed_memory_unit=op.consumed_memory_unit,
        model=model,
        seed=seed,
        seed_note=seed_note,
        issued_at=issued_at or datetime.now(timezone.utc).isoformat(),
        demo=demo or op.demo,
        warnings=[scrub_text(w) for w in op.parse_warnings],
    )
