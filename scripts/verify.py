#!/usr/bin/env python3
"""Offline verification: full unit+E2E suite, no network, no credentials.

Live paths (real contree/Nemotron calls) are intentionally excluded so this
is reproducible for anyone. Usage: python3 scripts/verify.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=ROOT))
