import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assessment_contract import finalize_assessment_text, load_contract, marker, render_scaffold  # noqa: E402
from check_assessment import validate  # noqa: E402


def valid_v2_assessment(level: str, mode: str = "targeted") -> str:
    if mode == "discovery-only":
        return render_scaffold("L0", mode="discovery-only")
    contract = load_contract()
    
    alternatives = [
        f"- O-1: level: L0 | selected: {'yes' if level == 'L0' else 'no'} | concepts: none | argument-for: smallest | argument-against: pressure remains | revisit: pressure disappears",
        f"- O-2: level: L1 | selected: {'yes' if level == 'L1' else 'no'} | concepts: one module | argument-for: local | argument-against: limited | revisit: boundary changes",
        f"- O-3: level: L2 | selected: {'yes' if level == 'L2' else 'no'} | concepts: one port | argument-for: contains volatility | argument-against: added indirection | revisit: multiple consumers",
    ]
    if level == "L3":
        alternatives.append(
            "- O-4: level: L3 | selected: yes | concepts: distributed system | argument-for: scale | argument-against: complexity | revisit: none"
        )

    pattern = ""
    if contract["levels"][level]["requires_pattern_gate"]:
        questions = ", ".join(f"Q{number}=yes" for number in range(1, 15))
        pattern = f"\n- G-1: pattern: Adapter | scope: introduced | result: admit | questions: {questions} | evidence: F-1, P-1"

    target_discovery = ""
    if mode == "autonomous-discovery":
        target_discovery = f"\n## Target Discovery Candidates\n- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: {level} | blast-radius: local | product-intent-required: false | status: selected | reason: Dominant candidate.\n"
    elif mode == "discovery-only":
        target_discovery = f"\n## Target Discovery Candidates\n- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: low | likely-level: {level} | blast-radius: local | product-intent-required: false | status: deferred | reason: Unsafe candidate.\n"

    selected_level_summary = level

    facts = [
        "- F-1: `src/system.py:1` | anchor: `current` | observation: The current function owns the behavior | source: code | strength: direct | freshness: current."
    ]
    if level == "L3":
        facts.extend([
            "- F-2: `deploy/service.yaml:1` | anchor: `replicaCount` | observation: Multi-instance deployment configuration | source: deployment | strength: direct | freshness: current.",
            "- F-3: `schema/v1.sql:1` | anchor: `CREATE TABLE` | observation: Database table schema | source: schema | strength: direct | freshness: current."
        ])

    next_owner = "plan-with-senior-dev"
    if mode == "discovery-only":
        next_owner = "codebase-issue-auditor"
    elif level == "L0":
        next_owner = "finish assessment"

    sections = [
        f"# Select the Minimum Safe {level} Design",
        marker(level),
        "",
        "## Decision Summary",
        f"- Invocation mode: {mode}",
        "- Selected target: src/system.py",
        f"- Selected level: {selected_level_summary}",
        "- Recommended design: minimum safe design",
        "- Why minimum sufficient: direct local edit satisfies constraints",
        "- Protected behavior and contracts: C-1 preserved",
        "- Primary structural pressure: P-1",
        "- Technical-debt disposition: TD-1 disposition: repay | boundary: local",
        "- Residual risk: R-1 low",
        f"- Next owner: {next_owner}",
        "",
        "## Scope and Protected Contracts",
        "- C-1: status: preserved | contract: public command output | authorization: none",
        f"- H-1: status: assessment-only | next: {next_owner}",
        "- A-1: status: none | impact: none | verification: none",
        "- TD-1: type: structural | evidence: F-1 | principal: legacy shortcut | interest: minor maintainability cost | frequency: current | blast-radius: src/system.py | disposition: repay | reason: removes debt | repayment-boundary: local | recurrence-guard: unit test | revisit-trigger: none",
        "",
        "## Evidence and Current State",
        *facts,
        "- Current flow: input -> current -> output.",
        target_discovery.rstrip("\n"),
        "## Design Pressures and Classification",
        "- P-1: rank: 1 | evidence: F-1 | pressure: The scoped behavior has a verified change cost.",
        f"- D-1: level: {level} | selected: minimum safe design for src/system.py | because: F-1, P-1 | rejected: a stronger design adds cost.",
        "",
        "## Alternatives and Pattern Decisions",
        *alternatives,
    ]
    if pattern:
        sections.append(pattern.lstrip("\n"))
    sections.extend([
        "",
        "## Verification and Residual Risk",
        "- V-1: proves: D-1 | method: run focused tests | expected: behavior remains stable.",
        "- R-1: severity: low | scenario: future pressure changes | consequence: revisit design | owner: maintainer | follow-up: inspect history",
    ])
    if level == "L1":
        sections.extend([
            "",
            "## Local Simplification and Preservation",
            "- Responsibility: current module.",
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
            "- M-1: prerequisite: characterize current calls | changed boundary: payment gateway | preserved: C-1 | proof: V-1 | rollback trigger: payload mismatch | rollback action: restore direct caller | cleanup: remove shim after all callers migrate",
            "",
            "## Operational Semantics",
        ])
        sections.extend(
            f"- {field.title()}: not-applicable: verified local-only assessment."
            for field in contract["operational_fields"]
        )
    if level == "L3":
        sections.extend(["", "## System Ownership and Evolution"])
        sections.extend(f"- {field.title()}: explicitly defined." for field in contract["l3_evolution_fields"])

    text = "\n".join(s for s in sections if s is not None) + "\n"
    return text.replace("\n\n\n", "\n\n")


def assessment(level: str, mode: str = "targeted") -> str:
    raw = valid_v2_assessment(level, mode=mode)
    return finalize_assessment_text(raw, level, mode=mode)


def codes(text: str, level: str, repo_root: Path) -> set[str]:
    return {item.code for item in validate(text, level, repo_root)}


def test_valid_v2_assessments_pass_every_level(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "service.yaml").write_text("replicaCount: 2\n", encoding="utf-8")
    schema = tmp_path / "schema"
    schema.mkdir()
    (schema / "v1.sql").write_text("CREATE TABLE users;\n", encoding="utf-8")

    for level in ("L0", "L1", "L2", "L3"):
        assert validate(valid_v2_assessment(level), level, tmp_path) == []


def test_missing_citation_is_rejected(tmp_path: Path) -> None:
    text = valid_v2_assessment("L0")
    assert "fact.path.missing" in codes(text, "L0", tmp_path)


def test_declared_level_must_match_classification(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = valid_v2_assessment("L2").replace("- D-1: level: L2", "- D-1: level: L1")

    assert "decision.level.mismatch" in codes(text, "L2", tmp_path)


def test_authorized_contract_change_requires_named_authorization(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = valid_v2_assessment("L0").replace("status: preserved", "status: authorized-change")

    assert "contract.authorization.missing" in codes(text, "L0", tmp_path)


def test_tech_debt_repay_requires_recurrence_guard(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = valid_v2_assessment("L0").replace("recurrence-guard: unit test", "recurrence-guard: none")

    assert "tech_debt.recurrence_guard.missing" in codes(text, "L0", tmp_path)


def test_l3_requires_multi_category_evidence(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "service.yaml").write_text("replicaCount: 2\n", encoding="utf-8")
    schema = tmp_path / "schema"
    schema.mkdir()
    (schema / "v1.sql").write_text("CREATE TABLE users;\n", encoding="utf-8")

    text = valid_v2_assessment("L3").replace("source: deployment", "source: code").replace("source: schema", "source: code")
    assert "evidence.l3.categories_insufficient" in codes(text, "L3", tmp_path)


def test_git_history_locator_format(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): pass\n", encoding="utf-8")
    
    text = valid_v2_assessment("L0").replace(
        "`src/system.py:1`", "`git-history:abc1234:src/system.py`"
    )
    # git-history: ref does not trigger fact.path.missing
    diags = validate(text, "L0", tmp_path)
    assert "fact.path.missing" not in {d.code for d in diags}


def test_inferred_only_evidence_fails_l2(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): pass\n", encoding="utf-8")

    text = valid_v2_assessment("L2").replace("strength: direct", "strength: inferred")
    diags = validate(text, "L2", tmp_path)
    assert "evidence.l2_l3.inferred_only" in {d.code for d in diags}


def test_at_risk_unresolved_contract_fails_approval(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): pass\n", encoding="utf-8")

    text = valid_v2_assessment("L0").replace("status: preserved", "status: at-risk | owner: team | resolution: none | blocking: true")
    diags = validate(text, "L0", tmp_path)
    assert "contract.at_risk.unresolved" in {d.code for d in diags}


def test_verification_proving_self_fails(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): pass\n", encoding="utf-8")

    text = valid_v2_assessment("L0").replace("proves: D-1", "proves: V-1")
    diags = validate(text, "L0", tmp_path)
    assert "verification.proves.invalid" in {d.code for d in diags}
