import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_plan_shape import validate, TIERS


def shape_errors(text: str, tier: str = "tiny") -> list[str]:
    diags = validate(text, tier)
    return [d.message for d in diags if not d.is_warning]


def shape_warnings(text: str, tier: str = "tiny") -> list[str]:
    diags = validate(text, tier)
    return [d.message for d in diags if d.is_warning]


# ---- Title Tests ----

class TestTitle:
    def test_valid_title(self):
        text = "# Add test suite for validation scripts\n## Goal\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text)
        assert not any("title" in e.lower() for e in errs)

    def test_generic_title_detected(self):
        text = "# Plan\n## Goal\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text)
        assert any("generic" in e.lower() for e in errs)

    def test_missing_h1_detected(self):
        text = "## Goal\n## Current State"
        errs = shape_errors(text)
        assert any("h1" in e.lower() for e in errs)

    def test_too_few_words_in_title(self):
        text = "# Fix bug\n## Goal\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text)
        assert any("word" in e.lower() and "4" in e for e in errs)

    def test_title_missing_action_verb(self):
        text = "# The plan for doing things differently\n## Goal\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text)
        assert any("verb" in e.lower() for e in errs)


# ---- Section Tests ----

class TestRequiredSections:
    def test_tiny_missing_required_section(self):
        text = "# Add test suite\n## Goal\n## Change"
        errs = shape_errors(text, "tiny")
        missing = [e for e in errs if "Missing required section" in e]
        assert any("Current State" in m for m in missing)
        assert any("Test/Verification" in m for m in missing)
        assert any("Assumptions" in m for m in missing)

    def test_tiny_has_all_required_sections(self):
        text = "# Add test suite\n## Goal\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text, "tiny")
        missing = [e for e in errs if "Missing required section" in e]
        assert len(missing) == 0

    def test_standard_missing_required(self):
        text = "# Add test suite\n## Goal\n## Current State\n## Change"
        errs = shape_errors(text, "standard")
        missing = [e for e in errs if "Missing required section" in e]
        assert any("Scope" in m for m in missing)
        assert any("Approach" in m for m in missing)
        assert any("Changes" in m for m in missing)

    def test_high_risk_missing_required(self):
        text = "# Add test suite\n## Goal\n## Current State\n## Change"
        errs = shape_errors(text, "high-risk")
        missing = [e for e in errs if "Missing required section" in e]
        assert any("Compatibility" in m for m in missing)
        assert any("Migration" in m for m in missing)
        assert any("Risk" in m for m in missing)


class TestOptionalSections:
    def test_tiny_optional_warning(self):
        text = "# Add test suite\n## Goal\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        warns = shape_warnings(text, "standard")
        optional_warnings = [w for w in warns if "Missing optional section" in w]
        assert any("Tracer Bullet" in w for w in optional_warnings)

    def test_standard_optional_included(self):
        text = "# Add test suite\n## Goal\n## Success Criteria\n## Current State\n## Scope\n## Approach\n## Changes\n## Tracer Bullet\n## Test Strategy\n## Rollback Plan\n## Assumptions\n## Doc Updates\n## Failure Modes"
        warns = shape_warnings(text, "standard")
        optional_warnings = [w for w in warns if "Missing optional section" in w]
        assert len(optional_warnings) == 0


# ---- Line Count Tests ----

class TestLineCount:
    def test_tiny_under_min_lines(self):
        text = "# X"
        errs = shape_errors(text, "tiny")
        assert any("non-empty lines" in e for e in errs)

    def test_tiny_within_range(self):
        text = "# Add unit tests for validation scripts\n## Goal\nCover the validators\n## Current State\nNo tests exist\n## Change\nAdd test files\n## Test/Verification\npytest returns 0\n## Assumptions\nLow impact"
        errs = shape_errors(text, "tiny")
        line_errors = [e for e in errs if "non-empty lines" in e]
        assert len(line_errors) == 0


# ---- Heading Duplicate Tests ----

class TestDuplicateHeadings:
    def test_duplicate_heading_detected(self):
        text = "# Add unit tests for validation scripts\n## Goal\nWrite tests\n## Current State\nNo tests\n## Goal\n## Change\nAdd files\n## Test/Verification\npytest returns 0\n## Assumptions\nLow"
        errs = shape_errors(text, "tiny")
        assert any("Duplicate heading" in e for e in errs)

    def test_no_duplicate_heading(self):
        text = "# Add unit tests for validation scripts\n## Goal\nCover all\n## Current State\nNo tests\n## Change\nAdd files\n## Test/Verification\npytest returns 0\n## Assumptions\nLow"
        errs = shape_errors(text, "tiny")
        dupes = [e for e in errs if "Duplicate heading" in e]
        assert len(dupes) == 0

    @staticmethod
    def _requires_issue_52_fix():
        import pytest
        pytest.skip("Requires issue #52 fix to be merged first")

    def test_heading_in_code_block_not_detected_as_duplicate(self):
        self._requires_issue_52_fix()

    def test_heading_in_code_block_not_counted_for_required_section(self):
        self._requires_issue_52_fix()


# ---- Uncertainty Pattern Tests ----

class TestUncertaintyPatterns:
    def test_deferred_decision_detected(self):
        text = "# Add test suite\n## Goal\ndecide later what to do\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text, "tiny")
        assert any("deferred_decision" in e for e in errs)

    def test_placeholder_detected(self):
        text = "# Add test suite\n## Goal\nTBD\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text, "tiny")
        assert any("placeholder" in e for e in errs)

    def test_vague_work_detected(self):
        text = "# Add test suite\n## Goal\nhandle edge cases later\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text, "tiny")
        assert any("vague_work" in e for e in errs)

    def test_weak_verification_detected(self):
        text = "# Add test suite\n## Goal\nTest the change\n## Current State\n## Change\n## Test/Verification\nRun tests.\n## Assumptions"
        errs = shape_errors(text, "tiny")
        assert any("weak_verification" in e for e in errs)

    def test_soft_commitment_detected(self):
        text = "# Add test suite\n## Goal\nmight want to check this\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text, "tiny")
        assert any("soft_commitment" in e for e in errs)

    def test_no_uncertainty_in_clean_plan(self):
        text = "# Add test suite\n## Goal\nFix the bug\n## Current State\nBug exists\n## Change\nAdd null check\n## Test/Verification\npython test.py returns 0\n## Assumptions\nLow risk"
        errs = shape_errors(text, "tiny")
        uncertainty = [e for e in errs if "uncertainty" in e]
        assert len(uncertainty) == 0

    def test_uncertainty_inside_code_block_not_flagged(self):
        text = "# Add test suite\n## Goal\nFix the bug\n## Current State\nBug exists\n## Change\n```\nhandle edge cases\n```\n## Test/Verification\npython test.py\n## Assumptions\nLow risk"
        errs = shape_errors(text, "tiny")
        uncertainty = [e for e in errs if "uncertainty" in e]
        assert len(uncertainty) == 0


# ---- Over-Abstraction Tests ----

class TestOverAbstraction:
    def test_factory_without_pattern_ref(self):
        text = "# Build a registry for all the handler classes\n## Goal\nWrite tests\n## State\nNo tests\n## Change\nAdd files\n## Test/Verification\npytest returns 0\n## Assumptions\nLow"
        errs = shape_errors(text, "tiny")
        assert any("Over-abstraction" in e for e in errs)

    def test_factory_with_pattern_ref_not_suspicious(self):
        text = "# Add test suite\n## Goal\nAdd a factory following existing pattern\n## Current State\n## Change\n## Test/Verification\n## Assumptions"
        errs = shape_errors(text, "tiny")
        over_abs = [e for e in errs if "over_abstraction" in e]
        assert len(over_abs) == 0


# ---- Permission to Proceed Tests ----

class TestPermissionToProceed:
    def test_shall_i_proceed_detected(self):
        text = "# Add unit tests for validation scripts\n## Goal\nFix the bug\n## State\nBug exists\n## Change\nAdd check\n## Test/Verification\npytest returns 0\n## Assumptions\nShall I proceed with implementation"
        errs = shape_errors(text, "tiny")
        assert any("permission to proceed" in e.lower() for e in errs)

    def test_no_permission_ask_in_clean_plan(self):
        text = "# Add test suite\n## Goal\nFix the bug\n## Current State\nBug exists\n## Change\nAdd check\n## Test/Verification\npython test.py\n## Assumptions\nLow risk"
        errs = shape_errors(text, "tiny")
        perm = [e for e in errs if "permission_to_proceed" in e]
        assert len(perm) == 0


# ---- Evidence Check Tests ----

class TestEvidence:
    def test_missing_evidence_in_standard(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nSomething is broken\n## Scope\nEverything\n## Approach\nRefactor\n## Changes\nStep 1: fix\n## Test Strategy\nRun tests\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = shape_errors(text, "standard")
        assert any("evidence" in e.lower() or "citation" in e.lower() for e in errs)

    def test_file_line_evidence_satisfies(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nsrc/file.py:42 is broken\n## Scope\nEverything\n## Approach\nRefactor following existing pattern\n## Changes\nStep 1: fix\n## Test Strategy\nRun tests\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = shape_errors(text, "standard")
        evidence_errors = [e for e in errs if "evidence" in e.lower() or "citation" in e.lower()]
        assert len(evidence_errors) == 0


# ---- Empty Section Test ----

class TestEmptySection:
    def test_empty_section_detected(self):
        text = "# Add test suite\n## Goal\n## Current State\n"
        errs = shape_errors(text, "tiny")
        assert any("empty" in e.lower() for e in errs)

    def test_section_with_only_code_block_is_empty(self):
        text = "# Add unit tests for validation scripts\n## Goal\nFix it\n## Change\n```\nsome code\n```\n## Test/Verification\npytest returns 0\n## Assumptions\nLow"
        errs = shape_errors(text, "tiny")
        empty = [e for e in errs if "empty" in e.lower()]
        assert any("Change" in e for e in empty)
