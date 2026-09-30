#!/usr/bin/env python3
"""Debug helper: call the planner API once and print the raw result."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from runanchor.agent_loop import NemotronPlanner
from runanchor.cli import _api_key

key = _api_key()
print("api_key present:", bool(key))
p = NemotronPlanner(api_key=key, model=sys.argv[1] if len(sys.argv) > 1
                    else "nvidia/nemotron-3-super-120b-a12b")
try:
    action = p.next([], "Fix calc.py so tests pass")
    print("action:", action)
except Exception:
    traceback.print_exc()
