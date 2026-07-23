#!/usr/bin/env python3
"""Score a blind audit bundle against synthetic-repository expectations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
RUNTIME_SCRIPTS = REPO_ROOT / "skills" / "engineering" / "codebase-issue-auditor" / "scripts"
if str(RUNTIME_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SCRIPTS))

from audit_bundle import AuditBundleError, read_json, validate_audit_bundle  # noqa: E402


EXPECTATIONS_PATH = DEV_DIR / "evals" / "expectations.json"


def candidate_text(candidate: dict[str, Any]) -> str:
    evidence = candidate.get("evidence", [])
    evidence_text = " ".join(
        f"{item.get('location', '')} {item.get('observation', '')}"
        for item in evidence
        if isinstance(item, dict)
    )
    fields = [
        candidate.get("title", ""),
        candidate.get("summary", ""),
        candidate.get("root_cause", ""),
        candidate.get("affected_workflow", ""),
        candidate.get("impact", ""),
        evidence_text,
    ]
    return " ".join(str(field) for field in fields).casefold()


def matches(text: str, keywords: list[str]) -> bool:
    return all(keyword.casefold() in text for keyword in keywords)


def score(bundle: dict[str, Any], expectations: dict[str, Any]) -> list[str]:
    errors = validate_audit_bundle(bundle)
    if errors:
        return ["bundle validation: " + error for error in errors]

    accepted = [candidate for candidate in bundle["candidates"] if candidate["decision"] == "accepted"]
    texts = [candidate_text(candidate) for candidate in accepted]
    score_errors: list[str] = []
    for expected in expectations.get("expected_findings", []):
        if not any(matches(text, expected["keywords"]) for text in texts):
            score_errors.append(f"missing expected finding {expected['id']}")
    for forbidden in expectations.get("forbidden_findings", []):
        if any(matches(text, forbidden["keywords"]) for text in texts):
            score_errors.append(f"promoted decoy finding {forbidden['id']}")
    return score_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a blind audit bundle against a synthetic case.")
    parser.add_argument("case", help="Evaluation case name.")
    parser.add_argument("bundle", help="Path to the produced audit bundle.")
    parser.add_argument("--expectations", default=str(EXPECTATIONS_PATH), help="Expectation file path.")
    args = parser.parse_args(argv)

    try:
        bundle = read_json(Path(args.bundle))
        expectations_raw = json.loads(Path(args.expectations).read_text(encoding="utf-8"))
    except (AuditBundleError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not isinstance(bundle, dict):
        print("ERROR: evaluation input must be an audit bundle object", file=sys.stderr)
        return 2
    if not isinstance(expectations_raw, dict) or args.case not in expectations_raw:
        print(f"ERROR: unknown evaluation case {args.case!r}", file=sys.stderr)
        return 2

    case_expectations = expectations_raw[args.case]
    if not isinstance(case_expectations, dict):
        print(f"ERROR: invalid expectations for {args.case!r}", file=sys.stderr)
        return 2
    errors = score(bundle, case_expectations)
    if errors:
        print("Audit evaluation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Audit evaluation passed for {args.case}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
