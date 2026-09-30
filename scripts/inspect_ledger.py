#!/usr/bin/env python3
"""Print a compact view of a ledger: chain integrity + per-receipt verify state."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from runanchor.ledger import Ledger

l = Ledger(sys.argv[1])
print("chain broken at:", l.check_integrity() or "none")
for r in l.all():
    v = r.verification or {}
    o = v.get("oracle") or {}
    print(f"{r.receipt_id[:8]} {r.task[:28]:<30} {r.state:<9} "
          f"verify={v.get('verdict', '-'):<12} oracle={o.get('verdict', '-'):<7} "
          f"replay_op={str(v.get('replay_operation_uuid'))[:12]}")
