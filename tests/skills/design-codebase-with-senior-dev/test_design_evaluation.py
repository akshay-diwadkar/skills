import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "design-codebase-with-senior-dev"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_design_evaluation  # noqa: E402
from assessment_contract import finalize_assessment_text, load_contract, marker  # noqa: E402


def _setup_fixture_repo(fixture_path: Path, target_path_str: str) -> None:
    fixture_path.mkdir(parents=True, exist_ok=True)
    file_rel = target_path_str if target_path_str != "none" else "src/system.py"
    target_file = fixture_path / file_rel
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.is_file():
        target_file.write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    deploy_file = fixture_path / "deploy" / "service.yaml"
    deploy_file.parent.mkdir(parents=True, exist_ok=True)
    if not deploy_file.is_file():
        deploy_file.write_text("replicaCount: 2\n", encoding="utf-8")

    schema_file = fixture_path / "schema" / "v1.sql"
    schema_file.parent.mkdir(parents=True, exist_ok=True)
    if not schema_file.is_file():
        schema_file.write_text("CREATE TABLE users;\n", encoding="utf-8")


def build_scenario_assessment(name: str, case: dict) -> str:
    mode = case.get("expected_mode", "targeted")
    level = case.get("expected_level", "L0")
    target = case.get("expected_target", "src/system.py")
    design_id = case.get("expected_design_id", "test-design")
    handoff = case.get("expected_handoff", "finish assessment" if level == "L0" else "plan-with-senior-dev")

    debt_info = case.get("expected_debt", {"id": "TD-1", "disposition": "repay"})
    debt_disp = debt_info.get("disposition", "repay")

    if mode == "discovery-only":
        return """# Assessment: Architectural Discovery and Triage
<!-- design-assessment-contract: 2; mode: discovery-only -->

## Decision Summary
- Invocation mode: discovery-only
- Selected target: none
- Selected level: discovery-only
- Recommended design: Refuse autonomous target selection. Hand off repository-wide triage to codebase-issue-auditor.
- Why minimum sufficient: Multiple candidate concerns rank similarly or require unavailable product intent.
- Protected behavior and contracts: C-1 preserved
- Primary structural pressure: P-1
- Technical-debt disposition: accept
- Residual risk: R-1
- Next owner: codebase-issue-auditor
- Selected design-id: none

## Scope and Protected Contracts
- C-1: status: preserved | contract: public command output | authorization: none
- H-1: status: assessment-only | next: codebase-issue-auditor
- TD-1: type: structural | evidence: F-1 | principal: legacy shortcut | interest: minor maintainability cost | frequency: current | blast-radius: src/system.py | disposition: accept | reason: low impact | repayment-boundary: none | recurrence-guard: none | revisit-trigger: when scope expands

## Evidence and Current State
- F-1: `src/system.py:1` | anchor: `current` | observation: Verified current behavior | source: code | strength: direct | freshness: current
- Current flow: input -> current -> output.

## Target Discovery Candidates
- T-1: target: src/system.py | evidence: F-1 | pressure: none | affected: C-1 | confidence: low | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: deferred | reason: Unsafe candidate with high operational risk requiring human product intent alignment. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: low

## Verification and Residual Risk
- V-1: proves: T-1 | method: run focused tests | expected: behavior remains stable.
- R-1: severity: low | scenario: future pressure changes | consequence: revisit design | owner: maintainer | follow-up: inspect history
"""

    contract = load_contract()

    alternatives = [
        f"- O-1: level: L0 | design-id: {'replace-l0-design' if level == 'L0' else 'test-l0-alt'} | selected: {'yes' if level == 'L0' else 'no'} | concepts: none | argument-for: smallest | argument-against: pressure remains | revisit: pressure disappears",
        f"- O-2: level: L1 | design-id: {'replace-l1-design' if level == 'L1' else 'test-l1-alt'} | selected: {'yes' if level == 'L1' else 'no'} | concepts: one module | argument-for: local | argument-against: limited | revisit: boundary changes",
        f"- O-3: level: L2 | design-id: {'replace-l2-design' if level == 'L2' else 'test-l2-alt'} | selected: {'yes' if level == 'L2' else 'no'} | concepts: one port | argument-for: contains volatility | argument-against: added indirection | revisit: multiple consumers",
    ]
    if level == "L3":
        alternatives.append(
            f"- O-4: level: L3 | design-id: {design_id} | selected: yes | concepts: distributed system | argument-for: scale | argument-against: complexity | revisit: none"
        )
    for i, a in enumerate(alternatives):
        if "selected: yes" in a:
            alternatives[i] = f"- O-{i+1}: level: {level} | design-id: {design_id} | selected: yes | concepts: chosen concept | argument-for: satisfies pressure | argument-against: added concept | revisit: stable boundary"

    pattern = ""
    if contract["levels"][level]["requires_pattern_gate"]:
        pattern = """### G-1: Adapter — admit
- Scope: introduced | Result: admit | Evidence: F-1, P-1

| Gate | Answer | Evidence | Consequence |
|---|---|---|---|
| Q1 | yes | F-1, P-1 | Resolves current pressure |
| Q2 | yes | F-1, P-1 | Evidenced recurrence |
| Q3 | yes | F-1, P-1 | Lower levels insufficient |
| Q4 | yes | F-1, P-1 | Single owner |
| Q5 | yes | F-1, P-1 | Stable contract |
| Q6 | yes | F-1, P-1 | Reduces propagation |
| Q7 | yes | F-1, P-1 | Constrains coupling |
| Q8 | yes | F-1, P-1 | Unambiguous state |
| Q9 | yes | F-1, P-1 | Contracts preserved |
| Q10 | yes | F-1, P-1 | Observable proof |
| Q11 | yes | F-1, P-1 | Operational semantics explicit |
| Q12 | yes | F-1, P-1 | Repository idiom |
| Q13 | yes | F-1, P-1 | Reversible slices |
| Q14 | yes | F-1, P-1 | Net value positive |"""

    target_discovery = ""
    if mode == "autonomous-discovery":
        target_discovery = f"\n## Target Discovery Candidates\n- T-1: target: {target} | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: {level} | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate with strong repository evidence. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high\n"

    facts = [
        f"- F-1: `{target}:1` | anchor: `current` | observation: The target file owns the behavior | source: code | strength: direct | freshness: current."
    ]
    if level == "L3":
        facts.extend([
            "- F-2: `deploy/service.yaml:1` | anchor: `replicaCount` | observation: Multi-instance deployment configuration | source: deployment | strength: direct | freshness: current.",
            "- F-3: `schema/v1.sql:1` | anchor: `CREATE TABLE` | observation: Database table schema | source: schema | strength: direct | freshness: current."
        ])

    sections = [
        f"# Select the Minimum Safe {level} Design",
        marker(level, mode=mode),
        "",
        "## Decision Summary",
        f"- Invocation mode: {mode}",
        f"- Selected target: {target}",
        f"- Selected level: {level}",
        f"- Recommended design: minimum safe design ({design_id})",
        "- Why minimum sufficient: direct local edit satisfies constraints",
        "- Protected behavior and contracts: C-1 preserved",
        "- Primary structural pressure: P-1",
        f"- Technical-debt disposition: TD-1 disposition: {debt_disp} | boundary: local",
        "- Residual risk: R-1 low",
        f"- Next owner: {handoff}",
        f"- Selected design-id: {design_id}",
        "",
        "## Scope and Protected Contracts",
        "- C-1: status: preserved | contract: public command output | authorization: none",
        f"- H-1: status: assessment-only | next: {handoff}",
        f"- TD-1: type: structural | evidence: F-1 | principal: legacy shortcut | interest: maintainability cost | frequency: current | blast-radius: {target} | disposition: {debt_disp} | reason: removes structural debt | repayment-boundary: local | recurrence-guard: unit test | revisit-trigger: when file volatility increases" + (" | containment-boundary: local" if debt_disp == "contain" else ""),
        "",
        "## Evidence and Current State",
        *facts,
        "- Current flow: input -> current -> output.",
        target_discovery.rstrip("\n"),
        "## Design Pressures and Classification",
        "- P-1: rank: 1 | evidence: F-1 | pressure: The scoped behavior has a verified change cost.",
        f"- D-1: level: {level} | design-id: {design_id} | selected: minimum safe design for {target} | because: F-1, P-1 | rejected: a stronger design adds cost.",
        "",
        "## Alternatives and Pattern Decisions",
        *alternatives,
    ]
    if pattern:
        sections.append(pattern)

    if level == "L1":
        sections.extend([
            "",
            "## Local Simplification and Preservation",
            "- Responsibility: current module owns execution.",
            "- Concepts removed: redundant factory.",
            "- Concepts retained: public command.",
            "- Preservation proof: C-1 and V-1.",
        ])
    if level in {"L2", "L3"}:
        sections.extend([
            "",
            "## Target Boundary",
            "- Responsibility and owner: domain-owned gateway.",
            "- Dependency direction: policy to port to adapter.",
            "- State and contract ownership: domain owns the stable contract.",
            "- Allowed calls and failures: authorize with explicit provider errors.",
            "",
            "## Migration and Rollback",
            "- M-1: prerequisite: characterize current calls | changed boundary: payment gateway | preserved: C-1 | proof: V-1 | rollback trigger: payload mismatch | rollback action: restore direct caller | cleanup: remove shim after all callers migrate with direct verification proof.",
            "",
            "## Operational Semantics",
            "- Source Of Truth: primary database table.",
            "- Failures: handled gracefully via domain exception.",
            "- Timeouts: 5000ms deadline passed to adapter.",
            "- Retries: 2 retries on 5xx errors.",
            "- Idempotency: idempotency key per request.",
            "- Ordering: not-applicable | evidence: F-1 | reason: Single requests are stateless.",
            "- Transactions: local database transaction.",
            "- Observability: log provider status code.",
            "- Resource Limits: max 50 concurrent connections.",
        ])
    if level == "L3":
        sections.extend([
            "",
            "## System Ownership and Evolution",
            "- System Invariant: domain entities maintain internal consistency.",
            "- Deployment Compatibility: backward compatible release.",
            "- Durable State Evolution: schema migration script v1 to v2.",
            "- Reconciliation: async event bus retry queue.",
            "- Rollback Compatibility: double writing supported for 1 release.",
        ])

    sections.extend([
        "",
        "## Verification and Residual Risk",
        "- V-1: proves: D-1 | method: run focused tests | expected: behavior remains stable.",
        "- R-1: severity: low | scenario: future pressure changes | consequence: revisit design | owner: maintainer | follow-up: inspect history",
    ])

    text = "\n".join(s for s in sections if s is not None) + "\n"
    return text.replace("\n\n\n", "\n\n")


def test_evaluation_catalog_has_fifteen_blind_cases() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    assert len(expectations) >= 15, f"Expected at least 15 evaluation cases, got {len(expectations)}"
    for name, case in expectations.items():
        fixture = DEV_DIR / "evals" / "fixtures" / name
        assert (fixture / "prompt.md").is_file(), f"Missing prompt.md in fixture {name}"


def test_all_fixture_expectations_accept_scenario_assessments() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    for name, case in expectations.items():
        fixture_path = DEV_DIR / "evals" / "fixtures" / name
        target_file = case.get("expected_target", "src/system.py")
        _setup_fixture_repo(fixture_path, target_file)

        raw = build_scenario_assessment(name, case)
        mode = case.get("expected_mode", "targeted")
        level = case.get("expected_level", "L0")

        finalized = finalize_assessment_text(raw, level, mode=mode)
        result = score_design_evaluation.score(finalized, case, fixture_path)
        assert result["passed"] is True, f"Fixture '{name}' failed scoring: {result}"
        assert result["score"] == 100, f"Fixture '{name}' score is {result['score']}, expected 100: {result}"


def test_scorer_hard_fails_invalid_assessment() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["l0-long-file-decoy"]
    fixture_path = DEV_DIR / "evals" / "fixtures" / "l0-long-file-decoy"
    _setup_fixture_repo(fixture_path, case.get("expected_target", "src/system.py"))

    result = score_design_evaluation.score(
        "# Architecture\n## Decision\nUse services.\n",
        case,
        fixture_path,
    )

    assert result["passed"] is False
    assert result["hard_failures"]


def test_scorer_rejects_negative_semantic_mutations() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    for name, case in expectations.items():
        fixture_path = DEV_DIR / "evals" / "fixtures" / name
        target_file = case.get("expected_target", "src/system.py")
        _setup_fixture_repo(fixture_path, target_file)

        raw = build_scenario_assessment(name, case)
        mode = case.get("expected_mode", "targeted")
        level = case.get("expected_level", "L0")

        # Mutate handoff to wrong value
        mutated_raw = (
            raw.replace("plan-with-senior-dev", "implement-with-senior-dev")
            .replace("finish assessment", "implement-with-senior-dev")
            .replace("codebase-issue-auditor", "implement-with-senior-dev")
        )
        finalized = finalize_assessment_text(mutated_raw, level, mode=mode)
        result = score_design_evaluation.score(finalized, case, fixture_path)
        assert result["passed"] is False or len(result["hard_failures"]) > 0, f"Fixture '{name}' failed to reject mutated assessment"
