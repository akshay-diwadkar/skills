#!/usr/bin/env python3
"""Score an ideate handoff artifact (ideas.md) against offline structural coverage rules.

Standard-library-only. Zero model calls or network dependencies.
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


def score_ideas_draft(draft_path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    raw_text = draft_path.read_text(encoding="utf-8")
    diagnostics = validate_ideas_path(draft_path, repo_root=repo_root)

    # 12 Structural Checks
    checks = {
        "1_goal_understanding": "- Goal:" in raw_text and "- Success measure:" in raw_text and "- Baseline / status quo:" in raw_text,
        "2_evidence_traceability": "## 2. Evidence" in raw_text and ("| L1 |" in raw_text or "| E1 |" in raw_text),
        "3_candidate_relevance": "### I1." in raw_text and "### I2." in raw_text and "### I3." in raw_text,
        "4_mechanism_diversity": "- Mechanism category:" in raw_text,
        "5_lack_of_duplication": not any(d.code == "ideas.duplicate_mechanism_category" for d in diagnostics),
        "6_ranking_defensibility": "## 4. Comparison" in raw_text and not any(d.code == "ideas.recommendation_mismatch" for d in diagnostics),
        "7_confidence_calibration": not any(d.code == "ideas.limited_strong_verification" for d in diagnostics),
        "8_experiment_decisiveness": "Cheapest decisive experiment:" in raw_text and not any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics),
        "9_handling_of_contradictions": "## 6. Contradictions and open questions" in raw_text and not any(d.code == "ideas.empty_section6" for d in diagnostics),
        "10_no_hallucination_fake_precision": not any(
            d.code in ("ideas.hash_verified_without_digest", "ideas.hash_verified_digest_mismatch")
            for d in diagnostics
        ),
        "11_actionability": "- Why it beats rank 2:" in raw_text and "- Conditions that would change the ranking:" in raw_text,
        "12_structural_completeness": len(diagnostics) == 0,
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
