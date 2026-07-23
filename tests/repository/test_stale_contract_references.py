from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_stale_v2_plan_contract_references_in_runtime_files() -> None:
    # Scan runtime SKILL.md and references markdown files
    skills_dir = REPO_ROOT / "skills"
    stale_patterns = [
        re.compile(r"\bplan contract v2\b", re.IGNORECASE),
        re.compile(r"\bvalidated-v2-plan\b", re.IGNORECASE),
        re.compile(r"\bv2 plan\b", re.IGNORECASE),
    ]

    violations = []
    for md_file in skills_dir.rglob("*.md"):
        # Exclude tests if any
        if any(part in ("tests", "evals", "fixtures") for part in md_file.parts):
            continue
        text = md_file.read_text(encoding="utf-8")
        rel_path = md_file.relative_to(REPO_ROOT)
        for line_num, line in enumerate(text.splitlines(), start=1):
            # Allow lines that explicitly test or reject v2/v1 (e.g. "Reject v1, v2", "Contract v1/v2 plans are invalid", etc.)
            if any(reject in line.lower() for reject in ("reject", "unsupported", "invalid", "legacy")):
                continue
            for pattern in stale_patterns:
                if pattern.search(line):
                    violations.append(f"{rel_path}:{line_num}: {line.strip()}")

    assert not violations, "Stale plan contract v2 references found in runtime files:\n" + "\n".join(violations)
