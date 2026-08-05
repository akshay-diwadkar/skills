#!/usr/bin/env python3
"""Measure the v7 one-pass plan sealer without agent exploration."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]

import sys

sys.path.insert(0, str(ROOT / "tests" / "skills" / "plan-change"))
import v6_helpers as HELPERS  # noqa: E402


def _percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95 + 0.999) - 1))]


def _timing(values: list[float]) -> dict[str, float]:
    return {"median": statistics.median(values), "p95": _percentile95(values)}


def _make_repo(root: Path) -> Path:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "target.py").write_text(
        "def target(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8"
    )
    (root / "tests" / "test_target.py").write_text(
        "from src.target import target\n\ndef test_target():\n    assert target(' x ') == 'x'\n",
        encoding="utf-8",
    )
    return root


def _v7_draft(tier: str) -> str:
    metadata = {
        "tiny": '{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
        "standard": '{"intent":"refactor","tier":"standard","risk_domains":[]}',
        "high-risk": '{"intent":"bug-fix","tier":"high-risk","risk_domains":["security"]}',
    }[tier]
    locality = "local" if tier == "tiny" else "shared"
    propagation = ""
    if locality == "shared":
        propagation = """
## Propagation
P-1: surface: test | disposition: test-only | path: tests/test_target.py | owner: CH-1 | reason: F-1
"""
    boundaries = ""
    if tier == "high-risk":
        boundaries = """
## Boundaries and Risks
B-1: class: trusted input boundary | evidence: F-1 | flow: caller input -> authorization decision -> target normalization
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: unauthorized input could cross the normalization boundary
"""
    return f"""# Update the target behavior

<!-- plan-contract: 7 -->
<!-- plan-metadata: {metadata} -->

## Obligations
RQ-1: source: request | anchor: {tier} target change | obligation: apply the tier-specific target normalization update | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: a padded target value | when: target processes the input | then: it returns the stripped value | unchanged: the public string result remains stable

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns the current string normalization

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | change: preserve exact string normalization while applying the requested tier-specific implementation update | depends_on: none | locality: {locality} | reversibility: reversible
{propagation}{boundaries}## Verification
T-1: covers: SC-1, CH-1 | given: padded and plain target values | when: targeted tests execute | then: the regression fails before the fix when required and both values retain the exact normalized result | command: python -m pytest tests/test_target.py -q
"""


def _measure(iterations: int) -> dict[str, Any]:
    tiers = ("tiny", "standard", "high-risk")
    samples: dict[str, list[float]] = {tier: [] for tier in tiers}
    operations: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="plan-change-sealing-benchmark-") as temporary:
        root = Path(temporary)
        repo = _make_repo(root / "repo")
        for tier in tiers:
            request = root / f"{tier}-request.md"
            request.write_text(f"Apply the equivalent {tier} target change.\n", encoding="utf-8")
            draft = root / f"{tier}-v7.md"
            draft.write_text(_v7_draft(tier), encoding="utf-8")
            for _ in range(iterations):
                started = time.perf_counter()
                sealed = HELPERS.RUNTIME.seal_plan(repo, request, draft)
                samples[tier].append(time.perf_counter() - started)
            operations[tier] = sealed.counters
    return {"timings": {tier: _timing(samples[tier]) for tier in tiers}, "operations": operations}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    measured = _measure(args.iterations)
    command = f"python tests/skills/plan-change/evals/tools/benchmark_sealing.py --iterations {args.iterations}"
    if args.output:
        command += f" --output {args.output.as_posix()}"
    report = {
        "schema_version": 3,
        "methodology": {
            "benchmark_type": "targeted sealing microbenchmark",
            "excluded": ["agent exploration", "agent drafting", "tool-call accounting", "token accounting"],
            "end_to_end_native_agent_parity": "not_measured",
        },
        "v7_sealing_microbenchmark": {
            "label": "v7 sealing only; excludes repository exploration and agent work",
            "command": command,
            "iterations": args.iterations,
            "timings_seconds": measured["timings"],
            "operation_counts": measured["operations"],
        },
        "environment": {"date": "2026-08-05", "platform": platform.platform(), "python": platform.python_version()},
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
