#!/usr/bin/env python3
"""Score a design assessment against one blind fixture expectation using structured Contract v2 model assertions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_assessment import parse_assessment, validate  # noqa: E402

EXPECTATIONS_PATH = DEV_DIR / "evals" / "expectations.json"
WEIGHTS = {
    "grounding": 25,
    "classification": 25,
    "preservation": 15,
    "alternatives": 15,
    "migration": 10,
    "handoff": 10,
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


def score(assessment_text: str, case: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    level = str(case.get("level", "L0"))
    if "mode: discovery-only" in assessment_text.lower() or "invocation mode: discovery-only" in assessment_text.lower():
        level = "discovery-only"

    parsed_assessment, parse_diags = parse_assessment(assessment_text)
    diagnostics = validate(assessment_text, level, repo_root, require_finalized=True)

    hard_failures = [f"validator:{item.code}" for item in diagnostics if not item.is_warning]

    # Model-level semantic assertions
    if "expected_mode" in case and parsed_assessment.mode != case["expected_mode"]:
        hard_failures.append(f"semantic:mode-mismatch:{parsed_assessment.mode}!={case['expected_mode']}")

    if "expected_level" in case and parsed_assessment.level != case["expected_level"]:
        hard_failures.append(f"semantic:level-mismatch:{parsed_assessment.level}!={case['expected_level']}")

    if "expected_handoff" in case:
        act_handoff = parsed_assessment.handoff.next if parsed_assessment.handoff else ""
        if act_handoff != case["expected_handoff"]:
            hard_failures.append(f"semantic:handoff-mismatch:{act_handoff}!={case['expected_handoff']}")

    if "expected_debt_disposition" in case:
        act_disp = parsed_assessment.decision_summary.debt_disposition if parsed_assessment.decision_summary else ""
        if act_disp != case["expected_debt_disposition"]:
            hard_failures.append(f"semantic:debt-disposition-mismatch:{act_disp}!={case['expected_debt_disposition']}")

    sources = {
        "grounding": "\n".join(
            (
                _section(assessment_text, "Evidence and Current State"),
                _section(assessment_text, "Target Discovery Candidates"),
            )
        ),
        "classification": "\n".join(
            (
                _section(assessment_text, "Design Pressures and Classification"),
                _section(assessment_text, "Decision Summary"),
            )
        ),
        "preservation": _section(assessment_text, "Scope and Protected Contracts"),
        "alternatives": _section(assessment_text, "Alternatives and Pattern Decisions"),
        "migration": "\n".join(
            _section(assessment_text, name)
            for name in ("Migration and Rollback", "Operational Semantics", "System Ownership and Evolution")
        ),
        "handoff": "\n".join(
            (
                _section(assessment_text, "Scope and Protected Contracts"),
                _section(assessment_text, "Decision Summary"),
                _section(assessment_text, "Verification and Residual Risk"),
            )
        ),
    }
    dimension_scores = {
        dimension: _dimension_score(sources[dimension], case.get(dimension, []))
        for dimension in WEIGHTS
    }

    lowered = assessment_text.casefold()
    for forbidden in case.get("forbidden", []):
        if all(keyword.casefold() in lowered for keyword in forbidden["keywords"]):
            hard_failures.append(f"forbidden:{forbidden['id']}")
    for critical in case.get("critical", []):
        if not all(_keyword_matches(lowered, keyword) for keyword in critical["keywords"]):
            hard_failures.append(f"critical-miss:{critical['id']}")

    total = sum(dimension_scores[name] * weight for name, weight in WEIGHTS.items())
    return {
        "score": round(total, 2),
        "passed": not hard_failures and total >= float(case.get("minimum_score", 90)),
        "level": level,
        "hard_failures": sorted(set(hard_failures)),
        "dimension_scores": {name: round(value * 100, 2) for name, value in dimension_scores.items()},
        "diagnostics": [item.to_dict() for item in diagnostics],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("assessment")
    parser.add_argument("--expectations", type=Path, default=EXPECTATIONS_PATH)
    args = parser.parse_args(argv)
    expectations = json.loads(args.expectations.read_text(encoding="utf-8"))
    if args.case not in expectations:
        print(f"ERROR: unknown evaluation case {args.case!r}", file=sys.stderr)
        return 2
    fixture_root = DEV_DIR / "evals" / "fixtures" / args.case
    result = score(Path(args.assessment).read_text(encoding="utf-8"), expectations[args.case], fixture_root)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
