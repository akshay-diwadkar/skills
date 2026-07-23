#!/usr/bin/env python3
"""Score an optimization report against one blind fixture expectation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase-with-senior-dev" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_optimization import validate  # noqa: E402


EXPECTATIONS_PATH = DEV_DIR / "evals" / "expectations.json"
WEIGHTS = {
    "grounding": 20,
    "coverage": 15,
    "baseline": 15,
    "ecosystem": 10,
    "gating": 20,
    "plan": 15,
    "safety": 5,
}


def _keyword_matches(text: str, keyword: str) -> bool:
    return any(alternative.strip().casefold() in text for alternative in keyword.split("||"))


def _contains_groups(text: str, groups: list[list[str]]) -> tuple[int, int]:
    lowered = text.casefold()
    matched = sum(all(_keyword_matches(lowered, keyword) for keyword in group) for group in groups)
    return matched, len(groups)


def _dimension_score(text: str, groups: list[list[str]]) -> float:
    matched, total = _contains_groups(text, groups)
    return 1.0 if total == 0 else matched / total


def _section(text: str, name: str) -> str:
    match = re.search(
        rf"^## {re.escape(name)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else ""


def score(report: str, case: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    scope = str(case["scope"])
    stage = str(case["stage"])
    diagnostics = validate(report, scope, stage, repo_root)
    hard_failures = [f"validator:{item.code}" for item in diagnostics if not item.is_warning]
    sources = {
        "grounding": "\n".join((_section(report, "Brief and Authorization"), _section(report, "Evidence and Baselines"))),
        "coverage": _section(report, "System and Coverage Map"),
        "baseline": _section(report, "Evidence and Baselines"),
        "ecosystem": _section(report, "Capability Research"),
        "gating": _section(report, "Candidate Decisions"),
        "plan": "\n".join((_section(report, "Recommended Plan"), _section(report, "Verification, Rollback, and Residual Risk"))),
        "safety": "\n".join((_section(report, "Brief and Authorization"), _section(report, "Rejects, Deferrals, and Limitations"), _section(report, "Execution Record"))),
    }
    dimension_scores = {
        dimension: _dimension_score(sources[dimension], case.get(dimension, []))
        for dimension in WEIGHTS
    }
    lowered = report.casefold()
    for forbidden in case.get("forbidden", []):
        if all(_keyword_matches(lowered, keyword) for keyword in forbidden["keywords"]):
            hard_failures.append(f"forbidden:{forbidden['id']}")
    for critical in case.get("critical", []):
        if not all(_keyword_matches(lowered, keyword) for keyword in critical["keywords"]):
            hard_failures.append(f"critical-miss:{critical['id']}")
    total = sum(dimension_scores[name] * weight for name, weight in WEIGHTS.items())
    return {
        "score": round(total, 2),
        "passed": not hard_failures and total >= float(case.get("minimum_score", 90)),
        "scope": scope,
        "stage": stage,
        "hard_failures": sorted(set(hard_failures)),
        "dimension_scores": {name: round(value * 100, 2) for name, value in dimension_scores.items()},
        "diagnostics": [item.to_dict() for item in diagnostics],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("report")
    parser.add_argument("--expectations", type=Path, default=EXPECTATIONS_PATH)
    args = parser.parse_args(argv)
    expectations = json.loads(args.expectations.read_text(encoding="utf-8"))
    if args.case not in expectations:
        print(f"ERROR: unknown evaluation case {args.case!r}", file=sys.stderr)
        return 2
    fixture_root = DEV_DIR / "evals" / "fixtures" / args.case
    result = score(Path(args.report).read_text(encoding="utf-8"), expectations[args.case], fixture_root)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
