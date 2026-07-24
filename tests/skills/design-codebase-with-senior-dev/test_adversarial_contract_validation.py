#!/usr/bin/env python3
"""Adversarial test suite covering 20 edge-case failure scenarios for Contract v2."""

from __future__ import annotations

import sys
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_contract import finalize_assessment_text, render_scaffold  # noqa: E402
from check_assessment import validate  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def setup_mock_repo(tmp_path: Path) -> Path:
    source = tmp_path / "src"
    source.mkdir(exist_ok=True)
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")
    deploy = tmp_path / "deploy"
    deploy.mkdir(exist_ok=True)
    (deploy / "service.yaml").write_text("replicaCount: 2\n", encoding="utf-8")
    schema = tmp_path / "schema"
    schema.mkdir(exist_ok=True)
    (schema / "v1.sql").write_text("CREATE TABLE users;\n", encoding="utf-8")
    return tmp_path


# 1. Autonomous mode with selected candidate but no D-n
def test_1_autonomous_selected_missing_decision(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery")
    # Remove D-1 line
    text_no_d = "\n".join(line for line in text.splitlines() if not line.strip().startswith("- D-1:"))
    diags = validate(text_no_d, "L1", root)
    assert any(d.code == "decision.record.missing" for d in diags)


# 2. Discovery-only CLI finalization
def test_2_discovery_only_finalization(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    disc = render_scaffold("L0", mode="discovery-only")
    disc = disc.replace("path:1", "src/system.py:1").replace("existing_anchor", "def current")
    finalized = finalize_assessment_text(disc, "discovery-only", mode="discovery-only")
    diags = validate(finalized, "discovery-only", root, require_finalized=True)
    assert not [d for d in diags if not d.is_warning], f"Discovery-only finalization errors: {diags}"
    assert "<!-- assessment-validation: 2; mode: discovery-only; sha256:" in finalized


# 3. L2 missing migration
def test_3_l2_missing_migration(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L2")
    text_no_m = "\n".join(line for line in text.splitlines() if not line.strip().startswith("- M-1:"))
    diags = validate(text_no_m, "L2", root)
    assert any(d.code == "l2.migration.missing" for d in diags)


# 4. L3 missing evolution fields
def test_4_l3_missing_evolution_fields(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L3")
    text_no_evo = "\n".join(line for line in text.splitlines() if "System Invariant:" not in line)
    diags = validate(text_no_evo, "L3", root)
    assert any(d.code == "l3.evolution_field.missing" for d in diags)


# 5. Four same-source facts attempting an L3 bypass
def test_5_l3_same_source_bypass(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L3")
    text_same_source = text.replace("source: deployment", "source: code").replace("source: schema", "source: code")
    diags = validate(text_same_source, "L3", root)
    assert any(d.code == "evidence.l3.categories_insufficient" for d in diags)


# 6. Pattern admission with no parsed questions
def test_6_pattern_admission_no_questions(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L2")
    # Replace table format with one-line gate lacking questions
    text_no_q = text.replace(
        "| Gate | Answer | Evidence | Consequence |", ""
    )
    text_no_q = "\n".join(line for line in text_no_q.splitlines() if not line.strip().startswith("| Q"))
    diags = validate(text_no_q, "L2", root)
    assert any(d.code == "pattern.questions.missing" for d in diags)


# 7. Pattern removal without responsibility transfer
def test_7_pattern_removal_no_destination(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L2").replace("Result: admit", "Result: remove")
    diags = validate(text, "L2", root)
    assert any(d.code == "pattern.removal.destination_missing" for d in diags)


# 8. Fact with valid file but nonexistent anchor
def test_8_fact_nonexistent_anchor(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L0").replace("anchor: `current`", "anchor: `nonexistent_symbol_anchor`")
    diags = validate(text, "L0", root)
    assert any(d.code == "fact.anchor.missing" for d in diags)


# 9. Fact with line outside file bounds
def test_9_fact_line_out_of_bounds(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L0").replace("`src/system.py:1`", "`src/system.py:9999`")
    diags = validate(text, "L0", root)
    assert any(d.code == "fact.line.out_of_bounds" for d in diags)


# 10. Invalid Git-history commit
def test_10_invalid_git_history_commit(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    import subprocess
    subprocess.run(["git", "init"], cwd=root, capture_output=True)
    text = valid_v2_assessment("L0").replace("`src/system.py:1`", "`git-history:deadbeef00000000000000000000000000000000:src/system.py`").replace("source: code", "source: repository-history")
    diags = validate(text, "L0", root)
    assert any(d.code == "fact.git_history.commit_missing" for d in diags)


# 11. Autonomous candidate with unknown evidence
def test_11_autonomous_candidate_unknown_evidence(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("evidence: F-1", "evidence: F-99")
    diags = validate(text, "L1", root)
    assert any(d.code == "pressure.evidence.invalid" or d.code == "discovery.autonomous.evidence_missing" or d.code == "discovery.candidate.evidence_invalid" for d in diags)


# 12. Autonomous candidate with unknown affected contract
def test_12_autonomous_candidate_unknown_contract(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("affected: C-1", "affected: C-99")
    diags = validate(text, "L1", root)
    assert any("affected" in d.message.lower() or "c-99" in d.message.lower() or "contract" in d.message.lower() for d in diags)


# 13. Genuine tied candidates forcing refusal / discovery-only
def test_13_tied_candidates_selecting_one(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery")
    # Add a second candidate T-2 with exact same ranking fields as T-1 so scores tie
    cand2 = "- T-2: target: src/other.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 2 | status: deferred | reason: Equal score. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    text_tied = text.replace("## Target Discovery Candidates\n", f"## Target Discovery Candidates\n{cand2}\n")
    diags = validate(text_tied, "L1", root)
    assert any(d.code == "discovery.autonomous.ranking_tied" for d in diags)


# 14. Selected target inconsistent with D-n
def test_14_target_inconsistent_with_decision(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace(
        "- Selected target: src/system.py", "- Selected target: src/other.py"
    )
    diags = validate(text, "L1", root)
    assert any(d.code == "summary.target.mismatch" for d in diags)


# 15. Selected alternative inconsistent with D-n
def test_15_selected_alt_inconsistent_with_decision(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L1").replace(
        "selected: yes", "selected: no_temp"
    ).replace(
        "- O-1: level: L0 | design-id: test-l0 | selected: no", "- O-1: level: L0 | design-id: test-l0 | selected: yes"
    ).replace(
        "selected: no_temp", "selected: no"
    )
    diags = validate(text, "L1", root)
    assert any(d.code == "alternatives.selected.level_mismatch" for d in diags)


# 16. Technical debt with unknown evidence
def test_16_tech_debt_unknown_evidence(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L0").replace("evidence: F-1", "evidence: F-999")
    diags = validate(text, "L0", root)
    assert any(d.code == "tech_debt.evidence.invalid" for d in diags)


# 17. Migration with unknown proof
def test_17_migration_unknown_proof(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L2").replace("proof: V-1", "proof: V-999")
    diags = validate(text, "L2", root)
    assert any(d.code == "migration.proof.invalid" for d in diags)


# 18. Duplicate handoffs
def test_18_duplicate_handoffs(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    text = valid_v2_assessment("L0") + "\n- H-2: status: assessment-only | next: finish assessment\n"
    diags = validate(text, "L0", root)
    assert any(d.code == "handoff.count.invalid" for d in diags)


# 19. L3 scaffold with single selected alternative
def test_19_l3_scaffold_single_selected_alt() -> None:
    scaffold = render_scaffold("L3")
    selected_alts = [line for line in scaffold.splitlines() if line.startswith("- O-") and "selected: yes" in line]
    assert len(selected_alts) == 1, f"Expected 1 selected alternative in L3 scaffold, got {len(selected_alts)}: {selected_alts}"


# 20. Unfinalized otherwise-valid assessment
def test_20_unfinalized_assessment_fails_require_finalized(tmp_path: Path) -> None:
    root = setup_mock_repo(tmp_path)
    raw = valid_v2_assessment("L0")
    diags = validate(raw, "L0", root, require_finalized=True)
    assert any(d.code == "finalization.receipt.missing" for d in diags)
