"""Shared secret scrubbing: patterns for token-shaped strings.

Used both when evidence is shipped to the judge endpoint (judge.py) and when
artifacts are persisted to the ledger (receipt.py) — the ledger may be
published as part of the reproducible measurement package, so secrets must
never reach it in the first place.
"""

from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*\S+", re.IGNORECASE),
]


def scrub_text(text: str) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub("REDACTED", text)
    return text


def scrub(value):
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value
