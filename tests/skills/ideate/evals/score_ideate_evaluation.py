#!/usr/bin/env python3
"""Score an ideate handoff artifact (ideas.md) against offline structural coverage rules.

Structural only: this checks that contract-required structure is present and
deterministically valid. It does not measure relevance, novelty, truth, or
ranking wisdom. Standard-library-only. Zero model calls or network
dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_SCRIPTS = REPO_ROOT / "skills" / "research" / "ideate" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from ideas_contract import validate_ideas_path  # noqa: E402

SECTION6_FIELDS = (
    "- Strongest challenge to rank 1:",
    "- Baseline / status quo comparison:",
    "- Condition for a different winner:",
    "- Remaining contradiction or uncertainty:",
)


def score_ideas_draft(draft_path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    raw_text = draft_path.read_text(encoding="utf-8")
    diagnostics = validate_ideas_path(draft_path, repo_root=repo_root)
    codes = {d.code for d in diagnostics}

    # 14 Structural Checks
    checks = {
        "1_goal_understanding": "- Goal:" in raw_text and "- Success measure:" in raw_text and "- Baseline / status quo:" in raw_text,
        "2_evidence_section": "## 2. Evidence" in raw_text and "External research status:" in raw_text,
        "3_candidate_presence": "### I1." in raw_text and "### I2." in raw_text and "### I3." in raw_text,
        "4_support_basis_declared": "- Support basis:" in raw_text
        and not any(
            code in codes
            for code in (
                "ideas.invalid_support_basis",
                "ideas.evidence_backed_without_refs",
                "ideas.unknown_evidence_reference",
            )
        ),
        "5_mechanism_distinctness": not any(d == "ideas.duplicate_mechanism_category" for d in codes),
        "6_lead_match_exact": "## 4. Comparison" in raw_text and "ideas.recommendation_mismatch" not in codes,
        "7_no_overclaimed_verification": "ideas.limited_strong_verification" not in codes,
        "8_experiment_decisiveness": "Cheapest decisive experiment:" in raw_text
        and "ideas.decisive_experiment_incomplete" not in codes,
        "9_challenge_substantive": all(field in raw_text for field in SECTION6_FIELDS)
        and "ideas.empty_section6_field" not in codes
        and "ideas.empty_section6" not in codes,
        "10_no_fake_precision": "ideas.hash_verified_without_digest" not in codes
        and "ideas.hash_verified_digest_mismatch" not in codes,
        "11_criteria_applied": "- Decision-criteria fit:" in raw_text
        and "- How decision criteria were applied:" in raw_text,
        "12_state_coherence": "ideas.unsupported_decision_ready" not in codes,
        "13_research_stop_recorded": "- Research stop condition:" in raw_text
        and "- Research stop reason:" in raw_text
        and "ideas.invalid_research_stop_reason" not in codes,
        "14_structural_completeness": len(diagnostics) == 0,
    }

    passed_count = sum(1 for v in checks.values() if v)
    score_pct = (passed_count / len(checks)) * 100.0

    return {
        "valid": len(diagnostics) == 0,
        "score_pct": score_pct,
        "passed_dimensions": passed_count,
        "total_dimensions": len(checks),
        "checks": checks,
        "diagnostics": [str(d) for d in diagnostics],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an ideas.md draft against structural coverage rubric")
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()

    if not args.draft.is_file():
        parser.error("--draft must be a valid file")

    results = score_ideas_draft(args.draft, repo_root=args.repo_root)
    print(json.dumps(results, indent=2))
    return 0 if results["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
