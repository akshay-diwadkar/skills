import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assessment_contract import load_contract, marker  # noqa: E402
from check_assessment import validate  # noqa: E402


def assessment(level: str) -> str:
    contract = load_contract()
    alternatives = [
        "- O-1: level: L0 | selected: no | concepts: none | argument-for: smallest | argument-against: pressure remains | revisit: pressure disappears",
        "- O-2: level: L1 | selected: yes | concepts: one module | argument-for: local | argument-against: limited | revisit: boundary changes",
    ]
    if contract["levels"][level]["minimum_alternatives"] == 3:
        alternatives.append(
            "- O-3: level: L2 | selected: no | concepts: one port | argument-for: contains volatility | argument-against: added indirection | revisit: multiple consumers"
        )
    pattern = ""
    if contract["levels"][level]["requires_pattern_gate"]:
        questions = ", ".join(f"Q{number}=yes" for number in range(1, 15))
        pattern = f"\n- G-1: pattern: Adapter | scope: introduced | result: admit | questions: {questions} | evidence: F-1, P-1"

    sections = [
        f"# Select the Minimum Safe {level} Design",
        marker(level),
        "",
        "## Scope and Protected Contracts",
        "- C-1: status: preserved | contract: public command output | authorization: none",
        "- H-1: status: assessment-only | next: finish assessment",
        "- A-1: status: none | impact: none | verification: none",
        "",
        "## Evidence and Current State",
        "- F-1: `src/system.py:1` | anchor: `current` | observation: The current function owns the behavior.",
        "- Current flow: input -> current -> output.",
        "",
        "## Design Pressures and Classification",
        "- P-1: rank: 1 | evidence: F-1 | pressure: The scoped behavior has a verified change cost.",
        f"- D-1: level: {level} | selected: minimum safe design | because: F-1, P-1 | rejected: a stronger design adds cost.",
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
    return "\n".join(sections) + "\n"


def codes(text: str, level: str, repo_root: Path) -> set[str]:
    return {item.code for item in validate(text, level, repo_root)}


def test_valid_assessments_pass_every_level(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    for level in ("L0", "L1", "L2", "L3"):
        assert validate(assessment(level), level, tmp_path) == []


def test_missing_citation_is_rejected(tmp_path: Path) -> None:
    text = assessment("L0")

    assert "fact.path.missing" in codes(text, "L0", tmp_path)


def test_declared_level_must_match_classification(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = assessment("L2").replace("- D-1: level: L2", "- D-1: level: L1")

    assert "decision.level.mismatch" in codes(text, "L2", tmp_path)


def test_authorized_contract_change_requires_named_authorization(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = assessment("L0").replace("status: preserved", "status: authorized-change")

    assert "contract.authorization.missing" in codes(text, "L0", tmp_path)


def test_l1_requires_three_alternatives(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = assessment("L1").replace(
        "- O-3: level: L2 | selected: no | concepts: one port | argument-for: contains volatility | argument-against: added indirection | revisit: multiple consumers\n",
        "",
    )

    assert "alternatives.count" in codes(text, "L1", tmp_path)


def test_l2_requires_scoped_pattern_and_executable_rollback(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = assessment("L2").replace("scope: introduced", "scope: repository-wide").replace(
        " | rollback action: restore direct caller", " | reversal: restore direct caller"
    )

    findings = codes(text, "L2", tmp_path)
    assert "pattern.required" in findings
    assert "migration.format" in findings


def test_l3_requires_every_evolution_field(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n", encoding="utf-8")
    text = assessment("L3").replace("- Reconciliation: explicitly defined.\n", "")

    assert "evolution.field.missing" in codes(text, "L3", tmp_path)
