from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "routing" / "route-work"
SCRIPT_DIR = SKILL_ROOT / "scripts"
SCRIPT = SCRIPT_DIR / "route_work.py"
SCHEMA = json.loads(
    (SKILL_ROOT / "schemas" / "route-validation.schema.json").read_text(encoding="utf-8")
)
RESULT_FIELDS = {"valid", "workflow", "errors", "warnings", "route_handoff"}
FIXTURES = Path(__file__).parent / "fixtures"

sys.path.insert(0, str(SCRIPT_DIR))

from route_work import (  # noqa: E402
    SKILLS,
    AgentDecision,
    KnownFacts,
    canonical_path,
    handoff_destination,
    topological_order,
    unsafe_handoff_root,
    validate_workflow,
)


def load_cases(name: str) -> list[dict[str, object]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def decision_from_selection(selection: dict[str, object]) -> AgentDecision:
    raw_facts = selection.get("facts", {})
    assert isinstance(raw_facts, dict)
    selected = selection["selected_skills"]
    assert isinstance(selected, list)
    excluded = selection.get("excluded_skills", [])
    assert isinstance(excluded, list)
    capabilities = selection.get("required_capabilities", [])
    assert isinstance(capabilities, list)
    primary = selection.get("primary_skill")
    rationale = selection.get("rationale", "")
    intent = selection.get("intent", "")
    assert primary is None or isinstance(primary, str)
    assert isinstance(rationale, str)
    assert isinstance(intent, str)
    return AgentDecision(
        selected_skills=tuple(selected),
        primary_skill=primary,
        rationale=rationale,
        intent=intent,
        excluded_skills=tuple(excluded),
        required_capabilities=tuple(capabilities),
        known_facts=KnownFacts(**raw_facts),
    )


@pytest.mark.parametrize("case", load_cases("validation-cases.json"), ids=lambda case: case["id"])
def test_validation_cases_are_deterministic_and_exact(case: dict[str, object]) -> None:
    selection = case["selection"]
    assert isinstance(selection, dict)
    expected = case["expected"]
    assert isinstance(expected, dict)

    decision = decision_from_selection(selection)
    first = cast(dict[str, Any], validate_workflow(decision).to_dict())
    second = cast(dict[str, Any], validate_workflow(decision).to_dict())

    assert first == second
    assert set(first) == RESULT_FIELDS
    assert first["valid"] is expected["valid"]
    assert first["workflow"] == expected["workflow"]
    assert [error["code"] for error in first["errors"]] == expected["errors"]
    assert [warning["code"] for warning in first["warnings"]] == expected["warnings"]

    route_handoff = first["route_handoff"]
    assert isinstance(route_handoff, str)
    assert "# Route Handoff Guidance" in route_handoff
    assert "```mermaid" in route_handoff
    if expected["errors"]:
        assert "## Validation Errors" in route_handoff
    if expected["warnings"]:
        assert "## Validation Warnings" in route_handoff
    jsonschema.validate(first, SCHEMA)


def test_unknown_and_duplicate_selections_keep_agent_order_in_workflow() -> None:
    decision = AgentDecision(
        selected_skills=("audit-codebase", "bogus-skill", "audit-codebase"),
    )
    result = validate_workflow(decision)
    assert result.valid is False
    assert result.workflow == ("audit-codebase",)
    codes = [error.code for error in result.errors]
    assert codes == ["selection.unknown_skill", "selection.duplicate"]


def test_gate_is_never_satisfied_by_selection() -> None:
    pipeline = validate_workflow(
        AgentDecision(selected_skills=("plan-change", "implement-plan"))
    )
    assert pipeline.valid is False
    assert [error.code for error in pipeline.errors] == ["gate.approval_required"]

    approved = validate_workflow(
        AgentDecision(
            selected_skills=("plan-change", "implement-plan"),
            known_facts=KnownFacts(approved_plan_available=True),
        )
    )
    assert approved.valid is True
    assert approved.workflow == ("plan-change", "implement-plan")


def test_script_never_chooses_adds_or_removes_skills() -> None:
    decision = AgentDecision(selected_skills=("audit-codebase", "plan-change"))
    result = validate_workflow(decision)
    assert set(result.workflow) == {"audit-codebase", "plan-change"}

    invalid = validate_workflow(AgentDecision(selected_skills=("raise-issue",)))
    assert invalid.valid is False
    assert invalid.workflow == ("raise-issue",)


def test_intent_and_rationale_are_echoed_verbatim_never_analyzed() -> None:
    decision = AgentDecision(
        selected_skills=("audit-codebase",),
        intent="Fix the bug.",
        rationale="Audit evidence shows a real risk.",
    )
    result = cast(dict[str, Any], validate_workflow(decision).to_dict())
    route_handoff = result["route_handoff"]
    assert "Fix the bug." in route_handoff
    assert "Audit evidence shows a real risk." in route_handoff


def test_compact_handoff_is_the_default_and_detailed_is_opt_in() -> None:
    decision = AgentDecision(selected_skills=("plan-change", "implement-plan"))
    compact_handoff = validate_workflow(decision).route_handoff
    assert "## Workflow Route Diagram" in compact_handoff
    assert "Step-by-Step Execution Guidance" not in compact_handoff
    assert "Quick Start for New Users" not in compact_handoff

    detailed_handoff = validate_workflow(decision, detail="detailed").route_handoff
    assert "## Route Steps" in detailed_handoff
    assert "Step-by-Step Execution Guidance" in detailed_handoff
    assert "Quick Start for New Users" in detailed_handoff


def test_topological_order_detects_cycles() -> None:
    order, members = topological_order(
        ("a", "b"), (("a", "b"), ("b", "a"))
    )
    assert order is None
    assert set(members) == {"a", "b"}

    order, members = topological_order(("b", "a"), (("a", "b"),))
    assert order == ("a", "b")
    assert members == []


def _mermaid_nodes_and_edges(
    route_handoff: str,
) -> tuple[set[str], list[tuple[str, str, str]], dict[str, str]]:
    block = route_handoff.split("```mermaid\n", 1)[1].split("\n```", 1)[0]
    nodes: set[str] = set()
    edges: list[tuple[str, str, str]] = []
    declarations: dict[str, str] = {}

    def node_id(raw: str) -> str:
        for separator in ("[", "{", "("):
            raw = raw.split(separator, 1)[0]
        return raw.strip()

    def record(raw: str) -> str:
        identifier = node_id(raw)
        nodes.add(identifier)
        declarations.setdefault(identifier, raw.strip())
        return identifier

    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("flowchart"):
            continue
        if "-->" in line:
            left, right = line.split("-->", 1)
            target = record(right)
            source = left.strip()
            label = ""
            if ' -- "' in left:
                source, label = left.split(' -- "', 1)
                source = source.strip()
                label = label.rstrip('"')
            source = record(source)
            edges.append((source, target, label))
        else:
            record(line)
    return nodes, edges, declarations


def test_mermaid_decision_branches_are_complete() -> None:
    cases = [
        (
            ("audit-codebase", "raise-issue"),
            "Publish Issues?",
        ),
        (
            ("map-codebase", "plan-change", "implement-plan"),
            "Plan Approved?",
        ),
        (
            ("implement-plan",),
            "Verification Passed?",
        ),
    ]
    for selection, decision_label in cases:
        decision = AgentDecision(selected_skills=selection)
        route_handoff = validate_workflow(decision).route_handoff
        nodes, edges, declarations = _mermaid_nodes_and_edges(route_handoff)
        outgoing: dict[str, list[str]] = {}
        for source, target, _ in edges:
            outgoing.setdefault(source, []).append(target)
        decision_nodes = [node for node in nodes if node.startswith("Branch")]
        assert decision_nodes, route_handoff
        for node in decision_nodes:
            assert len(outgoing[node]) == 2, (node, outgoing[node], route_handoff)
            assert "?" in declarations[node], route_handoff
            assert len([edge for edge in edges if edge[1] == node]) == 1, (
                node,
                edges,
                route_handoff,
            )
        assert any(
            decision_label in declaration for declaration in declarations.values()
        ), route_handoff


def test_audit_publication_mermaid_routes_through_decision() -> None:
    decision = AgentDecision(selected_skills=("audit-codebase", "raise-issue"))
    route_handoff = validate_workflow(decision).route_handoff
    assert 'BranchPub1 -- "Yes" --> Step2["2. raise-issue' in route_handoff
    assert 'BranchPub1 -- "No" --> End' in route_handoff
    assert "Publish Issues?" in route_handoff


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_directory_link(link: Path, target: Path) -> bool:
    """Create a directory symlink, falling back to a Windows junction."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except OSError:
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0 and link.is_dir():
                    return True
            except OSError:
                pass
    return False


def test_cli_rejects_unsafe_handoff_destinations_without_writes(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    before = file_hashes(tmp_path)
    before.update(file_hashes(SKILL_ROOT))
    destinations = [
        ("--output-file", repository / "route-handoff.md"),
        ("--output-file", repository / "nested" / "route-handoff.md"),
        ("--output-file", SKILL_ROOT / "SKILL.md"),
        ("--output-file", SKILL_ROOT / "scripts" / "route_work.py"),
        ("--output-file", SKILL_ROOT / "nested" / "route-handoff.md"),
        ("--output-dir", repository),
        ("--output-dir", repository / "nested"),
        ("--output-dir", SKILL_ROOT),
    ]
    for flag, target in destinations:
        result = _run_cli(
            "--selected-skill",
            "audit-codebase",
            "--repo-root",
            str(repository),
            flag,
            str(target),
        )
        assert result.returncode == 2, (flag, target, result.stderr)
        assert result.stdout == ""
        assert "outside the repository" in result.stderr, (flag, target)
    after = file_hashes(tmp_path)
    after.update(file_hashes(SKILL_ROOT))
    assert after == before


def test_cli_rejects_symlinked_handoff_destinations_resolving_into_protected_roots(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    link_repo = tmp_path / "link-repo"
    link_skill = tmp_path / "link-skill"
    if not _make_directory_link(link_repo, repository) or not _make_directory_link(
        link_skill, SKILL_ROOT
    ):
        pytest.skip("directory symlinks are not supported on this platform")
    before = file_hashes(tmp_path)
    before.update(file_hashes(SKILL_ROOT))
    for link in (link_repo, link_skill):
        result = _run_cli(
            "--selected-skill",
            "audit-codebase",
            "--repo-root",
            str(repository),
            "--output-file",
            str(link / "route-handoff.md"),
        )
        assert result.returncode == 2, (link, result.stderr)
        assert "outside the repository" in result.stderr
    after = file_hashes(tmp_path)
    after.update(file_hashes(SKILL_ROOT))
    assert after == before


def test_handoff_destination_validator_accounts_for_symlinked_and_future_paths(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    protected = (canonical_path(repository), canonical_path(SKILL_ROOT))

    future_inside = handoff_destination(repository / "nested" / "route-handoff.md", None)
    assert future_inside is not None
    assert unsafe_handoff_root(future_inside, protected) == canonical_path(repository)

    future_skill = handoff_destination(SKILL_ROOT / "deep" / "route-handoff.md", None)
    assert future_skill is not None
    assert unsafe_handoff_root(future_skill, protected) == canonical_path(SKILL_ROOT)

    output_dir_inside = handoff_destination(None, repository / "nested")
    assert output_dir_inside is not None
    assert unsafe_handoff_root(output_dir_inside, protected) == canonical_path(repository)

    external = handoff_destination(tmp_path / "external" / "route-handoff.md", None)
    assert external is not None
    assert unsafe_handoff_root(external, protected) is None

    link = tmp_path / "link"
    if _make_directory_link(link, repository):
        via_link = handoff_destination(link / "route-handoff.md", None)
        assert via_link is not None
        assert unsafe_handoff_root(via_link, protected) == canonical_path(repository)


def test_cli_writes_handoff_outside_repository_and_skill(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    output_file = tmp_path / "external" / "route-handoff.md"
    result = _run_cli(
        "--selected-skill",
        "audit-codebase",
        "--repo-root",
        str(repository),
        "--output-file",
        str(output_file),
    )
    assert result.returncode == 0, result.stderr
    assert output_file.is_file()
    assert "# Route Handoff Guidance" in output_file.read_text(encoding="utf-8")

    output_dir = tmp_path / "external-dir"
    output_dir.mkdir()
    result = _run_cli(
        "--selected-skill",
        "audit-codebase",
        "--repo-root",
        str(repository),
        "--output-dir",
        str(output_dir),
    )
    assert result.returncode == 0, result.stderr
    assert (output_dir / "route-handoff.md").is_file()


def test_cli_rejects_handoff_output_inside_repository(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--selected-skill",
            "audit-codebase",
            "--repo-root",
            str(repository),
            "--output-dir",
            str(repository / "docs"),
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "outside the repository" in result.stderr


def test_cli_detailed_handoff_writes_file_on_request(tmp_path: Path) -> None:
    output_file = tmp_path / "route-handoff.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--selected-skill",
            "ideate",
            "--selected-skill",
            "design-codebase",
            "--selected-skill",
            "plan-change",
            "--handoff",
            "detailed",
            "--output-file",
            str(output_file),
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output_file.is_file()
    text = output_file.read_text(encoding="utf-8")
    assert "# Route Handoff Guidance" in text
    assert "```mermaid" in text
    assert "ideate" in text
    assert "design-codebase" in text
    assert "plan-change" in text
    assert "Step-by-Step Execution Guidance" in text
    assert "Quick Start for New Users" in text


def test_cli_pipeline_semantics_satisfy_artifacts() -> None:
    result = _run_cli(
        "--selected-skill",
        "audit-codebase",
        "--selected-skill",
        "raise-issue",
    )
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)
    assert decision["valid"] is True
    assert decision["workflow"] == ["audit-codebase", "raise-issue"]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--selected-skill", "plan-change", "--repo-root", "missing"], "repository root does not exist"),
        (["--repo-root", "."], "at least one --selected-skill is required"),
        (
            ["--selected-skill", "audit-codebase", "--output-file", "route-handoff.md"],
            "outside the repository",
        ),
    ],
)
def test_cli_invalid_inputs_fail_without_a_decision(
    arguments: list[str],
    message: str,
) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr


def test_cli_rejects_nonexistent_output_directory(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    result = _run_cli(
        "--selected-skill",
        "audit-codebase",
        "--repo-root",
        str(repository),
        "--output-dir",
        str(tmp_path / "missing-dir"),
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "output directory does not exist" in result.stderr


def test_routing_policy_documents_every_router_skill() -> None:
    policy = (SKILL_ROOT / "references" / "routing-policy.md").read_text(encoding="utf-8")
    undocumented = [skill for skill in SKILLS if f"`{skill}`" not in policy]
    assert undocumented == []


def test_cli_echoes_selection_without_writing(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    before = file_hashes(tmp_path)

    result = _run_cli(
        "--selected-skill",
        "audit-codebase",
        "--selected-skill",
        "raise-issue",
        "--primary-skill",
        "audit-codebase",
        "--intent",
        "Audit the repository and publish the issues.",
        "--rationale",
        "Evidence shows confirmed risks.",
        "--repo-root",
        str(repository),
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    decision = json.loads(result.stdout)
    assert decision["valid"] is True
    assert decision["workflow"] == ["audit-codebase", "raise-issue"]
    assert "Audit the repository and publish the issues." in decision["route_handoff"]
    assert "Evidence shows confirmed risks." in decision["route_handoff"]
    jsonschema.validate(decision, SCHEMA)
    assert file_hashes(tmp_path) == before
