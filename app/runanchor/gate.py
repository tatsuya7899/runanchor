"""The gate: human (or measurement-mode machine) decisions over pending runs.

Thin layer over Ledger — it exists so callers (CLI, judge) have one
acceptance-level API and the ledger stays purely mechanical.
"""

from __future__ import annotations

from .ledger import Ledger
from .receipt import Receipt


class Gate:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def pending(self) -> list[Receipt]:
        return self.ledger.pending()

    def approve(self, receipt_id: str, *, by: str, reason: str | None = None) -> Receipt:
        return self.ledger.decide(receipt_id, "adopted", by=by, reason=reason)

    def reject(self, receipt_id: str, *, by: str, reason: str) -> Receipt:
        return self.ledger.decide(receipt_id, "rejected", by=by, reason=reason)
