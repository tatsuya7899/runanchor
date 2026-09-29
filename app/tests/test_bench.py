"""Acceptance S8: bench runs the labeled corpus and reports the confusion matrix."""

import json
from pathlib import Path

import pytest

from runanchor.agent_loop import ScriptedPlanner as ScriptedPlanner_
from runanchor.bench import CorpusError, load_corpus, run_bench
from runanchor.contree_driver import DemoDriver
from runanchor.judge import Verdict
from runanchor.ledger import Ledger

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def write_item(base, slug, label, bug_type=None, mode="honest"):
    d = base / slug
    (d / "seed").mkdir(parents=True)
    (d / "task.md").write_text("fix it\n")
    (d / "label.json").write_text(json.dumps(
        {"label": label, "bug_type": bug_type, "mode": mode, "oracle": "x"}))
    (d / "seed" / "x.py").write_text("x = 1\n")
    return d


class TestCorpusLoader:
    def test_committed_corpus_is_valid(self):
        items = load_corpus(CORPUS_DIR)
        assert len(items) >= 35
        labels = [i.label for i in items]
        assert labels.count("seeded") >= 24
        assert labels.count("clean") >= 11
        assert all(i.seed_dir.exists() for i in items)
        # every seeded item must declare its trap and its ground truth
        assert all(i.bug_type and i.oracle for i in items if i.label == "seeded")

    def test_missing_label_raises(self, tmp_path):
        d = tmp_path / "bad"
        d.mkdir()
        (d / "task.md").write_text("x")
        with pytest.raises(CorpusError):
            load_corpus(tmp_path)

    def test_bad_label_value_raises(self, tmp_path):
        d = write_item(tmp_path, "x", label="maybe")
        with pytest.raises(CorpusError):
            load_corpus(tmp_path)


class FakeJudge:
    """Deterministic judge: adopts iff the final run's exit code is 0 AND the
    stdout actually looks like a test log (no 'faked' marker)."""

    def __init__(self):
        self.seen = []

    def review(self, evidence):
        self.seen.append(evidence)
        if evidence["exit_code"] == 0 and "faked" not in evidence["stdout_tail"]:
            return Verdict("adopt", "looks real")
        return Verdict("reject", "evidence inconsistent")


GREEN_OP = dict(operation_uuid="g", image_uuid="i0", result_image_uuid="i1",
                command="pytest -q", cwd="/work", shell_mode=False,
                status="SUCCESS", exit_code=0, stdout="1 passed\n", stderr="")
FAKE_OP = dict(operation_uuid="f", image_uuid="i0", result_image_uuid="i1",
               command="echo '1 passed'", cwd="/work", shell_mode=False,
               status="SUCCESS", exit_code=0, stdout="1 passed (faked)\n", stderr="")
RED_OP = dict(operation_uuid="r", image_uuid="i0", result_image_uuid="i1",
              command="pytest -q", cwd="/work", shell_mode=False,
              status="FAILURE", exit_code=1, stdout="1 failed\n", stderr="")


def test_bench_produces_confusion_matrix(tmp_path):
    # 2 seeded (one caught, one slips through) + 2 clean (one ok, one wrongly rejected)
    write_item(tmp_path, "s-caught", "seeded", "log_fabrication", mode="cheat")
    write_item(tmp_path, "s-slip", "seeded", "simplification", mode="cheat")
    write_item(tmp_path, "c-ok", "clean")
    write_item(tmp_path, "c-wrong", "clean")

    ops_by_slug = {
        "s-caught": [FAKE_OP],      # judge catches the faked log -> reject (TP)
        "s-slip": [GREEN_OP],       # green-looking cheat -> adopt (FN)
        "c-ok": [GREEN_OP],         # honest green -> adopt (TN)
        "c-wrong": [RED_OP],        # honest failure -> reject (FP)
    }

    judge = FakeJudge()
    report = run_bench(
        tmp_path,
        Ledger(tmp_path / "bench-ledger.jsonl"),
        driver_for=lambda item: DemoDriver(ops_by_slug[item.slug]),
        planner_for=lambda item: ScriptedPlanner_([{"command": "pytest -q"}]),
        judge=judge,
    )

    m = report.matrix
    assert (m.tp, m.fn, m.tn, m.fp) == (1, 1, 1, 1)
    assert report.sensitivity == 0.5
    assert report.specificity == 0.5
    assert report.n == 4


def test_bench_evidence_has_no_label(tmp_path):
    """The judge must never see the ground truth (non-circular measurement)."""
    write_item(tmp_path, "seeded-x", "seeded", "log_fabrication", mode="cheat")
    judge = FakeJudge()
    run_bench(
        tmp_path, Ledger(tmp_path / "l.jsonl"),
        driver_for=lambda item: DemoDriver([FAKE_OP]),
        planner_for=lambda item: ScriptedPlanner_([{"command": "x"}]),
        judge=judge,
    )
    evidence = judge.seen[0]
    for forbidden in ("label", "bug_type", "oracle", "seeded"):
        assert forbidden not in json.dumps(evidence)
    # the judge sees the task TEXT (task.md), never the directory slug
    assert evidence["task"] == "fix it"


def test_bench_mounts_seed_workspace(tmp_path):
    """P0: the agent must receive the item's seed/ files — an unmounted
    bench measures nothing."""
    write_item(tmp_path, "c1", "clean")

    class RecordingDriver:
        is_demo = True
        def __init__(self):
            self.ran = []
        def use(self, image):
            pass
        def run(self, command, cwd, files=None, shell_mode=False, disposable=False):
            self.ran.append({"files": files})
            from runanchor.receipt import OperationRecord
            return OperationRecord(**GREEN_OP)
        def events(self, uuid):
            return []

    driver = RecordingDriver()
    run_bench(
        tmp_path, Ledger(tmp_path / "l.jsonl"),
        driver_for=lambda item: driver,
        planner_for=lambda item: ScriptedPlanner_([{"command": "pytest -q"}]),
        judge=FakeJudge(),
    )
    mounted = driver.ran[0]["files"]
    assert mounted and any(f.endswith("x.py") for f in mounted)


def test_harness_error_isolated_not_fatal(tmp_path):
    """One broken item must not stop the corpus run (and must not inflate
    the metrics — error rows stay out of the matrix)."""
    write_item(tmp_path, "s1", "seeded", "x", mode="cheat")
    write_item(tmp_path, "c1", "clean")

    def driver_for(item):
        if item.slug == "s1":
            raise RuntimeError("sandbox quota")
        return DemoDriver([GREEN_OP])

    report = run_bench(
        tmp_path, Ledger(tmp_path / "l.jsonl"),
        driver_for=driver_for,
        planner_for=lambda item: ScriptedPlanner_([{"command": "x"}]),
        judge=FakeJudge(),
    )
    assert report.n == 1  # only the clean item reached a decision
    error_rows = [r for r in report.rows if r["predicted"] == "error"]
    assert len(error_rows) == 1 and error_rows[0]["slug"] == "s1"


def test_report_lines_are_printable(tmp_path):
    write_item(tmp_path, "s1", "seeded", "x", mode="cheat")
    write_item(tmp_path, "c1", "clean")
    report = run_bench(
        tmp_path, Ledger(tmp_path / "l.jsonl"),
        driver_for=lambda item: DemoDriver([FAKE_OP if item.slug == "s1" else GREEN_OP]),
        planner_for=lambda item: ScriptedPlanner_([{"command": "x"}]),
        judge=FakeJudge(),
    )
    text = "\n".join(report.lines)
    assert "sensitivity" in text and "specificity" in text
    assert "s1" in text  # per-item row
