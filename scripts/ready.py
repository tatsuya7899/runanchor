#!/usr/bin/env python3
"""Submission-readiness gate for runanchor.

Runs structural checks on the repo and reports PASS/FAIL per item. Exits 1
while anything required is missing or dishonest — e.g. a README measurement
still marked _pending_, because headline numbers must be real measurements.

Usage: python3 scripts/ready.py
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))


_PLACEHOLDER_TAIL = ("…", "<", ">", "your_", "xxx", "placeholder",
                     "example", "dummy", "REDACTED")


def _looks_placeholder(match: str) -> bool:
    """`API_KEY=…` in docs is not a secret — only treat real-looking values
    as hits."""
    tail = match.rsplit("=", 1)[-1].rsplit(":", 1)[-1].strip()
    if any(tail.lower().startswith(p.lower().rstrip("_"))
           or p in tail for p in _PLACEHOLDER_TAIL):
        return True
    # `api_key = api_key` — an identifier-valued assignment is not a secret;
    # only quoted literals or long key-shaped bare values count as real hits
    if tail[:1] in {'"', "'"} and tail[-1:] == tail[:1]:
        return len(tail.strip("\"'")) < 8
    has_letter = any(c.isalpha() for c in tail)
    has_digit = any(c.isdigit() for c in tail)
    return not (len(tail) >= 20 and has_letter and has_digit)


def _embedded_word(text: str, m: "re.Match[str]") -> bool:
    """`task-…` words can contain the token shape — a match whose start is
    glued to a word char is not a secret."""
    return m.start() > 0 and text[m.start() - 1].isalnum()


def main() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8") \
        if (ROOT / "README.md").exists() else ""

    check("README.md exists", bool(readme))
    check("README documents setup/demo", "Demo (no credentials" in readme)
    check("README names Nemotron + Token Factory",
          "Nemotron" in readme and "Token Factory" in readme)
    check("README states reproduce-the-measurement procedure",
          "Reproduce the measurement" in readme)
    check("LICENSE file present", (ROOT / "LICENSE").exists())
    check("architecture diagram present",
          (ROOT / "docs" / "architecture.svg").exists())

    # submission text
    for f in ("description.md", "feedback.md", "demo-script.md"):
        check(f"submit/{f} present", (ROOT / "submit" / f).exists())

    # corpus integrity via the committed generator + loader
    sys.path.insert(0, str(APP))
    try:
        from runanchor.bench import load_corpus
        items = load_corpus(APP / "corpus")
        seeded = sum(1 for i in items if i.label == "seeded")
        clean = sum(1 for i in items if i.label == "clean")
        check("corpus loads cleanly", True, f"{len(items)} items")
        check("corpus size >= 24 seeded + 11 clean",
              seeded >= 24 and clean >= 11, f"seeded={seeded} clean={clean}")
        check("every seeded item declares bug_type + oracle",
              all(i.bug_type and i.oracle for i in items if i.label == "seeded"))
    except Exception as e:  # noqa: BLE001 — report, don't crash the gate
        check("corpus loads cleanly", False, str(e))

    # demo fixtures exist
    fx = APP / "fixtures" / "demo"
    check("demo fixtures present", (fx / "ops.jsonl").exists())

    # offline suite must pass
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ROOT,
        capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    check("offline test suite green", proc.returncode == 0, tail)

    # demo must run end to end
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, "-m", "runanchor.cli", "--ledger",
             str(Path(td) / "d.jsonl"), "demo"],
            cwd=APP, capture_output=True, text=True)
        check("offline demo runs", proc.returncode == 0)

    # secret scan over tracked text files (the ledger package may be published)
    # — reuse the real patterns, not a naive substring ("task-" embeds "sk-")
    from runanchor.sanitize import SECRET_PATTERNS
    secret_hit = None
    for p in list(ROOT.rglob("*")):
        if p.is_dir() or any(part.startswith(".") for part in p.parts):
            continue
        if p.suffix in {".png", ".svg", ".ico"} or ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # test files legitimately carry fixture-shaped literals (marked in tests)
        rel = p.relative_to(ROOT)
        if str(rel).startswith("app/tests"):
            continue
        hits = [m for pat in SECRET_PATTERNS for m in pat.finditer(text)]
        real = [m.group(0) for m in hits
                if not _embedded_word(text, m) and not _looks_placeholder(m.group(0))]
        if real:
            secret_hit = p
            break
    check("no obvious secrets in tracked files", secret_hit is None,
          str(secret_hit or ""))

    # honesty gate: measured numbers must not be placeholders at submission
    pending = "_pending_" in readme
    check("measured values are real (not pending)", not pending,
          "live measurement #0 still pending — cannot submit with placeholders")

    print("== submission readiness ==")
    fails = 0
    for name, ok, detail in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" +
              (f"  — {detail}" if detail and not ok else ""))
        fails += not ok
    print(f"== {len(RESULTS) - fails}/{len(RESULTS)} checks pass ==")
    if fails:
        print("NOT READY.")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
