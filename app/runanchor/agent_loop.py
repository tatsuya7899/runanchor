"""The autonomous agent loop: write -> run -> red -> fix -> green.

Each sandbox run is issued a receipt; the series ends on green, planner
done, or max_iter. A series that never reaches green marks its final
receipt unresolved=True (the failure stays on the ledger, not discarded).

Planners are injectable: ScriptedPlanner for tests/demo, NemotronPlanner
calls the Token Factory chat API (OpenAI-compatible).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Protocol

from .contree_driver import Driver
from .ledger import Ledger
from .receipt import Receipt, issue_receipt

DEFAULT_MODEL = "nvidia/Nemotron-3_5-Lightning"
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"

PLANNER_SYSTEM = (
    "You are a coding agent driving a sandboxed workspace. Reply with exactly one "
    'JSON object: {"command": "<shell command to run next>"} to act, or '
    '{"done": true} when the task is complete. Add "shell_mode": true if the '
    "command uses pipes, redirects or env vars. No other text."
)


class Planner(Protocol):
    def next(self, history: list[Receipt]) -> dict | None:
        """Return {"command": str, ...} for the next run, or {"done": true}/None."""


class ScriptedPlanner:
    """Deterministic planner for tests and --demo replay."""

    def __init__(self, actions: list[dict]):
        self._actions = list(actions)

    def next(self, history: list[Receipt]) -> dict | None:
        if not self._actions:
            return None
        action = self._actions.pop(0)
        return None if action.get("done") else action


class NemotronPlanner:
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

    def next(self, history: list[Receipt]) -> dict | None:
        body = {
            "model": self.model,
            "messages": self._messages(history),
            "temperature": 0.2,
            "max_tokens": 4096,  # reasoning tokens count; leave headroom
        }
        if self.seed is not None:
            body["seed"] = self.seed
        payload = self._http_post(self.base_url, self._headers, body)
        return _parse_action(payload)

    def _messages(self, history: list[Receipt]) -> list[dict]:
        log = "\n".join(
            f"run {r.run_seq}: cmd={r.command} status={r.status} "
            f"exit={r.exit_code} tail={r.stdout_tail!r}"
            for r in history
        )
        return [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": f"Run history so far:\n{log or '(none)'}"},
        ]


def _parse_action(payload: dict) -> dict | None:
    """Extract the last JSON object from the model reply (reasoning preface OK)."""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, str):
        return None
    start = content.rfind("{")
    while start >= 0:
        try:
            action = json.loads(content[start:])
        except json.JSONDecodeError:
            start = content.rfind("{", 0, start)
            continue
        if action.get("done"):
            return None
        if isinstance(action.get("command"), str):
            return action
        return None
    return None


def run_loop(
    driver: Driver,
    ledger: Ledger,
    planner: Planner,
    *,
    task: str,
    max_iter: int = 5,
    model: str | None = None,
    seed: int | None = None,
    demo: bool = False,
) -> list[Receipt]:
    history: list[Receipt] = []
    while len(history) < max_iter:
        try:
            action = planner.next(history)
        except Exception:
            # planner/API failure mid-series: keep what ran, mark unresolved
            break
        if action is None:
            break
        if not str(action.get("command") or "").strip():
            # planner emitted an empty command — end the series cleanly
            break
        try:
            op = driver.run(
                action["command"],
                cwd=action.get("cwd", "/work"),
                files=action.get("files"),
                shell_mode=action.get("shell_mode", False),
            )
        except Exception:
            # e.g. planner emitted an empty command — end the series,
            # the last real run still gets its unresolved marker
            break
        receipt = issue_receipt(
            op,
            task=task,
            run_seq=len(history) + 1,
            model=model,
            seed=seed,
            demo=demo,
        )
        ledger.append_receipt(receipt)
        history.append(receipt)
        if op.exit_code == 0:
            return history
    if history:
        ledger.mark_unresolved(history[-1].receipt_id)
    return history
