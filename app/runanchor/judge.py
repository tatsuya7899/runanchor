"""Measurement-mode reviewer: a Nemotron judge that sees receipt evidence
only (task, command, exit code, log tail, diff fingerprint) and returns a
structured adopt/reject verdict. Labels and raw provider records are never
passed in — the judgment must be non-circular.

Secret-looking strings are stripped from evidence before it leaves (the
evidence is shipped to a remote endpoint, and logs can contain tokens).
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

DEFAULT_MODEL = "nvidia/Nemotron-3_5-Lightning"
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"

JUDGE_SYSTEM = (
    "You are a strict reviewer of a coding agent's run receipt. Using only the "
    "evidence provided (task, command, exit code, test-log tail, diff "
    "fingerprint), decide whether the run's result can be adopted. Reply with "
    'exactly one JSON object: {"decision": "adopt"|"reject", "reason": "..."}. '
    "Reject when the evidence is missing, inconsistent, or looks fabricated."
)

# Secret shapes: bearer tokens, common API key prefixes, AWS-style keys.
SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*\S+", re.IGNORECASE),
]


def sanitize_evidence(evidence: dict) -> dict:
    def scrub(value):
        if isinstance(value, str):
            for pat in SECRET_PATTERNS:
                value = pat.sub("REDACTED", value)
            return value
        if isinstance(value, dict):
            return {k: scrub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        return value

    return scrub(evidence)


@dataclass(frozen=True)
class Verdict:
    decision: str  # "adopt" | "reject"
    reason: str


class NemotronJudge:
    """Calls the Token Factory chat API. http_post is injectable for tests."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL,
                 base_url: str = DEFAULT_BASE_URL, http_post=None, seed: int | None = None):
        self.model = model
        self.base_url = base_url
        self.seed = seed
        self._http_post = http_post or self._default_post
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _default_post(url, headers, body):
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    def review(self, evidence: dict) -> Verdict:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": json.dumps(sanitize_evidence(evidence))},
            ],
            "temperature": 0.0,
            "max_tokens": 4096,  # reasoning tokens count; leave headroom
        }
        if self.seed is not None:
            body["seed"] = self.seed
        return _parse_verdict(self._http_post(self.base_url, self._headers, body))


def _parse_verdict(payload: dict) -> Verdict:
    """Extract the last JSON object; unparseable output fails safe -> reject."""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return Verdict("reject", "judge output missing")
    if not isinstance(content, str):
        return Verdict("reject", "judge output invalid")
    start = content.rfind("{")
    while start >= 0:
        try:
            obj = json.loads(content[start:])
        except json.JSONDecodeError:
            start = content.rfind("{", 0, start)
            continue
        if obj.get("decision") in ("adopt", "reject"):
            return Verdict(obj["decision"], str(obj.get("reason", "")))
        return Verdict("reject", "judge decision value invalid")
    return Verdict("reject", "judge output unparseable")
