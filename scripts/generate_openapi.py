#!/usr/bin/env python3
import json
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

candidates = [
    ("main", "app"),          # if you have top-level main.py
    ("app.main", "app"),      # if app/main.py exists
    ("app.api.main", "app"),  # your repo often uses this path
]

app = None
last_err = None
for module_name, attr in candidates:
    try:
        mod = importlib.import_module(module_name)
        app = getattr(mod, attr)
        break
    except Exception as e:
        last_err = e

if app is None:
    raise RuntimeError(f"Could not locate FastAPI 'app' in any of {candidates}. Last error: {last_err}")

out = PROJECT_ROOT / "dist"
out.mkdir(exist_ok=True)
with open(out / "openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2)
print(f"wrote {out/'openapi.json'}")
