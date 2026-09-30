#!/usr/bin/env python3
"""List Token Factory chat models available to this credential."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from runanchor.cli import _api_key

req = urllib.request.Request(
    "https://api.tokenfactory.nebius.com/v1/models",
    headers={"Authorization": f"Bearer {_api_key()}"})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read())
for m in data.get("data", []):
    print(m.get("id"))
