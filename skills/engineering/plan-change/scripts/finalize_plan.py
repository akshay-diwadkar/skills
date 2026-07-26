#!/usr/bin/env python3
"""Finalize a v4 plan only when its repository and planning session are unchanged."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _plan_utils import read_plan
from check_plan import collect_diagnostics
from plan_contract import load_contract
from plan_runtime import finalized_text, load_snapshot
from v4_model import binding_for


def main() -> int:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(contract["tiers"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--initial-state", type=Path, required=True, help="External snapshot created before planning.")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    try:
        draft, baseline = read_plan(args.path), load_snapshot(args.initial_state)
    except Exception as exc:
        print(f"Error [finalization.input]: {exc}", file=sys.stderr)
        return 1
    diagnostics = collect_diagnostics(draft, args.tier, root, baseline=baseline)
    if diagnostics:
        for item in diagnostics:
            print(item, file=sys.stderr)
        return 1
    binding = binding_for(draft, root)
    text = draft
    repository = "<!-- plan-repository: " + json.dumps(binding, sort_keys=True, separators=(",", ":")) + " -->"
    import re

    text = re.sub(r"^<!-- plan-repository: .* -->$", repository, text, flags=re.MULTILINE)
    if repository not in text:
        text = text.replace("<!-- plan-contract: 4 -->", "<!-- plan-contract: 4 -->\n" + repository)
    finalized = finalized_text(text, binding)
    diagnostics = collect_diagnostics(finalized, args.tier, root, require_finalized=True, baseline=baseline)
    if diagnostics:
        for item in diagnostics:
            print(item, file=sys.stderr)
        return 1
    sys.stdout.write(finalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
