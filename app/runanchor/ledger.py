"""Append-only JSONL ledger: the single source of truth for receipts.

Each line is a full receipt snapshot. Decisions append a new snapshot; lines
are never modified or deleted, so rejected and failed runs stay on record.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .receipt import Receipt

TRANSITIONS = {
    "pending": {"adopted", "rejected", "mismatch"},
    "adopted": {"mismatch"},
    "rejected": {"mismatch"},
    "mismatch": set(),
}


class InvalidTransition(Exception):
    pass


class Ledger:
    def __init__(self, path):
        self.path = Path(path)

    def append_receipt(self, receipt: Receipt) -> None:
        self._append(receipt.to_dict())

    def decide(self, receipt_id: str, state: str, *, by: str, reason: str | None = None) -> Receipt:
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
            },
        )
        self._append(updated.to_dict())
        return updated

    def get(self, receipt_id: str) -> Receipt | None:
        return self._index().get(receipt_id)

    def all(self) -> list[Receipt]:
        return list(self._index().values())

    def pending(self) -> list[Receipt]:
        return [r for r in self.all() if r.state == "pending"]

    def by_task(self, task: str) -> list[Receipt]:
        return sorted((r for r in self.all() if r.task == task), key=lambda r: r.run_seq)

    def _append(self, obj: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def _index(self) -> dict[str, Receipt]:
        idx: dict[str, Receipt] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = Receipt.from_dict(json.loads(line))
                    idx[r.receipt_id] = r  # last snapshot wins
        return idx
