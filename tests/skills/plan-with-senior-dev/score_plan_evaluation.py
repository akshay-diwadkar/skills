#!/usr/bin/env python3
"""Score a blind v3 plan against synthetic-repository expectations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_plan_rubric  # noqa: E402
import check_plan_shape  # noqa: E402
import plan_model  # noqa: E402
from _plan_utils import validate_receipt  # noqa: E402
from plan_model import parse_markdown, validate_semantics  # noqa: E402


EXPECTATIONS_PATH = DEV_DIR / "evals" / "expectations.json"
WEIGHTS = {
    "grounding": 20,
    "decisions": 20,
    "propagation": 20,
    "verification": 15,
    "adversarial": 10,
    "blueprint": 15,
}


def _keyword_matches(text: str, keyword: str) -> bool:
    """Match one semantic keyword, allowing explicit ``a||b`` wording variants."""
    return any(alternative.strip().casefold() in text for alternative in keyword.split("||"))


def _contains_groups(text: str, groups: list[list[str]]) -> tuple[int, int]:
    lowered = text.casefold()
    matched = sum(all(_keyword_matches(lowered, keyword) for keyword in group) for group in groups)
    return matched, len(groups)


def _dimension_score(text: str, groups: list[list[str]]) -> float:
    matched, total = _contains_groups(text, groups)
    return 1.0 if total == 0 else matched / total


def _body(document: plan_model.MarkdownDocument, *names: str) -> str:
    return "\n".join(section.body for name in names if (section := document.find_section(name)) is not None)


def score(
    plan: str,
    case: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    tier = str(case["tier"])
    document = parse_markdown(plan)
    diagnostics = [
        *check_plan_shape.validate(plan, tier),
        *check_plan_rubric.validate(plan, tier),
        *validate_semantics(plan, tier, repo_root),
        *validate_receipt(plan, required=True),
    ]
    hard_failures = [f"validator:{item.code}" for item in diagnostics if not item.is_warning]
    dimension_sources = {
        "grounding": _body(document, "Evidence Ledger"),
        "decisions": _body(document, "Decisions"),
        "propagation": _body(document, "Implementation Specification", "Traceability"),
        "verification": _body(document, "Verification"),
        "adversarial": _body(
            document,
            "Risks, Assumptions, and Attack",
            "Compatibility and Rollout",
            "Durable Rollback",
        ),
        "blueprint": _body(document, "Implementation Specification"),
    }
    forbidden_source = dimension_sources["propagation"].casefold()
    dimension_scores = {
        dimension: _dimension_score(dimension_sources[dimension], case.get(dimension, []))
        for dimension in WEIGHTS
    }
    lowered = plan.casefold()
    for forbidden in case.get("forbidden", []):
        if all(keyword.casefold() in forbidden_source for keyword in forbidden["keywords"]):
            hard_failures.append(f"forbidden:{forbidden['id']}")
    for critical in case.get("critical", []):
        if not all(keyword.casefold() in lowered for keyword in critical["keywords"]):
            hard_failures.append(f"critical-miss:{critical['id']}")
    total = sum(dimension_scores[name] * weight for name, weight in WEIGHTS.items())
    return {
        "score": round(total, 2),
        "passed": not hard_failures and total >= float(case.get("minimum_score", 90)),
        "contract_version": 3,
        "hard_failures": sorted(set(hard_failures)),
        "dimension_scores": {name: round(value * 100, 2) for name, value in dimension_scores.items()},
        "diagnostics": [item.to_dict() for item in diagnostics],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("plan")
    parser.add_argument("--expectations", default=str(EXPECTATIONS_PATH))
    args = parser.parse_args(argv)
    expectations = json.loads(Path(args.expectations).read_text(encoding="utf-8"))
    if args.case not in expectations:
        print(f"ERROR: unknown evaluation case {args.case!r}", file=sys.stderr)
        return 2
    case = expectations[args.case]
    repo_root = DEV_DIR / "evals" / "fixtures" / args.case
    result = score(
        Path(args.plan).read_text(encoding="utf-8"),
        case,
        repo_root,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
