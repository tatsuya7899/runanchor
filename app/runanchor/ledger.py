"""Append-only JSONL ledger: the single source of truth for receipts.

Each line is a full receipt snapshot wrapped as {"_chain": sha256-of-previous-
raw-line, "receipt": {...}}. Decisions append a new snapshot; lines are never
modified or deleted, so rejected and failed runs stay on record. The chain
makes appended forgeries or removed lines detectable via check_integrity() —
the ledger is tamper-evident, not tamper-proof (the provider anchor is the
trust boundary; see design doc "Gate 1" notes).

Corrupt/torn tail lines are skipped and reported via corrupt_lines() rather
than taking the whole ledger down.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .receipt import Receipt

TRANSITIONS = {
    "pending": {"adopted", "rejected", "mismatch"},
    "adopted": {"mismatch"},
    "rejected": {"mismatch"},
    # mismatch is evidence, not a verdict: a human may still decide
    "mismatch": {"adopted", "rejected"},
}


class InvalidTransition(Exception):
    pass


class DuplicateReceipt(Exception):
    pass


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self._corrupt: list[int] = []

    def append_receipt(self, receipt: Receipt) -> None:
        if receipt.state != "pending":
            raise ValueError("new receipts must enter as pending")
        if self.get(receipt.receipt_id) is not None:
            raise DuplicateReceipt(receipt.receipt_id)
        self._append(receipt.to_dict())

    def decide(self, receipt_id: str, state: str, *, by: str, reason: str | None = None,
               meta: dict | None = None) -> Receipt:
        current = self.get(receipt_id)
        if current is None:
            raise KeyError(receipt_id)
        if state not in TRANSITIONS.get(current.state, set()):
            raise InvalidTransition(f"{current.state} -> {state}")
        if state == "rejected" and not (reason and reason.strip()):
            raise ValueError("reject requires a reason")
        updated = replace(
            current,
            state=state,
            decision={
                "by": by,
                "reason": reason,
                "at": datetime.now(timezone.utc).isoformat(),
                # evidence binding (e.g. the sha256 of the exact payload the
                # decider judged) — a recorded decision points at the evidence
                # it claims to have reviewed, not just at the receipt
                "meta": dict(meta or {}),
            },
        )
        self._append(updated.to_dict())
        return updated

    def mark_unresolved(self, receipt_id: str) -> Receipt:
        """Flag a receipt whose agent loop ended without reaching green."""
        current = self.get(receipt_id)
        if current is None:
            raise KeyError(receipt_id)
        updated = replace(current, unresolved=True)
        self._append(updated.to_dict())
        return updated

    def get(self, receipt_id: str) -> Receipt | None:
        return self._index()[0].get(receipt_id)

    def resolve(self, id_or_prefix: str) -> Receipt | None:
        """Exact id or unique prefix -> receipt. Raises on ambiguity."""
        exact = self.get(id_or_prefix)
        if exact:
            return exact
        hits = [r for r in self.all() if r.receipt_id.startswith(id_or_prefix)]
        if len(hits) > 1:
            raise ValueError(f"ambiguous receipt id prefix: {id_or_prefix}")
        return hits[0] if hits else None

    def all(self) -> list[Receipt]:
        return list(self._index()[0].values())

    def pending(self) -> list[Receipt]:
        return [r for r in self.all() if r.state == "pending"]

    def by_task(self, task: str) -> list[Receipt]:
        return sorted((r for r in self.all() if r.task == task), key=lambda r: r.run_seq)

    def history(self, receipt_id: str) -> list[Receipt]:
        """Every snapshot of a receipt in append order (audit trail)."""
        return [r for r in self._snapshots() if r.receipt_id == receipt_id]

    def record_verification(self, receipt_id: str, verdict: str, diffs: dict,
                            replay_operation_uuid: str | None = None,
                            replay_anchor_source: str | None = None,
                            oracle: dict | None = None,
                            oracle_operation_uuid: str | None = None) -> Receipt:
        """Append verification evidence — a match must be anchored too, not
        only the mismatch it may cause. State itself is unchanged."""
        current = self.get(receipt_id)
        if current is None:
            raise KeyError(receipt_id)
        updated = replace(current, verification={
            "verdict": verdict, "diffs": diffs,
            "replay_operation_uuid": replay_operation_uuid,
            "replay_anchor_source": replay_anchor_source,
            "oracle": oracle,
            "oracle_operation_uuid": oracle_operation_uuid,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self._append(updated.to_dict())
        return updated

    def corrupt_lines(self) -> list[int]:
        """Line numbers that failed to parse (evidence loss must be visible)."""
        self._index()
        return list(self._corrupt)

    def check_integrity(self) -> list[int]:
        """Return line numbers whose chain hash doesn't match the previous
        raw line — i.e. probable tampering or reordering. Empty = intact."""
        if not self.path.exists():
            return []
        broken = []
        prev_hash = "genesis"
        for n, raw_line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            try:
                wrap = json.loads(raw_line)
                if wrap.get("_chain") != prev_hash:
                    broken.append(n)
                prev_hash = _sha256(raw_line)
            except json.JSONDecodeError:
                broken.append(n)
        return broken

    def _append(self, obj: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        prev_hash = "genesis"
        if self.path.exists():
            lines = self.path.read_text(encoding="utf-8").splitlines()
            if lines and lines[-1].strip():
                prev_hash = _sha256(lines[-1])
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"_chain": prev_hash, "receipt": obj}, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _snapshots(self) -> list[Receipt]:
        return list(self._index()[1])

    def _index(self) -> tuple[dict[str, Receipt], list[Receipt]]:
        idx: dict[str, Receipt] = {}
        snaps: list[Receipt] = []
        self._corrupt = []
        if self.path.exists():
            for n, line in enumerate(
                self.path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                try:
                    wrap = json.loads(line)
                    r = Receipt.from_dict(wrap["receipt"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    self._corrupt.append(n)
                    continue
                idx[r.receipt_id] = r  # last snapshot wins
                snaps.append(r)
        return idx, snaps
