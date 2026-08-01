#!/usr/bin/env python3
"""Measure v6 sealing by risk tier without including fixture setup time."""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HELPERS_PATH = ROOT / "tests" / "skills" / "plan-change" / "v6_helpers.py"
SPEC = importlib.util.spec_from_file_location("plan_change_v6_helpers", HELPERS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load v6 benchmark fixtures")
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

sys.path.insert(0, str(ROOT / "skills" / "engineering" / "plan-change" / "scripts"))
from plan_runtime import seal_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")

    drafts = {
        "tiny": HELPERS.tiny_plan(),
        "standard": HELPERS.new_file_plan(),
        "high-risk": HELPERS.high_risk_plan(),
    }
    samples: dict[str, list[float]] = {tier: [] for tier in drafts}
    operations: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="plan-change-v6-") as temporary:
        root = Path(temporary)
        repo = HELPERS.make_repo(root / "repo")
        request = root / "request.md"
        draft = root / "draft.md"
        request.write_text("Benchmark plan-change v6 sealing.\n", encoding="utf-8")
        for tier, text in drafts.items():
            draft.write_text(text, encoding="utf-8")
            for _ in range(args.iterations):
                started = time.perf_counter()
                result = seal_plan(repo, request, draft)
                samples[tier].append(time.perf_counter() - started)
            operations[tier] = result.counters

    report = {
        "iterations": args.iterations,
        "timings_seconds": {
            tier: {
                "median": statistics.median(values),
                "p95": sorted(values)[max(0, int(len(values) * 0.95) - 1)],
            }
            for tier, values in samples.items()
        },
        "operations": operations,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
