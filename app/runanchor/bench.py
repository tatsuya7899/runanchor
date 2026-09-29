"""Corpus runner + confusion matrix: measures gate quality on labeled tasks.

Positive class = "should reject" (seeded bad run). TP = seeded that the gate
rejected; FN = seeded that slipped through; TN = clean adopted; FP = clean
wrongly rejected. The judge sees receipt evidence only — labels never leak.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .agent_loop import run_loop
from .gate import Gate
from .ledger import Ledger


class CorpusError(Exception):
    pass


@dataclass(frozen=True)
class CorpusItem:
    slug: str
    task: str
    label: str  # "seeded" | "clean"
    bug_type: str | None
    mode: str  # "honest" | "cheat"
    oracle: str
    seed_dir: Path


VALID_LABELS = {"seeded", "clean"}


def load_corpus(corpus_dir) -> list[CorpusItem]:
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.is_dir():
        raise CorpusError(f"corpus dir not found: {corpus_dir}")
    items = []
    for d in sorted(p for p in corpus_dir.iterdir() if p.is_dir()):
        label_file = d / "label.json"
        if not label_file.exists():
            raise CorpusError(f"{d.name}: missing label.json")
        if not (d / "task.md").exists():
            raise CorpusError(f"{d.name}: missing task.md")
        if not (d / "seed").is_dir():
            raise CorpusError(f"{d.name}: missing seed/ dir")
        meta = json.loads(label_file.read_text(encoding="utf-8"))
        if meta.get("label") not in VALID_LABELS:
            raise CorpusError(f"{d.name}: label must be one of {VALID_LABELS}")
        items.append(CorpusItem(
            slug=d.name,
            task=(d / "task.md").read_text(encoding="utf-8").strip(),
            label=meta["label"],
            bug_type=meta.get("bug_type"),
            mode=meta.get("mode", "honest"),
            oracle=meta.get("oracle", ""),
            seed_dir=d / "seed",
        ))
    if not items:
        raise CorpusError("corpus is empty")
    return items


@dataclass(frozen=True)
class ConfusionMatrix:
    tp: int = 0  # seeded rejected (bad run stopped)
    fn: int = 0  # seeded adopted (bad run slipped through)
    tn: int = 0  # clean adopted (good run passed)
    fp: int = 0  # clean rejected (good run blocked)


@dataclass(frozen=True)
class BenchReport:
    matrix: ConfusionMatrix
    rows: list[dict]
    lines: list[str]

    @property
    def n(self) -> int:
        m = self.matrix
        return m.tp + m.fn + m.tn + m.fp

    @property
    def sensitivity(self) -> float | None:
        m = self.matrix
        return m.tp / (m.tp + m.fn) if (m.tp + m.fn) else None

    @property
    def specificity(self) -> float | None:
        m = self.matrix
        return m.tn / (m.tn + m.fp) if (m.tn + m.fp) else None


def _evidence(receipt) -> dict:
    """What the judge may see — receipt evidence only, no labels."""
    return {
        "task": receipt.task,
        "command": receipt.command,
        "exit_code": receipt.exit_code,
        "stdout_tail": receipt.stdout_tail,
        "diff_sha256": receipt.diff_sha256,
        "status": receipt.status,
        "unresolved": receipt.unresolved,
    }


def run_bench(corpus_dir, ledger: Ledger, *, driver_for, planner_for, judge,
              max_iter: int = 5) -> BenchReport:
    items = load_corpus(corpus_dir)
    gate = Gate(ledger)
    counts = dict(tp=0, fn=0, tn=0, fp=0)
    rows = []

    for item in items:
        series = run_loop(
            driver_for(item), ledger, planner_for(item),
            task=item.slug, max_iter=max_iter,
        )
        if not series:
            rows.append({"slug": item.slug, "label": item.label,
                         "predicted": "no-run", "correct": False})
            continue
        final = ledger.get(series[-1].receipt_id)
        verdict = judge.review(_evidence(final))
        if verdict.decision == "adopt":
            gate.approve(final.receipt_id, by=f"judge:{getattr(judge, 'model', 'fake')}",
                         reason=verdict.reason)
            predicted = "adopted"
        else:
            gate.reject(final.receipt_id, by=f"judge:{getattr(judge, 'model', 'fake')}",
                        reason=verdict.reason)
            predicted = "rejected"

        if item.label == "seeded":
            key = "tp" if predicted == "rejected" else "fn"
        else:
            key = "fp" if predicted == "rejected" else "tn"
        counts[key] += 1
        rows.append({"slug": item.slug, "label": item.label, "bug_type": item.bug_type,
                     "predicted": predicted, "correct": key in ("tp", "tn"),
                     "verdict_reason": verdict.reason, "runs": len(series)})

    matrix = ConfusionMatrix(**counts)
    report = BenchReport(matrix, rows, [])
    sens = report.sensitivity
    spec = report.specificity
    lines = [
        f"bench: n={report.n} (seeded={matrix.tp + matrix.fn}, clean={matrix.tn + matrix.fp})",
        f"  sensitivity (bad runs caught): {'n/a' if sens is None else f'{sens:.0%}'}",
        f"  specificity (good runs passed): {'n/a' if spec is None else f'{spec:.0%}'}",
        f"  tp={matrix.tp} fn={matrix.fn} tn={matrix.tn} fp={matrix.fp}",
        "",
        "per-item:",
    ]
    lines += [
        f"  {r['slug']:<28} label={r['label']:<6} predicted={r['predicted']:<8} "
        f"{'OK' if r.get('correct') else 'MISS'}"
        for r in rows
    ]
    object.__setattr__(report, "lines", lines)
    return report
