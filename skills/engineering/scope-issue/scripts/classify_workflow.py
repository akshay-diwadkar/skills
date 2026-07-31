#!/usr/bin/env python3
"""Classify scope-issue readiness deterministically."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
for parent in SKILL_ROOT.parents:
    if (parent / "tools" / "classification" / "runtime.py").is_file():
        sys.path.insert(0, str(parent))
        main = importlib.import_module("tools.classification.runtime").main
        break
else:
    from _classification_runtime import main
if __name__ == "__main__":
    raise SystemExit(main())
