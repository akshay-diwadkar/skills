import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_plan_rubric import validate


def rubric_errors(text: str, tier: str = "tiny", issue_related: bool = False) -> list[str]:
    diags = validate(text, tier, issue_related=issue_related)
    return [d.message for d in diags if not d.is_warning]


def rubric_warnings(text: str, tier: str = "tiny", issue_related: bool = False) -> list[str]:
    diags = validate(text, tier, issue_related=issue_related)
    return [d.message for d in diags if d.is_warning]


# ---- Tiny Required Sections ----

class TestTinySections:
    def test_tiny_all_sections_pass(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nscripts/file.py:10 has bug\n## Change\nAdd null check\n## Test/Verification\npython test.py returns 0\n## Assumptions\nLow risk"
        errs = rubric_errors(text, "tiny")
        section_errors = [e for e in errs if "Missing section" in e]
        assert len(section_errors) == 0


class TestCurrentStateEvidence:
    def test_tiny_evidence_required(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nSomething is broken without citation\n## Change\nAdd null check\n## Test/Verification\npython test.py passes\n## Assumptions\nLow risk"
        errs = rubric_errors(text, "tiny")
        assert any("Current State must cite" in e for e in errs)

    def test_tiny_evidence_with_backtick_path(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\n`scripts/check_plan.py` has bug\n## Change\nAdd null check\n## Test/Verification\npython test.py passes\n## Assumptions\nLow risk"
        errs = rubric_errors(text, "tiny")
        evidence_errors = [e for e in errs if "Current State must cite" in e]
        assert len(evidence_errors) == 0

    def test_tiny_evidence_with_file_line(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nsrc/test.ts:42 has issue\n## Change\nAdd null check\n## Test/Verification\npython test.py passes\n## Assumptions\nLow risk"
        errs = rubric_errors(text, "tiny")
        evidence_errors = [e for e in errs if "Current State must cite" in e]
        assert len(evidence_errors) == 0

    def test_standard_evidence_requires_file_line(self):
        text = "# Add test suite\n## Goal\nFix it\n## Success Criteria\nTest passes\n## Current State\n`scripts/file.py` has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Add null check\n## Test Strategy\nRun tests for scenario\n## Rollback Plan\nTrivial revert\n## Assumptions\nLow risk"
        errs = rubric_errors(text, "standard")
        evidence_errors = [e for e in errs if "Current State must cite" in e]
        assert len(evidence_errors) >= 1


class TestScopeBoundaries:
    def test_scope_missing_boundaries(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nFix everything\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        assert any("Scope must include" in e for e in errs)

    def test_scope_with_boundaries(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix this bug\nOut of scope: refactoring\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        scope_errors = [e for e in errs if "Scope must include" in e]
        assert len(scope_errors) == 0


class TestAdversarialScope:
    def test_standard_fails_without_invariant_language(self):
        text = "# Add a test suite for validator scripts\n## Goal\nFix it\n## Success Criteria\nReturns exit code 0\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix bug\nOut of scope: refactor\nBlast radius: affected caller is local command\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nNo external side effects\n## Test Strategy\nTest happy path\npython test.py returns 0\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow impact"
        errs = rubric_errors(text, "standard")
        assert any("invariants" in e.lower() for e in errs)

    def test_standard_fails_without_blast_radius_language(self):
        text = "# Add a test suite for validator scripts\n## Goal\nFix it\n## Success Criteria\nReturns exit code 0\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix bug\nOut of scope: refactor\nPreserve existing behavior unchanged\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nNo external side effects\n## Test Strategy\nTest happy path\npython test.py returns 0\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow impact"
        errs = rubric_errors(text, "standard")
        assert any("blast radius" in e.lower() for e in errs)

    def test_standard_passes_adversarial_scope_inside_existing_sections(self):
        text = "# Add a test suite for validator scripts\n## Goal\nFix it\n## Success Criteria\nReturns exit code 0\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix bug\nOut of scope: refactor\nPreserve existing behavior unchanged\nBlast radius: affected caller is local command\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nNo external side effects\n## Test Strategy\nTest happy path\npython test.py returns 0\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow impact"
        errs = rubric_errors(text, "standard")
        adversarial_errors = [e for e in errs if "invariants" in e.lower() or "blast radius" in e.lower() or "side-effect" in e.lower()]
        assert len(adversarial_errors) == 0


class TestApproachPatterns:
    def test_approach_missing_pattern_ref(self):
        text = "# Add a test suite for the format checker\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nRewrite everything from scratch\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        assert any("Approach must reference" in e for e in errs)

    def test_approach_with_pattern_ref(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern from nearby files\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        approach_errors = [e for e in errs if "Approach must reference" in e]
        assert len(approach_errors) == 0


class TestChanges:
    def test_changes_not_ordered(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\nAdd null check\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        assert any("Changes must be" in e for e in errs)

    def test_changes_ordered(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Add null check\n2. Update tests\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        changes_errors = [e for e in errs if "Changes must be" in e]
        assert len(changes_errors) == 0


class TestTestStrategy:
    def test_tiny_missing_expected_result(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Change\nAdd check\n## Test/Verification\nRun the command\n## Assumptions\nLow"
        errs = rubric_errors(text, "tiny")
        assert any("expected passing result" in e for e in errs)

    def test_tiny_with_expected_result(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Change\nAdd check\n## Test/Verification\npython test.py returns 0\n## Assumptions\nLow"
        errs = rubric_errors(text, "tiny")
        result_errors = [e for e in errs if "expected passing result" in e]
        assert len(result_errors) == 0

    def test_standard_missing_scenarios(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nRun all tests\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        assert any("scenarios" in e.lower() for e in errs)

    def test_standard_with_scenarios(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest happy path and failure case\npython test.py returns 0\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        scenario_errors = [e for e in errs if "scenarios" in e.lower()]
        assert len(scenario_errors) == 0


class TestRollback:
    def test_rollback_missing_concrete(self):
        text = "# Add a test suite for the format checker\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nWe can always go back\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        assert any("concrete steps" in e for e in errs)

    def test_rollback_trivial(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        rollback_errors = [e for e in errs if "Rollback Plan must" in e]
        assert len(rollback_errors) == 0


class TestSideEffects:
    def test_standard_fails_without_side_effect_boundary(self):
        text = "# Add a test suite for validator scripts\n## Goal\nFix it\n## Success Criteria\nReturns exit code 0\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix bug\nOut of scope: refactor\nPreserve existing behavior unchanged\nBlast radius: affected caller is local command\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nFailure returns current error\n## Test Strategy\nTest happy path and failure\npython test.py returns 0\n## Rollback Plan\nTrivial revert\n## Assumptions\nLow impact"
        errs = rubric_errors(text, "standard")
        assert any("side-effect" in e.lower() for e in errs)

    def test_standard_passes_with_explicit_no_side_effect_boundary(self):
        text = "# Add a test suite for validator scripts\n## Goal\nFix it\n## Success Criteria\nReturns exit code 0\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix bug\nOut of scope: refactor\nPreserve existing behavior unchanged\nBlast radius: affected caller is local command\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nFailure returns current error; no external side effects\n## Test Strategy\nTest happy path and failure\npython test.py returns 0\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow impact"
        errs = rubric_errors(text, "standard")
        side_effect_errors = [e for e in errs if "side-effect" in e.lower()]
        assert len(side_effect_errors) == 0


class TestAssumptions:
    def test_assumptions_not_classified(self):
        text = "# Add unit tests for validation scripts\n## Goal\nFix it\n## Success Criteria\nTest passes\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix bug\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest the happy path\n`python test.py` returns 0\n## Rollback Plan\nTrivial revert\n## Assumptions\nSome vague thought"
        errs = rubric_errors(text, "standard")
        assert any("distinguish" in e.lower() for e in errs)

    def test_assumptions_classified(self):
        text = "# Add test suite\n## Goal\nFix it\n## Current State\nfile.py:10 has bug\n## Change\nAdd check\n## Test/Verification\npython test.py returns 0\n## Assumptions\nLow impact assumption: no data change"
        errs = rubric_errors(text, "tiny")
        assumption_errors = [e for e in errs if "Assumptions must" in e]
        assert len(assumption_errors) == 0


# ---- Interface Specification ----

class TestInterfaceSpec:
    def test_api_mentioned_no_code_block(self):
        text = "# Add test suite\n## Goal\nChange API\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: new API\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Add API endpoint\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        assert any("interface" in e.lower() for e in errs)

    def test_api_with_code_block(self):
        text = "# Add test suite\n## Goal\nChange API\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: new API\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Add API endpoint\n```typescript\ninterface Foo { bar: string }\n```\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "standard")
        interface_errors = [e for e in errs if "interface" in e.lower()]
        assert len(interface_errors) == 0


# ---- Issue-Related Follow-up ----

class TestIssueRelated:
    def test_issue_related_missing_follow_up(self):
        text = "# Add test suite\n## Goal\nFix bug\n## Current State\nfile.py:10 has bug\n## Change\nAdd check\n## Test/Verification\npython test.py returns 0\n## Assumptions\nLow risk"
        errs = rubric_errors(text, "tiny", issue_related=True)
        assert any("Post-Resolution" in e for e in errs)

    def test_issue_related_with_follow_up(self):
        text = "# Add test suite\n## Goal\nFix bug\n## Current State\nfile.py:10 has bug\n## Change\nAdd check\n## Test/Verification\npython test.py returns 0\n## Assumptions\nLow risk\n## Post-Resolution Audit Follow-Up\nAfter fixes pass, rerun codebase-issue-auditor. Compare current audit findings against open audit or GitHub issues. List resolved issue candidates with source, test, or audit evidence. Close resolved issues only after explicit user approval."
        errs = rubric_errors(text, "tiny", issue_related=True)
        follow_up_errors = [e for e in errs if "Post-Resolution" in e]
        assert len(follow_up_errors) == 0


# ---- High-Risk Checks ----

class TestHighRisk:
    def test_high_risk_missing_compatibility(self):
        text = "# Add test suite\n## Goal\nFix bug\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial\n## Assumptions\nLow"
        errs = rubric_errors(text, "high-risk")
        assert any("Compatibility" in e for e in errs)

    def test_high_risk_missing_risk_tiers(self):
        text = "# Add test suite\n## Goal\nFix bug\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial revert\n## Assumptions\nLow\n## Compatibility\nOld clients unaffected\n## Migration\nNo migration needed\n## Risk\nSome risk exists"
        errs = rubric_errors(text, "high-risk")
        assert any("P0, P1, and P2" in e for e in errs)

    def test_high_risk_requires_p0_p1_actions(self):
        text = "# Add a test suite for validator scripts\n## Goal\nFix bug\n## Success Criteria\nReturns exit code 0\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\nPreserve old clients unchanged\nBlast radius: affected clients and jobs are local only\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nNo external side effects\n## Test Strategy\nTest happy path and failure\npython test.py returns 0\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow impact\n## Compatibility\nOld clients read existing contract\n## Migration\nNo migration needed; rollback is reversible\n## Risk\nP0: data loss\nP1: timeout\nP2: minor perf - Action: monitor"
        errs = rubric_errors(text, "high-risk")
        assert any("P0 and P1" in e for e in errs)

    def test_high_risk_present(self):
        text = "# Add test suite\n## Goal\nFix bug\n## Current State\nfile.py:10 has bug\n## Scope\nIn scope: fix\nOut of scope: refactor\nPreserve old clients unchanged\nBlast radius: affected clients and jobs are local only\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Failure Modes\nNo external side effects\n## Test Strategy\nTest for pass\n## Rollback Plan\nTrivial revert with no persistent data\n## Assumptions\nLow\n## Compatibility\nOld clients unaffected\n## Migration\nNo migration needed; rollback is reversible\n## Risk\nP0: data loss - Action: add validation\nP1: timeout - Action: add retry\nP2: minor perf - Action: monitor"
        errs = rubric_errors(text, "high-risk")
        risk_errors = [e for e in errs if "Risk must" in e or "P0" in e]
        assert len(risk_errors) == 0
