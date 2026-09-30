"""The autonomous agent loop: write -> run -> red -> fix -> green.

Each sandbox run is issued a receipt; the series ends only on planner
done, planner/driver failure, empty command, or max_iter — an exit-0 run
is evidence, not completion (a reconnaissance `ls` exits 0 without
demonstrating anything). A series that never reaches green marks its
final receipt unresolved=True (the failure stays on the ledger).

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
    "You are a coding agent driving a sandboxed workspace at /work. Reply with "
    'exactly one JSON object: {"command": "<shell command to run next>"} to '
    'act, or {"done": true} when the task is complete. Add "shell_mode": true '
    "if the command uses pipes, redirects or env vars. Work in small steps: "
    "inspect the files, edit them (e.g. via python3 -c, sed, or a heredoc with "
    "shell_mode), then run the project's test command. Only answer done AFTER "
    "you have run the tests and they pass — declaring done without green test "
    "evidence in the history is a rejected claim. No other text."
)


class Planner(Protocol):
    def next(self, history: list[Receipt], task: str | None = None) -> dict | None:
        """Return {"command": str, ...} for the next run, or {"done": true}/None."""


class ScriptedPlanner:
    """Deterministic planner for tests and --demo replay."""

    def __init__(self, actions: list[dict]):
        self._actions = list(actions)

    def next(self, history: list[Receipt], task: str | None = None) -> dict | None:
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

    def next(self, history: list[Receipt], task: str | None = None) -> dict | None:
        body = {
            "model": self.model,
            "messages": self._messages(history, task),
            "temperature": 0.2,
            "max_tokens": 4096,  # reasoning tokens count; leave headroom
        }
        if self.seed is not None:
            body["seed"] = self.seed
        payload = self._http_post(self.base_url, self._headers, body)
        return _parse_action(payload)

    def _messages(self, history: list[Receipt], task: str | None) -> list[dict]:
        log = "\n".join(
            f"run {r.run_seq}: cmd={r.command} status={r.status} "
            f"exit={r.exit_code} tail={r.stdout_tail!r}"
            for r in history
        )
        return [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content":
                f"Task: {task or '(unspecified)'}\n"
                f"Run history so far:\n{log or '(none)'}"},
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
    files: list[str] | None = None,
    demo: bool = False,
) -> list[Receipt]:
    history: list[Receipt] = []
    base_files = list(files or [])
    while len(history) < max_iter:
        try:
            action = planner.next(history, task)
        except Exception:
            # planner/API failure mid-series: keep what ran, mark unresolved
            break
        if action is None:
            break
        if not str(action.get("command") or "").strip():
            # planner emitted an empty command — end the series cleanly
            break
        try:
            # Seed files mount on the FIRST run only — ConTree applies --file
            # mounts per-invocation, so re-mounting on every run would
            # overwrite the agent's edits with the original host content
            # (live-measured 2026-09-30: a written calc.py reverted on the
            # next run because the seed remounted over it).
            op = driver.run(
                action["command"],
                cwd=action.get("cwd", "/work"),
                # Only the operator's seed mounts are passed — planner-emitted
                # "files" are ignored: a model must not inject host-side paths
                # into --file mounts (confused-deputy boundary; the model's
                # JSON is not a trusted mount spec).
                files=base_files if not history else [],
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
    # exit_code==0 alone must NOT end the series — a reconnaissance command
    # (`ls`, `cat`) exits 0 without demonstrating anything. Only the planner's
    # `done`, a planner/driver failure, an empty command, or max_iter ends it.
    if history and history[-1].exit_code != 0:
        # mark_unresolved appends a NEW snapshot — replace the history entry so
        # downstream evidence builders see the flag (the returned receipts are
        # what the judge reads, not just the ledger)
        history[-1] = ledger.mark_unresolved(history[-1].receipt_id)
    return history
