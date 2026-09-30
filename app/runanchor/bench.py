"""Corpus runner + confusion matrix: measures gate quality on labeled tasks.

Two decision layers are measured independently against ground truth:

  evidence-only   — the judge sees series evidence only (what a log reviewer
                    could see). This is the "no replay" baseline.
  gate            — the judge sees series evidence PLUS the verification
                    record (replay verdict + hidden-oracle outcome). This is
                    the full runanchor pipeline.

Ground truth is the hidden oracle: for each item an executable oracle check
(corpus/<slug>/oracle/) runs against the produced RESULT image — a green
oracle means the end state satisfies the real contract regardless of what
the agent's log claimed. When no oracle can run, the item's label is the
fallback truth and the row is marked. Positive class = "should reject"
(truth=defective). TP = defective that the layer rejected; FN = defective
that slipped through; TN = good adopted; FP = good wrongly rejected.

Labels never reach planner or judge — the judge sees task text, run
evidence, and the verification record only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
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
    label: str  # "seeded" | "clean" — describes the planted trap, NOT the verdict
    bug_type: str | None
    mode: str  # "honest" | "cheat"
    oracle: str  # human-readable description of the ground truth
    seed_dir: Path
    oracle_dir: Path | None
    oracle_command: str | None


VALID_LABELS = {"seeded", "clean"}
DEFAULT_ORACLE_COMMAND = "python3 -m pytest -q oracle/"


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
        oracle_dir = d / "oracle"
        items.append(CorpusItem(
            slug=d.name,
            task=(d / "task.md").read_text(encoding="utf-8").strip(),
            label=meta["label"],
            bug_type=meta.get("bug_type"),
            mode=meta.get("mode", "honest"),
            oracle=meta.get("oracle", ""),
            seed_dir=d / "seed",
            oracle_dir=oracle_dir if oracle_dir.is_dir() else None,
            oracle_command=meta.get("oracle_command") or (
                DEFAULT_ORACLE_COMMAND if oracle_dir.is_dir() else None),
        ))
    if not items:
        raise CorpusError("corpus is empty")
    return items


@dataclass(frozen=True)
class ConfusionMatrix:
    tp: int = 0  # defective rejected (bad run stopped)
    fn: int = 0  # defective adopted (bad run slipped through)
    tn: int = 0  # good adopted (good run passed)
    fp: int = 0  # good rejected (good run blocked)


@dataclass(frozen=True)
class BenchReport:
    matrix: ConfusionMatrix              # gate layer (evidence + verify)
    evidence_matrix: ConfusionMatrix     # evidence-only layer (the baseline)
    rows: list[dict]
    lines: list[str]
    truth_source: str = "oracle"         # ground truth = oracle outcome (label fallback)

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


def _evidence(receipts, item) -> dict:
    """What the judge may see — the whole run series' receipt evidence plus
    the task text. Labels, bug types and oracles never leak."""
    return {
        "task": item.task,
        "runs": [{
            "seq": r.run_seq,
            "command": r.command,
            "exit_code": r.exit_code,
            "status": r.status,
            "stdout_tail": r.stdout_tail,
            "stderr_tail": r.stderr_tail,
            "unresolved": r.unresolved,
        } for r in receipts],
    }


def _verify_block(verify_result) -> dict | None:
    if verify_result is None:
        return None
    block = {"replay_verdict": verify_result.verdict,
             "replay_diffs": verify_result.diffs}
    if verify_result.oracle is not None:
        # the judge sees the oracle's outcome AND its output tail — a bare
        # "fail" without output is unreasoned rejection bait
        block["oracle"] = dict(verify_result.oracle)
    return block


def _evidence_sha(evidence: dict) -> str:
    return hashlib.sha256(
        json.dumps(evidence, sort_keys=True).encode()).hexdigest()


def _matrix_cell(truth: str, predicted: str) -> str:
    """truth='defective'|'good', predicted='adopted'|'rejected' -> tp/fn/tn/fp."""
    if truth == "defective":
        return "tp" if predicted == "rejected" else "fn"
    return "fp" if predicted == "rejected" else "tn"


def run_bench(corpus_dir, ledger: Ledger, *, driver_for, planner_for, judge,
              verify_driver_for=None, max_iter: int = 5) -> BenchReport:
    items = load_corpus(corpus_dir)
    gate = Gate(ledger)
    counts = dict(tp=0, fn=0, tn=0, fp=0)
    counts_evidence = dict(tp=0, fn=0, tn=0, fp=0)
    rows = []

    for item in items:
        # Seed mounts land on the FIRST run only (re-mounting later runs
        # would overwrite the agent's edits with pristine host content —
        # live-measured). ConTree --file takes host_path:instance_path.
        seed_files = [
            f"{p.resolve()}:/work/{p.relative_to(item.seed_dir)}"
            for p in sorted(item.seed_dir.rglob("*")) if p.is_file()
        ]
        oracle_files = [
            f"{p.resolve()}:/work/oracle/{p.relative_to(item.oracle_dir)}"
            for p in sorted(item.oracle_dir.rglob("*")) if p.is_file()
        ] if item.oracle_dir else []

        driver = None
        try:
            driver = driver_for(item)
            planner = planner_for(item)
            series = run_loop(
                driver, ledger, planner,
                task=item.task, max_iter=max_iter, files=seed_files,
                model=getattr(planner, "model", None),
            )
        except Exception as e:  # noqa: BLE001 — one bad item must not kill the bench
            rows.append({"slug": item.slug, "label": item.label,
                         "predicted": "error", "correct": False,
                         "verdict_reason": f"harness error: {e}"})
            continue
        finally:
            # each item gets a throwaway session — release it whether the
            # series ran or not (images themselves are global, not per-session)
            if driver is not None:
                try:
                    driver.close()
                except Exception:
                    pass
        if not series:
            rows.append({"slug": item.slug, "label": item.label,
                         "predicted": "no-run", "correct": False})
            continue

        final = ledger.get(series[-1].receipt_id)

        # --- verification stage: replay + hidden oracle ---------------------
        verify_result = None
        verify_error = None
        if verify_driver_for is not None:
            vdriver = None
            try:
                vdriver = verify_driver_for(item)
                from .verifier import verify_receipt
                verify_result = verify_receipt(
                    final, vdriver,
                    oracle_files=oracle_files,
                    oracle_command=item.oracle_command,
                )
                ledger.record_verification(
                    final.receipt_id, verify_result.verdict,
                    verify_result.diffs,
                    replay_operation_uuid=verify_result.replay_operation_uuid,
                    replay_anchor_source=verify_result.replay_anchor_source,
                    oracle=verify_result.oracle,
                    oracle_operation_uuid=verify_result.oracle_operation_uuid,
                )
            except Exception as e:  # noqa: BLE001 — verify failure is data, not fatal
                verify_result = None
                verify_error = f"verify error: {e}"
            finally:
                if vdriver is not None:
                    try:
                        vdriver.close()
                    except Exception:
                        pass

        # --- ground truth --------------------------------------------------
        # The hidden oracle decides what the produced state actually is:
        # oracle fail = defective run (whatever the log showed), oracle pass =
        # good run. No oracle -> fall back to the seed's planted-trap label.
        oracle_v = verify_result.oracle_verdict if verify_result else None
        if oracle_v == "fail":
            truth = "defective"
        elif oracle_v == "pass":
            truth = "good"
        else:
            truth = "defective" if item.label == "seeded" else "good"

        # --- two-layer judgment --------------------------------------------
        evidence = _evidence(series, item)
        evidence_hash = _evidence_sha(evidence)
        try:
            ev_verdict = judge.review(evidence)
        except Exception as e:  # noqa: BLE001
            rows.append({"slug": item.slug, "label": item.label,
                         "predicted": "judge-error", "correct": False,
                         "verdict_reason": f"judge error: {e}",
                         "truth": truth})
            continue
        gate_evidence = dict(evidence)
        vb = _verify_block(verify_result)
        if vb is not None:
            gate_evidence["verification"] = vb
        try:
            gate_verdict = judge.review(gate_evidence)
        except Exception as e:  # noqa: BLE001
            gate_verdict = ev_verdict  # degraded: fall back to evidence layer

        for verdict, cnt in ((ev_verdict, counts_evidence), (gate_verdict, counts)):
            predicted = "adopted" if verdict.decision == "adopt" else "rejected"
            cnt[_matrix_cell(truth, predicted)] += 1

        # the ledger decision records the GATE verdict bound to the evidence
        # hash it was judged on — the decision is falsifiable, not free text
        final = ledger.get(final.receipt_id)  # post-verification snapshot
        if gate_verdict.decision == "adopt":
            gate.approve(final.receipt_id, by=f"judge:{getattr(judge, 'model', 'fake')}",
                         reason=gate_verdict.reason,
                         meta={"evidence_sha256": _evidence_sha(gate_evidence)})
            predicted = "adopted"
        else:
            gate.reject(final.receipt_id, by=f"judge:{getattr(judge, 'model', 'fake')}",
                        reason=gate_verdict.reason,
                        meta={"evidence_sha256": _evidence_sha(gate_evidence)})
            predicted = "rejected"

        rows.append({
            "slug": item.slug, "label": item.label, "bug_type": item.bug_type,
            "truth": truth,
            "predicted": predicted,
            "predicted_evidence_only": "adopted" if ev_verdict.decision == "adopt" else "rejected",
            "correct": _matrix_cell(truth, predicted) in ("tp", "tn"),
            "oracle": oracle_v,
            "verify": verify_result.verdict if verify_result else None,
            "verify_error": verify_error,
            "verdict_reason": gate_verdict.reason,
            "evidence_verdict_reason": ev_verdict.reason,
            "runs": len(series),
        })

    report = BenchReport(ConfusionMatrix(**counts),
                         ConfusionMatrix(**counts_evidence), rows, [])
    sens, spec = report.sensitivity, report.specificity
    em = report.evidence_matrix
    e_sens = em.tp / (em.tp + em.fn) if (em.tp + em.fn) else None
    e_spec = em.tn / (em.tn + em.fp) if (em.tn + em.fp) else None
    n_def = sum(1 for r in rows if r.get("truth") == "defective")
    n_good = sum(1 for r in rows if r.get("truth") == "good")
    lines = [
        f"bench: n={report.n} (defective={n_def}, good={n_good}; truth=oracle where runnable)",
        "  gate layer (evidence + replay + oracle):",
        f"    sensitivity (bad runs caught): {'n/a' if sens is None else f'{sens:.0%}'}",
        f"    specificity (good runs passed): {'n/a' if spec is None else f'{spec:.0%}'}",
        f"    tp={report.matrix.tp} fn={report.matrix.fn} tn={report.matrix.tn} fp={report.matrix.fp}",
        "  evidence-only layer (judge baseline):",
        f"    sensitivity: {'n/a' if e_sens is None else f'{e_sens:.0%}'}",
        f"    specificity: {'n/a' if e_spec is None else f'{e_spec:.0%}'}",
        f"    tp={em.tp} fn={em.fn} tn={em.tn} fp={em.fp}",
        "",
        "per-item:",
    ]
    lines += [
        f"  {r['slug']:<28} label={r['label']:<6} truth={r.get('truth', '-'):<9} "
        f"oracle={r.get('oracle') or '-':<4} gate={r['predicted']:<8} "
        f"evidence={r.get('predicted_evidence_only', '-'):<8} "
        f"{'OK' if r.get('correct') else 'MISS'}"
        for r in rows
    ]
    object.__setattr__(report, "lines", lines)
    return report
