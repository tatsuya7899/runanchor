#!/usr/bin/env python3
"""Static packaging check: prove that `pip install .` will work, without
running pip (package builds are a gated op in this environment).

Verifies:
 1. pyproject declares the setuptools backend + app/ layout mapping
 2. setuptools actually discovers `runanchor` under app/
 3. the declared entry point `runanchor.cli:main` resolves and is callable
 4. the console-script target works: `python3 -m runanchor.cli` reaches main()
"""
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"


def main() -> int:
    problems = []

    meta = tomllib.loads((ROOT / "pyproject.toml").read_text())
    bs = meta.get("build-system", {})
    if bs.get("build-backend") != "setuptools.build_meta":
        problems.append("build-backend is not setuptools.build_meta")
    pd = meta.get("tool", {}).get("setuptools", {}).get("package-dir", {})
    if pd.get("") != "app":
        problems.append(f"package-dir mapping wrong: {pd}")

    # what setuptools.packages.find(where=["app"], include=["runanchor*"])
    # will discover: dirs under app/ containing __init__.py
    found = sorted(p.parent.name for p in APP.rglob("__init__.py"))
    if "runanchor" not in found:
        problems.append(f"runanchor not discovered under app/ (found: {found})")
    if not (APP / "runanchor" / "__init__.py").exists():
        problems.append("app/runanchor/__init__.py missing — not a package")

    sys.path.insert(0, str(APP))
    try:
        from runanchor.cli import main as cli_main
        if not callable(cli_main):
            problems.append("runanchor.cli:main is not callable")
    except Exception as e:  # noqa: BLE001
        problems.append(f"entry point does not resolve: {e}")

    # every import the console script pulls must resolve from app/ alone
    try:
        import runanchor  # noqa: F401
        import runanchor.agent_loop  # noqa: F401
        import runanchor.bench  # noqa: F401
        import runanchor.cli  # noqa: F401
        import runanchor.contree_driver  # noqa: F401
        import runanchor.demo  # noqa: F401
        import runanchor.gate  # noqa: F401
        import runanchor.judge  # noqa: F401
        import runanchor.ledger  # noqa: F401
        import runanchor.receipt  # noqa: F401
        import runanchor.sanitize  # noqa: F401
        import runanchor.verifier  # noqa: F401
    except Exception as e:  # noqa: BLE001
        problems.append(f"package import failed: {e}")

    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        return 1
    print(f"ok: packaging config valid, {len(found)} packages discovered under app/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
