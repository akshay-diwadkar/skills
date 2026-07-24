#!/usr/bin/env python3
"""Test that all worked examples in worked-examples.md pass Contract v2 validation and finalization."""

from __future__ import annotations

import re
import sys
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_contract import finalize_assessment_text, validate_receipt  # noqa: E402
from check_assessment import parse_assessment, validate  # noqa: E402


def extract_worked_examples() -> list[tuple[str, str, str]]:
    worked_examples_path = SKILL_DIR / "references" / "worked-examples.md"
    text = worked_examples_path.read_text(encoding="utf-8")
    
    # Split by level markers
    sections = re.split(r"(?=# Assessment:)", text)
    examples = []
    for sec in sections:
        if "<!-- design-assessment-contract: 2;" not in sec:
            continue
        level_match = re.search(r"<!-- design-assessment-contract: 2; level: (?P<level>L[0-3]) -->", sec)
        if not level_match:
            continue
        level = level_match.group("level")
        title_match = re.search(r"^# Assessment: (?P<title>.+)$", sec, re.MULTILINE)
        title = title_match.group("title").strip() if title_match else "Worked Example"
        examples.append((title, level, sec.strip()))
    return examples


def test_worked_examples_pass_validation(tmp_path: Path):
    examples = extract_worked_examples()
    assert len(examples) >= 2, "Expected at least 2 worked examples in worked-examples.md"

    # Create dummy files referenced in examples for file checks
    (tmp_path / "billing").mkdir(parents=True, exist_ok=True)
    (tmp_path / "billing" / "formatter.py").write_text("def render_invoice(): pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "test_formatter.py").write_text("def test_compact_and_detailed(): pass\n", encoding="utf-8")
    (tmp_path / "payments").mkdir(parents=True, exist_ok=True)
    (tmp_path / "payments" / "service.py").write_text("import provider_sdk\n", encoding="utf-8")

    for title, level, example_text in examples:
        assessment, parse_diags = parse_assessment(example_text)
        assert not parse_diags, f"Parse diagnostics for '{title}': {parse_diags}"

        # Validate draft
        diags = validate(example_text, level, repo_root=tmp_path)
        errors = [d for d in diags if not d.is_warning]
        assert not errors, f"Draft validation errors for '{title}': {errors}"

        # Finalize and check receipt
        finalized = finalize_assessment_text(example_text, level)
        receipt_diags = validate_receipt(finalized, required=True, expected_level_or_mode=level)
        assert not receipt_diags, f"Receipt validation errors for '{title}': {receipt_diags}"

        final_diags = validate(finalized, level, repo_root=tmp_path, require_finalized=True)
        final_errors = [d for d in final_diags if not d.is_warning]
        assert not final_errors, f"Finalized validation errors for '{title}': {final_errors}"
