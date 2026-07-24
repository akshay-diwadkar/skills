#!/usr/bin/env python3
"""Score a design assessment against one blind fixture expectation using parsed Contract v2 semantic model assertions."""

from __future__ import annotations

import argparse
import json
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


def score(assessment_text: str, case: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    level = str(case.get("expected_level", case.get("level", "L0")))
    if "mode: discovery-only" in assessment_text.lower() or "invocation mode: discovery-only" in assessment_text.lower():
        level = "discovery-only"

    parsed_assessment, parse_diags = parse_assessment(assessment_text)
    diagnostics = validate(assessment_text, level, repo_root, require_finalized=True)

    hard_failures: list[str] = [f"validator:{item.code}" for item in diagnostics if not item.is_warning]
    semantic_checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, err_msg: str) -> None:
        semantic_checks.append((name, condition, err_msg))
        if not condition:
            hard_failures.append(f"semantic:{name}:{err_msg}")

    # Mode check
    if "expected_mode" in case:
        check("mode", parsed_assessment.mode == case["expected_mode"], f"{parsed_assessment.mode}!={case['expected_mode']}")

    # Level check
    if "expected_level" in case:
        check("level", parsed_assessment.level == case["expected_level"], f"{parsed_assessment.level}!={case['expected_level']}")

    # Target check
    if "expected_target" in case:
        act_target = parsed_assessment.decision_summary.target if parsed_assessment.decision_summary else ""
        check("target", act_target == case["expected_target"], f"{act_target}!={case['expected_target']}")

    # Design ID check
    if "expected_design_id" in case:
        act_did = parsed_assessment.decision.design_id if parsed_assessment.decision else ""
        check("design_id", act_did == case["expected_design_id"], f"{act_did}!={case['expected_design_id']}")

    # Handoff check
    if "expected_handoff" in case:
        act_handoff = parsed_assessment.handoff.next if parsed_assessment.handoff else ""
        check("handoff", act_handoff == case["expected_handoff"], f"{act_handoff}!={case['expected_handoff']}")

    # Required Contracts
    if "required_contracts" in case:
        c_dict = {c.id: c.status for c in parsed_assessment.contracts}
        for req_c in case["required_contracts"]:
            cid = req_c["id"]
            stat = req_c.get("status")
            present = cid in c_dict
            check(f"contract:{cid}", present and (stat is None or c_dict[cid] == stat), f"missing or status mismatch for {cid}")

    # Required Evidence Sources
    if "required_evidence_sources" in case:
        sources_present = {f.source for f in parsed_assessment.facts} | {ef.source_id for ef in parsed_assessment.external_facts}
        for req_src in case["required_evidence_sources"]:
            check(f"evidence_source:{req_src}", req_src in sources_present, f"source {req_src} missing")

    # Minimum Evidence Strength
    if "minimum_evidence_strength" in case:
        req_st = case["minimum_evidence_strength"]
        strengths = {f.strength for f in parsed_assessment.facts}
        if req_st == "direct":
            check("evidence_strength", "direct" in strengths or "corroborated" in strengths, f"lacks direct/corroborated evidence (got {strengths})")

    # Technical Debt Disposition
    if "expected_debt" in case:
        req_debt = case["expected_debt"]
        req_id = req_debt.get("id", "TD-1")
        req_disp = req_debt.get("disposition")
        act_td = next((td for td in parsed_assessment.tech_debts if td.id == req_id), None)
        if act_td is None:
            check(f"debt:{req_id}", False, f"technical debt {req_id} missing")
        elif req_disp:
            check(f"debt_disposition:{req_id}", act_td.disposition == req_disp, f"{act_td.disposition}!={req_disp}")

    # Selected Candidate Rank
    if "expected_selected_candidate_rank" in case:
        sel_cands = [tc for tc in parsed_assessment.discovery_candidates if tc.status == "selected"]
        exp_rank = case["expected_selected_candidate_rank"]
        check("selected_candidate_rank", len(sel_cands) == 1 and sel_cands[0].rank == exp_rank, "selected candidate rank mismatch")

    # Selected Alternative Level
    if "expected_selected_alternative_level" in case:
        sel_alts = [a for a in parsed_assessment.alternatives if a.selected]
        exp_l = case["expected_selected_alternative_level"]
        check("selected_alt_level", len(sel_alts) == 1 and sel_alts[0].level == exp_l, "selected alternative level mismatch")

    # Pattern Result
    if "expected_pattern_result" in case:
        exp_res = case["expected_pattern_result"]
        act_res = parsed_assessment.pattern_gates[0].result if parsed_assessment.pattern_gates else None
        check("pattern_result", act_res == exp_res, f"{act_res}!={exp_res}")

    # Migration Requirement
    if "requires_migration" in case:
        req_mig = case["requires_migration"]
        check("migration", (len(parsed_assessment.migrations) > 0) == req_mig, "migration presence mismatch")

    # Discovery Refusal
    if "requires_discovery_refusal" in case:
        req_ref = case["requires_discovery_refusal"]
        check("discovery_refusal", (parsed_assessment.mode == "discovery-only") == req_ref, "discovery refusal mismatch")

    # Prohibited Free-text Claims
    if "prohibited_claims" in case:
        text_lower = assessment_text.lower()
        for claim in case["prohibited_claims"]:
            if claim.lower() in text_lower:
                hard_failures.append(f"prohibited_claim:{claim}")

    # Calculate Score
    total_checks = len(semantic_checks)
    passed_checks = sum(1 for _, cond, _ in semantic_checks if cond)
    if total_checks == 0:
        sem_score = 100.0
    else:
        sem_score = round((passed_checks / total_checks) * 100.0, 2)

    passed = (len(hard_failures) == 0) and (sem_score >= float(case.get("minimum_score", 90.0)))

    return {
        "score": sem_score,
        "passed": passed,
        "level": level,
        "hard_failures": sorted(set(hard_failures)),
        "dimension_scores": {
            "semantic_compliance": sem_score,
            "validator_pass": 100.0 if not [item for item in diagnostics if not item.is_warning] else 0.0,
        },
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
